from flask import Blueprint


doctor_bp = Blueprint("doctor", __name__, template_folder="../../templates")

from app.blueprints.doctor import routes as _routes  # noqa: E402,F401
