# app/routes/user_routes.py
# ──────────────────────────
# User management blueprint:
#
#   GET    /api/users/me                 current user's own profile
#   GET    /api/users/                   list users (scoped by role)
#   PATCH  /api/users/<id>/activate      reactivate a deactivated account
#   PATCH  /api/users/<id>/deactivate    soft-disable an account (keeps history)
#   DELETE /api/users/<id>               permanently delete a user

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models     import User
from app.utils      import role_required

user_bp = Blueprint("users", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users/me
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/me", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def get_me(current_user: User):
    """
    Return the currently authenticated user's profile.

    Called by the React app on startup to restore session state from a
    stored JWT without asking the user to log in again.
    """
    return jsonify(current_user.to_dict(include_store=True)), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users/
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin")
def list_users(current_user: User):
    """
    List users visible to the current user.

    Scope rules
    ───────────
    • Admin    →  only clerks in their own store
    • Merchant →  all users; filterable via query params

    Query params (merchant only)
    ────────────────────────────
    ?role=clerk          filter by role
    ?store_id=1          filter by store
    ?include_inactive=1  include deactivated accounts (default: active only)
    """
    role_filter       = request.args.get("role")
    store_id_filter   = request.args.get("store_id", type=int)
    include_inactive  = request.args.get("include_inactive", "0") == "1"

    query = User.query

    if current_user.role == "admin":
        # Admins can only see clerks inside their own store — hard-coded scope
        query = query.filter_by(
            store_id = current_user.store_id,
            role     = "clerk",
        )
    else:
        # Merchant: apply optional filters
        if role_filter:
            query = query.filter_by(role=role_filter)
        if store_id_filter:
            query = query.filter_by(store_id=store_id_filter)

    # By default only return active accounts; admins use include_inactive=1
    # to see who has been deactivated
    if not include_inactive:
        query = query.filter_by(is_active=True)

    users = query.order_by(User.last_name, User.first_name).all()

    return jsonify([u.to_dict(include_store=True) for u in users]), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/users/<id>/deactivate
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/<int:user_id>/deactivate", methods=["PATCH"])
@jwt_required()
@role_required("merchant", "admin")
def deactivate_user(current_user: User, user_id: int):
    """
    Soft-disable a user account (set is_active = False).

    The account still exists and all their historical data (inventory entries,
    supply requests) is preserved.  They simply cannot log in any more.
    This supports the "probation" use case from the spec.

    Who can deactivate whom
    ───────────────────────
    • Merchant  →  can deactivate admins and clerks
    • Admin     →  can only deactivate clerks in their own store
    • Neither can deactivate themselves
    """
    target = User.query.get_or_404(user_id, description="User not found.")

    # ── Guard: cannot deactivate yourself ────────────────────────────────────
    if target.id == current_user.id:
        return jsonify({"message": "You cannot deactivate your own account."}), 400

    # ── Guard: admin scope ────────────────────────────────────────────────────
    if current_user.role == "admin":
        if target.role != "clerk" or target.store_id != current_user.store_id:
            return jsonify({
                "message": "Admins can only deactivate clerks in their own store."
            }), 403

    # ── Guard: already inactive ───────────────────────────────────────────────
    if not target.is_active:
        return jsonify({"message": "This account is already deactivated."}), 400

    target.is_active = False
    db.session.commit()

    return jsonify({
        "message": f"Account for {target.email} has been deactivated.",
        "user":    target.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/users/<id>/activate
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/<int:user_id>/activate", methods=["PATCH"])
@jwt_required()
@role_required("merchant", "admin")
def activate_user(current_user: User, user_id: int):
    """
    Restore a deactivated user's ability to log in (set is_active = True).

    Useful after a probation period ends or if a deactivation was a mistake.
    """
    target = User.query.get_or_404(user_id, description="User not found.")

    if current_user.role == "admin":
        if target.role != "clerk" or target.store_id != current_user.store_id:
            return jsonify({
                "message": "Admins can only activate clerks in their own store."
            }), 403

    if target.is_active:
        return jsonify({"message": "This account is already active."}), 400

    target.is_active = True
    db.session.commit()

    return jsonify({
        "message": f"Account for {target.email} has been reactivated.",
        "user":    target.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/users/<id>
# ─────────────────────────────────────────────────────────────────────────────

@user_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
@role_required("merchant", "admin")
def delete_user(current_user: User, user_id: int):
    """
    Permanently delete a user record from the database.

    WARNING: This is irreversible. All inventory entries and supply requests
    created by this user will lose their clerk reference (or cascade-delete
    depending on DB constraints).  Consider deactivating instead to preserve
    the audit trail.

    Who can delete whom
    ───────────────────
    • Merchant  →  can delete admins and clerks
    • Admin     →  can only delete clerks in their own store
    • Neither can delete themselves
    """
    target = User.query.get_or_404(user_id, description="User not found.")

    if target.id == current_user.id:
        return jsonify({"message": "You cannot delete your own account."}), 400

    if current_user.role == "admin":
        if target.role != "clerk" or target.store_id != current_user.store_id:
            return jsonify({
                "message": "Admins can only delete clerks in their own store."
            }), 403

    email = target.email   # capture before deletion for the response message
    db.session.delete(target)
    db.session.commit()

    return jsonify({"message": f"User {email} has been permanently deleted."}), 200