from __future__ import annotations

from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.pharmacy import pharmacy_bp
from app.blueprints.rbac import roles_required
from app.extensions import db
from app.models import Appointment, Prescription
from app.utils.audit import log_action


@pharmacy_bp.get("/queue")
@roles_required("pharmacy")
def queue():
    prescriptions = (
        Prescription.query.join(Prescription.appointment)
        .filter(Prescription.pharmacy_id == str(current_user.id))
        .order_by(Prescription.issued_at.desc())
        .all()
    )
    return render_template("pharmacy/queue.html", prescriptions=prescriptions)


@pharmacy_bp.post("/prescriptions/<int:prescription_id>/update")
@roles_required("pharmacy")
def update(prescription_id: int):
    p = Prescription.query.get_or_404(prescription_id)
    if p.pharmacy_id != str(current_user.id):
        abort(403)

    fulfillment_status = (request.form.get("fulfillment_status") or "pending").strip()
    delivery_status = (request.form.get("delivery_status") or "not_started").strip()

    p.fulfillment_status = fulfillment_status
    p.delivery_status = delivery_status
    db.session.commit()
    log_action("pharmacy_update_fulfillment", "prescription")

    return redirect(url_for("pharmacy.queue"))
