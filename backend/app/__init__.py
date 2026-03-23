# app/__init__.py
# ────────────────
# Application factory for StockFlow.
#
# What is an application factory?
# ─────────────────────────────────
# Instead of creating the Flask app at module level (app = Flask(__name__)),
# we wrap it in a function (create_app).  This lets us:
#   1. Create multiple isolated instances — one for dev, one per test function.
#   2. Pass different configs without touching source code.
#   3. Avoid circular imports because extensions are initialised here, not
#      at import time.
#
# Every entry point (run.py, pytest fixtures, gunicorn) calls create_app()
# to get a ready-to-use Flask application.

import os
from flask import Flask
from dotenv import load_dotenv

from app.extensions import db, migrate, jwt, mail, cors


def create_app(config_name: str = "development") -> Flask:
    """
    Build, configure, and return a Flask application instance.

    Parameters
    ----------
    config_name : str
        Which config class to load.  One of:
          "development"  ← default (dev server, SQL echo on)
          "testing"      ← pytest (in-memory SQLite, mail suppressed)
          "production"   ← live server (debug off, strict settings)

    Returns
    -------
    Flask
        A fully initialised Flask app ready to serve requests.
    """

    # Pull values from the .env file into os.environ so config.py can read them
    load_dotenv()

    app = Flask(__name__)

    # ── 1. Load the matching config class ─────────────────────────────────────
    _config_map = {
        "development": "app.config.DevelopmentConfig",
        "testing":     "app.config.TestingConfig",
        "production":  "app.config.ProductionConfig",
    }
    app.config.from_object(_config_map.get(config_name, "app.config.DevelopmentConfig"))

    # ── 2. Bind extensions to this specific app instance ──────────────────────
    # Each extension was created without an app in extensions.py.
    # init_app() wires it up now.
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)

    # Allow requests from the React frontend origin
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("FRONTEND_URL", "http://localhost:3000")
            }
        }
    )

    # ── 3. Import models so SQLAlchemy / Alembic can discover the table defs ──
    # These imports have no other effect — they just register the classes with
    # SQLAlchemy's metadata so flask db upgrade knows what tables to create.
    from app.models import (  # noqa: F401
        User, Store, Product, InventoryEntry, SupplyRequest, InvitationToken
    )

    # ── 4. Register route blueprints ──────────────────────────────────────────
    # Each blueprint is defined in its own file under app/routes/.
    # Importing inside create_app() avoids circular import issues.
    from app.routes.auth_routes      import auth_bp
    from app.routes.user_routes      import user_bp
    from app.routes.product_routes   import product_bp
    from app.routes.inventory_routes import inventory_bp
    from app.routes.report_routes    import report_bp
    from app.routes.supply_routes    import supply_bp

    app.register_blueprint(auth_bp,       url_prefix="/api/auth")
    app.register_blueprint(user_bp,       url_prefix="/api/users")
    app.register_blueprint(product_bp,    url_prefix="/api/products")
    app.register_blueprint(inventory_bp,  url_prefix="/api/inventory")
    app.register_blueprint(report_bp,     url_prefix="/api/reports")
    app.register_blueprint(supply_bp,     url_prefix="/api/supply")

    # ── 5. Register JWT error handlers ────────────────────────────────────────
    # By default Flask-JWT-Extended returns HTML error pages.
    # We override them to return JSON, which the React app can parse.

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        # Client should use the refresh token to get a new access token
        return {"message": "Your session has expired. Please log in again."}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"message": "Invalid authentication token."}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"message": "Authentication token required."}, 401

    return app