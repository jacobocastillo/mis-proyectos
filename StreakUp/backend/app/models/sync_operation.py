"""
Sync operation receipt model.

Responsibility:
- Record processed client operations so sync replay is idempotent.
"""

from datetime import datetime, timezone

from app.extensions import db


class SyncOperation(db.Model):
    """Receipt for one client-originated sync operation."""

    __tablename__ = "sync_operations"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "client_operation_id",
            name="uq_sync_operations_user_client_operation",
        ),
        db.CheckConstraint(
            "status IN ('acked','failed','conflict')",
            name="ck_sync_operations_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_operation_id = db.Column(db.String(120), nullable=False)
    operation_type = db.Column(db.String(60), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    response_json = db.Column(db.Text, nullable=False)
    error_code = db.Column(db.String(80), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    processed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("User", backref=db.backref("sync_operations", lazy=True))
