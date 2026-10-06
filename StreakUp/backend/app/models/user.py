"""
User model module.

Responsibility:
- Define persistence structure for user entities.
- Password hashing and verification at model level.
"""

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    """User entity with secure password storage."""

    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint("total_xp >= 0", name="ck_users_total_xp_nonnegative"),
        db.CheckConstraint("level >= 1", name="ck_users_level_positive"),
        db.CheckConstraint("xp_in_level >= 0", name="ck_users_xp_in_level_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.String(20), nullable=False, default="user", server_default=db.text("'user'")
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    total_xp = db.Column(db.Integer, nullable=False, default=0, server_default=db.text("0"))
    level = db.Column(db.Integer, nullable=False, default=1, server_default=db.text("1"))
    xp_in_level = db.Column(db.Integer, nullable=False, default=0, server_default=db.text("0"))

    @property
    def xp_progress_pct(self) -> float:
        """Return XP progress percentage within the current level."""
        xp_per_level = 250
        return round((self.xp_in_level / xp_per_level) * 100, 1) if xp_per_level > 0 else 0

    def set_password(self, password: str) -> None:
        """Hash and store the given plain-text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Return a JSON-safe representation (never expose password_hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
