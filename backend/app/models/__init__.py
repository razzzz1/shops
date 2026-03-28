# app/models/__init__.py
# ───────────────────────
# Re-exports every model class so the rest of the codebase can use
# a single clean import instead of knowing which file each model lives in:
#
#   from app.models import User, Store, Product   ← clean (use this)
#   from app.models.user import User              ← also works but verbose
#
# SQLAlchemy requires ALL model classes to be imported before
# `flask db upgrade` or `db.create_all()` is called — otherwise Alembic
# doesn't know about the tables and won't create them.
#
# This file serves as that central registration point.  create_app() imports
# from here (see app/__init__.py) to ensure all models are visible to
# SQLAlchemy's metadata before any DB operation runs.

from app.models.user             import User             # noqa: F401
from app.models.store            import Store            # noqa: F401
from app.models.product          import Product          # noqa: F401
from app.models.inventory_entry  import InventoryEntry   # noqa: F401
from app.models.supply_request   import SupplyRequest    # noqa: F401
from app.models.invitation_token import InvitationToken  # noqa: F401

__all__ = [
    "User",
    "Store",
    "Product",
    "InventoryEntry",
    "SupplyRequest",
    "InvitationToken",
]