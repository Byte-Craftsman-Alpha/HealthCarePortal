from __future__ import annotations

import os
from datetime import datetime

from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from app.blueprints.patient import patient_bp
from app.blueprints.rbac import roles_required
from app.extensions import db
from app.models import Appointment, AuditEvent, Consent, Doctor, DoctorFeedback, MedicalRecord, Patient, Prescription, User
from app.utils.audit import log_action, log_event


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

    appts = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .order_by(Appointment.scheduled_at.desc())
        .limit(50)
        .all()
    )

    if request.method == "POST":
        f = request.files.get("file")
        description = (request.form.get("description") or "").strip()
        appointment_id_raw = (request.form.get("appointment_id") or "").strip()

        if not f or not f.filename:
            return render_template(
                "patient/records.html",
                patient=patient,
                records=_patient_records(),
                appointments=appts,
                error="Please choose a file to upload.",
            )

        appointment_id = None
        if appointment_id_raw and appointment_id_raw.isdigit():
            appointment_id = int(appointment_id_raw)
            owned = Appointment.query.filter_by(id=appointment_id, patient_id=current_user.id).first()
            if owned is None:
                appointment_id = None

        upload_root = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "static", "uploads"))
        os.makedirs(upload_root, exist_ok=True)

        safe_name = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{os.path.basename(f.filename)}"
        rel_path = os.path.join("uploads", safe_name)
        abs_path = os.path.join(current_app.root_path, "static", rel_path)

        f.save(abs_path)

        rec = MedicalRecord(
            patient_id=current_user.id,
            file_path=rel_path,
            description=description or None,
            appointment_id=appointment_id,
            created_by_user_id=current_user.id,
        )
        db.session.add(rec)
        db.session.commit()
        log_action("upload_medical_record", "medical_record")
        log_event("record_uploaded", "medical_record", patient_id=current_user.id, doctor_id=None, entity_id=rec.id)

        return redirect(url_for("patient.records"))

    log_event("view_records", "medical_record", patient_id=current_user.id, doctor_id=None, entity_id=None)
    return render_template("patient/records.html", patient=patient, records=_patient_records(), appointments=appts)


@patient_bp.get("/records/<int:record_id>/view")
@roles_required("patient")
def record_view(record_id: int):
    rec = MedicalRecord.query.get_or_404(record_id)
    if rec.patient_id != current_user.id:
        return redirect(url_for("patient.records"))

    log_event("record_viewed", "medical_record", patient_id=current_user.id, doctor_id=None, entity_id=rec.id)
    return redirect(url_for("static", filename=rec.file_path))


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

    selected_doctor_id = request.args.get("doctor_id")
    return render_template(
        "patient/appointments.html",
        doctors=doctors,
        appointments=_patient_appointments(),
        selected_doctor_id=int(selected_doctor_id) if selected_doctor_id and selected_doctor_id.isdigit() else None,
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

        can_view_history = (request.form.get("can_view_history") or "").strip().lower() in {"1", "true", "on", "yes"}
        can_add_record = (request.form.get("can_add_record") or "").strip().lower() in {"1", "true", "on", "yes"}

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

        consent.can_view_history = can_view_history
        consent.can_add_record = can_add_record

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


@patient_bp.get("/doctors")
@roles_required("patient")
def doctors():
    q = (request.args.get("q") or "").strip()

    query = Doctor.query.join(Doctor.user)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Doctor.specialization.ilike(like),
                Doctor.hospital_id.ilike(like),
                User.email.ilike(like),
                User.name.ilike(like),
            )
        )

    doctors = query.order_by(Doctor.specialization.asc()).all()
    log_action("view_doctors_directory", "doctor")
    return render_template("patient/doctors.html", doctors=doctors, q=q)


@patient_bp.route("/doctors/<int:doctor_id>", methods=["GET", "POST"])
@roles_required("patient")
def doctor_detail(doctor_id: int):
    doctor = Doctor.query.get_or_404(doctor_id)

    my_feedback = DoctorFeedback.query.filter_by(doctor_id=doctor.user_id, patient_id=current_user.id).first()

    if request.method == "POST":
        rating_raw = (request.form.get("rating") or "5").strip()
        comment = (request.form.get("comment") or "").strip() or None

        try:
            rating = int(rating_raw)
        except ValueError:
            rating = 5

        if rating < 1:
            rating = 1
        if rating > 5:
            rating = 5

        if my_feedback is None:
            my_feedback = DoctorFeedback(doctor_id=doctor.user_id, patient_id=current_user.id)
            db.session.add(my_feedback)

        my_feedback.rating = rating
        my_feedback.comment = comment
        db.session.commit()
        log_action("submit_doctor_feedback", "doctor_feedback")
        return redirect(url_for("patient.doctor_detail", doctor_id=doctor.user_id))

    feedback = (
        DoctorFeedback.query.filter_by(doctor_id=doctor.user_id)
        .order_by(DoctorFeedback.created_at.desc())
        .limit(10)
        .all()
    )

    log_action("view_doctor_profile", "doctor")
    return render_template(
        "patient/doctor_detail.html",
        doctor=doctor,
        feedback=feedback,
        my_feedback=my_feedback,
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


@patient_bp.get("/activity")
@roles_required("patient")
def activity():
    events = (
        AuditEvent.query.filter_by(patient_id=current_user.id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(250)
        .all()
    )
    log_event("view_activity", "audit_event", patient_id=current_user.id, doctor_id=None, entity_id=None)
    return render_template("patient/activity.html", events=events)


@patient_bp.get("/history")
@roles_required("patient")
def history():
    appts = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .order_by(Appointment.scheduled_at.desc())
        .all()
    )

    appt_ids = [a.id for a in appts]
    records_by_appt: dict[int, list[MedicalRecord]] = {}
    if appt_ids:
        linked = (
            MedicalRecord.query.filter(MedicalRecord.patient_id == current_user.id, MedicalRecord.appointment_id.in_(appt_ids))
            .order_by(MedicalRecord.uploaded_at.desc())
            .all()
        )
        for r in linked:
            records_by_appt.setdefault(r.appointment_id, []).append(r)

    unlinked_records = (
        MedicalRecord.query.filter_by(patient_id=current_user.id, appointment_id=None)
        .order_by(MedicalRecord.uploaded_at.desc())
        .all()
    )

    log_event("view_history", "appointment", patient_id=current_user.id, doctor_id=None, entity_id=None)
    return render_template(
        "patient/history.html",
        appointments=appts,
        records_by_appt=records_by_appt,
        unlinked_records=unlinked_records,
    )


@patient_bp.route("/profile", methods=["GET", "POST"])
@roles_required("patient")
def profile():
    patient = Patient.query.get(current_user.id)

    if request.method == "POST":
        current_user.name = (request.form.get("name") or "").strip() or None
        current_user.phone = (request.form.get("phone") or "").strip() or None

        patient.dob = (request.form.get("dob") or "").strip() or None
        patient.gender = (request.form.get("gender") or "").strip() or None

        patient.blood_group = (request.form.get("blood_group") or "").strip() or None
        patient.allergies = (request.form.get("allergies") or "").strip() or None
        patient.chronic_conditions = (request.form.get("chronic_conditions") or "").strip() or None
        patient.emergency_contacts = (request.form.get("emergency_contacts") or "").strip() or None

        db.session.commit()
        log_action("update_patient_profile", "patient")
        return redirect(url_for("patient.profile"))

    return render_template("patient/profile.html", patient=patient)


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
