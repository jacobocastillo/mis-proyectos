"""
Configuration module for the StreakUP Flask backend.

Responsibility:
- Centralize environment-driven settings.
- Provide base and environment-specific config classes.

Should contain:
- Config classes and default values.
- Environment variable mapping.

Should NOT contain:
- Business logic.
- Runtime side effects.
- Service orchestration.
"""

import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

load_dotenv()
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env.local", override=False)

DEFAULT_SQLITE_DB_PATH = BASE_DIR / "data" / "app.db"
MIN_SECRET_LENGTH = 32
INSECURE_SECRET_VALUES = {
    "",
    "change-me-in-production",
    "change-me-jwt-secret",
    "replace-with-strong-secret",
    "replace-with-strong-jwt-secret",
}


def _coerce_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(raw_value: str | None) -> str:
    """Return a SQLAlchemy-safe database URL."""
    if raw_value is None or not str(raw_value).strip():
        return f"sqlite:///{DEFAULT_SQLITE_DB_PATH}"

    normalized = str(raw_value).strip()
    if normalized.startswith("postgres://"):
        return "postgresql+psycopg://" + normalized[len("postgres://") :]

    split_url = urlsplit(normalized)
    if split_url.scheme == "postgresql":
        return urlunsplit(
            (
                "postgresql+psycopg",
                split_url.netloc,
                split_url.path,
                split_url.query,
                split_url.fragment,
            )
        )

    return normalized


def build_engine_options(database_url: str) -> dict[str, object]:
    """Return SQLAlchemy engine options for the configured backend."""
    if database_url.startswith("sqlite:"):
        return {}

    return {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }


def _looks_placeholder(secret: str) -> bool:
    normalized = secret.strip().lower()
    return normalized in INSECURE_SECRET_VALUES or normalized.startswith(
        ("change-me", "replace-with", "example-", "default-")
    )


class Config:
    """Base configuration loaded from environment variables."""

    DEBUG = _coerce_bool(os.getenv("FLASK_DEBUG", "false"))
    TESTING = _coerce_bool(os.getenv("TESTING", "false"))
    ENVIRONMENT = os.getenv("FLASK_ENV", "production").strip().lower()

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = build_engine_options(SQLALCHEMY_DATABASE_URI)

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-jwt-secret")
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def is_development_like(config: Mapping[str, object]) -> bool:
    """Return True when the runtime should allow local-development defaults."""
    environment = str(
        config.get("ENVIRONMENT") or config.get("FLASK_ENV") or "production"
    ).strip().lower()
    return bool(config.get("DEBUG")) or bool(config.get("TESTING")) or environment == "development"


def get_cors_origins(config: Mapping[str, object]) -> tuple[str, ...]:
    """Return the allowed CORS origins for the current runtime."""
    raw_value = config.get("CORS_ALLOWED_ORIGINS")
    if isinstance(raw_value, str):
        origins = tuple(
            origin.strip().rstrip("/")
            for origin in raw_value.split(",")
            if origin.strip()
        )
    elif isinstance(raw_value, (list, tuple, set)):
        origins = tuple(
            str(origin).strip().rstrip("/")
            for origin in raw_value
            if str(origin).strip()
        )
    else:
        origins = ()

    if origins:
        return origins

    if is_development_like(config):
        return ("*",)

    return ()


def validate_runtime_secrets(config: Mapping[str, object]) -> None:
    """Fail fast on insecure secrets outside development-like runtimes."""
    if is_development_like(config):
        return

    invalid_settings: list[str] = []

    for setting_name in ("SECRET_KEY", "JWT_SECRET_KEY"):
        secret = str(config.get(setting_name) or "").strip()
        if len(secret) < MIN_SECRET_LENGTH or _looks_placeholder(secret):
            invalid_settings.append(setting_name)

    if invalid_settings:
        names = ", ".join(invalid_settings)
        raise ValueError(
            f"Insecure runtime secret configuration for {names}. "
            f"Set strong values with at least {MIN_SECRET_LENGTH} characters."
        )


def is_openai_configured(config: Mapping[str, object]) -> bool:
    """Return True when photo validation has a configured provider key."""
    return bool(str(config.get("OPENAI_API_KEY") or "").strip())


def describe_openai_configuration(config: Mapping[str, object]) -> dict[str, object]:
    """Describe validation configuration without overstating provider readiness."""
    if not is_openai_configured(config):
        return {
            "provider": "openai",
            "configured": False,
            "status": "not_configured",
            "message": "OpenAI API key is not configured.",
        }

    return {
        "provider": "openai",
        "configured": True,
        "status": "configured_unverified",
        "message": "OpenAI API key is configured; provider availability is verified at request time.",
    }
