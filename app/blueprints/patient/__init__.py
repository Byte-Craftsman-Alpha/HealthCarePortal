from flask import Blueprint


patient_bp = Blueprint("patient", __name__, template_folder="../../templates")

from app.blueprints.patient import routes as _routes  # noqa: E402,F401
