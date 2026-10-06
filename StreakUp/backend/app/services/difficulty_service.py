"""
Difficulty service module.

Responsibility:
- Produce advisory habit difficulty metadata.
- Keep difficulty recommendations separate from XP calculation.
"""

from __future__ import annotations

from collections.abc import Mapping

from flask import current_app

from app.config import is_openai_configured
from app.services.openai_service import analyze_habit_difficulty

DIFFICULTY_LEVELS = {"facil", "media", "dificil"}
DEFAULT_CONFIDENCE = 0.55


def _normalize_level(value: object, fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in DIFFICULTY_LEVELS:
            return normalized
    return fallback if fallback in DIFFICULTY_LEVELS else "media"


def _fallback_recommendation(
    habit_name: str,
    current_difficulty: str | None,
    context: Mapping[str, object] | None = None,
) -> dict:
    level = _normalize_level(current_difficulty, "media")
    validation_type = str((context or {}).get("validation_type") or "").strip()
    target_summary = str((context or {}).get("target_summary") or "").strip()

    detail = f" con validación {validation_type}" if validation_type else ""
    if target_summary:
        detail = f"{detail} y objetivo {target_summary}"

    return {
        "level": level,
        "confidence": DEFAULT_CONFIDENCE,
        "explanation": (
            f"Se conserva la dificultad configurada para {habit_name}{detail}. "
            "La recomendación es solo informativa y no cambia la XP."
        ),
        "source": "deterministic",
        "advisory": True,
    }


def _coerce_ai_recommendation(raw: Mapping[str, object], fallback: dict) -> dict:
    level = _normalize_level(raw.get("level"), fallback["level"])
    try:
        confidence = float(raw.get("confidence", fallback["confidence"]))
    except (TypeError, ValueError):
        confidence = fallback["confidence"]

    explanation = str(raw.get("explanation") or fallback["explanation"]).strip()
    if not explanation:
        explanation = fallback["explanation"]

    return {
        "level": level,
        "confidence": max(0.0, min(1.0, confidence)),
        "explanation": explanation,
        "source": "openai",
        "advisory": True,
    }


def recommend_difficulty(
    habit_name: str,
    current_difficulty: str | None,
    context: Mapping[str, object] | None = None,
) -> dict:
    """Return advisory difficulty metadata without changing rewards."""
    fallback = _fallback_recommendation(habit_name, current_difficulty, context)

    if not is_openai_configured(current_app.config):
        return fallback

    try:
        ai_result = analyze_habit_difficulty(
            habit_name,
            current_difficulty=fallback["level"],
            context=context or {},
        )
    except Exception:
        current_app.logger.exception("Difficulty recommendation provider failed.")
        return fallback

    return _coerce_ai_recommendation(ai_result, fallback)
