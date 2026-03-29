# app/routes/supply_routes.py
# ────────────────────────────
# Supply request blueprint:
#
#   GET    /api/supply/              list requests (scoped by role)
#   POST   /api/supply/              clerk submits a supply request
#   GET    /api/supply/<id>          retrieve one request
#   PATCH  /api/supply/<id>/action   admin approves or declines a request

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models     import SupplyRequest, Product
from app.utils      import role_required

supply_bp = Blueprint("supply", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/supply/
# ─────────────────────────────────────────────────────────────────────────────

@supply_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def list_supply_requests(current_user):
    """
    Return supply requests visible to the current user.

    Scope rules
    ───────────
    • Clerk    →  only THEIR OWN requests
    • Admin    →  all requests for their store
    • Merchant →  all stores; use ?store_id= to narrow down

    Query params
    ────────────
    ?status=pending    "pending" | "approved" | "declined"
    ?store_id=1        merchant only
    ?product_id=5      filter by product
    """
    query = SupplyRequest.query

    # ── Scope by role ─────────────────────────────────────────────────────────
    if current_user.role == "clerk":
        # Clerks only see their own requests
        query = query.filter_by(clerk_id=current_user.id)

    elif current_user.role == "admin":
        # Admins see all requests for their store
        query = query.filter_by(store_id=current_user.store_id)

    else:
        # Merchant: optional store filter
        store_id_filter = request.args.get("store_id", type=int)
        if store_id_filter:
            query = query.filter_by(store_id=store_id_filter)

    # ── Optional filters ──────────────────────────────────────────────────────
    status_filter = request.args.get("status")
    if status_filter in ("pending", "approved", "declined"):
        query = query.filter_by(status=status_filter)

    product_id_filter = request.args.get("product_id", type=int)
    if product_id_filter:
        query = query.filter_by(product_id=product_id_filter)

    requests_list = query.order_by(SupplyRequest.created_at.desc()).all()

    return jsonify([r.to_dict() for r in requests_list]), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/supply/
# ─────────────────────────────────────────────────────────────────────────────

@supply_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("clerk", "admin")
def create_supply_request(current_user):
    """
    Submit a request for additional stock.

    The request starts as "pending" and awaits admin action.
    The admin receives it in their dashboard and can approve or decline.

    Request body (JSON)
    -------------------
    {
        "product_id":         10,
        "quantity_requested": 200,
        "reason":             "Stock running low — only 12 units left"
    }
    """
    data = request.get_json(silent=True) or {}

    product_id         = data.get("product_id")
    quantity_requested = data.get("quantity_requested")

    # ── Validate required fields ──────────────────────────────────────────────
    if not product_id or not quantity_requested:
        return jsonify({
            "message": "'product_id' and 'quantity_requested' are required."
        }), 400

    try:
        quantity_requested = int(quantity_requested)
        if quantity_requested <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({
            "message": "'quantity_requested' must be a positive whole number."
        }), 400

    # ── Verify the product exists and belongs to this store ───────────────────
    product = Product.query.get(product_id)
    if not product or product.store_id != current_user.store_id:
        return jsonify({
            "message": "Product not found in your store."
        }), 404

    supply_request = SupplyRequest(
        store_id           = current_user.store_id,
        product_id         = product_id,
        clerk_id           = current_user.id,
        quantity_requested = quantity_requested,
        reason             = data.get("reason", "").strip() or None,
        status             = "pending",
    )

    db.session.add(supply_request)
    db.session.commit()

    return jsonify({
        "message": (
            "Supply request submitted. "
            "Your store admin will review it."
        ),
        "request": supply_request.to_dict(),
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/supply/<id>
# ─────────────────────────────────────────────────────────────────────────────

@supply_bp.route("/<int:request_id>", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def get_supply_request(current_user, request_id: int):
    """Retrieve a single supply request by id."""
    supply_req = SupplyRequest.query.get_or_404(
        request_id, description="Supply request not found."
    )

    # Clerks can only view their own requests
    if current_user.role == "clerk" and supply_req.clerk_id != current_user.id:
        return jsonify({"message": "Access denied."}), 403

    # Admins can only view requests in their store
    if current_user.role == "admin" and supply_req.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    return jsonify(supply_req.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/supply/<id>/action
# ─────────────────────────────────────────────────────────────────────────────

@supply_bp.route("/<int:request_id>/action", methods=["PATCH"])
@jwt_required()
@role_required("admin", "merchant")
def action_supply_request(current_user, request_id: int):
    """
    Approve or decline a pending supply request.

    Only admin and merchant can take action on supply requests.
    Once a decision is made, the status is FINAL — it cannot be changed again.

    Request body (JSON)
    -------------------
    {
        "action": "approved",
        "note":   "Confirmed with supplier — delivery expected Friday."
    }

    or

    {
        "action": "declined",
        "note":   "Budget not available this month — resubmit next quarter."
    }

    The `note` field is optional but strongly encouraged for "declined"
    decisions so the clerk understands why their request was rejected.
    """
    supply_req = SupplyRequest.query.get_or_404(
        request_id, description="Supply request not found."
    )

    # Admin scoping
    if current_user.role == "admin" and supply_req.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    # ── Guard: only pending requests can be acted on ──────────────────────────
    if supply_req.status != "pending":
        return jsonify({
            "message": f"This request has already been {supply_req.status}. No further action is possible."
        }), 400

    data   = request.get_json(silent=True) or {}
    action = data.get("action", "").strip().lower()
    note   = data.get("note",   "").strip() or None

    if action not in ("approved", "declined"):
        return jsonify({
            "message": "'action' must be 'approved' or 'declined'."
        }), 400

    # ── Apply the decision ────────────────────────────────────────────────────
    supply_req.status      = action
    supply_req.admin_id    = current_user.id
    supply_req.admin_note  = note
    supply_req.resolved_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({
        "message": f"Supply request has been {action}.",
        "request": supply_req.to_dict(),
    }), 200