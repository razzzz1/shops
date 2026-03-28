# app/utils/__init__.py
# ──────────────────────
# Re-exports every utility so route files can use a single import line
# instead of knowing which sub-module each helper lives in:
#
#   ✓ Clean (use this):
#       from app.utils import hash_password, role_required
#
#   ✗ Verbose (also works but don't bother):
#       from app.utils.password_helpers import hash_password
#       from app.utils.decorators import role_required
#
# Adding a new utility?  Put it in the appropriate sub-module, then
# add it to this file's imports and __all__.

from app.utils.password_helpers import hash_password, check_password        # noqa: F401
from app.utils.token_helpers    import (                                     # noqa: F401
    generate_invitation_token,
    verify_invitation_token,
)
from app.utils.decorators       import role_required, same_store_required    # noqa: F401

__all__ = [
    # Password helpers
    "hash_password",
    "check_password",
    # Invitation token helpers
    "generate_invitation_token",
    "verify_invitation_token",
    # RBAC decorators
    "role_required",
    "same_store_required",
]