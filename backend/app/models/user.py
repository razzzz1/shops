# app/models/user.py
# ───────────────────
# User model — works with both SQLite (dev) and PostgreSQL (prod).
# Roles use String instead of db.Enum for SQLite compatibility.

from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name    = db.Column(db.String(100), nullable=False)
    last_name     = db.Column(db.String(100), nullable=False)

    # String instead of Enum — works on both SQLite and PostgreSQL
    # Valid values: "merchant", "admin", "clerk"
    role      = db.Column(db.String(20), nullable=False, default="clerk")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    store_id  = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    store             = db.relationship("Store", back_populates="users", foreign_keys=[store_id])
    inventory_entries = db.relationship("InventoryEntry", back_populates="clerk", lazy="dynamic")
    supply_requests   = db.relationship("SupplyRequest", back_populates="clerk", foreign_keys="SupplyRequest.clerk_id", lazy="dynamic")
    sent_invitations  = db.relationship("InvitationToken", back_populates="inviter", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, include_store=False):
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