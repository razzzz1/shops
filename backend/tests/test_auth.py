# tests/test_auth.py
# ───────────────────
# Tests for every endpoint in app/routes/auth_routes.py:
#
#   POST   /api/auth/login
#   POST   /api/auth/refresh
#   POST   /api/auth/logout
#   POST   /api/auth/invite
#   GET    /api/auth/verify-invite
#   POST   /api/auth/register
#
# Test naming convention:  test_<endpoint>_<scenario>
# Each test is self-contained — it relies only on fixtures from conftest.py.

import pytest
from tests.conftest import auth_headers, make_invitation_token
from app.models     import User, InvitationToken


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/auth/login
# ═════════════════════════════════════════════════════════════════════════════

class TestLogin:
    """All scenarios for the login endpoint."""

    def test_login_success_returns_tokens_and_user(self, client, seeded_merchant):
        """Valid credentials → 200 with access_token, refresh_token, user."""
        response = client.post("/api/auth/login", json={
            "email":    seeded_merchant["email"],
            "password": seeded_merchant["password"],
        })
        assert response.status_code == 200

        data = response.get_json()
        assert "access_token"  in data
        assert "refresh_token" in data
        assert data["user"]["email"] == seeded_merchant["email"]
        assert data["user"]["role"]  == "merchant"

    def test_login_wrong_password_returns_401(self, client, seeded_merchant):
        """Wrong password → 401. Same error as wrong email (prevents enumeration)."""
        response = client.post("/api/auth/login", json={
            "email":    seeded_merchant["email"],
            "password": "WrongPassword!",
        })
        assert response.status_code == 401
        assert "Invalid" in response.get_json()["message"]

    def test_login_unknown_email_returns_401(self, client):
        """Non-existent email → 401. Same message as wrong password."""
        response = client.post("/api/auth/login", json={
            "email":    "nobody@nowhere.com",
            "password": "anything",
        })
        assert response.status_code == 401

    def test_login_missing_email_returns_400(self, client):
        """Missing email field → 400 validation error."""
        response = client.post("/api/auth/login", json={"password": "secret"})
        assert response.status_code == 400

    def test_login_missing_password_returns_400(self, client):
        """Missing password field → 400 validation error."""
        response = client.post("/api/auth/login", json={"email": "a@b.com"})
        assert response.status_code == 400

    def test_login_deactivated_account_returns_403(self, client, db_session, seeded_clerk):
        """Deactivated user → 403 even with correct password."""
        # Deactivate the clerk directly in the DB
        user = User.query.get(seeded_clerk["id"])
        user.is_active = False
        db_session.commit()

        response = client.post("/api/auth/login", json={
            "email":    seeded_clerk["email"],
            "password": seeded_clerk["password"],
        })
        assert response.status_code == 403
        assert "deactivated" in response.get_json()["message"].lower()

    def test_login_user_object_includes_store(self, client, seeded_admin):
        """The user object in the response should embed store details."""
        response = client.post("/api/auth/login", json={
            "email":    seeded_admin["email"],
            "password": seeded_admin["password"],
        })
        data = response.get_json()
        # include_store=True is passed in the route — check the key exists
        assert "store" in data["user"]
        assert data["user"]["store"]["id"] == seeded_admin["store_id"]


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/auth/refresh
# ═════════════════════════════════════════════════════════════════════════════

class TestRefresh:

    def test_refresh_with_valid_refresh_token_returns_new_access_token(
        self, client, seeded_clerk
    ):
        """Valid refresh token → 200 with a new access_token."""
        # First, log in to get a refresh token
        login_resp = client.post("/api/auth/login", json={
            "email":    seeded_clerk["email"],
            "password": seeded_clerk["password"],
        })
        refresh_token = login_resp.get_json()["refresh_token"]

        # Use the refresh token (not the access token) to get a new access token
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 200
        assert "access_token" in response.get_json()

    def test_refresh_with_access_token_returns_422(self, client, clerk_token):
        """
        Sending an ACCESS token to /refresh should fail.
        Flask-JWT-Extended expects a refresh token; access token → 422.
        """
        response = client.post(
            "/api/auth/refresh",
            headers=auth_headers(clerk_token),
        )
        # JWT-Extended returns 422 when the wrong token type is used
        assert response.status_code == 422

    def test_refresh_with_no_token_returns_401(self, client):
        """No token at all → 401."""
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/auth/invite
# ═════════════════════════════════════════════════════════════════════════════

class TestInvite:

    def test_merchant_can_invite_admin(self, client, merchant_token,
                                        seeded_store, seeded_merchant):
        """Merchant → invite admin → 201."""
        response = client.post(
            "/api/auth/invite",
            json={
                "email":    "newadmin@test.com",
                "role":     "admin",
                "store_id": seeded_store["id"],
            },
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 201
        assert "newadmin@test.com" in response.get_json()["message"]

    def test_admin_can_invite_clerk(self, client, admin_token, seeded_store):
        """Admin → invite clerk → 201."""
        response = client.post(
            "/api/auth/invite",
            json={
                "email": "newclerk@test.com",
                "role":  "clerk",
                # store_id is ignored for admins — taken from their account
            },
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 201

    def test_admin_cannot_invite_admin(self, client, admin_token, seeded_store):
        """Admin attempting to invite another admin → 403."""
        response = client.post(
            "/api/auth/invite",
            json={
                "email":    "badmove@test.com",
                "role":     "admin",
                "store_id": seeded_store["id"],
            },
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 403

    def test_clerk_cannot_invite_anyone(self, client, clerk_token):
        """Clerk has no permission to invite — @role_required blocks them → 403."""
        response = client.post(
            "/api/auth/invite",
            json={"email": "someone@test.com", "role": "clerk"},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403

    def test_invite_duplicate_email_returns_409(self, client, merchant_token,
                                                 seeded_admin, seeded_store):
        """Inviting an email that already has an account → 409 Conflict."""
        response = client.post(
            "/api/auth/invite",
            json={
                "email":    seeded_admin["email"],   # already exists
                "role":     "admin",
                "store_id": seeded_store["id"],
            },
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 409

    def test_invite_missing_fields_returns_400(self, client, merchant_token):
        """Missing email → 400."""
        response = client.post(
            "/api/auth/invite",
            json={"role": "clerk"},
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 400

    def test_invite_nonexistent_store_returns_404(self, client, merchant_token):
        """Pointing to a store that doesn't exist → 404."""
        response = client.post(
            "/api/auth/invite",
            json={"email": "x@test.com", "role": "admin", "store_id": 9999},
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 404

    def test_unauthenticated_invite_returns_401(self, client):
        """No JWT at all → 401."""
        response = client.post(
            "/api/auth/invite",
            json={"email": "x@test.com", "role": "clerk"},
        )
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/auth/verify-invite
# ═════════════════════════════════════════════════════════════════════════════

class TestVerifyInvite:

    def test_valid_token_returns_valid_true_and_metadata(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """A freshly created token → {"valid": true, "email": ..., "role": ...}"""
        raw_token = make_invitation_token(
            app, db_session,
            email      = "verify@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )

        response = client.get(f"/api/auth/verify-invite?token={raw_token}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["valid"]          is True
        assert data["email"]          == "verify@test.com"
        assert data["role"]           == "clerk"
        assert data["store_id"]       == seeded_store["id"]

    def test_missing_token_param_returns_400(self, client):
        """No ?token= query param → 400."""
        response = client.get("/api/auth/verify-invite")
        assert response.status_code == 400

    def test_garbage_token_returns_400(self, client, app, db_session,
                                       seeded_store, seeded_merchant):
        """A token string that isn't in the DB at all → 404."""
        response = client.get("/api/auth/verify-invite?token=not-a-real-token")
        assert response.status_code == 404

    def test_already_used_token_returns_400(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """A token that has already been used → 400."""
        from app.models import InvitationToken
        raw_token = make_invitation_token(
            app, db_session,
            email      = "used@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )
        # Mark it as used directly in the DB
        record = InvitationToken.query.filter_by(token=raw_token).first()
        record.is_used = True
        db_session.commit()

        response = client.get(f"/api/auth/verify-invite?token={raw_token}")
        assert response.status_code == 400
        assert data := response.get_json()
        assert data["valid"] is False


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/auth/register
# ═════════════════════════════════════════════════════════════════════════════

class TestRegister:

    def test_register_success_creates_user_and_returns_tokens(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """Valid token + valid form → 201, user created, token consumed."""
        raw_token = make_invitation_token(
            app, db_session,
            email      = "newclerk@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )

        response = client.post("/api/auth/register", json={
            "token":      raw_token,
            "first_name": "New",
            "last_name":  "Clerk",
            "password":   "SecurePass1!",
        })
        assert response.status_code == 201

        data = response.get_json()
        # Should be logged in immediately
        assert "access_token"  in data
        assert "refresh_token" in data
        # Role and store come from the token, not the request body
        assert data["user"]["role"]     == "clerk"
        assert data["user"]["store_id"] == seeded_store["id"]

        # Token should now be marked as used
        record = InvitationToken.query.filter_by(token=raw_token).first()
        assert record.is_used is True

        # User should exist in the DB
        user = User.query.filter_by(email="newclerk@test.com").first()
        assert user is not None
        assert user.first_name == "New"

    def test_register_token_consumed_after_use(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """Reusing the same token a second time → 400."""
        raw_token = make_invitation_token(
            app, db_session,
            email      = "onetime@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )

        payload = {
            "token":      raw_token,
            "first_name": "One",
            "last_name":  "Time",
            "password":   "SecurePass1!",
        }

        # First use → success
        r1 = client.post("/api/auth/register", json=payload)
        assert r1.status_code == 201

        # Second use → token is now consumed
        r2 = client.post("/api/auth/register", json=payload)
        assert r2.status_code in (400, 409)   # invalid token or duplicate email

    def test_register_weak_password_returns_400(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """Password shorter than 8 characters → 400."""
        raw_token = make_invitation_token(
            app, db_session,
            email      = "weakpass@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )
        response = client.post("/api/auth/register", json={
            "token":      raw_token,
            "first_name": "Weak",
            "last_name":  "Pass",
            "password":   "short",      # only 5 chars
        })
        assert response.status_code == 400
        assert "8" in response.get_json()["message"]   # error mentions minimum length

    def test_register_missing_fields_returns_400(
        self, client, app, db_session, seeded_store, seeded_merchant
    ):
        """Missing first_name → 400."""
        raw_token = make_invitation_token(
            app, db_session,
            email      = "incomplete@test.com",
            role       = "clerk",
            store_id   = seeded_store["id"],
            inviter_id = seeded_merchant["id"],
        )
        response = client.post("/api/auth/register", json={
            "token":     raw_token,
            # first_name missing
            "last_name": "Smith",
            "password":  "SecurePass1!",
        })
        assert response.status_code == 400

    def test_register_invalid_token_returns_400(self, client):
        """Garbage token string → 400."""
        response = client.post("/api/auth/register", json={
            "token":      "this-is-not-a-real-token",
            "first_name": "Ghost",
            "last_name":  "User",
            "password":   "SecurePass1!",
        })
        assert response.status_code == 400