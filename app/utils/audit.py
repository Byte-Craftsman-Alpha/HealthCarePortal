from __future__ import annotations

from flask_login import current_user

from app.extensions import db
from app.models import AuditLog


def log_action(action: str, entity: str) -> None:
    actor_id = None
    if getattr(current_user, "is_authenticated", False):
        actor_id = current_user.id

    db.session.add(AuditLog(actor_id=actor_id, action=action, entity=entity))
    db.session.commit()
