# tests/test_users.py
# ─────────────────────
# Tests for app/routes/user_routes.py:
#
#   GET    /api/users/me
#   GET    /api/users/
#   PATCH  /api/users/<id>/deactivate
#   PATCH  /api/users/<id>/activate
#   DELETE /api/users/<id>

from tests.conftest import auth_headers
from app.models     import User


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/users/me
# ═════════════════════════════════════════════════════════════════════════════

class TestGetMe:

    def test_clerk_gets_own_profile(self, client, clerk_token, seeded_clerk):
        """Authenticated clerk → 200 with their own user object."""
        response = client.get("/api/users/me", headers=auth_headers(clerk_token))
        assert response.status_code == 200

        data = response.get_json()
        assert data["email"]    == seeded_clerk["email"]
        assert data["role"]     == "clerk"
        assert data["store_id"] == seeded_clerk["store_id"]

    def test_response_includes_store_details(self, client, admin_token, seeded_store):
        """The /me response should embed a store sub-object."""
        response = client.get("/api/users/me", headers=auth_headers(admin_token))
        data = response.get_json()
        assert "store" in data
        assert data["store"]["id"] == seeded_store["id"]

    def test_unauthenticated_request_returns_401(self, client):
        """No JWT → 401."""
        response = client.get("/api/users/me")
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/users/
# ═════════════════════════════════════════════════════════════════════════════

class TestListUsers:

    def test_admin_sees_only_clerks_in_own_store(
        self, client, admin_token, seeded_clerk, seeded_admin
    ):
        """Admin → list returns only clerks, not the admin themselves."""
        response = client.get("/api/users/", headers=auth_headers(admin_token))
        assert response.status_code == 200

        users = response.get_json()
        roles = {u["role"] for u in users}
        # Admins should only see clerks, not other admins or merchants
        assert roles <= {"clerk"}

    def test_merchant_sees_all_users(
        self, client, merchant_token, seeded_clerk, seeded_admin
    ):
        """Merchant → list returns all active users (no role restriction)."""
        response = client.get("/api/users/", headers=auth_headers(merchant_token))
        assert response.status_code == 200

        users    = response.get_json()
        emails   = {u["email"] for u in users}
        # Should see both admin and clerk (merchant themselves is also active)
        assert seeded_clerk["email"] in emails
        assert seeded_admin["email"] in emails

    def test_merchant_can_filter_by_role(self, client, merchant_token, seeded_clerk):
        """Merchant passes ?role=clerk → only clerks returned."""
        response = client.get(
            "/api/users/?role=clerk",
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 200
        users = response.get_json()
        assert all(u["role"] == "clerk" for u in users)

    def test_inactive_users_excluded_by_default(
        self, client, admin_token, db_session, seeded_clerk
    ):
        """Deactivated user does not appear in the default listing."""
        user = User.query.get(seeded_clerk["id"])
        user.is_active = False
        db_session.commit()

        response = client.get("/api/users/", headers=auth_headers(admin_token))
        emails = {u["email"] for u in response.get_json()}
        assert seeded_clerk["email"] not in emails

    def test_clerk_cannot_list_users(self, client, clerk_token):
        """Clerk is not allowed to list users → 403."""
        response = client.get("/api/users/", headers=auth_headers(clerk_token))
        assert response.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/users/<id>/deactivate
# ═════════════════════════════════════════════════════════════════════════════

class TestDeactivateUser:

    def test_admin_deactivates_clerk_in_own_store(
        self, client, admin_token, seeded_clerk, db_session
    ):
        """Admin deactivates a clerk → 200, is_active becomes False."""
        response = client.patch(
            f"/api/users/{seeded_clerk['id']}/deactivate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        user = User.query.get(seeded_clerk["id"])
        assert user.is_active is False

    def test_cannot_deactivate_self(self, client, admin_token, seeded_admin):
        """Admin trying to deactivate themselves → 400."""
        response = client.patch(
            f"/api/users/{seeded_admin['id']}/deactivate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_admin_cannot_deactivate_merchant(
        self, client, admin_token, seeded_merchant
    ):
        """Admin trying to deactivate a merchant → 403 (out of scope)."""
        response = client.patch(
            f"/api/users/{seeded_merchant['id']}/deactivate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 403

    def test_deactivating_already_inactive_returns_400(
        self, client, admin_token, db_session, seeded_clerk
    ):
        """Deactivating a user who is already deactivated → 400."""
        user = User.query.get(seeded_clerk["id"])
        user.is_active = False
        db_session.commit()

        response = client.patch(
            f"/api/users/{seeded_clerk['id']}/deactivate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_clerk_cannot_deactivate_anyone(
        self, client, clerk_token, seeded_clerk
    ):
        """Clerk role cannot call deactivate → 403."""
        response = client.patch(
            f"/api/users/{seeded_clerk['id']}/deactivate",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/users/<id>/activate
# ═════════════════════════════════════════════════════════════════════════════

class TestActivateUser:

    def test_admin_reactivates_deactivated_clerk(
        self, client, admin_token, db_session, seeded_clerk
    ):
        """Admin reactivates a previously deactivated clerk → 200."""
        # First deactivate
        user = User.query.get(seeded_clerk["id"])
        user.is_active = False
        db_session.commit()

        response = client.patch(
            f"/api/users/{seeded_clerk['id']}/activate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        user = User.query.get(seeded_clerk["id"])
        assert user.is_active is True

    def test_activating_already_active_returns_400(
        self, client, admin_token, seeded_clerk
    ):
        """Activating a user who is already active → 400."""
        response = client.patch(
            f"/api/users/{seeded_clerk['id']}/activate",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# DELETE /api/users/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestDeleteUser:

    def test_admin_deletes_clerk(self, client, admin_token, seeded_clerk, db_session):
        """Admin permanently deletes a clerk → 200, user gone from DB."""
        response = client.delete(
            f"/api/users/{seeded_clerk['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        # Verify the user is gone
        user = User.query.get(seeded_clerk["id"])
        assert user is None

    def test_cannot_delete_self(self, client, admin_token, seeded_admin):
        """Admin trying to delete themselves → 400."""
        response = client.delete(
            f"/api/users/{seeded_admin['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_merchant_deletes_admin(
        self, client, merchant_token, seeded_admin, db_session
    ):
        """Merchant can delete an admin → 200."""
        response = client.delete(
            f"/api/users/{seeded_admin['id']}",
            headers=auth_headers(merchant_token),
        )
        assert response.status_code == 200
        assert User.query.get(seeded_admin["id"]) is None

    def test_delete_nonexistent_user_returns_404(self, client, admin_token):
        """Deleting a user id that doesn't exist → 404."""
        response = client.delete(
            "/api/users/999999",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 404

    def test_clerk_cannot_delete_anyone(self, client, clerk_token, seeded_clerk):
        """Clerk role cannot delete → 403."""
        response = client.delete(
            f"/api/users/{seeded_clerk['id']}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403