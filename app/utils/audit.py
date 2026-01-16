from __future__ import annotations

from flask_login import current_user

from app.extensions import db
from app.models import AuditEvent, AuditLog


def log_action(action: str, entity: str) -> None:
    actor_id = None
    if getattr(current_user, "is_authenticated", False):
        actor_id = current_user.id

    db.session.add(AuditLog(actor_id=actor_id, action=action, entity=entity))
    db.session.commit()


def log_event(
    action: str,
    entity: str,
    patient_id: int,
    doctor_id: int | None = None,
    organization_id: int | None = None,
    entity_id: int | None = None,
) -> None:
    actor_id = None
    if getattr(current_user, "is_authenticated", False):
        actor_id = current_user.id

    db.session.add(
        AuditEvent(
            actor_id=actor_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            organization_id=organization_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
        )
    )
    db.session.commit()
