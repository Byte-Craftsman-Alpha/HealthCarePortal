from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    org_type = db.Column(db.String(32), nullable=False, default="hospital", index=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    doctors = db.relationship(
        "Doctor",
        back_populates="organization",
        cascade="all",
        passive_deletes=True,
    )

    appointments = db.relationship(
        "Appointment",
        back_populates="organization",
        cascade="all",
        passive_deletes=True,
    )

    consents = db.relationship(
        "Consent",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name}>"
