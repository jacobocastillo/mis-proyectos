"""
Motivation service module.

Responsibility:
- Generate deterministic, context-aware feedback for progress surfaces.
"""

from __future__ import annotations

from collections.abc import Mapping


def _int_value(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_validation_feedback(context: Mapping[str, object]) -> dict:
    """Return deterministic feedback for one validation attempt."""
    approved = bool(context.get("approved"))
    xp_awarded = _int_value(context.get("xp_awarded"))
    streak = _int_value(context.get("streak"))
    today_completed = _int_value(context.get("today_completed"))
    today_total = _int_value(context.get("today_total"))
    habit_name = str(context.get("habit_name") or "este hábito").strip()

    if approved and today_total > 0 and today_completed >= today_total:
        message = f"Completaste tus {today_total} hábitos de hoy. {habit_name} suma a tu constancia."
        tone = "complete"
    elif approved and streak > 1:
        message = f"Validaste {habit_name} y mantienes una racha de {streak} días."
        tone = "streak"
    elif approved:
        message = f"Validaste {habit_name}. Sumaste {xp_awarded} XP con progreso concreto."
        tone = "progress"
    else:
        message = f"La evidencia de {habit_name} no fue suficiente. Ajusta el intento y vuelve a validar."
        tone = "retry"

    return {
        "message": message,
        "tone": tone,
        "context": {
            "today_completed": today_completed,
            "today_total": today_total,
            "streak": streak,
            "xp_awarded": xp_awarded,
        },
    }


def build_summary_feedback(summary: Mapping[str, object]) -> dict:
    """Return dashboard feedback from summary stats, with AI-generated message when available."""
    today_completed = _int_value(summary.get("today_completed"))
    today_total = _int_value(summary.get("today_total"))
    streak = _int_value(summary.get("streak"))
    completion_rate = _int_value(summary.get("completion_rate"))
    validations_today = _int_value(summary.get("validations_today"))

    if today_total == 0:
        message = "No tienes hábitos programados para hoy. Mantén tu sistema listo para el siguiente bloque."
        tone = "empty"
    elif today_completed >= today_total:
        message = f"Hoy cerraste {today_completed}/{today_total} hábitos. Tu racha actual es de {streak} días."
        tone = "complete"
    elif today_completed > 0:
        remaining = max(0, today_total - today_completed)
        message = f"Llevas {today_completed}/{today_total} hábitos. Te faltan {remaining} para cerrar el día."
        tone = "progress"
    elif streak > 0:
        message = f"Tu racha de {streak} días sigue en juego. Empieza por una validación concreta."
        tone = "streak"
    else:
        message = "El primer hábito de hoy reinicia el impulso. Elige uno pequeño y valídalo."
        tone = "start"

    try:
        from app.services.openai_service import generate_motivational_message
        ai_message = generate_motivational_message({
            "streak": streak,
            "today_completed": today_completed,
            "today_total": today_total,
            "completion_rate": completion_rate,
            "validations_today": validations_today,
        })
        if ai_message:
            message = ai_message
    except Exception:
        pass

    return {
        "message": message,
        "tone": tone,
        "context": {
            "today_completed": today_completed,
            "today_total": today_total,
            "streak": streak,
            "completion_rate": completion_rate,
            "validations_today": validations_today,
        },
    }
