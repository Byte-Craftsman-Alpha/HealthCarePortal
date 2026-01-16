from __future__ import annotations

from datetime import datetime

from app.extensions import db


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action = db.Column(db.String(128), nullable=False, index=True)
    entity = db.Column(db.String(128), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=True, index=True)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    actor = db.relationship("User")

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} patient_id={self.patient_id} action={self.action} entity={self.entity}>"
