"""
Social routes module.

Responsibility:
- Expose privacy-safe invite-only shared streak endpoints.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.social_service import (
    SocialPermissionError,
    create_group,
    get_group_detail,
    join_group,
    leave_group,
    list_groups,
)
from app.utils.error_handler import error_response

social_bp = Blueprint("social", __name__)


@social_bp.route("/groups", methods=["GET"])
@jwt_required()
def groups():
    user_id = int(get_jwt_identity())
    return jsonify(list_groups(user_id)), 200


@social_bp.route("/groups", methods=["POST"])
@jwt_required()
def create():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(
            create_group(
                user_id,
                data.get("name"),
                data.get("user_habit_id"),
                data.get("duration_days"),
            )
        ), 201
    except (ValueError, SocialPermissionError) as exc:
        return error_response(str(exc), 400)


@social_bp.route("/groups/join", methods=["POST"])
@jwt_required()
def join():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(join_group(user_id, data.get("invite_code"))), 200
    except ValueError as exc:
        return error_response(str(exc), 400)
    except LookupError as exc:
        return error_response(str(exc), 404)
    except SocialPermissionError as exc:
        return error_response(str(exc), 403)


@social_bp.route("/groups/<int:group_id>", methods=["GET"])
@jwt_required()
def detail(group_id: int):
    user_id = int(get_jwt_identity())
    try:
        return jsonify(get_group_detail(user_id, group_id)), 200
    except SocialPermissionError as exc:
        return error_response(str(exc), 403)
    except LookupError as exc:
        return error_response(str(exc), 404)


@social_bp.route("/groups/<int:group_id>/membership", methods=["DELETE"])
@jwt_required()
def leave(group_id: int):
    user_id = int(get_jwt_identity())
    try:
        return jsonify(leave_group(user_id, group_id)), 200
    except SocialPermissionError as exc:
        return error_response(str(exc), 403)
    except LookupError as exc:
        return error_response(str(exc), 404)
