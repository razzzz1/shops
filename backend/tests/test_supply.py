# tests/test_supply.py
# ──────────────────────
# Tests for app/routes/supply_routes.py:
#
#   GET    /api/supply/
#   POST   /api/supply/
#   GET    /api/supply/<id>
#   PATCH  /api/supply/<id>/action

from tests.conftest import auth_headers
from app.models     import SupplyRequest


# ─────────────────────────────────────────────────────────────────────────────
# Helper: create a supply request and return the parsed dict
# ─────────────────────────────────────────────────────────────────────────────

def submit_request(client, token, product_id, quantity=50, reason="Running low"):
    return client.post(
        "/api/supply/",
        json={
            "product_id":         product_id,
            "quantity_requested": quantity,
            "reason":             reason,
        },
        headers=auth_headers(token),
    )


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/supply/
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateSupplyRequest:

    def test_clerk_submits_request_successfully(
        self, client, clerk_token, seeded_product
    ):
        """Clerk submits a supply request → 201, status='pending'."""
        response = submit_request(client, clerk_token, seeded_product["id"])
        assert response.status_code == 201

        req = response.get_json()["request"]
        assert req["status"]             == "pending"
        assert req["quantity_requested"] == 50
        assert req["reason"]             == "Running low"
        assert req["admin_id"]           is None   # not yet resolved

    def test_missing_product_id_returns_400(self, client, clerk_token):
        """Missing product_id → 400."""
        response = client.post(
            "/api/supply/",
            json={"quantity_requested": 50},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 400

    def test_zero_quantity_returns_400(self, client, clerk_token, seeded_product):
        """quantity_requested=0 → 400 (must be positive)."""
        response = submit_request(client, clerk_token, seeded_product["id"],
                                  quantity=0)
        assert response.status_code == 400

    def test_negative_quantity_returns_400(self, client, clerk_token, seeded_product):
        """quantity_requested=-5 → 400."""
        response = submit_request(client, clerk_token, seeded_product["id"],
                                  quantity=-5)
        assert response.status_code == 400

    def test_nonexistent_product_returns_404(self, client, clerk_token):
        """Product id not found → 404."""
        response = submit_request(client, clerk_token, product_id=999999)
        assert response.status_code == 404

    def test_unauthenticated_returns_401(self, client, seeded_product):
        """No JWT → 401."""
        response = client.post(
            "/api/supply/",
            json={"product_id": seeded_product["id"], "quantity_requested": 10},
        )
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/supply/
# ═════════════════════════════════════════════════════════════════════════════

class TestListSupplyRequests:

    def test_clerk_sees_own_requests_only(
        self, client, clerk_token, seeded_product
    ):
        """After submitting, clerk sees their own request in the list."""
        submit_request(client, clerk_token, seeded_product["id"])

        response = client.get("/api/supply/", headers=auth_headers(clerk_token))
        assert response.status_code == 200
        requests = response.get_json()
        assert len(requests) >= 1

    def test_admin_sees_all_store_requests(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """Admin sees all requests in their store, not just their own."""
        submit_request(client, clerk_token, seeded_product["id"])

        response = client.get("/api/supply/", headers=auth_headers(admin_token))
        assert response.status_code == 200
        assert len(response.get_json()) >= 1

    def test_filter_by_pending_status(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """?status=pending returns only pending requests."""
        submit_request(client, clerk_token, seeded_product["id"])

        response = client.get(
            "/api/supply/?status=pending",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        requests = response.get_json()
        assert all(r["status"] == "pending" for r in requests)


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/supply/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestGetSupplyRequest:

    def test_clerk_gets_own_request(
        self, client, clerk_token, seeded_product
    ):
        """Clerk retrieves a specific request they submitted → 200."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        response = client.get(
            f"/api/supply/{req_id}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200
        assert response.get_json()["id"] == req_id

    def test_get_nonexistent_request_returns_404(self, client, clerk_token):
        """Non-existent request id → 404."""
        response = client.get(
            "/api/supply/999999",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/supply/<id>/action
# ═════════════════════════════════════════════════════════════════════════════

class TestActionSupplyRequest:

    def test_admin_approves_pending_request(
        self, client, clerk_token, admin_token, seeded_product, db_session
    ):
        """Admin approves a pending request → 200, status='approved'."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        response = client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "approved", "note": "Order placed with supplier"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        req = response.get_json()["request"]
        assert req["status"]      == "approved"
        assert req["admin_note"]  == "Order placed with supplier"
        assert req["resolved_at"] is not None

        # Verify directly in DB
        supply_req = SupplyRequest.query.get(req_id)
        assert supply_req.status == "approved"

    def test_admin_declines_pending_request(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """Admin declines a pending request → 200, status='declined'."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        response = client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "declined", "note": "Over budget this month"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.get_json()["request"]["status"] == "declined"

    def test_cannot_action_already_resolved_request(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """Once approved, a second action attempt → 400."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        # First action: approve
        client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "approved"},
            headers=auth_headers(admin_token),
        )
        # Second action on already-resolved request → 400
        response = client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "declined"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_invalid_action_value_returns_400(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """action='maybe' → 400."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        response = client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "maybe"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_clerk_cannot_action_requests(
        self, client, clerk_token, seeded_product
    ):
        """Clerk role cannot approve/decline → 403."""
        create_resp = submit_request(client, clerk_token, seeded_product["id"])
        req_id = create_resp.get_json()["request"]["id"]

        response = client.patch(
            f"/api/supply/{req_id}/action",
            json={"action": "approved"},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403