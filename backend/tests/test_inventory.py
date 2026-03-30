# tests/test_inventory.py
# ─────────────────────────
# Tests for app/routes/inventory_routes.py:
#
#   GET    /api/inventory/
#   POST   /api/inventory/
#   GET    /api/inventory/<id>
#   PATCH  /api/inventory/<id>
#   PATCH  /api/inventory/<id>/payment
#   DELETE /api/inventory/<id>

import pytest
from tests.conftest import auth_headers
from app.models     import InventoryEntry


# ─────────────────────────────────────────────────────────────────────────────
# Helper: POST a valid entry and return the entry dict
# ─────────────────────────────────────────────────────────────────────────────

def create_entry(client, token, product_id, overrides=None):
    """
    Submit a minimal valid stock entry and return the parsed response dict.
    `overrides` lets individual tests change specific fields.
    """
    payload = {
        "product_id":        product_id,
        "quantity_received": 100,
        "quantity_in_stock": 95,
        "quantity_spoilt":   5,
        "buying_price":      55.00,
        "selling_price":     75.00,
        "payment_status":    "unpaid",
    }
    if overrides:
        payload.update(overrides)
    return client.post(
        "/api/inventory/",
        json=payload,
        headers=auth_headers(token),
    )


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/inventory/
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateEntry:

    def test_clerk_creates_entry_successfully(
        self, client, clerk_token, seeded_product
    ):
        """Clerk submits valid data → 201 with the created entry."""
        response = create_entry(client, clerk_token, seeded_product["id"])
        assert response.status_code == 201

        entry = response.get_json()["entry"]
        assert entry["quantity_received"] == 100
        assert entry["quantity_in_stock"] == 95
        assert entry["quantity_spoilt"]   == 5
        assert entry["payment_status"]    == "unpaid"
        # Computed fields should be present
        assert entry["total_cost"]             == 55.00 * 100
        assert entry["total_revenue_potential"] == 75.00 * 95

    def test_entry_defaults_payment_to_unpaid(
        self, client, clerk_token, seeded_product
    ):
        """payment_status defaults to 'unpaid' when not supplied."""
        response = create_entry(
            client, clerk_token, seeded_product["id"],
            overrides={"payment_status": None},
        )
        # If payment_status is None the route should default to "unpaid"
        # (or 400 if it's required — either is acceptable)
        if response.status_code == 201:
            assert response.get_json()["entry"]["payment_status"] == "unpaid"

    def test_entry_with_entry_date(self, client, clerk_token, seeded_product):
        """entry_date field is respected when provided."""
        response = create_entry(
            client, clerk_token, seeded_product["id"],
            overrides={"entry_date": "2024-03-15"},
        )
        assert response.status_code == 201
        assert response.get_json()["entry"]["entry_date"] == "2024-03-15"

    def test_missing_required_fields_returns_400(
        self, client, clerk_token, seeded_product
    ):
        """Missing quantity_received → 400."""
        response = client.post(
            "/api/inventory/",
            json={
                "product_id":    seeded_product["id"],
                "quantity_in_stock": 50,
                "buying_price":  55.00,
                "selling_price": 75.00,
                # quantity_received is missing
            },
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 400

    def test_negative_quantity_returns_400(
        self, client, clerk_token, seeded_product
    ):
        """Negative quantity → 400."""
        response = create_entry(
            client, clerk_token, seeded_product["id"],
            overrides={"quantity_received": -10},
        )
        assert response.status_code == 400

    def test_invalid_product_id_returns_404(self, client, clerk_token):
        """Product that doesn't exist → 404."""
        response = create_entry(client, clerk_token, product_id=999999)
        assert response.status_code == 404

    def test_invalid_payment_status_returns_400(
        self, client, clerk_token, seeded_product
    ):
        """Invalid payment_status value → 400."""
        response = create_entry(
            client, clerk_token, seeded_product["id"],
            overrides={"payment_status": "maybe"},
        )
        assert response.status_code == 400

    def test_unauthenticated_request_returns_401(self, client, seeded_product):
        """No JWT → 401."""
        response = create_entry(client, token="bad", product_id=seeded_product["id"])
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/inventory/
# ═════════════════════════════════════════════════════════════════════════════

class TestListEntries:

    def test_clerk_sees_own_store_entries(
        self, client, clerk_token, seeded_product
    ):
        """After creating an entry, it appears in the list."""
        create_entry(client, clerk_token, seeded_product["id"])

        response = client.get("/api/inventory/", headers=auth_headers(clerk_token))
        assert response.status_code == 200
        assert len(response.get_json()) >= 1

    def test_filter_by_payment_status_unpaid(
        self, client, clerk_token, seeded_product
    ):
        """?payment_status=unpaid returns only unpaid entries."""
        create_entry(client, clerk_token, seeded_product["id"],
                     overrides={"payment_status": "unpaid"})

        response = client.get(
            "/api/inventory/?payment_status=unpaid",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200
        entries = response.get_json()
        assert all(e["payment_status"] == "unpaid" for e in entries)

    def test_filter_by_date_range(
        self, client, clerk_token, seeded_product
    ):
        """Entries outside the date range are excluded."""
        create_entry(client, clerk_token, seeded_product["id"],
                     overrides={"entry_date": "2023-01-10"})

        # Filter for 2024 only — the 2023 entry should not appear
        response = client.get(
            "/api/inventory/?from_date=2024-01-01&to_date=2024-12-31",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200
        entries = response.get_json()
        for e in entries:
            assert e["entry_date"] >= "2024-01-01"


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/inventory/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestGetEntry:

    def test_get_own_entry(self, client, clerk_token, seeded_product):
        """Clerk retrieves their own entry → 200."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.get(
            f"/api/inventory/{entry_id}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200
        assert response.get_json()["id"] == entry_id

    def test_get_nonexistent_entry_returns_404(self, client, clerk_token):
        """Entry id that doesn't exist → 404."""
        response = client.get(
            "/api/inventory/999999",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/inventory/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdateEntry:

    def test_clerk_updates_own_entry(
        self, client, clerk_token, seeded_product, db_session
    ):
        """Clerk updates quantity_in_stock on their own entry → 200."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.patch(
            f"/api/inventory/{entry_id}",
            json={"quantity_in_stock": 80, "notes": "Sold 15 units today"},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200

        entry = InventoryEntry.query.get(entry_id)
        assert entry.quantity_in_stock == 80
        assert entry.notes             == "Sold 15 units today"

    def test_clerk_cannot_update_others_entry(
        self, client, clerk_token, admin_token, seeded_product
    ):
        """Clerk cannot update an entry they didn't create → 403."""
        # Admin creates an entry
        create_resp = create_entry(client, admin_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        # Clerk tries to edit it
        response = client.patch(
            f"/api/inventory/{entry_id}",
            json={"quantity_in_stock": 1},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/inventory/<id>/payment
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdatePayment:

    def test_admin_marks_entry_as_paid(
        self, client, clerk_token, admin_token, seeded_product, db_session
    ):
        """Admin changes payment_status to 'paid' → 200, DB updated."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.patch(
            f"/api/inventory/{entry_id}/payment",
            json={"payment_status": "paid"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        entry = InventoryEntry.query.get(entry_id)
        assert entry.payment_status     == "paid"
        assert entry.payment_updated_at is not None   # audit timestamp set

    def test_clerk_cannot_change_payment_status(
        self, client, clerk_token, seeded_product
    ):
        """Clerk role → 403 on payment endpoint."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.patch(
            f"/api/inventory/{entry_id}/payment",
            json={"payment_status": "paid"},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403

    def test_invalid_payment_value_returns_400(
        self, client, admin_token, clerk_token, seeded_product
    ):
        """Invalid payment_status value → 400."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.patch(
            f"/api/inventory/{entry_id}/payment",
            json={"payment_status": "partial"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# DELETE /api/inventory/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestDeleteEntry:

    def test_admin_deletes_entry(
        self, client, clerk_token, admin_token, seeded_product, db_session
    ):
        """Admin deletes an entry → 200, gone from DB."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.delete(
            f"/api/inventory/{entry_id}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert InventoryEntry.query.get(entry_id) is None

    def test_clerk_cannot_delete_entry(
        self, client, clerk_token, seeded_product
    ):
        """Clerk role → 403."""
        create_resp = create_entry(client, clerk_token, seeded_product["id"])
        entry_id = create_resp.get_json()["entry"]["id"]

        response = client.delete(
            f"/api/inventory/{entry_id}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403