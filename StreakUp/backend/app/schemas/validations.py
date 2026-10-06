"""
Validation schemas module.

Responsibility:
- Define payload validation rules for auth inputs.
"""

import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
MIN_PASSWORD_LENGTH = 8


def validate_register_input(data: dict | None) -> list[str]:
    """Validate registration payload. Returns list of error messages."""
    errors: list[str] = []

    if not data:
        return ["Request body is required."]

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 80:
        errors.append("Username must be at most 80 characters.")

    if not email:
        errors.append("Email is required.")
    elif not EMAIL_REGEX.match(email):
        errors.append("Invalid email format.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    return errors


def validate_login_input(data: dict | None) -> list[str]:
    """Validate login payload. Returns list of error messages."""
    errors: list[str] = []

    if not data:
        return ["Request body is required."]

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email:
        errors.append("Email is required.")

    if not password:
        errors.append("Password is required.")

    return errors
