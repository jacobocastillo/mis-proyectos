"""
Check-in routes module.

Responsibility:
- HTTP endpoints for toggling and querying check-ins.
"""

from datetime import date as date_type

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.checkin_service import get_today_habits, toggle_checkin
from app.services.history_service import HistoryQueryError, get_habit_history
from app.utils.error_handler import error_response

checkins_bp = Blueprint("checkins", __name__)


@checkins_bp.route("/toggle", methods=["POST"])
@jwt_required()
def toggle():
    """Toggle a check-in for a habit."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data or "habit_id" not in data:
        return error_response("habit_id is required.", 400)

    try:
        habit_id = int(data["habit_id"])
    except (TypeError, ValueError):
        return error_response("habit_id must be an integer.", 400)

    target_date = None
    if "date" in data:
        try:
            target_date = date_type.fromisoformat(data["date"])
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD.", 400)

    try:
        result = toggle_checkin(user_id, habit_id, target_date)
        return jsonify(result), 200
    except LookupError as exc:
        return error_response(str(exc), 404)
    except ValueError as exc:
        return error_response(str(exc), 409)


@checkins_bp.route("/today", methods=["GET"])
@jwt_required()
def today():
    """Return today's habits with check-in status."""
    user_id = int(get_jwt_identity())
    habits = get_today_habits(user_id)
    return jsonify(habits), 200


@checkins_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    """Return event-level habit history for the authenticated user."""
    user_id = int(get_jwt_identity())
    try:
        result = get_habit_history(user_id, request.args.to_dict())
    except HistoryQueryError as exc:
        return error_response(str(exc), 400)
    return jsonify(result), 200
