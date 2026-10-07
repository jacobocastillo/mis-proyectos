"""
Validation service module.

Responsibility:
- Orchestrate photo-only habit validation via image analysis.
- Award XP and create check-ins only for approved validations.
"""

import hashlib
import json
from collections.abc import Mapping
from datetime import date as date_type, datetime, timezone

from flask import current_app

from app.config import get_image_validation_provider, get_text_validation_provider
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.services.achievement_service import evaluate_and_award
from app.services.difficulty_service import recommend_difficulty
from app.services.habit_service import get_user_habit
from app.services.motivation_service import build_validation_feedback
from app.services.openai_service import analyze_habit_image, analyze_habit_text
from app.services.streak_service import compute_current_streak
from app.services.xp_service import award_xp, award_habit_xp
from app.services.checkin_service import is_eligible_today

_LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo or timezone.utc


def _get_current_time_str() -> str:
    """Return current local time as HH:MM. Injectable for tests."""
    return datetime.now(_LOCAL_TIMEZONE).strftime("%H:%M")


def _to_local_date(value: datetime | None) -> date_type | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_LOCAL_TIMEZONE).date()


def _extract_image_payload(data: Mapping[str, object]) -> tuple[str | None, str | None]:
    """Support both legacy and current validation payload shapes."""
    image_value = data.get("image_base64") or data.get("image")
    mime_type = data.get("mime_type")

    if not isinstance(image_value, str):
        return None, None

    image_value = image_value.strip()
    normalized_mime_type = mime_type.strip() if isinstance(mime_type, str) else None

    if image_value.startswith("data:") and "," in image_value:
        metadata, encoded = image_value.split(",", 1)
        image_value = encoded.strip()

        if normalized_mime_type is None and ";base64" in metadata:
            normalized_mime_type = metadata[len("data:") :].split(";", 1)[0].strip() or None

    return image_value or None, normalized_mime_type


def _target_summary(user_habit: UserHabit) -> str | None:
    if user_habit.duracion_objetivo_minutos is not None:
        return f"{user_habit.duracion_objetivo_minutos} min"
    if user_habit.cantidad_objetivo is not None:
        amount = user_habit.cantidad_objetivo
        if amount == amount.to_integral_value():
            amount = int(amount)
        unit = f" {user_habit.unidad_objetivo}" if user_habit.unidad_objetivo else ""
        return f"{amount}{unit}"
    return None


def _difficulty_context(user_habit: UserHabit, validation_type: str, payload: Mapping[str, object]) -> dict:
    context = {
        "validation_type": validation_type,
        "target_summary": _target_summary(user_habit),
        "frequency": user_habit.frecuencia or user_habit.habit.frecuencia,
    }
    if validation_type in {"tiempo", "time"}:
        context["duration_minutes"] = payload.get("duration_minutes")
    if validation_type in {"texto", "text_ai"}:
        text_content = payload.get("text_content")
        context["text_length"] = len(text_content.strip()) if isinstance(text_content, str) else 0
    return context


def _progress_context(
    user_habit: UserHabit,
    today: date_type,
    streak: int,
    xp_awarded: int,
    approved: bool,
) -> dict:
    active_habits = [
        assigned_habit
        for assigned_habit in user_habit.user.assigned_habits
        if assigned_habit.activo
    ]
    eligible_today = [
        assigned_habit
        for assigned_habit in active_habits
        if is_eligible_today(assigned_habit, today)
    ]
    eligible_ids = [assigned_habit.id for assigned_habit in eligible_today]
    today_completed = 0
    if eligible_ids:
        today_completed = CheckIn.query.filter(
            CheckIn.habitousuario_id.in_(eligible_ids),
            CheckIn.fecha == today,
        ).count()

    habit_name = user_habit.nombre_personalizado or user_habit.habit.nombre
    return {
        "approved": approved,
        "habit_name": habit_name,
        "today_completed": min(today_completed, len(eligible_ids)),
        "today_total": len(eligible_ids),
        "streak": streak,
        "xp_awarded": xp_awarded,
    }


def validate_habit(
    user_id: int,
    habit_id: int,
    payload: Mapping[str, object],
) -> dict:
    """Validate a habit with photo evidence and award progress only on approval."""
    user_habit = get_user_habit(habit_id, user_id, active_only=True)
    if user_habit is None:
        raise ValueError("Habito no encontrado.")

    today = date_type.today()

    if not is_eligible_today(user_habit, today):
        raise ValueError("Este hábito no está programado para hoy.")

    existing = next(
        (
            validation
            for validation in ValidationLog.query.filter(
                ValidationLog.habitousuario_id == user_habit.id,
                ValidationLog.status == "approved",
                ValidationLog.validado == True,
            )
            .order_by(ValidationLog.fecha.desc())
            .all()
            if _to_local_date(validation.fecha) == today
        ),
        None,
    )
    if existing:
        raise ValueError("Ya validaste este habito hoy.")

    val_type = user_habit.habit.tipo_validacion if not user_habit.tipo_validacion else user_habit.tipo_validacion
    
    if not val_type:
        val_type = "foto"

    try:
        evidence_metadata = {
            "validation_type": val_type,
        }
        
        is_approved = False
        reason = ""
        confidence = 1.0

        if val_type in {"foto", "photo"}:
            image_base64, mime_type = _extract_image_payload(payload)
            if not image_base64:
                raise ValueError("image (base64) is required for photo validation.")
                
            evidence_metadata["provider"] = get_image_validation_provider(current_app.config)
            evidence_metadata["mime_type"] = mime_type or "image/jpeg"
            evidence_metadata["image_sha256"] = hashlib.sha256(image_base64.encode("utf-8")).hexdigest()
            
            log = ValidationLog(
                habitousuario_id=user_habit.id,
                tipo_validacion="foto",
                evidencia=json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True),
                status="pending",
                validado=False,
            )
            db.session.add(log)
            db.session.flush()

            try:
                habit_name = user_habit.nombre_personalizado or user_habit.habit.nombre
                ai_result = analyze_habit_image(habit_name, image_base64, mime_type=mime_type)
                is_approved = bool(ai_result["valido"])
                reason = ai_result["razon"]
                confidence = ai_result["confianza"]
            except Exception as ai_exc:
                current_app.logger.error(f"AI validation failed for log_id={log.id}: {str(ai_exc)}")
                raise

        elif val_type in {"texto", "text_ai"}:
            text_content = payload.get("text_content", "")
            if not isinstance(text_content, str):
                text_content = str(text_content)
            text_content = text_content.strip()

            if not text_content:
                raise ValueError("Se requiere texto para validar este hábito.")

            min_length = user_habit.min_text_length or 0
            if len(text_content) < min_length:
                raise ValueError(f"El texto debe tener al menos {min_length} caracteres. Actualmente tiene {len(text_content)}.")

            evidence_metadata["text_content"] = text_content
            evidence_metadata["text_length"] = len(text_content)

            log = ValidationLog(
                habitousuario_id=user_habit.id,
                tipo_validacion="texto",
                evidencia=json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True),
                status="pending",
                validado=False,
            )
            db.session.add(log)
            db.session.flush()

            if val_type == "text_ai":
                evidence_metadata["provider"] = get_text_validation_provider(current_app.config)
                try:
                    habit_name = user_habit.nombre_personalizado or user_habit.habit.nombre
                    ai_result = analyze_habit_text(habit_name, text_content)
                    is_approved = bool(ai_result["valido"])
                    reason = ai_result["razon"]
                    confidence = ai_result["confianza"]
                except Exception as ai_exc:
                    current_app.logger.error(f"AI text validation failed for log_id={log.id}: {str(ai_exc)}")
                    raise
            else:
                is_approved = True
                reason = "Texto validado correctamente."

        elif val_type in {"tiempo", "time"}:
            duration_minutes = payload.get("duration_minutes")
            if not duration_minutes:
                raise ValueError("Se requiere la duración completada.")
                
            try:
                duration_minutes = float(duration_minutes)
            except ValueError:
                raise ValueError("La duración debe ser un número.")
                
            if user_habit.duracion_objetivo_minutos and duration_minutes < user_habit.duracion_objetivo_minutos:
                raise ValueError(f"Debes completar al menos {user_habit.duracion_objetivo_minutos} minutos. Ingresaste {duration_minutes}.")
                
            evidence_metadata["duration_minutes"] = duration_minutes
            is_approved = True
            reason = f"Completaste {duration_minutes} minutos."
            
            log = ValidationLog(
                habitousuario_id=user_habit.id,
                tipo_validacion="tiempo",
                evidencia=json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True),
                status="pending",
                validado=False,
            )
            db.session.add(log)
            
        elif val_type == "check":
            deadline = user_habit.deadline_time
            if not deadline:
                raise ValueError("Este hábito requiere hora límite configurada (deadline_time).")

            now_time_str = _get_current_time_str()
            is_approved = now_time_str <= deadline
            reason = (
                f"Validado a las {now_time_str}, antes del límite de {deadline}."
                if is_approved
                else f"Validado a las {now_time_str}, después del límite de {deadline}."
            )
            evidence_metadata["checked_at"] = now_time_str
            evidence_metadata["deadline"] = deadline

            log = ValidationLog(
                habitousuario_id=user_habit.id,
                tipo_validacion="manual",
                evidencia=json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True),
                status="pending",
                validado=False,
            )
            db.session.add(log)

        else:
            raise ValueError(f"Tipo de validación no soportado: {val_type}")

        xp_awarded = 0
        if is_approved:
            duration_minutes_value = None
            if val_type in {"tiempo", "time"}:
                duration_minutes_value = float(payload.get("duration_minutes") or 0)
            xp_awarded = _apply_approved_progress(user_habit.id, user_id, today, duration_minutes=duration_minutes_value)

        status = "approved" if is_approved else "rejected"
        log.status = status
        log.validado = is_approved
        evidence_metadata.update(
            {
                "reason": reason,
                "confidence": confidence,
                "xp_awarded": xp_awarded,
            }
        )
        log.evidencia = json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True)
        
        active_user_habit_ids = [
            assigned_habit.id
            for assigned_habit in user_habit.user.assigned_habits
            if assigned_habit.activo
        ]
        
        nueva_racha = compute_current_streak(active_user_habit_ids, today)
        new_achievements = evaluate_and_award(user_id, current_streak=nueva_racha)
        habit_name = user_habit.nombre_personalizado or user_habit.habit.nombre
        difficulty_recommendation = recommend_difficulty(
            habit_name,
            user_habit.habit.dificultad,
            _difficulty_context(user_habit, val_type, payload),
        )
        db.session.flush()
        feedback = build_validation_feedback(
            _progress_context(user_habit, today, nueva_racha, xp_awarded, is_approved)
        )
        evidence_metadata.update(
            {
                "difficulty_recommendation": difficulty_recommendation,
                "feedback": feedback,
            }
        )
        log.evidencia = json.dumps(evidence_metadata, ensure_ascii=True, sort_keys=True)

        db.session.commit()

        return {
            "status": log.status,
            "valido": is_approved,
            "razon": reason,
            "confianza": confidence,
            "xp_ganado": xp_awarded,
            "nueva_racha": nueva_racha,
            "new_achievements": new_achievements,
            "difficulty_recommendation": difficulty_recommendation,
            "feedback": feedback,
        }
    except Exception:
        current_app.logger.exception(
            "Validation transaction failed for user_id=%s habit_id=%s",
            user_id,
            habit_id,
        )
        db.session.rollback()
        raise


def _apply_approved_progress(
    user_habit_id: int,
    user_id: int,
    today: date_type,
    duration_minutes: float | None = None,
) -> int:
    """Materialize one approved progress row and award XP at most once per day."""
    existing_checkin = CheckIn.query.filter_by(
        habitousuario_id=user_habit_id,
        fecha=today,
    ).first()
    if existing_checkin:
        return 0

    user_habit = db.session.get(UserHabit, user_habit_id)
    awarded_xp = award_habit_xp(
        user_id,
        user_habit,
        today,
        duration_minutes,
        reason="validation",
        commit=False,
    )
    checkin = CheckIn(
        habitousuario_id=user_habit_id,
        fecha=today,
        completado=True,
        xp_ganado=awarded_xp,
    )
    db.session.add(checkin)
    return awarded_xp
