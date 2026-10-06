"""
Habit routes module.

Responsibility:
- Define HTTP endpoints for catalog habits and user habit assignments.
- All endpoints require JWT authentication.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.schemas.habit_validations import (
    normalize_create_habit_payload,
    normalize_update_habit_payload,
)
from app.services.habit_service import (
    HabitConfigurationError,
    assign_habit_to_user,
    deactivate_user_habit,
    get_habits,
    get_user_habit_payload,
    list_catalog_habits,
    update_user_habit,
)
from app.utils.error_handler import error_response

habits_bp = Blueprint("habits", __name__)


@habits_bp.route("/habitos", methods=["GET"])
@jwt_required()
def list_catalog():
    """Return the habit catalog."""
    return jsonify(list_catalog_habits()), 200


@habits_bp.route("/habitos_usuario", methods=["POST"])
@jwt_required()
def assign():
    """Assign a catalog habit to the authenticated user."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    normalized, errors = normalize_create_habit_payload(data)
    if errors:
        return error_response(errors, 400)

    try:
        habito_id = int(normalized.pop("habito_id"))
        habit = assign_habit_to_user(user_id, habito_id, normalized)
        return jsonify(habit), 201
    except HabitConfigurationError as exc:
        return error_response(str(exc), 400)
    except ValueError as exc:
        return error_response(str(exc), 409)
    except LookupError as exc:
        return error_response(str(exc), 404)


@habits_bp.route("/mis-habitos", methods=["GET"])
@jwt_required()
def list_user_habits():
    """Return active habits for the authenticated user."""
    user_id = int(get_jwt_identity())
    return jsonify(get_habits(user_id)), 200


@habits_bp.route("/habitos_usuario/<int:habit_id>", methods=["DELETE"])
@jwt_required()
def deactivate(habit_id: int):
    """Deactivate an assigned habit for the authenticated user."""
    user_id = int(get_jwt_identity())
    if not deactivate_user_habit(habit_id, user_id):
        return error_response("Habit not found.", 404)
    return jsonify({"message": "Habit deactivated successfully."}), 200


@habits_bp.route("/habits", methods=["GET"])
@jwt_required()
def list_habits():
    """Compatibility endpoint for the existing frontend habits list."""
    user_id = int(get_jwt_identity())
    return jsonify(get_habits(user_id)), 200


@habits_bp.route("/habits/<int:habit_id>", methods=["GET"])
@jwt_required()
def get_habit_detail(habit_id: int):
    """Return one assigned habit for the authenticated user."""
    user_id = int(get_jwt_identity())
    habit = get_user_habit_payload(habit_id, user_id)
    if habit is None:
        return error_response("Habit not found.", 404)
    return jsonify(habit), 200


@habits_bp.route("/habits/catalog", methods=["GET"])
@jwt_required()
def list_catalog_compatible():
    """Compatibility endpoint for the habit catalog."""
    return jsonify(list_catalog_habits()), 200


@habits_bp.route("/habits", methods=["POST"])
@jwt_required()
def assign_compatible():
    """Compatibility endpoint for assigning a habit."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    normalized, errors = normalize_create_habit_payload(data)
    if errors:
        return error_response(errors, 400)

    try:
        habito_id = int(normalized.pop("habito_id"))
        habit = assign_habit_to_user(user_id, habito_id, normalized)
        return jsonify(habit), 201
    except HabitConfigurationError as exc:
        return error_response(str(exc), 400)
    except ValueError as exc:
        return error_response(str(exc), 409)
    except LookupError as exc:
        return error_response(str(exc), 404)

@habits_bp.route("/habits/<int:habit_id>", methods=["DELETE"])
@jwt_required()
def delete(habit_id: int):
    """Compatibility endpoint that deactivates an assigned habit."""
    user_id = int(get_jwt_identity())
    if not deactivate_user_habit(habit_id, user_id):
        return error_response("Habit not found.", 404)
    return jsonify({"message": "Habit deactivated successfully."}), 200

@habits_bp.route("/habits/<int:habit_id>", methods=["PUT"])
@jwt_required()
def update_compatible(habit_id: int):
    """Compatibility endpoint for updating an assigned habit."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    normalized, errors = normalize_update_habit_payload(data)
    if errors:
        return error_response(errors, 400)

    try:
        habit = update_user_habit(habit_id, user_id, normalized)
        return jsonify(habit), 200
    except HabitConfigurationError as exc:
        return error_response(str(exc), 400)
    except LookupError as exc:
        return error_response(str(exc), 404)


@habits_bp.route("/habitos_usuario/<int:habit_id>", methods=["PATCH"])
@jwt_required()
def patch_user_habit(habit_id: int):
    """Personalize an assigned habit (name, targets, frequency, validation type).

    Accepts partial updates — only fields present in the payload are modified.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    normalized, errors = normalize_update_habit_payload(data)
    if errors:
        return error_response(errors, 400)

    try:
        habit = update_user_habit(habit_id, user_id, normalized)
        return jsonify(habit), 200
    except HabitConfigurationError as exc:
        return error_response(str(exc), 400)
    except LookupError as exc:
        return error_response(str(exc), 404)
