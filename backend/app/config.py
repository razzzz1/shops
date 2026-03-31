# app/config.py
# ─────────────
# Configuration classes for each deployment environment.
#
# Flask loads one of these classes when the app is created.
# Environment is selected by passing config_name to create_app():
#   create_app("development")   ← default; used by run.py
#   create_app("testing")       ← used by pytest fixtures
#   create_app("production")    ← used by the live server
#
# All three inherit from BaseConfig so shared settings are only written once.

import os
from datetime import timedelta


class BaseConfig:
    """
    Settings shared by every environment.
    Values are read from environment variables so secrets never live in code.
    """

    # ── Flask core ─────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # ── Database ───────────────────────────────────────────────────────────────
    # SQLAlchemy reads SQLALCHEMY_DATABASE_URI to know which DB to connect to.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/stockflow_db"
    )
    # Disables a noisy SQLAlchemy feature we don't use (object-modification tracking)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT (JSON Web Tokens) ──────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-me")
    # Access tokens expire quickly for security; refresh tokens last longer
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES",  "3600")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800")))

    # ── Email ──────────────────────────────────────────────────────────────────
    MAIL_SERVER         = os.getenv("MAIL_SERVER",         "localhost")
    MAIL_PORT           = int(os.getenv("MAIL_PORT",       "1025"))
    MAIL_USE_TLS        = os.getenv("MAIL_USE_TLS",        "False") == "True"
    MAIL_USERNAME       = os.getenv("MAIL_USERNAME",       "")
    MAIL_PASSWORD       = os.getenv("MAIL_PASSWORD",       "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@stockflow.app")

    # ── Invitation links ───────────────────────────────────────────────────────
    # How long (seconds) before an emailed invite link stops working
    INVITATION_TOKEN_EXPIRES = int(os.getenv("INVITATION_TOKEN_EXPIRES", "86400"))  # 24 h
    # Used to build the clickable URL in the invitation email
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class DevelopmentConfig(BaseConfig):
    """
    Local development settings.
    DEBUG=True enables the interactive debugger and auto-reloader.
    SQLALCHEMY_ECHO=True prints every SQL query to the console — helpful
    for understanding what the ORM generates.
    """
    DEBUG           = True
    SQLALCHEMY_ECHO = True


class TestingConfig(BaseConfig):
    """
    Test-runner settings.

    Key differences from development:
    • Uses an in-memory SQLite database — no PostgreSQL needed, tests run fast,
      and each test function gets a completely blank database.
    • Emails are suppressed — no real SMTP calls during tests.
    • Invitation tokens expire after 5 seconds so we can test expiry behaviour
      without sleeping for 24 hours.
    """
    TESTING                  = True
    SQLALCHEMY_DATABASE_URI  = "sqlite:///:memory:"  # wiped after every test
    SQLALCHEMY_ECHO          = False
    MAIL_SUPPRESS_SEND       = True                  # never send real emails
    INVITATION_TOKEN_EXPIRES = 5                     # expire after 5 seconds


class ProductionConfig(BaseConfig):
    """
    Production settings.
    DEBUG is off.  DATABASE_URL must be set in the environment.

    Note: we use os.environ.get() here (not os.environ[]) so that importing
    this module during testing does NOT crash when DATABASE_URL is absent.
    The testing config overrides SQLALCHEMY_DATABASE_URI with SQLite anyway,
    so this class is never actually used during the test run.
    A missing DATABASE_URL in a real production deploy will surface as a
    SQLAlchemy connection error at first DB access — early enough to catch.
    """
    DEBUG                   = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")