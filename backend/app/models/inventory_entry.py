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