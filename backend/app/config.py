# app/config.py
# ─────────────
# Configuration classes for each deployment environment.
#
# DEFAULT DATABASE: SQLite
# ────────────────────────
# Development now uses SQLite by default — a simple file-based database
# that requires NO server, NO password, NO configuration.
# The database file is created automatically at backend/stockflow.db
# the first time you run `flask db upgrade`.
#
# To switch to PostgreSQL later, just set DATABASE_URL in your .env:
#   DATABASE_URL=postgresql://user:password@localhost:5432/stockflow_db

import os
from datetime import timedelta

# Absolute path to the backend/ directory
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, "stockflow.db")


class BaseConfig:
    SECRET_KEY                     = os.getenv("SECRET_KEY",     "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI        = os.getenv("DATABASE_URL",   f"sqlite:///{SQLITE_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY                 = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES       = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES",  "3600")))
    JWT_REFRESH_TOKEN_EXPIRES      = timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800")))
    MAIL_SERVER                    = os.getenv("MAIL_SERVER",         "localhost")
    MAIL_PORT                      = int(os.getenv("MAIL_PORT",       "1025"))
    MAIL_USE_TLS                   = os.getenv("MAIL_USE_TLS",        "False") == "True"
    MAIL_USERNAME                  = os.getenv("MAIL_USERNAME",       "")
    MAIL_PASSWORD                  = os.getenv("MAIL_PASSWORD",       "")
    MAIL_DEFAULT_SENDER            = os.getenv("MAIL_DEFAULT_SENDER", "noreply@stockflow.app")
    INVITATION_TOKEN_EXPIRES       = int(os.getenv("INVITATION_TOKEN_EXPIRES", "86400"))
    FRONTEND_URL                   = os.getenv("FRONTEND_URL", "http://localhost:3000")


class DevelopmentConfig(BaseConfig):
    """SQLite, no PostgreSQL needed. DB file: backend/stockflow.db"""
    DEBUG           = True
    SQLALCHEMY_ECHO = False


class TestingConfig(BaseConfig):
    """In-memory SQLite — each test gets a blank database."""
    TESTING                  = True
    SQLALCHEMY_DATABASE_URI  = "sqlite:///:memory:"
    SQLALCHEMY_ECHO          = False
    MAIL_SUPPRESS_SEND       = True
    INVITATION_TOKEN_EXPIRES = 5


class ProductionConfig(BaseConfig):
    """Set DATABASE_URL env var to a PostgreSQL URL for production."""
    DEBUG = False