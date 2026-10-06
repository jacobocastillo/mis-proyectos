"""
User service module.

Responsibility:
- Host profile/account use cases for authenticated users.
"""

from app.extensions import db
from app.models.user import User


def update_user_profile(user_id: int, *, username: str) -> dict:
    """Update basic profile fields for a user and return the public profile."""
    user = db.session.get(User, user_id)
    if user is None:
        raise LookupError("Usuario no encontrado.")

    existing = User.query.filter(User.username == username, User.id != user_id).first()
    if existing is not None:
        raise ValueError("A user with this username already exists.")

    user.username = username
    db.session.commit()
    return user.to_dict()
