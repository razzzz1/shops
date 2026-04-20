# app/models/product.py
# ──────────────────────
# Product model — master catalogue of stockable items for a store.
#
# Each product belongs to exactly one store.
# buying_price and selling_price here are the store's CURRENT / DEFAULT prices.
# Individual InventoryEntry rows record the actual prices for each delivery
# batch — they may differ from these defaults if a supplier changes their rate.
#
# The reorder_level field is the threshold at which the clerk should
# request more stock.  If quantity_in_stock falls below this, the system
# (or the clerk) should raise a SupplyRequest.

from datetime import datetime, timezone
from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Store link ─────────────────────────────────────────────────────────────
    # A product belongs to exactly one store.
    # Deleting a store would orphan products; in practice we deactivate stores
    # rather than deleting them, so this FK is safe.
    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    name     = db.Column(db.String(300), nullable=False)
    sku      = db.Column(db.String(100), unique=True, nullable=True)  # barcode / stock-keeping unit
    category = db.Column(db.String(100), nullable=True)               # e.g. "Dairy", "Electronics"
    unit     = db.Column(db.String(50),  nullable=True)               # e.g. "kg", "pieces", "litres"

    # ── Default pricing ────────────────────────────────────────────────────────
    # Numeric(12, 2) stores values like 9999999999.99 — suitable for KES prices.
    # Float is NOT used because floating-point arithmetic is imprecise for money.
    buying_price  = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # ── Reorder threshold ──────────────────────────────────────────────────────
    # When current stock falls at or below this level, it signals that a
    # supply request should be raised.
    reorder_level = db.Column(db.Integer, default=10, nullable=False)

    # ── Status ─────────────────────────────────────────────────────────────────
    # Soft-delete: deactivating hides the product from clerk dropdowns
    # but preserves its history in inventory_entries.
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    store = db.relationship(
        "Store",
        back_populates="products",
    )

    inventory_entries = db.relationship(
        "InventoryEntry",
        back_populates="product",
        lazy="dynamic",
    )

    supply_requests = db.relationship(
        "SupplyRequest",
        back_populates="product",
        lazy="dynamic",
    )

    # ── Helpers ────────────────────────────────────────────────────────────────
    def __repr__(self):
        return f"<Product id={self.id} name={self.name} sku={self.sku}>"

    @property
    def margin(self):
        """
        Gross margin as a decimal (e.g. 0.40 = 40%).
        Returns None if buying_price is zero to avoid division by zero.
        """
        if not self.buying_price:
            return None
        return float((self.selling_price - self.buying_price) / self.selling_price)

    def to_dict(self):
        return {
            "id":            self.id,
            "store_id":      self.store_id,
            "name":          self.name,
            "sku":           self.sku,
            "category":      self.category,
            "unit":          self.unit,
            # Convert Decimal → float so JSON serialisation works
            "buying_price":  float(self.buying_price),
            "selling_price": float(self.selling_price),
            "reorder_level": self.reorder_level,
            "is_active":     self.is_active,
            "margin_pct":    round(self.margin * 100, 2) if self.margin else None,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }