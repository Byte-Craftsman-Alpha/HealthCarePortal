from flask import Blueprint


pharmacy_bp = Blueprint("pharmacy", __name__, template_folder="../../templates")

from app.blueprints.pharmacy import routes as _routes  # noqa: E402,F401
