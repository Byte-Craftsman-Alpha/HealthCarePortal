from flask import Flask, request, url_for
from datetime import datetime

from app.config import CONFIG_BY_NAME
from app.extensions import db, login_manager, migrate


def create_app(env_name: str = "development") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    config_cls = CONFIG_BY_NAME.get(env_name, CONFIG_BY_NAME["development"])
    app.config.from_object(config_cls)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models  # noqa: F401
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.patient.routes import patient_bp
    from app.blueprints.doctor.routes import doctor_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.pharmacy.routes import pharmacy_bp
    from app.blueprints.emergency.routes import emergency_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp, url_prefix="/patient")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(pharmacy_bp, url_prefix="/pharmacy")
    app.register_blueprint(emergency_bp, url_prefix="/emergency")

    @app.context_processor
    def inject_page_meta():
        endpoint = request.endpoint or ""
        role = getattr(request, "current_user", None)
        role_name = ""
        try:
            from flask_login import current_user

            role_name = current_user.role if current_user.is_authenticated else ""
        except Exception:
            role_name = ""

        mappings = {
            "patient": {
                "patient.dashboard": ("Dashboard", [("Home", url_for("patient.dashboard")), ("Dashboard", None)]),
                "patient.profile": ("Profile", [("Home", url_for("patient.dashboard")), ("Profile", None)]),
                "patient.doctors": ("Doctors", [("Home", url_for("patient.dashboard")), ("Doctors", None)]),
                "patient.doctor_detail": ("Doctor profile", [("Home", url_for("patient.dashboard")), ("Doctors", url_for("patient.doctors")), ("Doctor profile", None)]),
                "patient.records": ("Records", [("Home", url_for("patient.dashboard")), ("Records", None)]),
                "patient.history": ("History", [("Home", url_for("patient.dashboard")), ("History", None)]),
                "patient.activity": ("Activity", [("Home", url_for("patient.dashboard")), ("Activity", None)]),
                "patient.appointments": ("Appointments", [("Home", url_for("patient.dashboard")), ("Appointments", None)]),
                "patient.consents": ("Consents", [("Home", url_for("patient.dashboard")), ("Consents", None)]),
                "patient.prescriptions": ("Prescriptions", [("Home", url_for("patient.dashboard")), ("Prescriptions", None)]),
                "patient.emergency_profile": ("Emergency", [("Home", url_for("patient.dashboard")), ("Emergency", None)]),
            },
            "doctor": {
                "doctor.dashboard": ("Dashboard", [("Home", url_for("doctor.dashboard")), ("Dashboard", None)]),
                "doctor.appointments": ("Appointments", [("Home", url_for("doctor.dashboard")), ("Appointments", None)]),
                "doctor.patients": ("Patients", [("Home", url_for("doctor.dashboard")), ("Patients", None)]),
                "doctor.patient_detail": ("Patient", [("Home", url_for("doctor.dashboard")), ("Patients", url_for("doctor.patients")), ("Patient", None)]),
                "doctor.prescribe": ("Prescription", [("Home", url_for("doctor.dashboard")), ("Appointments", url_for("doctor.appointments")), ("Prescription", None)]),
            },
            "pharmacy": {
                "pharmacy.queue": ("Queue", [("Home", url_for("pharmacy.queue")), ("Queue", None)]),
            },
            "emergency": {
                "emergency.lookup": ("Lookup", [("Home", url_for("emergency.lookup")), ("Lookup", None)]),
            },
        }

        page_title = None
        breadcrumbs = None

        now = datetime.now()
        current_date = f"{now:%A}, {now:%B} {now.day}, {now:%Y}"
        current_year = now.year
        if role_name in mappings and endpoint in mappings[role_name]:
            page_title, breadcrumbs = mappings[role_name][endpoint]
        else:
            if endpoint.endswith(".dashboard"):
                page_title = "Dashboard"

        return {"page_title": page_title, "breadcrumbs": breadcrumbs, "current_date": current_date, "current_year": current_year}

    return app
