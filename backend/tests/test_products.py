# tests/test_products.py
# ────────────────────────
# Tests for app/routes/product_routes.py:
#
#   GET    /api/products/
#   POST   /api/products/
#   GET    /api/products/<id>
#   PATCH  /api/products/<id>
#   DELETE /api/products/<id>

from tests.conftest import auth_headers
from app.models     import Product


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/products/
# ═════════════════════════════════════════════════════════════════════════════

class TestListProducts:

    def test_clerk_sees_active_products_in_own_store(
        self, client, clerk_token, seeded_product
    ):
        """Clerk → 200 with the store's active products."""
        response = client.get("/api/products/", headers=auth_headers(clerk_token))
        assert response.status_code == 200

        products = response.get_json()
        assert len(products) >= 1
        names = [p["name"] for p in products]
        assert seeded_product["name"] in names

    def test_inactive_products_hidden_from_clerk(
        self, client, clerk_token, db_session, seeded_product
    ):
        """Soft-deleted (is_active=False) product does not appear in list."""
        product = Product.query.get(seeded_product["id"])
        product.is_active = False
        db_session.commit()

        response = client.get("/api/products/", headers=auth_headers(clerk_token))
        products = response.get_json()
        ids = [p["id"] for p in products]
        assert seeded_product["id"] not in ids

    def test_unauthenticated_request_returns_401(self, client):
        """No JWT → 401."""
        response = client.get("/api/products/")
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/products/
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateProduct:

    def test_admin_creates_product(self, client, admin_token, seeded_store):
        """Admin creates a valid product → 201."""
        response = client.post(
            "/api/products/",
            json={
                "name":          "Bread 700g",
                "buying_price":  40.00,
                "selling_price": 60.00,
                "category":      "Bakery",
                "unit":          "pieces",
                "sku":           "BRD-700",
            },
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 201

        product = response.get_json()["product"]
        assert product["name"]          == "Bread 700g"
        assert product["buying_price"]  == 40.00
        assert product["selling_price"] == 60.00
        assert product["is_active"]     is True
        assert product["store_id"]      == seeded_store["id"]

    def test_product_appears_in_list_after_creation(
        self, client, admin_token
    ):
        """After creation, the new product appears in GET /products/."""
        client.post(
            "/api/products/",
            json={"name": "Eggs 12pk", "buying_price": 100, "selling_price": 140},
            headers=auth_headers(admin_token),
        )
        list_resp = client.get("/api/products/", headers=auth_headers(admin_token))
        names = [p["name"] for p in list_resp.get_json()]
        assert "Eggs 12pk" in names

    def test_missing_required_fields_returns_400(self, client, admin_token):
        """Missing selling_price → 400."""
        response = client.post(
            "/api/products/",
            json={"name": "No Price Item", "buying_price": 10},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_negative_price_returns_400(self, client, admin_token):
        """Negative buying_price → 400."""
        response = client.post(
            "/api/products/",
            json={"name": "Bad Price", "buying_price": -5, "selling_price": 10},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_clerk_cannot_create_product(self, client, clerk_token):
        """Clerk role → 403."""
        response = client.post(
            "/api/products/",
            json={"name": "X", "buying_price": 1, "selling_price": 2},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/products/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestGetProduct:

    def test_get_existing_product(self, client, clerk_token, seeded_product):
        """GET a specific product by id → 200 with product data."""
        response = client.get(
            f"/api/products/{seeded_product['id']}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"]   == seeded_product["id"]
        assert data["name"] == seeded_product["name"]

    def test_get_nonexistent_product_returns_404(self, client, clerk_token):
        """Product id that doesn't exist → 404."""
        response = client.get(
            "/api/products/999999",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/products/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdateProduct:

    def test_admin_updates_product_name(
        self, client, admin_token, seeded_product, db_session
    ):
        """Admin changes product name → 200, name updated in DB."""
        response = client.patch(
            f"/api/products/{seeded_product['id']}",
            json={"name": "Updated Milk Name"},
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        product = Product.query.get(seeded_product["id"])
        assert product.name == "Updated Milk Name"

    def test_partial_update_only_changes_supplied_fields(
        self, client, admin_token, seeded_product
    ):
        """Only the supplied field changes; others remain as before."""
        original = Product.query.get(seeded_product["id"])
        original_price = float(original.buying_price)

        client.patch(
            f"/api/products/{seeded_product['id']}",
            json={"selling_price": 99.99},
            headers=auth_headers(admin_token),
        )

        product = Product.query.get(seeded_product["id"])
        # buying_price should NOT have changed
        assert float(product.buying_price) == original_price
        assert float(product.selling_price) == 99.99

    def test_clerk_cannot_update_product(self, client, clerk_token, seeded_product):
        """Clerk role → 403."""
        response = client.patch(
            f"/api/products/{seeded_product['id']}",
            json={"name": "Hack"},
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# DELETE /api/products/<id>  (soft-delete)
# ═════════════════════════════════════════════════════════════════════════════

class TestDeactivateProduct:

    def test_admin_soft_deletes_product(
        self, client, admin_token, seeded_product, db_session
    ):
        """Admin 'deletes' product → 200, is_active=False in DB."""
        response = client.delete(
            f"/api/products/{seeded_product['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        product = Product.query.get(seeded_product["id"])
        # Record still exists — soft delete only
        assert product is not None
        assert product.is_active is False

    def test_deactivating_already_inactive_returns_400(
        self, client, admin_token, db_session, seeded_product
    ):
        """Deactivating an already-inactive product → 400."""
        product = Product.query.get(seeded_product["id"])
        product.is_active = False
        db_session.commit()

        response = client.delete(
            f"/api/products/{seeded_product['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_clerk_cannot_delete_product(self, client, clerk_token, seeded_product):
        """Clerk role → 403."""
        response = client.delete(
            f"/api/products/{seeded_product['id']}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403