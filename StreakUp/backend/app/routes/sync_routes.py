"""
Synchronization routes module.

Responsibility:
- Define HTTP endpoints for client/server sync workflows.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.sync_service import SyncPayloadError, process_sync_operations
from app.utils.error_handler import error_response

sync_bp = Blueprint("sync", __name__)


@sync_bp.route("", methods=["POST"])
@sync_bp.route("/", methods=["POST"])
@jwt_required()
def push_sync_operations():
    """Apply pending client operations for the authenticated user."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Request body must be a JSON object.", 400)

    try:
        result = process_sync_operations(user_id, data.get("operations"))
    except SyncPayloadError as exc:
        return error_response(str(exc), 400, code="invalid_sync_payload")

    return jsonify(result), 200
