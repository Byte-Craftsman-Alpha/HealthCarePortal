from __future__ import annotations

from flask import redirect, render_template, request, url_for

from app.blueprints.admin import admin_bp
from app.blueprints.rbac import roles_required
from app.extensions import db
from app.models import AuditLog, Doctor, User
from app.utils.audit import log_action


@admin_bp.get("/overview")
@roles_required("admin")
def overview():
    counts = {
        "users": User.query.count(),
        "doctors": Doctor.query.count(),
        "audit_logs": AuditLog.query.count(),
    }
    return render_template("admin/overview.html", counts=counts)


@admin_bp.route("/users", methods=["GET", "POST"])
@roles_required("admin")
def users():
    if request.method == "POST":
        user_id = int(request.form.get("user_id") or "0")
        role = (request.form.get("role") or "").strip().lower()

        u = User.query.get(user_id)
        if u and role in {"patient", "doctor", "admin", "pharmacy", "emergency"}:
            u.role = role
            db.session.commit()
            log_action("admin_update_role", "user")

        return redirect(url_for("admin.users"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/doctors", methods=["GET", "POST"])
@roles_required("admin")
def doctors():
    if request.method == "POST":
        user_id = int(request.form.get("user_id") or "0")
        specialization = (request.form.get("specialization") or "").strip()
        hospital_id = (request.form.get("hospital_id") or "").strip()

        d = Doctor.query.get(user_id)
        if d:
            d.specialization = specialization or d.specialization
            d.hospital_id = hospital_id or d.hospital_id
            db.session.commit()
            log_action("admin_update_doctor", "doctor")

        return redirect(url_for("admin.doctors"))

    doctors = Doctor.query.all()
    return render_template("admin/doctors.html", doctors=doctors)


@admin_bp.get("/audit-logs")
@roles_required("admin")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return render_template("admin/audit_logs.html", logs=logs)
