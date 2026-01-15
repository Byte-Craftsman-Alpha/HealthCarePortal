from __future__ import annotations

import os
from datetime import datetime

from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.patient import patient_bp
from app.blueprints.rbac import roles_required
from app.extensions import db
from app.models import Appointment, Consent, Doctor, MedicalRecord, Patient, Prescription
from app.utils.audit import log_action


@patient_bp.get("/dashboard")
@roles_required("patient")
def dashboard():
    patient = Patient.query.get(current_user.id)
    recent_appointments = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .order_by(Appointment.scheduled_at.desc())
        .limit(5)
        .all()
    )
    recent_records = (
        MedicalRecord.query.filter_by(patient_id=current_user.id)
        .order_by(MedicalRecord.uploaded_at.desc())
        .limit(5)
        .all()
    )
    active_consents = Consent.query.filter_by(patient_id=current_user.id, revoked_at=None).count()

    return render_template(
        "patient/dashboard.html",
        patient=patient,
        recent_appointments=recent_appointments,
        recent_records=recent_records,
        active_consents=active_consents,
    )


@patient_bp.route("/records", methods=["GET", "POST"])
@roles_required("patient")
def records():
    patient = Patient.query.get(current_user.id)

    if request.method == "POST":
        f = request.files.get("file")
        description = (request.form.get("description") or "").strip()

        if not f or not f.filename:
            return render_template(
                "patient/records.html",
                patient=patient,
                records=_patient_records(),
                error="Please choose a file to upload.",
            )

        upload_root = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "static", "uploads"))
        os.makedirs(upload_root, exist_ok=True)

        safe_name = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{os.path.basename(f.filename)}"
        rel_path = os.path.join("uploads", safe_name)
        abs_path = os.path.join(current_app.root_path, "static", rel_path)

        f.save(abs_path)

        rec = MedicalRecord(patient_id=current_user.id, file_path=rel_path, description=description or None)
        db.session.add(rec)
        db.session.commit()
        log_action("upload_medical_record", "medical_record")

        return redirect(url_for("patient.records"))

    return render_template("patient/records.html", patient=patient, records=_patient_records())


def _patient_records():
    return (
        MedicalRecord.query.filter_by(patient_id=current_user.id)
        .order_by(MedicalRecord.uploaded_at.desc())
        .all()
    )


@patient_bp.route("/appointments", methods=["GET", "POST"])
@roles_required("patient")
def appointments():
    doctors = (
        Doctor.query.join(Doctor.user)
        .order_by(Doctor.specialization.asc())
        .all()
    )

    if request.method == "POST":
        doctor_id = int(request.form.get("doctor_id") or "0")
        scheduled_at_raw = request.form.get("scheduled_at") or ""

        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_raw)
        except ValueError:
            return render_template(
                "patient/appointments.html",
                doctors=doctors,
                appointments=_patient_appointments(),
                error="Invalid date/time.",
            )

        appt = Appointment(patient_id=current_user.id, doctor_id=doctor_id, scheduled_at=scheduled_at, status="scheduled")
        db.session.add(appt)
        db.session.commit()
        log_action("book_appointment", "appointment")

        return redirect(url_for("patient.appointments"))

    return render_template(
        "patient/appointments.html",
        doctors=doctors,
        appointments=_patient_appointments(),
    )


def _patient_appointments():
    return (
        Appointment.query.filter_by(patient_id=current_user.id)
        .order_by(Appointment.scheduled_at.desc())
        .all()
    )


@patient_bp.route("/consents", methods=["GET", "POST"])
@roles_required("patient")
def consents():
    doctors = Doctor.query.all()

    if request.method == "POST":
        doctor_id = int(request.form.get("doctor_id") or "0")
        action = (request.form.get("action") or "grant").strip()

        consent = Consent.query.filter_by(patient_id=current_user.id, doctor_id=doctor_id).first()

        if action == "revoke":
            if consent and consent.revoked_at is None:
                consent.revoked_at = datetime.utcnow()
                db.session.commit()
                log_action("revoke_consent", "consent")
            return redirect(url_for("patient.consents"))

        if consent is None:
            consent = Consent(patient_id=current_user.id, doctor_id=doctor_id)
            db.session.add(consent)
        else:
            consent.revoked_at = None
            consent.granted_at = datetime.utcnow()

        db.session.commit()
        log_action("grant_consent", "consent")
        return redirect(url_for("patient.consents"))

    existing = Consent.query.filter_by(patient_id=current_user.id).all()
    consent_by_doctor = {c.doctor_id: c for c in existing}

    return render_template(
        "patient/consents.html",
        doctors=doctors,
        consent_by_doctor=consent_by_doctor,
    )


@patient_bp.get("/prescriptions")
@roles_required("patient")
def prescriptions():
    prescriptions = (
        Prescription.query.join(Prescription.appointment)
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Prescription.issued_at.desc())
        .all()
    )
    return render_template("patient/prescriptions.html", prescriptions=prescriptions)


@patient_bp.route("/emergency-profile", methods=["GET", "POST"])
@roles_required("patient")
def emergency_profile():
    patient = Patient.query.get(current_user.id)

    if request.method == "POST":
        patient.blood_group = (request.form.get("blood_group") or "").strip() or None
        patient.allergies = (request.form.get("allergies") or "").strip() or None
        patient.chronic_conditions = (request.form.get("chronic_conditions") or "").strip() or None
        patient.emergency_contacts = (request.form.get("emergency_contacts") or "").strip() or None
        db.session.commit()
        log_action("update_emergency_profile", "patient")
        return redirect(url_for("patient.emergency_profile"))

    return render_template("patient/emergency_profile.html", patient=patient)
