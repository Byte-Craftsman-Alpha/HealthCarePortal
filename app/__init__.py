from flask import Flask

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

    return app
