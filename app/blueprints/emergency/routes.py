from __future__ import annotations

from flask import render_template, request

from app.blueprints.emergency import emergency_bp
from app.blueprints.rbac import roles_required
from app.models import Patient, User
from app.utils.audit import log_action


@emergency_bp.route("/lookup", methods=["GET", "POST"])
@roles_required("emergency")
def lookup():
    patient = None
    if request.method == "POST":
        q = (request.form.get("query") or "").strip().lower()

        user = None
        if q.isdigit():
            user = User.query.get(int(q))
        if user is None:
            user = User.query.filter_by(email=q).first()

        if user and user.role == "patient":
            patient = Patient.query.get(user.id)
            if patient:
                log_action("emergency_lookup", "patient")

    return render_template("emergency/lookup.html", patient=patient)
