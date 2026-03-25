"""Flask application factory."""

import logging
import os

from flask import Flask

from src.api.routes_auth import auth_bp
from src.api.routes_payments import payments_bp
from src.api.routes_users import users_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(payments_bp, url_prefix="/api/v1/payments")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
