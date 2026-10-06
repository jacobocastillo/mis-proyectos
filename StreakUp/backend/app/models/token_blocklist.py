from datetime import datetime

from app.extensions import db


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    token_type = db.Column(db.String(10), nullable=False, default="access")
    revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
