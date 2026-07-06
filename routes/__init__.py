from flask import Blueprint

bp = Blueprint('routes', __name__)

from routes import auth, destinos, home, messages, packages  # noqa: E402, F401
