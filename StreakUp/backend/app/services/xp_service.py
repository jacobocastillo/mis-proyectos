"""
XP service module.

Responsibility:
- Host XP-related domain use cases.
- Keep user XP aggregates consistent with xp_logs.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date as date_type
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func

from app.extensions import db
from app.models.habit import Habit
from app.models.user import User
from app.models.xp_log import XpLog

if TYPE_CHECKING:
    from app.models.user_habit import UserHabit

XP_PER_LEVEL = 250
_XP_REASON_ALIASES = {
    "checkin": "checkin",
    "checkin_undo": "checkin_undo",
    "validation": "validation",
    "pomodoro": "pomodoro",
    "pomodoro_bonus": "pomodoro_bonus",
    "uncheck": "checkin_undo",
    "revocation": "checkin_undo",
}


def normalize_xp_reason(reason: str) -> str:
    """Return the canonical persisted reason for an XP log entry."""
    normalized = reason.strip().lower()
    canonical = _XP_REASON_ALIASES.get(normalized)
    if canonical is None:
        raise ValueError(f"Unsupported XP reason: {reason}")
    return canonical


def calculate_level_state(total_xp: int) -> tuple[int, int]:
    """Return the level and in-level XP for a total XP amount."""
    bounded_total = max(0, int(total_xp))
    level = (bounded_total // XP_PER_LEVEL) + 1
    xp_in_level = bounded_total % XP_PER_LEVEL
    return level, xp_in_level


def recompute_user_xp(user_id: int, *, commit: bool = True) -> User:
    """Rebuild a user's aggregate XP fields from xp_logs."""
    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")

    total_xp = (
        db.session.query(func.coalesce(func.sum(XpLog.cantidad), 0))
        .filter(XpLog.user_id == user_id)
        .scalar()
    )
    user.total_xp = max(0, int(total_xp or 0))
    user.level, user.xp_in_level = calculate_level_state(user.total_xp)

    if commit:
        db.session.commit()
    else:
        db.session.flush()

    return user


def recompute_all_users_xp(user_ids: Iterable[int] | None = None, *, commit: bool = True) -> int:
    """Rebuild aggregate XP fields for every selected user."""
    query = db.session.query(User.id).order_by(User.id)
    if user_ids is not None:
        ids = [int(user_id) for user_id in user_ids]
        if not ids:
            return 0
        query = query.filter(User.id.in_(ids))

    selected_ids = [row[0] for row in query.all()]
    for user_id in selected_ids:
        recompute_user_xp(user_id, commit=False)

    if commit:
        db.session.commit()

    return len(selected_ids)


def calculate_habit_xp(habit: Habit, duration_minutes: float | None = None) -> int:
    """Return raw XP from formula before daily cap.

    Time habits: min(max_xp_per_day, xp_base + minutes * xp_rate) when cap > 0.
    Non-time habits: xp_base.
    """
    is_time = habit.tipo_validacion in {"tiempo", "time"} or getattr(habit, "meta_type", "") == "time"
    if is_time:
        minutes = float(duration_minutes or 0)
        raw = int(habit.xp_base) + int(minutes * int(habit.xp_rate or 0))
        cap = int(habit.max_xp_per_day or 0)
        return min(cap, raw) if cap > 0 else raw
    return int(habit.xp_base)


def get_daily_xp_used(user_id: int, habit_id: int, event_date: date_type) -> int:
    """Sum already-awarded habit XP for user+habit on event_date (for cap auditing)."""
    total = (
        db.session.query(func.coalesce(func.sum(XpLog.cantidad), 0))
        .filter(
            XpLog.user_id == user_id,
            XpLog.habit_id == habit_id,
            XpLog.event_date == event_date,
            XpLog.source_event == "habit",
            XpLog.cantidad > 0,
        )
        .scalar()
    )
    return max(0, int(total or 0))


def award_xp(
    user_id: int,
    amount: int,
    reason: str = "validation",
    *,
    habit_id: int | None = None,
    event_date: date_type | None = None,
    source_event: str = "habit",
    cap_hit: bool = False,
    calculated_xp: int | None = None,
    commit: bool = True,
) -> None:
    """Award XP to a user and handle leveling up."""
    if amount < 0:
        raise ValueError("XP amount must be non-negative.")

    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found.")

    canonical_reason = normalize_xp_reason(reason)

    user.total_xp += amount
    user.level, user.xp_in_level = calculate_level_state(user.total_xp)

    log = XpLog(
        user_id=user_id,
        cantidad=amount,
        razon=canonical_reason,
        habit_id=habit_id,
        event_date=event_date,
        source_event=source_event,
        cap_hit=cap_hit,
        calculated_xp=calculated_xp if calculated_xp is not None else amount,
    )
    db.session.add(log)

    if commit:
        db.session.commit()
    else:
        db.session.flush()


def revoke_xp(user_id: int, amount: int, reason: str = "checkin_undo", *, commit: bool = True) -> None:
    """Revoke XP from a user and handle leveling down."""
    if amount < 0:
        raise ValueError("XP amount must be non-negative.")

    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found.")

    canonical_reason = normalize_xp_reason(reason)

    user.total_xp = max(0, user.total_xp - amount)
    user.level, user.xp_in_level = calculate_level_state(user.total_xp)

    log = XpLog(
        user_id=user_id,
        cantidad=-amount,
        razon=canonical_reason,
        habit_id=None,
        event_date=None,
        source_event="habit",
        cap_hit=False,
        calculated_xp=-amount,
    )
    db.session.add(log)

    if commit:
        db.session.commit()
    else:
        db.session.flush()


def award_habit_xp(
    user_id: int,
    user_habit: "UserHabit",
    event_date: date_type,
    duration_minutes: float | None = None,
    reason: str = "validation",
    *,
    commit: bool = True,
) -> int:
    """Calculate, enforce daily cap, and award XP for one habit completion.

    Returns awarded amount (0 if cap reached or habit has no XP).
    """
    habit = user_habit.habit
    if habit is None:
        return 0

    calculated = calculate_habit_xp(habit, duration_minutes)
    daily_cap = int(habit.max_xp_per_day or 0)

    if daily_cap > 0:
        used = get_daily_xp_used(user_id, user_habit.id, event_date)
        remaining = max(0, daily_cap - used)
        awarded = min(calculated, remaining)
        cap_hit = awarded == 0 and calculated > 0
    else:
        awarded = calculated
        cap_hit = False

    if awarded == 0:
        if cap_hit:
            log = XpLog(
                user_id=user_id,
                cantidad=0,
                razon=normalize_xp_reason(reason),
                habit_id=user_habit.id,
                event_date=event_date,
                source_event="habit",
                cap_hit=True,
                calculated_xp=calculated,
            )
            db.session.add(log)
            db.session.flush()
        return 0

    award_xp(
        user_id,
        awarded,
        reason,
        habit_id=user_habit.id,
        event_date=event_date,
        source_event="habit",
        cap_hit=False,
        calculated_xp=calculated,
        commit=commit,
    )
    return awarded


def get_user_xp(user_id: int) -> dict:
    """Get current XP, level, and progress for a user."""
    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")

    return {
        "total_xp": user.total_xp,
        "level": user.level,
        "xp_in_level": user.xp_in_level,
        "xp_for_next_level": XP_PER_LEVEL,
        "progress_pct": user.xp_progress_pct,
    }


def get_xp_history(user_id: int, days: int = 7) -> list[dict]:
    """Return XP earned per day for the last N days."""
    today = date_type.today()
    start = today - timedelta(days=days - 1)

    rows = (
        db.session.query(
            func.date(XpLog.fecha).label("day"),
            func.sum(XpLog.cantidad).label("total"),
        )
        .filter(
            XpLog.user_id == user_id,
            XpLog.cantidad > 0,
            func.date(XpLog.fecha) >= start.isoformat(),
            func.date(XpLog.fecha) <= today.isoformat(),
        )
        .group_by(func.date(XpLog.fecha))
        .all()
    )

    xp_map: dict[str, int] = {row.day: row.total for row in rows}

    day_names_es = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        result.append({
            "date": key,
            "label": day_names_es[d.weekday()],
            "xp": xp_map.get(key, 0),
        })

    return result
