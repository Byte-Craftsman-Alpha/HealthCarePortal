from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Consent(db.Model):
    __tablename__ = "consents"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    can_view_history = db.Column(db.Boolean, nullable=False, default=True)
    can_add_record = db.Column(db.Boolean, nullable=False, default=False)

    patient = db.relationship("Patient", back_populates="consents")
    doctor = db.relationship("Doctor", back_populates="consents")

    __table_args__ = (
        db.UniqueConstraint("patient_id", "doctor_id", name="uq_consent_patient_doctor"),
    )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def __repr__(self) -> str:
        return f"<Consent patient_id={self.patient_id} doctor_id={self.doctor_id} active={self.is_active}>"
