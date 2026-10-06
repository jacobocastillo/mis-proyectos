"""
Authentication service module.

Responsibility:
- Host authentication domain use cases (register, login).
- Coordinate between User model and JWT token issuance.
"""

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from app.extensions import db
from app.models.user import User


def register_user(username: str, email: str, password: str) -> dict:
    """Register a new user with a hashed password.

    Returns:
        dict with user data on success.

    Raises:
        ValueError: if username or email already exists.
    """
    username = username.strip()
    email = email.strip().lower()

    if User.query.filter_by(email=email).first():
        raise ValueError("A user with this email already exists.")

    if User.query.filter_by(username=username).first():
        raise ValueError("A user with this username already exists.")

    user = User(username=username, email=email, role="user")
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return user.to_dict()


def login_user(email: str, password: str) -> dict:
    """Authenticate a user and return JWT tokens.

    Returns:
        dict with access_token, refresh_token, and user data.

    Raises:
        ValueError: if credentials are invalid.
    """
    email = email.strip().lower()

    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(password):
        raise ValueError("Invalid email or password.")

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }


def refresh_access_token(refresh_token_str: str) -> dict:
    """Exchange a valid refresh token for a new access token.

    Returns:
        dict with new access_token.

    Raises:
        ValueError: if the token is invalid, expired, or not a refresh token.
    """
    try:
        decoded = decode_token(refresh_token_str)
    except Exception as exc:
        raise ValueError("Invalid or expired refresh token.") from exc

    if decoded.get("type") != "refresh":
        raise ValueError("Invalid or expired refresh token.")

    user_id_str = decoded.get("sub", "")
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired refresh token.") from exc

    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("Invalid or expired refresh token.")

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    return {"access_token": access_token}


def revoke_token(jti: str, token_type: str = "access") -> None:
    """Add a token JTI to the blocklist to permanently revoke it."""
    from app.models.token_blocklist import TokenBlocklist

    entry = TokenBlocklist(jti=jti, token_type=token_type)
    db.session.add(entry)
    db.session.commit()
