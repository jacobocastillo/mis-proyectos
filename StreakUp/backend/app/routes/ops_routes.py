"""
Operational routes module.

Responsibility:
- Provide simple liveness and readiness endpoints for hosting.
"""

import logging
import re

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from app.config import describe_openai_configuration
from app.extensions import db
from app.models.habit import Category, Habit

ops_bp = Blueprint("ops", __name__)
logger = logging.getLogger(__name__)

SENSITIVE_FIELD_NAMES = {"authorization", "cookie", "password", "refresh_token", "token"}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(access|refresh)?_?token['\"]?\s*[:=]\s*['\"]?[^'\"\s,}]+", re.IGNORECASE),
    re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^'\"\s,}]+", re.IGNORECASE),
)


def _redact_value(value: object) -> object:
    if value is None or isinstance(value, (int, float, bool)):
        return value

    text_value = str(value)
    for pattern in SENSITIVE_VALUE_PATTERNS:
        text_value = pattern.sub("[REDACTED]", text_value)
    return text_value[:500]


def _sanitize_report(raw_report: object) -> dict[str, object]:
    if not isinstance(raw_report, dict):
        return {"message": "Invalid client telemetry payload."}

    allowed_fields = {
        "message",
        "name",
        "stack",
        "component",
        "url",
        "userAgent",
        "release",
        "environment",
    }
    sanitized: dict[str, object] = {}

    for key, value in raw_report.items():
        normalized_key = str(key)
        if normalized_key.lower() in SENSITIVE_FIELD_NAMES:
            continue
        if normalized_key not in allowed_fields:
            continue
        sanitized[normalized_key] = _redact_value(value)

    if "message" not in sanitized:
        sanitized["message"] = "Client error report received."

    return sanitized


@ops_bp.route("/healthz", methods=["GET"])
def healthz():
    """Return process liveness only."""
    return jsonify({"status": "ok"}), 200


@ops_bp.route("/readyz", methods=["GET"])
def readyz():
    """Return readiness based on DB connectivity and required catalog data."""
    try:
        db.session.execute(text("SELECT 1"))
        categories = Category.query.count()
        habits = Habit.query.filter_by(activo=True).count()
    except Exception:
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "checks": {
                        "database": {"ready": False},
                        "catalog": {"ready": False},
                        "validation": describe_openai_configuration(current_app.config),
                    },
                }
            ),
            503,
        )

    catalog_ready = categories > 0 and habits > 0
    status_code = 200 if catalog_ready else 503

    return (
        jsonify(
            {
                "status": "ready" if catalog_ready else "not_ready",
                "checks": {
                    "database": {"ready": True},
                    "catalog": {
                        "ready": catalog_ready,
                        "categories": categories,
                        "habits": habits,
                    },
                    "validation": describe_openai_configuration(current_app.config),
                },
            }
        ),
        status_code,
    )


@ops_bp.route("/api/telemetry/errors", methods=["POST"])
def report_client_error():
    """Accept a sanitized client-side crash/error report."""
    report = _sanitize_report(request.get_json(silent=True))
    logger.warning("Client error report received: %s", report)
    return jsonify({"status": "accepted"}), 202
