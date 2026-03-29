# app/routes/inventory_routes.py
# ────────────────────────────────
# Inventory entry blueprint:
#
#   GET    /api/inventory/              list entries (scoped by role + filters)
#   POST   /api/inventory/              clerk creates a stock-taking entry
#   GET    /api/inventory/<id>          retrieve one entry
#   PATCH  /api/inventory/<id>          clerk/admin updates an entry
#   PATCH  /api/inventory/<id>/payment  admin marks supplier payment as paid/unpaid
#   DELETE /api/inventory/<id>          admin/merchant deletes an entry

from datetime import date, datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models     import InventoryEntry, Product
from app.utils      import role_required

inventory_bp = Blueprint("inventory", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/inventory/
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def list_entries(current_user):
    """
    Return inventory entries visible to the current user.

    Scope rules
    ───────────
    • Clerk / Admin  →  only their own store's entries
    • Merchant       →  all stores; use ?store_id= to filter one store

    Query params
    ────────────
    ?store_id=1              merchant: filter by store
    ?product_id=5            filter by product
    ?payment_status=unpaid   "paid" | "unpaid"
    ?from_date=2024-01-01    entries on or after this date (YYYY-MM-DD)
    ?to_date=2024-12-31      entries on or before this date (YYYY-MM-DD)
    ?clerk_id=3              admin/merchant: filter by specific clerk
    """
    query = InventoryEntry.query

    # ── Store scoping ─────────────────────────────────────────────────────────
    if current_user.role in ("admin", "clerk"):
        # Locked to their own store — cannot override with a query param
        query = query.filter_by(store_id=current_user.store_id)
    else:
        # Merchant: optional store filter
        store_id_filter = request.args.get("store_id", type=int)
        if store_id_filter:
            query = query.filter_by(store_id=store_id_filter)

    # ── Optional filters ──────────────────────────────────────────────────────
    product_id_filter = request.args.get("product_id", type=int)
    if product_id_filter:
        query = query.filter_by(product_id=product_id_filter)

    payment_filter = request.args.get("payment_status")
    if payment_filter in ("paid", "unpaid"):
        query = query.filter_by(payment_status=payment_filter)

    clerk_id_filter = request.args.get("clerk_id", type=int)
    if clerk_id_filter and current_user.role in ("admin", "merchant"):
        query = query.filter_by(clerk_id=clerk_id_filter)

    # ── Date range filters ────────────────────────────────────────────────────
    from_date_str = request.args.get("from_date")
    if from_date_str:
        try:
            query = query.filter(
                InventoryEntry.entry_date >= date.fromisoformat(from_date_str)
            )
        except ValueError:
            return jsonify({
                "message": "Invalid from_date. Use YYYY-MM-DD format."
            }), 400

    to_date_str = request.args.get("to_date")
    if to_date_str:
        try:
            query = query.filter(
                InventoryEntry.entry_date <= date.fromisoformat(to_date_str)
            )
        except ValueError:
            return jsonify({
                "message": "Invalid to_date. Use YYYY-MM-DD format."
            }), 400

    # ── Execute and return ────────────────────────────────────────────────────
    entries = query.order_by(InventoryEntry.entry_date.desc()).all()

    return jsonify([e.to_dict() for e in entries]), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/inventory/
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("clerk", "admin")
def create_entry(current_user):
    """
    Record a new stock-taking entry.

    Required body fields
    --------------------
    {
        "product_id":        10,
        "quantity_received": 100,
        "quantity_in_stock": 95,
        "buying_price":      55.00,
        "selling_price":     75.00
    }

    Optional fields
    ---------------
    "quantity_spoilt"  (default 0)
    "payment_status"   "paid" | "unpaid" (default "unpaid")
    "entry_date"       YYYY-MM-DD (defaults to today)
    "notes"            free text
    """
    data = request.get_json(silent=True) or {}

    # ── Validate required fields ──────────────────────────────────────────────
    required = ["product_id", "quantity_received", "quantity_in_stock",
                "buying_price", "selling_price"]
    missing = [f for f in required if data.get(f) is None]
    if missing:
        return jsonify({
            "message": f"Missing required fields: {', '.join(missing)}"
        }), 400

    # ── Verify the product exists and belongs to this store ───────────────────
    product = Product.query.get(data["product_id"])
    if not product:
        return jsonify({"message": "Product not found."}), 404

    if product.store_id != current_user.store_id:
        return jsonify({
            "message": "You can only record entries for products in your own store."
        }), 403

    # ── Parse entry_date (defaults to today) ──────────────────────────────────
    entry_date = date.today()
    if data.get("entry_date"):
        try:
            entry_date = date.fromisoformat(data["entry_date"])
        except ValueError:
            return jsonify({
                "message": "Invalid entry_date format. Use YYYY-MM-DD."
            }), 400

    # ── Validate quantities are non-negative integers ─────────────────────────
    try:
        qty_received = int(data["quantity_received"])
        qty_in_stock = int(data["quantity_in_stock"])
        qty_spoilt   = int(data.get("quantity_spoilt", 0))
    except (TypeError, ValueError):
        return jsonify({"message": "Quantities must be whole numbers."}), 400

    if any(q < 0 for q in [qty_received, qty_in_stock, qty_spoilt]):
        return jsonify({"message": "Quantities cannot be negative."}), 400

    # ── Validate payment status ────────────────────────────────────────────────
    payment_status = data.get("payment_status", "unpaid")
    if payment_status not in ("paid", "unpaid"):
        return jsonify({"message": "payment_status must be 'paid' or 'unpaid'."}), 400

    entry = InventoryEntry(
        store_id          = current_user.store_id,
        product_id        = data["product_id"],
        clerk_id          = current_user.id,
        quantity_received = qty_received,
        quantity_in_stock = qty_in_stock,
        quantity_spoilt   = qty_spoilt,
        buying_price      = float(data["buying_price"]),
        selling_price     = float(data["selling_price"]),
        payment_status    = payment_status,
        entry_date        = entry_date,
        notes             = data.get("notes", "").strip() or None,
    )

    db.session.add(entry)
    db.session.commit()

    return jsonify({
        "message": "Stock entry recorded successfully.",
        "entry":   entry.to_dict(),
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/inventory/<id>
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/<int:entry_id>", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def get_entry(current_user, entry_id: int):
    """Retrieve a single inventory entry by id."""
    entry = InventoryEntry.query.get_or_404(entry_id, description="Entry not found.")

    # Non-merchants can only view entries from their own store
    if current_user.role != "merchant" and entry.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    return jsonify(entry.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/inventory/<id>
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/<int:entry_id>", methods=["PATCH"])
@jwt_required()
@role_required("clerk", "admin")
def update_entry(current_user, entry_id: int):
    """
    Partially update an inventory entry.

    Rules
    ─────
    • Clerk  →  can only edit entries THEY created
    • Admin  →  can edit any entry in their store

    Only these fields can be updated:
    quantity_received, quantity_in_stock, quantity_spoilt,
    buying_price, selling_price, notes
    """
    entry = InventoryEntry.query.get_or_404(entry_id, description="Entry not found.")

    # Clerk can only touch their own entries
    if current_user.role == "clerk" and entry.clerk_id != current_user.id:
        return jsonify({"message": "You can only edit your own entries."}), 403

    # Admin can touch any entry in their store
    if current_user.role == "admin" and entry.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    data = request.get_json(silent=True) or {}

    # Partial update — only change what was provided
    editable = ["quantity_received", "quantity_in_stock", "quantity_spoilt",
                "buying_price", "selling_price", "notes"]

    for field in editable:
        if field in data:
            setattr(entry, field, data[field])

    db.session.commit()

    return jsonify({
        "message": "Entry updated.",
        "entry":   entry.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/inventory/<id>/payment
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/<int:entry_id>/payment", methods=["PATCH"])
@jwt_required()
@role_required("admin", "merchant")
def update_payment_status(current_user, entry_id: int):
    """
    Change the payment status of an inventory entry.

    This is the action that represents "we have paid the supplier for
    this batch".  Typically:  unpaid → paid.

    Admins can also revert to unpaid if a payment was marked in error.

    Request body
    ------------
    { "payment_status": "paid" }   or   { "payment_status": "unpaid" }

    A timestamp (payment_updated_at) is recorded when status changes
    to provide an audit trail.
    """
    entry = InventoryEntry.query.get_or_404(entry_id, description="Entry not found.")

    # Admin scoping
    if current_user.role == "admin" and entry.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    data           = request.get_json(silent=True) or {}
    new_status     = data.get("payment_status", "").strip()

    if new_status not in ("paid", "unpaid"):
        return jsonify({
            "message": "payment_status must be 'paid' or 'unpaid'."
        }), 400

    entry.payment_status     = new_status
    entry.payment_updated_at = datetime.now(timezone.utc)   # audit stamp

    db.session.commit()

    return jsonify({
        "message": f"Payment status updated to '{new_status}'.",
        "entry":   entry.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/inventory/<id>
# ─────────────────────────────────────────────────────────────────────────────

@inventory_bp.route("/<int:entry_id>", methods=["DELETE"])
@jwt_required()
@role_required("admin", "merchant")
def delete_entry(current_user, entry_id: int):
    """
    Permanently delete an inventory entry.

    Only admin and merchant can do this (clerks cannot delete records).
    Consider whether you really want to delete vs keeping for audit purposes.
    """
    entry = InventoryEntry.query.get_or_404(entry_id, description="Entry not found.")

    if current_user.role == "admin" and entry.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    db.session.delete(entry)
    db.session.commit()

    return jsonify({"message": "Entry deleted."}), 200