# app/models/user.py
# ───────────────────
# User model — every person who can log into the system.
#
# Roles
# ─────
#   merchant  →  top-level owner; invited admins, sees all stores
#   admin     →  manages one store; invites clerks, approves supply requests
#   clerk     →  enters daily stock records for their assigned store
#
# All three roles share this single table.  The `role` column controls
# what each user is allowed to do (enforced in app/utils/decorators.py).

from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Identity ───────────────────────────────────────────────────────────────
    # index=True speeds up the login query (WHERE email = ?)
    email      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name  = db.Column(db.String(100), nullable=False)

    # Passwords are ALWAYS stored as bcrypt hashes — never plain text.
    # The hash is a fixed-length string regardless of password length.
    password_hash = db.Column(db.String(255), nullable=False)

    # ── Role ───────────────────────────────────────────────────────────────────
    # db.Enum creates a PostgreSQL ENUM type, so only these three values
    # can ever be stored — the database itself enforces this constraint.
    role = db.Column(
        db.Enum("merchant", "admin", "clerk", name="user_role_enum"),
        nullable=False,
        default="clerk",
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    # is_active=False means the account is deactivated (locked out) but
    # NOT deleted.  All historical data (entries, requests) is preserved.
    # This supports the "probation" use case mentioned in the spec.
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Store assignment ───────────────────────────────────────────────────────
    # Clerks and admins belong to exactly one store.
    # Merchants are not scoped to a store (store_id may be NULL).
    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=True,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    # back_populates creates a two-way link:
    #   user.store         → the Store object this user belongs to
    #   store.users        → all User objects in that store
    store = db.relationship(
        "Store",
        back_populates="users",
        foreign_keys=[store_id],  # explicit because Store has multiple FK refs
    )

    # A clerk can create many inventory entries over time
    inventory_entries = db.relationship(
        "InventoryEntry",
        back_populates="clerk",
        lazy="dynamic",  # returns a query object; not loaded until .all() is called
    )

    # A clerk can submit many supply requests
    supply_requests = db.relationship(
        "SupplyRequest",
        back_populates="clerk",
        foreign_keys="SupplyRequest.clerk_id",
        lazy="dynamic",
    )

    # A merchant or admin can send many invitation emails
    sent_invitations = db.relationship(
        "InvitationToken",
        back_populates="inviter",
        lazy="dynamic",
    )

    # ── Helpers ────────────────────────────────────────────────────────────────
    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

    @property
    def full_name(self):
        """Convenience: 'Jane Smith'"""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, include_store=False):
        """
        Serialise to a plain dict that is safe to return as JSON.

        Parameters
        ----------
        include_store : bool
            If True, embed a small store sub-object {id, name} in the response.
            Useful for the /users/me endpoint so the frontend knows the store name.
        """
        data = {
            "id":         self.id,
            "email":      self.email,
            "first_name": self.first_name,
            "last_name":  self.last_name,
            "full_name":  self.full_name,
            "role":       self.role,
            "is_active":  self.is_active,
            "store_id":   self.store_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_store and self.store:
            data["store"] = {
                "id":       self.store.id,
                "name":     self.store.name,
                "location": self.store.location,
            }
        return data