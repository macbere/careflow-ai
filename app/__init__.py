"""Flask application factory."""
from flask import Flask

from app.config import get_config
from app.extensions import configure_logging, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    db.init_app(app)

    # Import models so SQLAlchemy metadata is populated before create_all().
    from app import models  # noqa: F401

    from app.api.patients import patients_bp
    from app.api.discharges import discharges_bp
    from app.api.calls import calls_bp
    from app.api.webhooks import webhooks_bp
    from app.api.escalations import escalations_bp
    from app.api.dashboard import dashboard_bp

    app.register_blueprint(patients_bp)
    app.register_blueprint(discharges_bp)
    app.register_blueprint(calls_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(escalations_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def index():
        from flask import redirect, url_for

        return redirect(url_for("dashboard.index"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
