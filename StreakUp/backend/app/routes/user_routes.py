"""
User routes module.

Responsibility:
- Define HTTP endpoints for user profile and account management.

Endpoints:
  GET  /api/users/me   → return the authenticated user's public profile.
  DELETE /api/users/me → permanently delete the account and all related data.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models.achievement import UserAchievement
from app.models.checkin import CheckIn
from app.models.pomodoro_session import PomodoroSession
from app.models.social import SharedStreakGroup, SharedStreakMembership
from app.models.sync_operation import SyncOperation
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog
from app.schemas.user_validations import validate_profile_update_input
from app.services.user_service import update_user_profile
from app.utils.error_handler import error_response

user_bp = Blueprint("users", __name__)


def _iso_date(value):
    return value.isoformat() if value else None


def _export_user_habit(user_habit: UserHabit) -> dict:
    return {
        "id": user_habit.id,
        "catalog_habit_id": user_habit.habito_id,
        "start_date": _iso_date(user_habit.fecha_inicio),
        "end_date": _iso_date(user_habit.fecha_fin),
        "active": bool(user_habit.activo),
        "custom_name": user_habit.nombre_personalizado,
        "custom_description": user_habit.descripcion_personalizada,
        "validation_type": user_habit.tipo_validacion,
        "frequency": user_habit.frecuencia,
        "target_quantity": float(user_habit.cantidad_objetivo)
        if user_habit.cantidad_objetivo is not None
        else None,
        "target_unit": user_habit.unidad_objetivo,
        "target_duration": user_habit.duracion_objetivo_minutos,
        "created_at": _iso_date(user_habit.fecha_creacion),
        "updated_at": _iso_date(user_habit.fecha_actualizacion),
    }


def _export_xp_log(log: XpLog) -> dict:
    return {
        "id": log.id,
        "amount": log.cantidad,
        "reason": log.razon,
        "created_at": _iso_date(log.fecha),
        "habit_id": log.habit_id,
        "event_date": _iso_date(log.event_date),
        "calculated_xp": log.calculated_xp,
        "source_event": log.source_event,
        "cap_hit": bool(log.cap_hit),
    }


def _export_social_membership(membership: SharedStreakMembership) -> dict:
    return {
        "id": membership.id,
        "group_id": membership.group_id,
        "status": membership.status,
        "share_progress": bool(membership.share_progress),
        "joined_at": _iso_date(membership.joined_at),
        "left_at": _iso_date(membership.left_at),
    }


def _export_social_group(group: SharedStreakGroup) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "invite_code": group.invite_code,
        "active": bool(group.active),
        "created_at": _iso_date(group.created_at),
        "updated_at": _iso_date(group.updated_at),
    }


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    """Return the authenticated user's public profile."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return error_response("Usuario no encontrado.", 404)

    return jsonify(user.to_dict()), 200


@user_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    """Update the authenticated user's editable public profile fields."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    normalized, errors = validate_profile_update_input(data)
    if errors:
        return error_response(errors, 400)

    try:
        user = update_user_profile(user_id, username=normalized["username"])
        return jsonify(user), 200
    except LookupError as exc:
        return error_response(str(exc), 404)
    except ValueError as exc:
        return error_response(str(exc), 409)


@user_bp.route("/me/export", methods=["GET"])
@jwt_required()
def export_me():
    """Return an authenticated user's portable data export."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return error_response("Usuario no encontrado.", 404)

    user_habits = UserHabit.query.filter_by(usuario_id=user_id).order_by(UserHabit.id).all()
    user_habit_ids = [habit.id for habit in user_habits]

    checkins = (
        CheckIn.query.filter(CheckIn.habitousuario_id.in_(user_habit_ids))
        .order_by(CheckIn.id)
        .all()
        if user_habit_ids
        else []
    )
    validations = (
        ValidationLog.query.filter(ValidationLog.habitousuario_id.in_(user_habit_ids))
        .order_by(ValidationLog.id)
        .all()
        if user_habit_ids
        else []
    )

    payload = {
        "profile": user.to_dict(),
        "habits": [_export_user_habit(habit) for habit in user_habits],
        "checkins": [checkin.to_dict() for checkin in checkins],
        "pomodoro_sessions": [
            session.to_dict()
            for session in PomodoroSession.query.filter_by(user_id=user_id).order_by(PomodoroSession.id).all()
        ],
        "achievements": [
            achievement.to_dict()
            for achievement in UserAchievement.query.filter_by(user_id=user_id).order_by(UserAchievement.id).all()
        ],
        "xp_logs": [
            _export_xp_log(log)
            for log in XpLog.query.filter_by(user_id=user_id).order_by(XpLog.id).all()
        ],
        "social_memberships": [
            _export_social_membership(membership)
            for membership in SharedStreakMembership.query.filter_by(user_id=user_id)
            .order_by(SharedStreakMembership.id)
            .all()
        ],
        "owned_social_groups": [
            _export_social_group(group)
            for group in SharedStreakGroup.query.filter_by(owner_user_id=user_id).order_by(SharedStreakGroup.id).all()
        ],
        "validation_records": [
            {
                "id": validation.id,
                "habit_id": validation.habitousuario_id,
                "validation_type": validation.tipo_validacion,
                "status": validation.status,
                "valid": bool(validation.validado),
                "created_at": _iso_date(validation.fecha),
                "evidence_present": bool(validation.evidencia),
                "time_seconds": validation.tiempo_segundos,
            }
            for validation in validations
        ],
    }

    return jsonify(payload), 200


@user_bp.route("/me", methods=["DELETE"])
@jwt_required()
def delete_account():
    """
    Permanently delete the authenticated user and all their data.

    Cascade order (child → parent to respect FK constraints):
      1. XpLog          (references User)
      2. ValidationLog  (references UserHabit)
      3. CheckIn        (references UserHabit)
      4. PomodoroSession(references User)
      5. UserAchievement(references User)
      6. UserHabit      (references User + Habit)
      7. User           (root entity)
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return error_response("Usuario no encontrado.", 404)

    try:
        # 1. XP logs
        XpLog.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        # 2. Gather user_habit IDs for child-table cleanup
        user_habit_ids = [
            row.id
            for row in UserHabit.query.filter_by(usuario_id=user_id).with_entities(UserHabit.id).all()
        ]

        if user_habit_ids:
            # 2a. Validation logs
            ValidationLog.query.filter(
                ValidationLog.habitousuario_id.in_(user_habit_ids)
            ).delete(synchronize_session=False)

            # 2b. Check-ins
            CheckIn.query.filter(
                CheckIn.habitousuario_id.in_(user_habit_ids)
            ).delete(synchronize_session=False)

        # 3. Pomodoro sessions
        PomodoroSession.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        # 4. Achievements
        UserAchievement.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        # 5. Social sharing and sync receipts
        SharedStreakMembership.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        SharedStreakGroup.query.filter_by(owner_user_id=user_id).delete(synchronize_session=False)
        SyncOperation.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        # 6. User habits
        UserHabit.query.filter_by(usuario_id=user_id).delete(synchronize_session=False)

        # 7. User itself
        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "Cuenta eliminada correctamente."}), 200

    except Exception:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(
            "Error deleting account for user_id=%s", user_id
        )
        return error_response("No se pudo eliminar la cuenta. Inténtalo de nuevo.", 500)
