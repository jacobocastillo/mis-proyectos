"""
Habit history service module.

Responsibility:
- Build event-level habit history for the authenticated user.
"""

import json
from datetime import date as date_type, datetime, time, timezone
from typing import Any

from app.models.checkin import CheckIn
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog

_LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo or timezone.utc
_EVENT_PRIORITY = {"completion": 0, "validation": 1}
_VALID_STATUSES = {"completed", "approved", "rejected", "pending"}
DEFAULT_HISTORY_LIMIT = 20
MAX_HISTORY_LIMIT = 100


class HistoryQueryError(ValueError):
    """Raised when history query parameters are invalid."""


def _parse_evidence(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_local_date(value: datetime | None) -> date_type | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_LOCAL_TIMEZONE).date()


def _date_to_datetime(value: date_type) -> datetime:
    return datetime.combine(value, time.min, tzinfo=_LOCAL_TIMEZONE)


def _effective_validation_type(user_habit: UserHabit, validation: ValidationLog | None = None) -> str | None:
    if validation is not None:
        evidence = _parse_evidence(validation.evidencia)
        evidence_type = evidence.get("validation_type")
        if isinstance(evidence_type, str) and evidence_type:
            return evidence_type
        return validation.tipo_validacion
    return user_habit.tipo_validacion or user_habit.habit.tipo_validacion


def _habit_metadata(user_habit: UserHabit) -> dict[str, Any]:
    catalog = user_habit.habit
    category = catalog.category if catalog else None
    return {
        "habit_id": user_habit.id,
        "catalog_habit_id": catalog.id if catalog else None,
        "habit_name": user_habit.nombre_personalizado or (catalog.nombre if catalog else None),
        "category_id": catalog.categoria_id if catalog else None,
        "category_name": category.nombre if category else None,
    }


def _validation_metadata(validation: ValidationLog | None) -> dict[str, Any]:
    if validation is None:
        return {
            "validation_id": None,
            "reason": None,
            "confidence": None,
        }

    evidence = _parse_evidence(validation.evidencia)
    confidence = evidence.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = None
    reason = evidence.get("reason")

    return {
        "validation_id": validation.id,
        "reason": reason if isinstance(reason, str) else None,
        "confidence": confidence,
    }


def _completion_event(
    checkin: CheckIn,
    validation: ValidationLog | None,
    xp_awarded: int | None = None,
) -> dict[str, Any]:
    user_habit = checkin.user_habit
    occurred_at = _date_to_datetime(checkin.fecha)
    return {
        "id": f"checkin:{checkin.id}",
        "source": "completion",
        **_habit_metadata(user_habit),
        "event_date": checkin.fecha.isoformat(),
        "occurred_at": occurred_at.isoformat(),
        "status": "completed",
        "validation_type": _effective_validation_type(user_habit, validation),
        "xp_awarded": int(checkin.xp_ganado or xp_awarded or 0),
        "checkin_id": checkin.id,
        **_validation_metadata(validation),
        "_sort_at": occurred_at,
        "_sort_priority": _EVENT_PRIORITY["completion"],
        "_sort_id": checkin.id,
    }


def _validation_event(validation: ValidationLog) -> dict[str, Any]:
    user_habit = validation.user_habit
    occurred_at = validation.fecha
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    local_date = _to_local_date(validation.fecha)
    evidence = _parse_evidence(validation.evidencia)
    xp_awarded = evidence.get("xp_awarded")
    if not isinstance(xp_awarded, int):
        xp_awarded = 0

    return {
        "id": f"validation:{validation.id}",
        "source": "validation",
        **_habit_metadata(user_habit),
        "event_date": local_date.isoformat() if local_date else None,
        "occurred_at": occurred_at.isoformat(),
        "status": validation.status,
        "validation_type": _effective_validation_type(user_habit, validation),
        "xp_awarded": xp_awarded,
        "checkin_id": None,
        **_validation_metadata(validation),
        "_sort_at": occurred_at,
        "_sort_priority": _EVENT_PRIORITY["validation"],
        "_sort_id": validation.id,
    }


def _public_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in event.items()
        if not key.startswith("_")
    }


def _normalize_limit(value: object) -> int:
    if value in (None, ""):
        return DEFAULT_HISTORY_LIMIT
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise HistoryQueryError("limit must be an integer.")
    if limit < 1:
        raise HistoryQueryError("limit must be greater than zero.")
    return min(limit, MAX_HISTORY_LIMIT)


def _normalize_cursor(value: object) -> int:
    if value in (None, ""):
        return 0
    try:
        cursor = int(value)
    except (TypeError, ValueError):
        raise HistoryQueryError("cursor must be an integer.")
    if cursor < 0:
        raise HistoryQueryError("cursor must be zero or greater.")
    return cursor


def _normalize_date(value: object, field_name: str) -> date_type | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise HistoryQueryError(f"{field_name} must use YYYY-MM-DD format.")
    try:
        return date_type.fromisoformat(value)
    except ValueError:
        raise HistoryQueryError(f"{field_name} must use YYYY-MM-DD format.")


def _normalize_habit_id(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        habit_id = int(value)
    except (TypeError, ValueError):
        raise HistoryQueryError("habit_id must be an integer.")
    if habit_id <= 0:
        raise HistoryQueryError("habit_id must be greater than zero.")
    return habit_id


def _normalize_status(value: object) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or value not in _VALID_STATUSES:
        raise HistoryQueryError("status must be one of completed, approved, rejected, pending.")
    return value


def get_habit_history(user_id: int, params: dict[str, object]) -> dict[str, object]:
    """Return paginated event-level habit history for one user."""
    limit = _normalize_limit(params.get("limit"))
    cursor = _normalize_cursor(params.get("cursor"))
    from_date = _normalize_date(params.get("from"), "from")
    to_date = _normalize_date(params.get("to"), "to")
    habit_id = _normalize_habit_id(params.get("habit_id"))
    status = _normalize_status(params.get("status"))

    if from_date and to_date and from_date > to_date:
        raise HistoryQueryError("from must be before or equal to to.")

    user_habits = UserHabit.query.filter_by(usuario_id=user_id).all()
    if habit_id is not None:
        user_habits = [user_habit for user_habit in user_habits if user_habit.id == habit_id]

    user_habit_ids = [user_habit.id for user_habit in user_habits]
    if not user_habit_ids:
        return {"items": [], "next_cursor": None}

    checkins = CheckIn.query.filter(CheckIn.habitousuario_id.in_(user_habit_ids)).all()
    validations = ValidationLog.query.filter(ValidationLog.habitousuario_id.in_(user_habit_ids)).all()
    xp_logs = XpLog.query.filter(
        XpLog.user_id == user_id,
        XpLog.habit_id.in_(user_habit_ids),
        XpLog.event_date.isnot(None),
        XpLog.cantidad > 0,
    ).all()

    xp_by_habit_date: dict[tuple[int, date_type], int] = {}
    for log in xp_logs:
        xp_by_habit_date[(log.habit_id, log.event_date)] = (
            xp_by_habit_date.get((log.habit_id, log.event_date), 0) + int(log.cantidad or 0)
        )

    validations_by_habit_date: dict[tuple[int, date_type], list[ValidationLog]] = {}
    for validation in validations:
        local_date = _to_local_date(validation.fecha)
        if local_date is None:
            continue
        validations_by_habit_date.setdefault((validation.habitousuario_id, local_date), []).append(validation)

    matched_validation_ids: set[int] = set()
    events: list[dict[str, Any]] = []

    for checkin in checkins:
        matching_validations = validations_by_habit_date.get((checkin.habitousuario_id, checkin.fecha), [])
        matching_validations.sort(key=lambda validation: validation.fecha, reverse=True)
        matched_validation = matching_validations[0] if matching_validations else None
        if matched_validation is not None:
            matched_validation_ids.add(matched_validation.id)
        xp_awarded = xp_by_habit_date.get((checkin.habitousuario_id, checkin.fecha))
        events.append(_completion_event(checkin, matched_validation, xp_awarded))

    for validation in validations:
        if validation.id not in matched_validation_ids:
            events.append(_validation_event(validation))

    def in_range(event: dict[str, Any]) -> bool:
        event_date_value = event.get("event_date")
        if not isinstance(event_date_value, str):
            return False
        event_date = date_type.fromisoformat(event_date_value)
        if from_date and event_date < from_date:
            return False
        if to_date and event_date > to_date:
            return False
        if status and event["status"] != status:
            return False
        return True

    filtered_events = [event for event in events if in_range(event)]
    filtered_events.sort(
        key=lambda event: (event["_sort_at"], -event["_sort_priority"], event["_sort_id"]),
        reverse=True,
    )

    page = filtered_events[cursor:cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(filtered_events) else None

    return {
        "items": [_public_event(event) for event in page],
        "next_cursor": str(next_cursor) if next_cursor is not None else None,
    }
