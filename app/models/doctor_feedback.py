from __future__ import annotations

from datetime import datetime

from app.extensions import db


class DoctorFeedback(db.Model):
    __tablename__ = "doctor_feedback"

    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating = db.Column(db.Integer, nullable=False, default=5)
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    doctor = db.relationship("Doctor")
    patient = db.relationship("Patient")

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "patient_id", name="uq_feedback_doctor_patient"),
    )

    def __repr__(self) -> str:
        return f"<DoctorFeedback id={self.id} doctor_id={self.doctor_id} patient_id={self.patient_id} rating={self.rating}>"
