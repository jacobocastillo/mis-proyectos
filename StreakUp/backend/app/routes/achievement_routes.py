"""
Achievement routes module.

Responsibility:
- Expose achievement catalog and user achievement state via HTTP.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.achievement_service import get_all_achievements, get_user_achievements

achievements_bp = Blueprint("achievements", __name__)


@achievements_bp.route("/achievements", methods=["GET"])
@jwt_required()
def list_achievements():
    """Return all catalog achievements with earned status for the current user."""
    user_id = int(get_jwt_identity())
    return jsonify(get_all_achievements(user_id)), 200


@achievements_bp.route("/achievements/earned", methods=["GET"])
@jwt_required()
def list_earned_achievements():
    """Return only the achievements the current user has earned."""
    user_id = int(get_jwt_identity())
    return jsonify(get_user_achievements(user_id)), 200
