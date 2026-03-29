# app/routes/product_routes.py
# ─────────────────────────────
# Product catalogue blueprint:
#
#   GET    /api/products/          list active products for a store
#   POST   /api/products/          admin creates a new product
#   GET    /api/products/<id>      get a single product
#   PATCH  /api/products/<id>      admin updates product details
#   DELETE /api/products/<id>      admin soft-deletes (deactivates) a product

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models     import Product
from app.utils      import role_required

product_bp = Blueprint("products", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/products/
# ─────────────────────────────────────────────────────────────────────────────

@product_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def list_products(current_user):
    """
    Return all active products for the current user's store.

    Scope
    ─────
    • Clerk / Admin  →  automatically scoped to their store
    • Merchant       →  must pass ?store_id= to see a specific store's catalogue

    Query params
    ────────────
    ?store_id=1       merchant: view a specific store's products
    ?category=Dairy   filter by category
    ?include_inactive=1  include soft-deleted products (admin/merchant only)
    """
    # Determine which store to show products for
    if current_user.role == "merchant":
        store_id = request.args.get("store_id", type=int) or current_user.store_id
    else:
        store_id = current_user.store_id   # locked to their store

    query = Product.query.filter_by(store_id=store_id)

    # Only show active products by default (clerks always see active only)
    include_inactive = (
        request.args.get("include_inactive", "0") == "1"
        and current_user.role in ("merchant", "admin")
    )
    if not include_inactive:
        query = query.filter_by(is_active=True)

    # Optional category filter
    category = request.args.get("category")
    if category:
        query = query.filter_by(category=category)

    products = query.order_by(Product.category, Product.name).all()

    return jsonify([p.to_dict() for p in products]), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/products/
# ─────────────────────────────────────────────────────────────────────────────

@product_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("admin", "merchant")
def create_product(current_user):
    """
    Add a new product to the store catalogue.

    Request body (JSON) — required fields
    --------------------------------------
    {
        "name":          "Full Cream Milk 1L",
        "buying_price":  55.00,
        "selling_price": 75.00
    }

    Optional fields
    ---------------
    "sku", "category", "unit", "reorder_level", "store_id" (merchant only)
    """
    data = request.get_json(silent=True) or {}

    # ── Validate required fields ──────────────────────────────────────────────
    required = ["name", "buying_price", "selling_price"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            "message": f"Missing required fields: {', '.join(missing)}"
        }), 400

    # ── Determine store ───────────────────────────────────────────────────────
    if current_user.role == "merchant":
        # Merchant can create products in any store
        store_id = int(data.get("store_id") or current_user.store_id)
    else:
        # Admin can only create products in their own store
        store_id = current_user.store_id

    # ── Validate numeric prices ───────────────────────────────────────────────
    try:
        buying_price  = float(data["buying_price"])
        selling_price = float(data["selling_price"])
    except (TypeError, ValueError):
        return jsonify({"message": "buying_price and selling_price must be numbers."}), 400

    if buying_price < 0 or selling_price < 0:
        return jsonify({"message": "Prices cannot be negative."}), 400

    product = Product(
        store_id      = store_id,
        name          = data["name"].strip(),
        sku           = data.get("sku", "").strip() or None,
        category      = data.get("category", "").strip() or None,
        unit          = data.get("unit", "").strip() or None,
        buying_price  = buying_price,
        selling_price = selling_price,
        reorder_level = int(data.get("reorder_level", 10)),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Product created successfully.",
        "product": product.to_dict(),
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/products/<id>
# ─────────────────────────────────────────────────────────────────────────────

@product_bp.route("/<int:product_id>", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def get_product(current_user, product_id: int):
    """Return a single product by id."""
    product = Product.query.get_or_404(product_id, description="Product not found.")

    # Non-merchants can only see products in their own store
    if current_user.role != "merchant" and product.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    return jsonify(product.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/products/<id>
# ─────────────────────────────────────────────────────────────────────────────

@product_bp.route("/<int:product_id>", methods=["PATCH"])
@jwt_required()
@role_required("admin", "merchant")
def update_product(current_user, product_id: int):
    """
    Update one or more fields on an existing product.

    This is a PARTIAL update — only fields present in the request body
    are changed.  Fields not mentioned keep their current values.

    Updatable fields
    ────────────────
    name, sku, category, unit, buying_price, selling_price, reorder_level
    """
    product = Product.query.get_or_404(product_id, description="Product not found.")

    if current_user.role == "admin" and product.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    data = request.get_json(silent=True) or {}

    # Update only the fields that were explicitly provided
    updatable = ["name", "sku", "category", "unit",
                 "buying_price", "selling_price", "reorder_level"]

    for field in updatable:
        if field in data:
            setattr(product, field, data[field])

    db.session.commit()

    return jsonify({
        "message": "Product updated.",
        "product": product.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/products/<id>
# ─────────────────────────────────────────────────────────────────────────────

@product_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required()
@role_required("admin", "merchant")
def deactivate_product(current_user, product_id: int):
    """
    Soft-delete a product by setting is_active = False.

    The product disappears from the clerk's dropdown and active listings,
    but all historical InventoryEntry rows that reference it are preserved.
    This is MUCH safer than a hard DELETE which would break foreign keys.
    """
    product = Product.query.get_or_404(product_id, description="Product not found.")

    if current_user.role == "admin" and product.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    if not product.is_active:
        return jsonify({"message": "Product is already deactivated."}), 400

    product.is_active = False
    db.session.commit()

    return jsonify({"message": f"Product '{product.name}' has been deactivated."}), 200