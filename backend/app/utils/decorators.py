# app/utils/decorators.py
# ────────────────────────
# Route decorators for Role-Based Access Control (RBAC).
#
# How Flask route decorators work
# ────────────────────────────────
# A decorator wraps a route function so code can run BEFORE the route
# handler itself.  If the checks pass, the original function is called.
# If they fail, we return an error response immediately.
#
# Decorator stacking order matters.  Flask-JWT-Extended's @jwt_required()
# must run FIRST (outermost) so the JWT is validated before our decorators
# try to read the user identity from it.
#
# Correct order:
#
#   @blueprint.route("/example")
#   @jwt_required()           ← 1st: validates the JWT and populates identity
#   @role_required("admin")   ← 2nd: checks role, injects current_user
#   @same_store_required      ← 3rd: checks store scope (optional)
#   def example_view(current_user):
#       ...
#
# The @wraps(fn) call on each inner wrapper preserves the original
# function's __name__ and __doc__ — without it, Flask would see multiple
# routes all named "wrapper" and raise an AssertionError.

from functools import wraps
from flask_jwt_extended import get_jwt_identity
from app.models import User


def role_required(*allowed_roles: str):
    """
    Decorator factory — restrict a route to users whose role is in
    the `allowed_roles` tuple.

    On success  →  calls the route, injecting the User object as
                   the keyword argument `current_user`.
    On failure  →  returns a JSON error response without calling the route.

    Checks performed (in order):
      1. User exists in the database (JWT identity is a valid user id)
      2. User's account is active (not deactivated)
      3. User's role is in the allowed_roles list

    Parameters
    ----------
    *allowed_roles : str
        One or more role strings: "merchant", "admin", "clerk"

    Usage
    -----
    @blueprint.route("/admin-only")
    @jwt_required()
    @role_required("merchant", "admin")
    def admin_view(current_user):
        return {"role": current_user.role}

    @blueprint.route("/clerk-entry")
    @jwt_required()
    @role_required("clerk")
    def clerk_view(current_user):
        return {"store": current_user.store_id}
    """
    def decorator(fn):
        @wraps(fn)   # preserve fn.__name__ so Flask routing doesn't break
        def wrapper(*args, **kwargs):

            # get_jwt_identity() reads the `sub` claim from the validated JWT.
            # We stored the user's integer id there when the token was issued.
            user_id = get_jwt_identity()

            # Look up the full User row — we need role, is_active, store_id
            user = User.query.get(user_id)

            # ── Guard 1: user must exist ───────────────────────────────────────
            if not user:
                return {
                    "message": "User account not found."
                }, 404

            # ── Guard 2: account must be active ───────────────────────────────
            # A deactivated user still has a valid JWT (we don't blacklist them)
            # so we must check is_active on every request.
            if not user.is_active:
                return {
                    "message": (
                        "Your account has been deactivated. "
                        "Please contact your administrator."
                    )
                }, 403

            # ── Guard 3: role must be permitted for this endpoint ──────────────
            if user.role not in allowed_roles:
                return {
                    "message": (
                        f"Access denied. "
                        f"This endpoint requires one of: "
                        f"{', '.join(allowed_roles)}."
                    )
                }, 403

            # All checks passed — inject user into the route handler.
            # Using a keyword argument means the route signature is explicit
            # and self-documenting: def my_route(current_user): ...
            return fn(*args, current_user=user, **kwargs)

        return wrapper
    return decorator


def same_store_required(fn):
    """
    Decorator — ensures admin/clerk users can only access resources
    that belong to THEIR OWN store.

    Merchants bypass this check entirely (they have global visibility
    across all stores — that is the point of the merchant role).

    Must be applied AFTER @role_required so that `current_user` has
    already been resolved and injected into kwargs.

    Expects the URL to contain a `store_id` path variable, e.g.:
        /api/inventory/?store_id=3
        /api/reports/summary?store_id=3

    If store_id is absent from the URL, the check is skipped (the route
    handler is responsible for scoping by current_user.store_id instead).

    Usage
    -----
    @blueprint.route("/stores/<int:store_id>/report")
    @jwt_required()
    @role_required("merchant", "admin")
    @same_store_required
    def store_report(current_user, store_id):
        # admin only reaches here if store_id == current_user.store_id
        # merchant always reaches here
        ...
    """
    @wraps(fn)
    def wrapper(*args, current_user: User, **kwargs):

        # Merchants can see all stores — skip the store check
        if current_user.role == "merchant":
            return fn(*args, current_user=current_user, **kwargs)

        # Extract store_id from URL path kwargs (e.g. <int:store_id>)
        # or fall back to a query-string param the caller may have passed
        requested_store_id = kwargs.get("store_id")

        if requested_store_id is not None:
            if int(requested_store_id) != current_user.store_id:
                return {
                    "message": (
                        "Access denied. "
                        "You can only access data for your own store."
                    )
                }, 403

        return fn(*args, current_user=current_user, **kwargs)

    return wrapper