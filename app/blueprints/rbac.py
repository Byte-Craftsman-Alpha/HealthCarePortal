from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

from flask import abort
from flask_login import current_user, login_required

from app.models import Consent, Patient


def roles_required(*roles: str):
    def decorator(fn: Callable):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                abort(401)

            if current_user.role not in roles:
                abort(403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def doctor_consent_required(patient_id_arg: str = "patient_id"):
    def decorator(fn: Callable):
        @wraps(fn)
        @roles_required("doctor")
        def wrapper(*args, **kwargs):
            patient_id = kwargs.get(patient_id_arg)
            if patient_id is None:
                abort(400)

            patient = Patient.query.get(int(patient_id))
            if patient is None:
                abort(404)

            org_id = None
            try:
                if getattr(current_user, "doctor", None) is not None:
                    org_id = current_user.doctor.organization_id
            except Exception:
                org_id = None

            if org_id is None:
                abort(403)

            consent = Consent.query.filter_by(patient_id=patient.user_id, organization_id=org_id).first()
            if consent is None or not consent.is_active or not getattr(consent, "can_view_history", True):
                abort(403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def pharmacy_scope_required():
    def decorator(fn: Callable):
        @wraps(fn)
        @roles_required("pharmacy")
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    return decorator
