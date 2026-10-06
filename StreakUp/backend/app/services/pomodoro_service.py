"""
Pomodoro service module.

Responsibility:
- Create and manage Pomodoro timer sessions.
"""

from datetime import date as date_type, datetime, timezone

from app.extensions import db
from app.models.checkin import CheckIn
from app.models.pomodoro_session import POMODORO_BONUS_XP, PomodoroSession
from app.models.user_habit import UserHabit
from app.services.xp_service import award_habit_xp, award_xp


VALID_THEMES = {"fire", "candle", "ice", "hourglass"}
_TIME_VALIDATION_TYPES = {"tiempo", "time"}


def _require_int(value, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


def create_session(user_id: int, data: dict) -> dict:
    """Create a new Pomodoro session."""
    theme = data.get("theme", "fire")
    if theme not in VALID_THEMES:
        raise ValueError(f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")

    study_minutes = _require_int(data.get("study_minutes", 25), "study_minutes")
    break_minutes = _require_int(data.get("break_minutes", 5), "break_minutes")
    cycles = _require_int(data.get("cycles", 4), "cycles")

    if study_minutes <= 0:
        raise ValueError("study_minutes must be greater than 0.")
    if break_minutes < 0:
        raise ValueError("break_minutes must be greater than or equal to 0.")
    if cycles <= 0:
        raise ValueError("cycles must be greater than 0.")

    habit_id = data.get("habit_id")
    if habit_id is not None:
        habit_id = _require_int(habit_id, "habit_id")
        user_habit = UserHabit.query.filter_by(id=habit_id, usuario_id=user_id, activo=True).first()
        if user_habit is None:
            raise ValueError("habit_id must reference an active habit owned by the user.")
        if user_habit.tipo_validacion not in _TIME_VALIDATION_TYPES:
            raise ValueError("habit_id must reference a time-based habit.")

    session = PomodoroSession(
        user_id=user_id,
        habit_id=habit_id,
        theme=theme,
        study_minutes=study_minutes,
        break_minutes=break_minutes,
        cycles=cycles,
    )
    db.session.add(session)
    db.session.commit()
    return session.to_dict()


def interrupt_session(session_id: int, user_id: int) -> dict | None:
    """Record one interruption (pause/stop) for an active session."""
    session = PomodoroSession.query.filter_by(id=session_id, user_id=user_id).first()
    if session is None:
        return None
    if session.completed:
        return session.to_dict()

    session.interruption_count += 1
    db.session.commit()
    return session.to_dict()


def complete_session(session_id: int, user_id: int) -> dict | None:
    """Mark a Pomodoro session as completed and award XP for linked time habits and bonus."""
    session = PomodoroSession.query.filter_by(id=session_id, user_id=user_id).first()
    if session is None:
        return None

    if session.completed:
        return {**session.to_dict(), "xp_awarded": 0}

    session.completed = True
    session.completed_at = datetime.now(timezone.utc)

    xp_awarded = 0
    if session.habit_id is not None:
        xp_awarded = _award_pomodoro_xp(session, user_id)

    bonus_xp = _award_bonus_xp(session, user_id)

    db.session.commit()
    return {**session.to_dict(), "xp_awarded": xp_awarded, "bonus_xp": bonus_xp}


def _award_pomodoro_xp(session: PomodoroSession, user_id: int) -> int:
    """Create one CheckIn and award XP for a completed Pomodoro linked to a time habit.

    Idempotent: if a CheckIn already exists for this habit on today's date, returns 0.
    """
    today = date_type.today()
    existing = CheckIn.query.filter_by(
        habitousuario_id=session.habit_id,
        fecha=today,
    ).first()
    if existing:
        return 0

    user_habit = db.session.get(UserHabit, session.habit_id)
    if user_habit is None or user_habit.tipo_validacion not in _TIME_VALIDATION_TYPES:
        return 0

    duration_minutes = session.study_minutes * session.cycles
    awarded = award_habit_xp(
        user_id,
        user_habit,
        today,
        duration_minutes,
        reason="pomodoro",
        commit=False,
    )
    checkin = CheckIn(
        habitousuario_id=session.habit_id,
        fecha=today,
        completado=True,
        xp_ganado=awarded,
    )
    db.session.add(checkin)
    return awarded


def _award_bonus_xp(session: PomodoroSession, user_id: int) -> int:
    """Award flat bonus XP for uninterrupted sessions. Idempotent via bonus_xp_awarded field."""
    if session.bonus_xp_awarded is not None:
        return 0
    if session.interruption_count > 0:
        session.bonus_xp_awarded = 0
        return 0

    bonus = POMODORO_BONUS_XP
    award_xp(
        user_id,
        bonus,
        reason="pomodoro_bonus",
        habit_id=session.habit_id,
        event_date=date_type.today(),
        source_event="habit",
        commit=False,
    )
    session.bonus_xp_awarded = bonus
    return bonus


def get_user_sessions(user_id: int, limit: int = 10) -> list[dict]:
    """Return recent Pomodoro sessions for a user."""
    sessions = (
        PomodoroSession.query
        .filter_by(user_id=user_id)
        .order_by(PomodoroSession.started_at.desc())
        .limit(limit)
        .all()
    )
    return [s.to_dict() for s in sessions]
