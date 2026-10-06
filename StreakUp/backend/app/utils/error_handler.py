"""
Error handling utilities module.

Responsibility:
- Define consistent error formatting for API responses.
"""

from flask import jsonify


def error_response(message: str | list[str], status_code: int = 400, code: str | None = None):
    """Return a standardized JSON error response."""
    if isinstance(message, list):
        body = {"errors": message}
    else:
        body = {"error": message}

    if code:
        body["code"] = code

    return jsonify(body), status_code
