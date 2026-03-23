# app/extensions.py
# ──────────────────
# All Flask extension objects are instantiated HERE — without an app —
# using the "application factory" pattern.
#
# Why a separate file?
# --------------------
# Models import `db` to define their columns.
# Routes import `db` to run queries.
# If both also imported from `app/__init__.py` (where the Flask app lives),
# we'd get a circular import chain:
#   app/__init__.py  →  models  →  app/__init__.py  ✗
#
# By keeping the extension objects in their own module, every file that
# needs `db`, `jwt`, etc. imports from here — no circularity.
#
# The actual Flask app is wired to these objects later inside create_app()
# via each extension's .init_app(app) method.

from flask_sqlalchemy   import SQLAlchemy
from flask_migrate      import Migrate
from flask_jwt_extended import JWTManager
from flask_mail         import Mail
from flask_cors         import CORS

db      = SQLAlchemy()    # ORM: maps Python classes ↔ PostgreSQL tables
migrate = Migrate()       # Schema migrations via Alembic (flask db upgrade)
jwt     = JWTManager()    # Issues / validates JSON Web Tokens
mail    = Mail()          # Sends invitation emails
cors    = CORS()          # Lets the React dev server (port 3000) call our API