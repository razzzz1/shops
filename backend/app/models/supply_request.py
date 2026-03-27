# app/models/supply_request.py
# ─────────────────────────────
# SupplyRequest model — a clerk's formal request for more stock.
#
# Lifecycle
# ─────────
#   1. Clerk submits request  →  status = "pending"
#   2a. Admin approves        →  status = "approved", resolved_at stamped
#   2b. Admin declines        →  status = "declined", resolved_at stamped
#
# Once resolved, the status is FINAL — no further transitions.
# The admin can optionally add a note explaining their decision.
#
# This request goes to the store admin (not the merchant directly).
# The admin then arranges the order with the supplier.
 
from datetime import datetime, timezone
from app.extensions import db
 
 
class SupplyRequest(db.Model):
    __tablename__ = "supply_requests"
 
    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
 
    # ── Foreign keys ───────────────────────────────────────────────────────────
    store_id   = db.Column(db.Integer, db.ForeignKey("stores.id"),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
 
    # The clerk who raised the request
    clerk_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
 
    # The admin who approved or declined it — NULL until a decision is made
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
 
    # ── Request details ────────────────────────────────────────────────────────
    quantity_requested = db.Column(db.Integer, nullable=False)
 
    # Clerk explains WHY they need more stock (optional but encouraged)
    reason = db.Column(db.Text, nullable=True)
 
    # ── Status ─────────────────────────────────────────────────────────────────
    status = db.Column(
        db.Enum("pending", "approved", "declined", name="supply_status_enum"),
        nullable=False,
        default="pending",
    )
 
    # Admin explains their decision (optional — especially for declines)
    admin_note = db.Column(db.Text, nullable=True)
 
    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # Stamped when admin approves or declines — NULL while still pending
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
 
    # ── Relationships ──────────────────────────────────────────────────────────
    store   = db.relationship("Store",   back_populates="supply_requests")
    product = db.relationship("Product", back_populates="supply_requests")
 
    # Two FK columns point to users.id so we must name them explicitly
    clerk = db.relationship("User", back_populates="supply_requests", foreign_keys=[clerk_id])
    admin = db.relationship("User", foreign_keys=[admin_id])