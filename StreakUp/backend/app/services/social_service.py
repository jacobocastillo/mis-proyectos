"""
Social sharing service.

Responsibility:
- Manage invite-only shared streak groups.
- Calculate privacy-safe shared progress from explicit memberships.
- Lazily evaluate duel outcomes (lost / winner) on each group read.
"""

from __future__ import annotations

import secrets
from datetime import date as date_type, datetime, timedelta, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Habit
from app.models.social import SharedStreakGroup, SharedStreakMembership
from app.models.user_habit import UserHabit

INVITE_CODE_LENGTH = 10
MAX_GROUP_NAME_LENGTH = 120
MAX_PARTICIPANTS = 3


class SocialPermissionError(PermissionError):
    """Raised when a user is not allowed to access a social resource."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_name(name: object) -> str:
    if not isinstance(name, str):
        raise ValueError("name is required.")
    normalized = " ".join(name.strip().split())
    if len(normalized) < 3:
        raise ValueError("name must be at least 3 characters.")
    if len(normalized) > MAX_GROUP_NAME_LENGTH:
        raise ValueError(f"name must be {MAX_GROUP_NAME_LENGTH} characters or fewer.")
    return normalized


def _normalize_invite_code(invite_code: object) -> str:
    if not isinstance(invite_code, str):
        raise ValueError("invite_code is required.")
    normalized = invite_code.strip().upper()
    if not normalized:
        raise ValueError("invite_code is required.")
    return normalized


def _generate_invite_code() -> str:
    for _ in range(10):
        code = secrets.token_urlsafe(12).replace("-", "").replace("_", "").upper()[:INVITE_CODE_LENGTH]
        if not SharedStreakGroup.query.filter_by(invite_code=code).first():
            return code
    raise RuntimeError("Could not generate a unique invite code.")


def _active_memberships(group_id: int) -> list[SharedStreakMembership]:
    """Active (still-competing) memberships — used for shared streak calculation."""
    return (
        SharedStreakMembership.query.filter_by(
            group_id=group_id,
            status="active",
            share_progress=True,
        )
        .order_by(SharedStreakMembership.joined_at.asc(), SharedStreakMembership.id.asc())
        .all()
    )


def _display_memberships(group_id: int) -> list[SharedStreakMembership]:
    """All non-left memberships — used for card display and member list."""
    return (
        SharedStreakMembership.query.filter(
            SharedStreakMembership.group_id == group_id,
            SharedStreakMembership.status.in_(["active", "lost", "winner"]),
        )
        .order_by(SharedStreakMembership.joined_at.asc(), SharedStreakMembership.id.asc())
        .all()
    )


def _require_active_membership(user_id: int, group_id: int) -> SharedStreakMembership:
    """Require caller to be an active member (not lost/winner/left)."""
    membership = SharedStreakMembership.query.filter_by(
        group_id=group_id,
        user_id=user_id,
        status="active",
    ).first()
    if membership is None:
        raise SocialPermissionError("You are not a member of this shared streak.")
    return membership


def _require_any_duel_membership(user_id: int, group_id: int) -> SharedStreakMembership:
    """Require caller to have been a duel participant (active, lost, or winner)."""
    membership = SharedStreakMembership.query.filter(
        SharedStreakMembership.group_id == group_id,
        SharedStreakMembership.user_id == user_id,
        SharedStreakMembership.status.in_(["active", "lost", "winner"]),
    ).first()
    if membership is None:
        raise SocialPermissionError("You are not a member of this shared streak.")
    return membership


def _validate_user_habit_ownership(user_id: int, user_habit_id: int) -> UserHabit:
    """Return the UserHabit if it belongs to user_id and is active, else raise."""
    user_habit = db.session.get(UserHabit, user_habit_id)
    if user_habit is None or not user_habit.activo:
        raise ValueError("Habit not found or inactive.")
    if user_habit.usuario_id != user_id:
        raise SocialPermissionError("This habit does not belong to you.")
    return user_habit


def _get_or_create_user_habit_for_catalog(user_id: int, habit_id: int) -> UserHabit:
    """Return existing active UserHabit for the catalog habit, or create one."""
    existing = UserHabit.query.filter_by(
        usuario_id=user_id,
        habito_id=habit_id,
        activo=True,
    ).first()
    if existing is not None:
        return existing

    habit = db.session.get(Habit, habit_id)
    if habit is None:
        raise ValueError("Catalog habit not found.")

    today = date_type.today()
    user_habit = UserHabit(
        usuario_id=user_id,
        habito_id=habit_id,
        fecha_inicio=today,
        activo=True,
    )
    db.session.add(user_habit)
    db.session.flush()
    return user_habit


# ---------------------------------------------------------------------------
# Completion helpers
# ---------------------------------------------------------------------------

def _member_completed_on_date(
    membership: SharedStreakMembership, target_date: date_type
) -> bool:
    if membership.user_habit_id is None:
        return False
    return (
        CheckIn.query.filter_by(
            habitousuario_id=membership.user_habit_id,
            fecha=target_date,
            completado=True,
        ).first()
        is not None
    )


def _count_member_completed_days(
    membership: SharedStreakMembership,
    start: date_type,
    end: date_type,
) -> int:
    if membership.user_habit_id is None or start > end:
        return 0
    return CheckIn.query.filter(
        CheckIn.habitousuario_id == membership.user_habit_id,
        CheckIn.fecha >= start,
        CheckIn.fecha <= end,
        CheckIn.completado == True,
    ).count()


def _completed_user_ids_for_date(
    memberships: list[SharedStreakMembership], target_date: date_type
) -> set[int]:
    if not memberships:
        return set()

    completed: set[int] = set()
    for membership in memberships:
        user_habit_id = membership.user_habit_id
        if user_habit_id is not None:
            if CheckIn.query.filter_by(
                habitousuario_id=user_habit_id,
                fecha=target_date,
                completado=True,
            ).first():
                completed.add(membership.user_id)
        else:
            row = (
                db.session.query(UserHabit.usuario_id)
                .join(CheckIn, CheckIn.habitousuario_id == UserHabit.id)
                .filter(
                    UserHabit.usuario_id == membership.user_id,
                    CheckIn.fecha == target_date,
                    CheckIn.completado == True,
                )
                .first()
            )
            if row is not None:
                completed.add(membership.user_id)

    return completed


def _first_completion_date(memberships: list[SharedStreakMembership]) -> date_type | None:
    if not memberships:
        return None

    earliest: date_type | None = None
    for membership in memberships:
        user_habit_id = membership.user_habit_id
        if user_habit_id is not None:
            result = (
                db.session.query(func.min(CheckIn.fecha))
                .filter(
                    CheckIn.habitousuario_id == user_habit_id,
                    CheckIn.completado == True,
                )
                .scalar()
            )
        else:
            result = (
                db.session.query(func.min(CheckIn.fecha))
                .join(UserHabit, CheckIn.habitousuario_id == UserHabit.id)
                .filter(
                    UserHabit.usuario_id == membership.user_id,
                    CheckIn.completado == True,
                )
                .scalar()
            )

        if result is not None:
            if earliest is None or result < earliest:
                earliest = result

    return earliest


# ---------------------------------------------------------------------------
# Duel evaluation (lazy — called on every group read)
# ---------------------------------------------------------------------------

def _finalize_fixed_duration(
    group: SharedStreakGroup,
    participants: list[SharedStreakMembership],
) -> None:
    """Close a fixed-duration group and crown winner(s) by completed_days."""
    if not participants:
        group.group_status = "finished"
        group.active = False
        return

    max_days = max((m.completed_days or 0) for m in participants)
    winners = [m for m in participants if (m.completed_days or 0) == max_days]

    if len(winners) == 1:
        winners[0].status = "winner"
        group.winner_user_id = winners[0].user_id
    else:
        # Tie: all tied members become winners; no single winner on the group
        for w in winners:
            w.status = "winner"
        group.winner_user_id = None

    group.group_status = "finished"
    group.active = False


def _evaluate_duel_outcomes(group: SharedStreakGroup) -> None:
    """
    Lazy evaluation of duel outcomes. Called on every group read.
    Idempotent — safe to call repeatedly.

    - Marks members 'lost' for each past day they missed their bound habit.
    - Refreshes completed_days for all non-left participants.
    - In unlimited mode: last active standing becomes winner.
    - In fixed-duration mode: finalizes when today > end_date.
    """
    if group.group_status != "active":
        return

    today = date_type.today()
    start = group.start_date
    if start is None:
        return

    yesterday = today - timedelta(days=1)

    # Mark members lost for past days they missed
    if start <= yesterday:
        active_in_duel = [m for m in group.memberships if m.status == "active"]
        day = start
        while day <= yesterday:
            for membership in list(active_in_duel):
                if not _member_completed_on_date(membership, day):
                    membership.status = "lost"
                    membership.lost_at = _now()
                    active_in_duel.remove(membership)
            day += timedelta(days=1)

    # Refresh completed_days for all non-left participants up to yesterday (or end_date)
    count_end = yesterday
    if group.end_date is not None:
        count_end = min(yesterday, group.end_date)

    if count_end >= start:
        for membership in group.memberships:
            if membership.status != "left":
                membership.completed_days = _count_member_completed_days(
                    membership, start, count_end
                )

    # Check winner conditions
    remaining_active = [m for m in group.memberships if m.status == "active"]
    participants = [m for m in group.memberships if m.status != "left"]

    if group.duration_days is None:
        # Unlimited mode: last active standing wins
        if len(participants) >= 2 and len(remaining_active) == 1:
            winner = remaining_active[0]
            winner.status = "winner"
            group.winner_user_id = winner.user_id
            group.group_status = "finished"
            group.active = False
        elif len(remaining_active) == 0 and participants:
            # All lost — no winner
            group.group_status = "finished"
            group.active = False
    else:
        # Fixed-duration mode: finalize when challenge period ends
        if group.end_date is not None and today > group.end_date:
            _finalize_fixed_duration(group, participants)

    db.session.flush()


# ---------------------------------------------------------------------------
# Streak calculation
# ---------------------------------------------------------------------------

def _shared_streak(
    memberships: list[SharedStreakMembership],
    today: date_type,
    start_date: date_type | None = None,
) -> dict:
    member_count = len(memberships)
    today_completed_ids = _completed_user_ids_for_date(memberships, today)
    today_completed = len(today_completed_ids)

    if member_count < 2:
        return {
            "current": 0,
            "today_completed_members": today_completed,
            "required_members": member_count,
            "ready": False,
        }

    # Streak is bounded by start_date — no historical check-ins count before the challenge
    first_date = start_date if start_date is not None else _first_completion_date(memberships)
    current = 0
    cursor = today
    while first_date is not None and cursor >= first_date:
        if len(_completed_user_ids_for_date(memberships, cursor)) != member_count:
            break
        current += 1
        cursor -= timedelta(days=1)

    return {
        "current": current,
        "today_completed_members": today_completed,
        "required_members": member_count,
        "ready": member_count >= 2,
    }


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def _member_payload(membership: SharedStreakMembership, today: date_type) -> dict:
    completed_today = bool(_completed_user_ids_for_date([membership], today))
    username = membership.user.username if membership.user is not None else None
    return {
        "user_id": membership.user_id,
        "username": username,
        "status": membership.status,
        "share_progress": bool(membership.share_progress),
        "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
        "lost_at": membership.lost_at.isoformat() if membership.lost_at else None,
        "completed_days": membership.completed_days or 0,
        "today_completed": completed_today,
    }


def _group_payload(group: SharedStreakGroup, *, include_members: bool = False) -> dict:
    today = date_type.today()

    # For streak: only still-active members contribute
    active_memberships = _active_memberships(group.id)
    # For display: all participants who haven't left
    display_memberships = _display_memberships(group.id)

    payload = {
        "id": group.id,
        "name": group.name,
        "invite_code": group.invite_code,
        "owner_user_id": group.owner_user_id,
        "habit_id": group.habit_id,
        "habit_name": group.habit.nombre if group.habit else None,
        "max_participants": group.max_participants,
        "start_date": group.start_date.isoformat() if group.start_date else None,
        "duration_days": group.duration_days,
        "end_date": group.end_date.isoformat() if group.end_date else None,
        "group_status": group.group_status,
        "winner_user_id": group.winner_user_id,
        "member_count": len(display_memberships),
        "shared_streak": _shared_streak(active_memberships, today, group.start_date),
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }
    if include_members:
        payload["members"] = [_member_payload(m, today) for m in display_memberships]
    return payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_group(
    user_id: int,
    name: object,
    user_habit_id: int | None = None,
    duration_days: int | None = None,
) -> dict:
    if user_habit_id is None:
        raise ValueError("user_habit_id is required.")
    if duration_days is not None:
        if not isinstance(duration_days, int) or duration_days <= 0:
            raise ValueError("duration_days must be a positive integer.")

    user_habit = _validate_user_habit_ownership(user_id, user_habit_id)
    habit_id = user_habit.habito_id

    today = date_type.today()
    end_date = today + timedelta(days=duration_days - 1) if duration_days is not None else None

    group = SharedStreakGroup(
        owner_user_id=user_id,
        habit_id=habit_id,
        name=_normalize_name(name),
        invite_code=_generate_invite_code(),
        max_participants=MAX_PARTICIPANTS,
        start_date=today,
        duration_days=duration_days,
        end_date=end_date,
        group_status="active",
        active=True,
    )
    db.session.add(group)
    db.session.flush()
    db.session.add(
        SharedStreakMembership(
            group_id=group.id,
            user_id=user_id,
            user_habit_id=user_habit_id,
            status="active",
            share_progress=True,
        )
    )
    db.session.commit()
    return _group_payload(group, include_members=True)


def join_group(user_id: int, invite_code: object) -> dict:
    normalized_code = _normalize_invite_code(invite_code)

    # Look up without active filter first so lost/winner members get the right error
    group = SharedStreakGroup.query.filter_by(invite_code=normalized_code).first()
    if group is None:
        raise LookupError("Shared streak invite not found.")

    membership = SharedStreakMembership.query.filter_by(group_id=group.id, user_id=user_id).first()

    # Can't rejoin if eliminated or already won
    if membership is not None and membership.status in ("lost", "winner"):
        raise ValueError("No puedes volver a unirte después de perder o ganar el reto.")

    # Group must still be active for anyone else
    if not group.active:
        raise LookupError("Shared streak invite not found.")

    active_count = SharedStreakMembership.query.filter_by(
        group_id=group.id, status="active"
    ).count()
    is_new = membership is None or membership.status != "active"

    if is_new and active_count >= group.max_participants:
        raise ValueError(
            f"Este grupo ya tiene el máximo de {group.max_participants} participantes."
        )

    # Resolve or create user_habit for this group's catalog habit
    user_habit_id: int | None = None
    if group.habit_id is not None:
        user_habit = _get_or_create_user_habit_for_catalog(user_id, group.habit_id)
        user_habit_id = user_habit.id

    if membership is None:
        membership = SharedStreakMembership(
            group_id=group.id,
            user_id=user_id,
            user_habit_id=user_habit_id,
            status="active",
            share_progress=True,
        )
        db.session.add(membership)
    else:
        membership.status = "active"
        membership.share_progress = True
        membership.left_at = None
        membership.joined_at = _now()
        if user_habit_id is not None:
            membership.user_habit_id = user_habit_id

    db.session.commit()
    return _group_payload(group, include_members=True)


def list_groups(user_id: int) -> list[dict]:
    memberships = (
        SharedStreakMembership.query.filter(
            SharedStreakMembership.user_id == user_id,
            SharedStreakMembership.status.in_(["active", "lost", "winner"]),
        )
        .order_by(SharedStreakMembership.joined_at.desc(), SharedStreakMembership.id.desc())
        .all()
    )
    payloads = []
    for m in memberships:
        if m.group is None:
            continue
        _evaluate_duel_outcomes(m.group)
        payloads.append(_group_payload(m.group, include_members=False))
    db.session.commit()
    return payloads


def get_group_detail(user_id: int, group_id: int) -> dict:
    group = db.session.get(SharedStreakGroup, group_id)
    if group is None:
        raise LookupError("Shared streak group not found.")
    _require_any_duel_membership(user_id, group_id)
    _evaluate_duel_outcomes(group)
    payload = _group_payload(group, include_members=True)
    db.session.commit()
    return payload


def leave_group(user_id: int, group_id: int) -> dict:
    group = db.session.get(SharedStreakGroup, group_id)
    if group is None:
        raise LookupError("Shared streak group not found.")
    membership = SharedStreakMembership.query.filter(
        SharedStreakMembership.group_id == group_id,
        SharedStreakMembership.user_id == user_id,
        SharedStreakMembership.status.in_(["active", "lost", "winner"]),
    ).first()
    if membership is None:
        raise SocialPermissionError("You are not a member of this shared streak.")
    membership.status = "left"
    membership.share_progress = False
    membership.left_at = _now()
    db.session.commit()
    return {"left": True, "group_id": group_id}
