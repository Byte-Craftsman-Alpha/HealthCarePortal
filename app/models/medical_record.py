from __future__ import annotations

from datetime import datetime

from app.extensions import db


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    file_path = db.Column(db.String(512), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient = db.relationship("Patient", back_populates="medical_records")
    appointment = db.relationship("Appointment")
    created_by = db.relationship("User")

    def __repr__(self) -> str:
        return f"<MedicalRecord id={self.id} patient_id={self.patient_id}>"
