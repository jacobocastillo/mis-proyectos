"""
User profile validation helpers.

Responsibility:
- Validate authenticated profile update payloads.
"""

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 80


def validate_profile_update_input(data: dict | None) -> tuple[dict[str, str], list[str]]:
    """Validate profile update payload and return normalized fields plus errors."""
    if not data:
        return {}, ["Request body is required."]

    errors: list[str] = []
    normalized: dict[str, str] = {}

    if "email" in data:
        errors.append("Email cannot be changed from this endpoint.")

    if "username" not in data:
        errors.append("Username is required.")
    else:
        raw_username = data.get("username")
        username = raw_username.strip() if isinstance(raw_username, str) else ""
        if not username:
            errors.append("Username is required.")
        elif len(username) < MIN_USERNAME_LENGTH:
            errors.append(f"Username must be at least {MIN_USERNAME_LENGTH} characters.")
        elif len(username) > MAX_USERNAME_LENGTH:
            errors.append(f"Username must be at most {MAX_USERNAME_LENGTH} characters.")
        else:
            normalized["username"] = username

    return normalized, errors
