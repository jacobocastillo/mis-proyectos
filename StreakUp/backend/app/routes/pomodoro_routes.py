"""
Pomodoro routes module.

Responsibility:
- HTTP endpoints for Pomodoro timer sessions.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.pomodoro_service import (
    complete_session,
    create_session,
    get_user_sessions,
    interrupt_session,
)
from app.utils.error_handler import error_response

pomodoro_bp = Blueprint("pomodoro", __name__)


@pomodoro_bp.route("/sessions", methods=["POST"])
@jwt_required()
def create():
    """Create a new Pomodoro session."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        session = create_session(user_id, data)
        return jsonify(session), 201
    except ValueError as exc:
        return error_response(str(exc), 400)


@pomodoro_bp.route("/sessions/<int:session_id>/interrupt", methods=["PUT"])
@jwt_required()
def interrupt(session_id: int):
    """Record one interruption for an active session."""
    user_id = int(get_jwt_identity())
    result = interrupt_session(session_id, user_id)

    if result is None:
        return error_response("Session not found.", 404)

    return jsonify(result), 200


@pomodoro_bp.route("/sessions/<int:session_id>/complete", methods=["PUT"])
@jwt_required()
def complete(session_id: int):
    """Mark a Pomodoro session as completed."""
    user_id = int(get_jwt_identity())
    result = complete_session(session_id, user_id)

    if result is None:
        return error_response("Session not found.", 404)

    return jsonify(result), 200


@pomodoro_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    """Return recent Pomodoro sessions."""
    user_id = int(get_jwt_identity())
    sessions = get_user_sessions(user_id)
    return jsonify(sessions), 200
