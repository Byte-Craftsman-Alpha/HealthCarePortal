from flask import Blueprint


emergency_bp = Blueprint("emergency", __name__, template_folder="../../templates")

from app.blueprints.emergency import routes as _routes  # noqa: E402,F401
