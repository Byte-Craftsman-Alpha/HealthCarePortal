from __future__ import annotations

from datetime import datetime

import os

from flask import abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.doctor import doctor_bp
from app.blueprints.rbac import doctor_consent_required, roles_required
from app.extensions import db
from app.models import Appointment, Consent, MedicalRecord, Patient, Prescription
from app.utils.audit import log_action, log_event


@doctor_bp.get("/dashboard")
@roles_required("doctor")
def dashboard():
    upcoming = (
        Appointment.query.filter_by(doctor_id=current_user.id)
        .order_by(Appointment.scheduled_at.asc())
        .limit(10)
        .all()
    )
    active_consents = Consent.query.filter_by(doctor_id=current_user.id, revoked_at=None).count()
    return render_template("doctor/dashboard.html", upcoming=upcoming, active_consents=active_consents)


@doctor_bp.get("/appointments")
@roles_required("doctor")
def appointments():
    appts = (
        Appointment.query.filter_by(doctor_id=current_user.id)
        .order_by(Appointment.scheduled_at.desc())
        .all()
    )
    return render_template("doctor/appointments.html", appointments=appts)


@doctor_bp.get("/patients")
@roles_required("doctor")
def patients():
    consents = Consent.query.filter_by(doctor_id=current_user.id, revoked_at=None).all()
    patient_ids = [c.patient_id for c in consents]
    patients = Patient.query.filter(Patient.user_id.in_(patient_ids)).all() if patient_ids else []
    return render_template("doctor/patients.html", patients=patients)


@doctor_bp.get("/patients/<int:patient_id>")
@doctor_consent_required("patient_id")
def patient_detail(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)

    consent = Consent.query.filter_by(patient_id=patient.user_id, doctor_id=current_user.id).first()
    can_add_record = bool(consent and consent.is_active and getattr(consent, "can_add_record", False))

    records = (
        MedicalRecord.query.filter_by(patient_id=patient.user_id)
        .order_by(MedicalRecord.uploaded_at.desc())
        .all()
    )
    appts = (
        Appointment.query.filter_by(doctor_id=current_user.id, patient_id=patient.user_id)
        .order_by(Appointment.scheduled_at.desc())
        .all()
    )
    log_event("doctor_view_patient", "patient", patient_id=patient.user_id, doctor_id=current_user.id, entity_id=patient.user_id)
    return render_template(
        "doctor/patient_detail.html",
        patient=patient,
        records=records,
        appointments=appts,
        can_add_record=can_add_record,
    )


@doctor_bp.post("/patients/<int:patient_id>/records")
@doctor_consent_required("patient_id")
def add_record(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)

    consent = Consent.query.filter_by(patient_id=patient.user_id, doctor_id=current_user.id).first()
    if consent is None or not consent.is_active or not getattr(consent, "can_add_record", False):
        abort(403)

    f = request.files.get("file")
    description = (request.form.get("description") or "").strip() or None
    appointment_id_raw = (request.form.get("appointment_id") or "").strip()

    if not f or not f.filename:
        abort(400)

    appointment_id = None
    if appointment_id_raw and appointment_id_raw.isdigit():
        appointment_id = int(appointment_id_raw)
        owned = Appointment.query.filter_by(id=appointment_id, patient_id=patient.user_id, doctor_id=current_user.id).first()
        if owned is None:
            appointment_id = None

    upload_root = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "static", "uploads"))
    os.makedirs(upload_root, exist_ok=True)

    safe_name = f"doc_{current_user.id}_patient_{patient.user_id}_{int(datetime.utcnow().timestamp())}_{os.path.basename(f.filename)}"
    rel_path = os.path.join("uploads", safe_name)
    abs_path = os.path.join(current_app.root_path, "static", rel_path)
    f.save(abs_path)

    rec = MedicalRecord(
        patient_id=patient.user_id,
        file_path=rel_path,
        description=description,
        appointment_id=appointment_id,
        created_by_user_id=current_user.id,
    )
    db.session.add(rec)
    db.session.commit()

    log_action("doctor_add_medical_record", "medical_record")
    log_event("record_added_by_doctor", "medical_record", patient_id=patient.user_id, doctor_id=current_user.id, entity_id=rec.id)
    return redirect(url_for("doctor.patient_detail", patient_id=patient.user_id))


@doctor_bp.get("/records/<int:record_id>/view")
@roles_required("doctor")
def record_view(record_id: int):
    rec = MedicalRecord.query.get_or_404(record_id)
    consent = Consent.query.filter_by(patient_id=rec.patient_id, doctor_id=current_user.id).first()
    if consent is None or not consent.is_active or not getattr(consent, "can_view_history", True):
        abort(403)

    log_event("doctor_view_record", "medical_record", patient_id=rec.patient_id, doctor_id=current_user.id, entity_id=rec.id)
    return redirect(url_for("static", filename=rec.file_path))


@doctor_bp.route("/appointments/<int:appointment_id>/prescribe", methods=["GET", "POST"])
@roles_required("doctor")
def prescribe(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        abort(403)

    consent = Consent.query.filter_by(patient_id=appt.patient_id, doctor_id=current_user.id).first()
    if consent is None or not consent.is_active:
        abort(403)

    existing = Prescription.query.filter_by(appointment_id=appt.id).first()

    if request.method == "POST":
        notes = (request.form.get("notes") or "").strip() or None
        pharmacy_id = (request.form.get("pharmacy_id") or "").strip() or None

        if existing is None:
            existing = Prescription(appointment_id=appt.id, issued_at=datetime.utcnow())
            db.session.add(existing)

        existing.notes = notes
        existing.pharmacy_id = pharmacy_id
        existing.fulfillment_status = "pending"
        existing.delivery_status = "not_started"

        db.session.commit()
        log_action("issue_prescription", "prescription")
        return redirect(url_for("doctor.appointments"))

    return render_template("doctor/prescribe.html", appointment=appt, prescription=existing)
