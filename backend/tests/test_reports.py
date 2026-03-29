# tests/conftest.py
# ──────────────────
# Shared pytest fixtures for the entire test suite.
#
# What is a fixture?
# ──────────────────
# A fixture is a function decorated with @pytest.fixture that sets up
# a resource (database, test client, seeded user) and tears it down
# after each test.  Test functions declare what they need by listing
# fixture names as parameters — pytest injects them automatically.
#
# Scopes
# ──────
# scope="function"  (default) — run once per test function, torn down after
# scope="module"              — run once per test file
# scope="session"             — run once for the entire test run
#
# Why function scope for the DB?
# ──────────────────────────────
# Each test gets a FRESH, EMPTY database.  This means tests cannot
# accidentally depend on data left over from a previous test.
# It also means tests can run in any order without breaking each other.
#
# Fixture dependency
# ──────────────────
# Fixtures can depend on other fixtures by listing them as parameters.
#   app → client  (client needs app)
#   app → db_session  (db_session needs app)
#   db_session → seeded_store, seeded_merchant, etc.

import pytest
from datetime import datetime, timezone, timedelta

from app         import create_app
from app.extensions import db as _db
from app.models  import User, Store, Product, InventoryEntry, SupplyRequest, InvitationToken
from app.utils   import hash_password, generate_invitation_token


# ─────────────────────────────────────────────────────────────────────────────
# App + database fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def app():
    """
    Create a Flask application configured for testing.

    Key differences from development:
    • Uses SQLite in-memory — no PostgreSQL installation required.
      The DB is created fresh and destroyed for every test function.
    • Mail sending is suppressed — no actual SMTP calls.
    • Invitation tokens expire after 5 seconds so we can test expiry.
    """
    application = create_app("testing")

    with application.app_context():
        # Create all tables from the model definitions
        _db.create_all()

        yield application  # hand control to the test

        # Teardown: close the session and drop all tables
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Flask test client.

    Simulates HTTP requests to the API without running a real server.
    Usage in tests:
        response = client.post("/api/auth/login", json={...})
        assert response.status_code == 200
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """
    Provide the SQLAlchemy session for direct DB manipulation in tests.

    Tests that need to insert rows or query the DB directly use this.
    """
    return _db.session


# ─────────────────────────────────────────────────────────────────────────────
# Seed data fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def seeded_store(db_session):
    """
    A Store row in the database.
    Returned as a plain dict to avoid detached-instance SQLAlchemy errors.
    """
    store = Store(name="Test Store", location="123 Test Street")
    db_session.add(store)
    db_session.commit()
    return {"id": store.id, "name": store.name}


@pytest.fixture(scope="function")
def seeded_merchant(db_session, seeded_store):
    """
    A merchant-role User + their plain-text password.
    The merchant can invite admins and see all stores.
    """
    user = User(
        email         = "merchant@test.com",
        password_hash = hash_password("MerchPass1!"),
        first_name    = "Merchant",
        last_name     = "User",
        role          = "merchant",
        store_id      = seeded_store["id"],
    )
    db_session.add(user)
    db_session.commit()
    # Return both the id and the plain-text password so tests can log in
    return {"id": user.id, "email": user.email, "password": "MerchPass1!",
            "store_id": seeded_store["id"]}


@pytest.fixture(scope="function")
def seeded_admin(db_session, seeded_store):
    """An admin-role User in the seeded store."""
    user = User(
        email         = "admin@test.com",
        password_hash = hash_password("AdminPass1!"),
        first_name    = "Admin",
        last_name     = "User",
        role          = "admin",
        store_id      = seeded_store["id"],
    )
    db_session.add(user)
    db_session.commit()
    return {"id": user.id, "email": user.email, "password": "AdminPass1!",
            "store_id": seeded_store["id"]}


@pytest.fixture(scope="function")
def seeded_clerk(db_session, seeded_store):
    """A clerk-role User in the seeded store."""
    user = User(
        email         = "clerk@test.com",
        password_hash = hash_password("ClerkPass1!"),
        first_name    = "Clerk",
        last_name     = "User",
        role          = "clerk",
        store_id      = seeded_store["id"],
    )
    db_session.add(user)
    db_session.commit()
    return {"id": user.id, "email": user.email, "password": "ClerkPass1!",
            "store_id": seeded_store["id"]}


@pytest.fixture(scope="function")
def seeded_product(db_session, seeded_store):
    """An active Product in the seeded store."""
    product = Product(
        store_id      = seeded_store["id"],
        name          = "Full Cream Milk 1L",
        sku           = "MILK-001",
        category      = "Dairy",
        unit          = "litres",
        buying_price  = 55.00,
        selling_price = 75.00,
        reorder_level = 20,
    )
    db_session.add(product)
    db_session.commit()
    return {"id": product.id, "name": product.name, "store_id": product.store_id}


# ─────────────────────────────────────────────────────────────────────────────
# Token helper fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def merchant_token(client, seeded_merchant):
    """
    JWT access token for the seeded merchant.

    Tests that need to make requests as a merchant use this fixture.
    Usage:
        headers = auth_headers(merchant_token)
        client.get("/api/users/", headers=headers)
    """
    response = client.post("/api/auth/login", json={
        "email":    seeded_merchant["email"],
        "password": seeded_merchant["password"],
    })
    return response.get_json()["access_token"]


@pytest.fixture(scope="function")
def admin_token(client, seeded_admin):
    """JWT access token for the seeded admin."""
    response = client.post("/api/auth/login", json={
        "email":    seeded_admin["email"],
        "password": seeded_admin["password"],
    })
    return response.get_json()["access_token"]


@pytest.fixture(scope="function")
def clerk_token(client, seeded_clerk):
    """JWT access token for the seeded clerk."""
    response = client.post("/api/auth/login", json={
        "email":    seeded_clerk["email"],
        "password": seeded_clerk["password"],
    })
    return response.get_json()["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers (not fixtures — plain functions used inside tests)
# ─────────────────────────────────────────────────────────────────────────────

def auth_headers(token: str) -> dict:
    """
    Build the Authorization header dict for an authenticated request.

    Usage:
        client.get("/api/users/me", headers=auth_headers(clerk_token))
    """
    return {"Authorization": f"Bearer {token}"}


def make_invitation_token(app, db_session, email, role, store_id,
                           inviter_id, expired=False):
    """
    Helper: create a real InvitationToken row in the DB and return the raw
    token string.  Used by auth tests that need a valid invite to register.

    Parameters
    ----------
    expired : bool
        If True, sets expires_at to the past so the token is expired.
    """
    with app.app_context():
        raw_token = generate_invitation_token(email, role, store_id)
        if expired:
            expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        record = InvitationToken(
            token      = raw_token,
            email      = email,
            role       = role,
            store_id   = store_id,
            inviter_id = inviter_id,
            expires_at = expires_at,
        )
        db_session.add(record)
        db_session.commit()
        return raw_token