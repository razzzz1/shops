# app/models/store.py
# ────────────────────
# Store model — a physical or logical store location.
#
# Relationships in plain English:
#   One store  →  many users   (one admin + many clerks)
#   One store  →  many products  (the product catalogue for that store)
#   One store  →  many inventory entries  (daily stock records)
#   One store  →  many supply requests

from datetime import datetime, timezone
from app.extensions import db


class Store(db.Model):
    __tablename__ = "stores"

    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Details ────────────────────────────────────────────────────────────────
    name     = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(500), nullable=True)   # street address, city, etc.

    # Soft-delete flag — deactivating a store hides it from the merchant
    # dashboard without losing its historical data.
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Timestamp ──────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    # foreign_keys must be specified explicitly here because the User model
    # has TWO foreign keys that reference stores.id (store_id and potentially
    # others), so SQLAlchemy cannot infer which one to use for this relationship.
    users = db.relationship(
        "User",
        back_populates="store",
        foreign_keys="User.store_id",
        lazy="dynamic",
    )

    products = db.relationship(
        "Product",
        back_populates="store",
        lazy="dynamic",
    )

    inventory_entries = db.relationship(
        "InventoryEntry",
        back_populates="store",
        lazy="dynamic",
    )

    supply_requests = db.relationship(
        "SupplyRequest",
        back_populates="store",
        lazy="dynamic",
    )

    # ── Helpers ────────────────────────────────────────────────────────────────
    def __repr__(self):
        return f"<Store id={self.id} name={self.name}>"

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "location":  self.location,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }