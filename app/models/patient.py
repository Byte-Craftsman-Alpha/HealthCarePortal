from __future__ import annotations

from app.extensions import db


class Patient(db.Model):
    __tablename__ = "patients"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    dob = db.Column(db.String(32), nullable=True)
    gender = db.Column(db.String(32), nullable=True)

    blood_group = db.Column(db.String(8), nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    chronic_conditions = db.Column(db.Text, nullable=True)
    emergency_contacts = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="patient")

    medical_records = db.relationship(
        "MedicalRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    consents = db.relationship(
        "Consent",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Patient user_id={self.user_id}>"
