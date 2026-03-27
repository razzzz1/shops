# app/models/inventory_entry.py
# ──────────────────────────────
# InventoryEntry model — a single stock-taking record created by a clerk.
#
# One entry = one batch/delivery of one product on one date.
# Multiple entries accumulate over time, building the historical dataset
# that the reporting module aggregates into weekly/monthly/annual charts.
#
# Key quantities
# ──────────────
#   quantity_received  →  items that arrived from the supplier this batch
#   quantity_in_stock  →  items currently on the shelf (received - sold - spoilt)
#   quantity_spoilt    →  items that are broken, expired, or otherwise unusable
#
# Payment tracking
# ────────────────
#   payment_status = "unpaid"  →  supplier invoice is outstanding
#   payment_status = "paid"    →  invoice has been settled
#
# When an admin marks a batch as paid, payment_updated_at is stamped so
# there is an audit trail of when payment was recorded.

from datetime import datetime, timezone
from app.extensions import db


class InventoryEntry(db.Model):
    __tablename__ = "inventory_entries"

    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Foreign keys ───────────────────────────────────────────────────────────
    store_id   = db.Column(db.Integer, db.ForeignKey("stores.id"),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    clerk_id   = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)

    # ── Stock quantities ───────────────────────────────────────────────────────
    quantity_received = db.Column(db.Integer, nullable=False, default=0)
    quantity_in_stock = db.Column(db.Integer, nullable=False, default=0)
    quantity_spoilt   = db.Column(db.Integer, nullable=False, default=0)

    # ── Prices for THIS delivery batch ────────────────────────────────────────
    # Stored here (not just on Product) because supplier prices can change
    # between deliveries.  This gives accurate cost reporting per batch.
    buying_price  = db.Column(db.Numeric(12, 2), nullable=False)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False)

    # ── Supplier payment status ────────────────────────────────────────────────
    payment_status = db.Column(
        db.Enum("paid", "unpaid", name="payment_status_enum"),
        nullable=False,
        default="unpaid",
    )
    # Stamped by the admin when they change status to "paid"
    payment_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Date of entry ──────────────────────────────────────────────────────────
    # Date only (no time) — one entry per product per day is the typical pattern,
    # but the schema does not enforce uniqueness so a clerk can log multiple
    # deliveries on the same day if needed.
    entry_date = db.Column(
        db.Date,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).date(),
    )

    # Optional free-text notes (e.g. "Delivery damaged — see photos")
    notes = db.Column(db.Text, nullable=True)

    # ── Record creation timestamp ─────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    store   = db.relationship("Store",   back_populates="inventory_entries")
    product = db.relationship("Product", back_populates="inventory_entries")
    clerk   = db.relationship("User",    back_populates="inventory_entries")

    # ── Helpers ────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<InventoryEntry id={self.id} "
            f"product_id={self.product_id} "
            f"date={self.entry_date} "
            f"payment={self.payment_status}>"
        )

    @property
    def total_cost(self):
        """Total cost of this delivery batch (buying_price × quantity_received)."""
        return float(self.buying_price) * self.quantity_received

    @property
    def total_revenue_potential(self):
        """Potential revenue if all in-stock items are sold at selling price."""
        return float(self.selling_price) * self.quantity_in_stock

    def to_dict(self, include_product=True, include_clerk=True):
        """
        Serialise to a JSON-safe dict.

        Parameters
        ----------
        include_product : bool
            Embed a small product sub-object {id, name, sku}.
        include_clerk : bool
            Embed a small clerk sub-object {id, first_name, last_name}.
        """
        data = {
            "id":                  self.id,
            "store_id":            self.store_id,
            "product_id":          self.product_id,
            "clerk_id":            self.clerk_id,
            "quantity_received":   self.quantity_received,
            "quantity_in_stock":   self.quantity_in_stock,
            "quantity_spoilt":     self.quantity_spoilt,
            "buying_price":        float(self.buying_price),
            "selling_price":       float(self.selling_price),
            "total_cost":          round(self.total_cost, 2),
            "total_revenue_potential": round(self.total_revenue_potential, 2),
            "payment_status":      self.payment_status,
            "payment_updated_at":  (
                self.payment_updated_at.isoformat()
                if self.payment_updated_at else None
            ),
            "entry_date":          self.entry_date.isoformat() if self.entry_date else None,
            "notes":               self.notes,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
        }
        if include_product and self.product:
            data["product"] = {
                "id":       self.product.id,
                "name":     self.product.name,
                "sku":      self.product.sku,
                "category": self.product.category,
                "unit":     self.product.unit,
            }
        if include_clerk and self.clerk:
            data["clerk"] = {
                "id":         self.clerk.id,
                "first_name": self.clerk.first_name,
                "last_name":  self.clerk.last_name,
            }
        return data