from __future__ import annotations

from app.extensions import db


class Doctor(db.Model):
    __tablename__ = "doctors"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    specialization = db.Column(db.String(128), nullable=False)
    hospital_id = db.Column(db.String(64), nullable=True, index=True)

    user = db.relationship("User", back_populates="doctor")

    appointments = db.relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    consents = db.relationship(
        "Consent",
        back_populates="doctor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Doctor user_id={self.user_id} specialization={self.specialization}>"
