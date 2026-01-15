from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)

    pharmacy_id = db.Column(db.String(64), nullable=True, index=True)
    fulfillment_status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    delivery_status = db.Column(db.String(32), nullable=False, default="not_started", index=True)

    appointment = db.relationship("Appointment", back_populates="prescription")

    def __repr__(self) -> str:
        return f"<Prescription id={self.id} appointment_id={self.appointment_id} status={self.fulfillment_status}>"
