"""
Authentication routes module.

Responsibility:
- Define HTTP endpoints for user registration, login, token refresh, and logout.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from app.schemas.validations import validate_login_input, validate_register_input
from app.services.auth_service import login_user, refresh_access_token, register_user, revoke_token
from app.utils.error_handler import error_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True)

    errors = validate_register_input(data)
    if errors:
        return error_response(errors, 400)

    try:
        user = register_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )
        return jsonify({"message": "User registered successfully.", "user": user}), 201
    except ValueError as exc:
        return error_response(str(exc), 409)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT tokens."""
    data = request.get_json(silent=True)

    errors = validate_login_input(data)
    if errors:
        return error_response(errors, 400)

    try:
        result = login_user(email=data["email"], password=data["password"])
        return jsonify(result), 200
    except ValueError as exc:
        return error_response(str(exc), 401)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Exchange a valid refresh token for a new access token."""
    data = request.get_json(silent=True) or {}
    refresh_token_str = (data.get("refresh_token") or "").strip()

    if not refresh_token_str:
        return error_response("refresh_token is required.", 400)

    try:
        result = refresh_access_token(refresh_token_str)
        return jsonify(result), 200
    except ValueError as exc:
        return error_response(str(exc), 401)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Revoke the current access token, ending the session."""
    jti = get_jwt()["jti"]
    revoke_token(jti, token_type="access")
    return jsonify({"message": "Logged out."}), 200
