"""
Achievement service module.

Responsibility:
- Define the canonical achievement catalog.
- Evaluate and award achievements after habit progress events.
- Provide helpers for querying user achievement state.

Design principle: evaluators are pure functions that receive DB-visible
state (counts, streak) and return True/False — the award loop handles
idempotency so callers never need to worry about double-awarding.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import func

from app.extensions import db
from app.models.achievement import Achievement, UserAchievement
from app.models.checkin import CheckIn
from app.models.validation_log import ValidationLog

if TYPE_CHECKING:
    from app.models.user import User


# ---------------------------------------------------------------------------
# Catalog definition
# ---------------------------------------------------------------------------

ACHIEVEMENT_CATALOG: tuple[dict, ...] = (
    {
        "key": "first_validation",
        "name": "Primera Validación",
        "description": "Completa tu primera validación con foto aprobada por IA.",
        "emoji": "🌟",
        "xp_bonus": 25,
    },
    {
        "key": "streak_7",
        "name": "Racha de 7 días",
        "description": "Mantén una racha activa de 7 días consecutivos.",
        "emoji": "🔥",
        "xp_bonus": 50,
    },
    {
        "key": "completions_30",
        "name": "30 Completaciones",
        "description": "Acumula 30 hábitos completados con evidencia válida.",
        "emoji": "🏆",
        "xp_bonus": 100,
    },
)


def seed_achievements() -> int:
    """Idempotently insert all catalog achievements. Returns count of new rows."""
    created = 0
    for row in ACHIEVEMENT_CATALOG:
        existing = Achievement.query.filter_by(key=row["key"]).first()
        if existing is None:
            achievement = Achievement(**row)
            db.session.add(achievement)
            created += 1
        else:
            # Keep catalog attrs in sync
            existing.name = row["name"]
            existing.description = row["description"]
            existing.emoji = row["emoji"]
            existing.xp_bonus = row["xp_bonus"]

    db.session.commit()
    return created


# ---------------------------------------------------------------------------
# Evaluators — pure functions, no DB writes
# ---------------------------------------------------------------------------

def _total_approved_validations(user_id: int) -> int:
    """Count approved validations across all habits for a user."""
    from app.models.user_habit import UserHabit

    return (
        db.session.query(func.count(ValidationLog.id))
        .join(UserHabit, ValidationLog.habitousuario_id == UserHabit.id)
        .filter(
            UserHabit.usuario_id == user_id,
            ValidationLog.status == "approved",
        )
        .scalar()
        or 0
    )


def _total_checkin_completions(user_id: int) -> int:
    """Count total completed checkin rows for a user."""
    from app.models.user_habit import UserHabit

    return (
        db.session.query(func.count(CheckIn.id))
        .join(UserHabit, CheckIn.habitousuario_id == UserHabit.id)
        .filter(UserHabit.usuario_id == user_id, CheckIn.completado == True)  # noqa: E712
        .scalar()
        or 0
    )


_EVALUATORS: dict[str, "callable"] = {
    "first_validation": lambda user_id, streak: _total_approved_validations(user_id) >= 1,
    "streak_7": lambda user_id, streak: streak >= 7,
    "completions_30": lambda user_id, streak: _total_checkin_completions(user_id) >= 30,
}


# ---------------------------------------------------------------------------
# Award engine
# ---------------------------------------------------------------------------

def evaluate_and_award(user_id: int, current_streak: int = 0) -> list[dict]:
    """Check all achievements for the user and award any newly earned ones.

    Returns a list of newly awarded achievement dicts (empty if none new).
    This is idempotent — already-earned achievements are silently skipped.
    """
    from app.services.xp_service import award_xp

    # Load the set of already-earned achievement keys for this user
    already_earned: set[str] = {
        ua.achievement.key
        for ua in UserAchievement.query.filter_by(user_id=user_id)
        .join(Achievement)
        .all()
    }

    newly_earned: list[dict] = []

    for achievement in Achievement.query.all():
        if achievement.key in already_earned:
            continue

        evaluator = _EVALUATORS.get(achievement.key)
        if evaluator is None:
            continue

        try:
            earned = evaluator(user_id, current_streak)
        except Exception:
            # Never let an evaluator crash break a habit progress flow
            continue

        if not earned:
            continue

        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
        )
        db.session.add(user_achievement)

        if achievement.xp_bonus > 0:
            award_xp(user_id, achievement.xp_bonus, "validation", source_event="achievement", commit=False)

        db.session.flush()
        newly_earned.append({
            **achievement.to_dict(),
            "earned_at": user_achievement.earned_at.isoformat()
            if user_achievement.earned_at
            else None,
        })

    if newly_earned:
        db.session.commit()

    return newly_earned


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_user_achievements(user_id: int) -> list[dict]:
    """Return all achievements earned by a user, ordered by earned_at."""
    rows = (
        UserAchievement.query.filter_by(user_id=user_id)
        .join(Achievement)
        .order_by(UserAchievement.earned_at)
        .all()
    )
    return [row.to_dict() for row in rows]


def get_all_achievements(user_id: int) -> list[dict]:
    """Return all catalog achievements with an earned flag for the given user."""
    earned_achievement_ids: set[int] = {
        ua.achievement_id
        for ua in UserAchievement.query.filter_by(user_id=user_id).all()
    }
    result = []
    for achievement in Achievement.query.order_by(Achievement.id).all():
        entry = achievement.to_dict()
        entry["earned"] = achievement.id in earned_achievement_ids
        result.append(entry)
    return result
