from __future__ import annotations

from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.models import Doctor, Patient, User
from app.utils.audit import log_action


def _redirect_for_role(role: str):
    if role == "patient":
        return redirect(url_for("patient.dashboard"))
    if role == "doctor":
        return redirect(url_for("doctor.dashboard"))
    if role == "admin":
        return redirect(url_for("admin.overview"))
    if role == "pharmacy":
        return redirect(url_for("pharmacy.queue"))
    if role == "emergency":
        return redirect(url_for("emergency.lookup"))
    return redirect(url_for("auth.login"))


@auth_bp.get("/")
def home():
    if current_user.is_authenticated:
        return _redirect_for_role(current_user.role)
    return render_template("landing.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            log_action("login", "user")
            return _redirect_for_role(user.role)

        return render_template("auth/login.html", error="Invalid credentials")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        name = (request.form.get("name") or "").strip() or None
        phone = (request.form.get("phone") or "").strip() or None
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "patient").strip().lower()

        if role not in {"patient", "doctor", "pharmacy", "emergency"}:
            role = "patient"

        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template("auth/register.html", error="Email already registered")

        user = User(email=email, role=role, name=name, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        if role == "patient":
            db.session.add(Patient(user_id=user.id))
            db.session.commit()

        if role == "doctor":
            specialization = (request.form.get("specialization") or "General Medicine").strip()
            hospital_id = (request.form.get("hospital_id") or "HOSP-001").strip()
            db.session.add(Doctor(user_id=user.id, specialization=specialization, hospital_id=hospital_id))
            db.session.commit()

        log_action("register", "user")
        login_user(user)
        return _redirect_for_role(user.role)

    return render_template("auth/register.html")


@auth_bp.post("/logout")
def logout():
    log_action("logout", "user")
    logout_user()
    return redirect(url_for("auth.login"))
