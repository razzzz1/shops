// src/pages/clerk/ClerkDashboard.js
// ─────────────────────────────────────
// Main landing page for clerks (and admins using the stock entry view).
//
// Two sections:
//   1. KPI summary cards — pulled from GET /api/reports/summary
//   2. Quick stock-entry form — POST /api/inventory/
//
// When a product is selected from the dropdown, the buying and selling
// price fields are auto-filled with the product's defaults (clerk can
// override them for a specific delivery).

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  Package,
  TrendingDown,
  AlertCircle,
  DollarSign,
  Plus,
  ShoppingCart,
} from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchSummary,
  fetchProducts,
  createEntry,
} from "../../store/slices/inventorySlice";

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ icon: Icon, label, value, color }) {
  return (
    <div className={`kpi-card kpi-card--${color}`}>
      <div className="kpi-card__icon">
        <Icon size={22} />
      </div>
      <div className="kpi-card__body">
        <span className="kpi-card__label">{label}</span>
        <span className="kpi-card__value">{value ?? "—"}</span>
      </div>
    </div>
  );
}

// ── Initial form state ────────────────────────────────────────────────────────
const EMPTY_FORM = {
  product_id:        "",
  quantity_received: "",
  quantity_in_stock: "",
  quantity_spoilt:   "0",
  buying_price:      "",
  selling_price:     "",
  payment_status:    "unpaid",
  entry_date:        "",
  notes:             "",
};

export default function ClerkDashboard() {
  const dispatch = useDispatch();
  const { summary, products, loading } = useSelector((s) => s.inventory);
  const { user } = useSelector((s) => s.auth);

  const [form, setForm] = useState(EMPTY_FORM);

  // ── Load data on mount ────────────────────────────────────────────────────
  useEffect(() => {
    dispatch(fetchSummary());
    dispatch(fetchProducts());
  }, [dispatch]);

  // ── Auto-fill prices when product changes ─────────────────────────────────
  function handleProductChange(e) {
    const id      = e.target.value;
    const product = products.find((p) => String(p.id) === id);
    setForm((prev) => ({
      ...prev,
      product_id:    id,
      buying_price:  product ? String(product.buying_price)  : "",
      selling_price: product ? String(product.selling_price) : "",
    }));
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  // ── Submit stock entry ────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();

    if (!form.product_id) {
      toast.error("Please select a product.");
      return;
    }

    try {
      await dispatch(createEntry({
        product_id:        Number(form.product_id),
        quantity_received: Number(form.quantity_received),
        quantity_in_stock: Number(form.quantity_in_stock),
        quantity_spoilt:   Number(form.quantity_spoilt || 0),
        buying_price:      Number(form.buying_price),
        selling_price:     Number(form.selling_price),
        payment_status:    form.payment_status,
        entry_date:        form.entry_date || undefined,
        notes:             form.notes || undefined,
      })).unwrap();

      toast.success("Stock entry recorded!");

      // Reset quantities but keep the selected product for rapid entries
      setForm((prev) => ({
        ...EMPTY_FORM,
        product_id:    prev.product_id,
        buying_price:  prev.buying_price,
        selling_price: prev.selling_price,
      }));

      // Refresh KPI summary
      dispatch(fetchSummary());

    } catch (err) {
      toast.error(err || "Failed to save entry.");
    }
  }

  // ── Greeting based on time of day ─────────────────────────────────────────
  const hour     = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      {/* Page header */}
      <div className="page__header">
        <div>
          <h2 className="page__title">
            {greeting}, {user?.first_name}!
          </h2>
          <p className="page__sub">Record today's stock and view your store summary.</p>
        </div>
        <Link to="/clerk/supply" className="btn btn--outline">
          <ShoppingCart size={15} /> Supply Requests
        </Link>
      </div>

      {/* ── KPI summary cards ─────────────────────────────────────────── */}
      <div className="kpi-grid">
        <KpiCard
          icon={Package}
          label="Total Received"
          value={summary?.total_received?.toLocaleString()}
          color="blue"
        />
        <KpiCard
          icon={Package}
          label="In Stock"
          value={summary?.total_in_stock?.toLocaleString()}
          color="green"
        />
        <KpiCard
          icon={TrendingDown}
          label="Total Spoilt"
          value={summary?.total_spoilt?.toLocaleString()}
          color="red"
        />
        <KpiCard
          icon={AlertCircle}
          label="Unpaid Amount"
          value={
            summary?.unpaid_cost != null
              ? `KES ${Number(summary.unpaid_cost).toLocaleString()}`
              : null
          }
          color="amber"
        />
        <KpiCard
          icon={DollarSign}
          label="Revenue Potential"
          value={
            summary?.revenue_potential != null
              ? `KES ${Number(summary.revenue_potential).toLocaleString()}`
              : null
          }
          color="green"
        />
      </div>

      {/* ── Stock entry form ───────────────────────────────────────────── */}
      <div className="card">
        <div className="card__header">
          <Plus size={17} />
          <h3 className="card__title">Record Stock Entry</h3>
        </div>

        <form onSubmit={handleSubmit} className="entry-form">

          {/* Product selector — full width */}
          <div className="form-group" style={{ gridColumn: "1 / -1" }}>
            <label className="form-label">Product *</label>
            <select
              name="product_id"
              value={form.product_id}
              onChange={handleProductChange}
              className="form-input"
              required
            >
              <option value="">— Select a product —</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}{p.sku ? ` (${p.sku})` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Qty received */}
          <div className="form-group">
            <label className="form-label">Qty Received *</label>
            <input
              type="number" name="quantity_received"
              value={form.quantity_received} onChange={handleChange}
              className="form-input" min="0" required
            />
          </div>

          {/* Qty in stock */}
          <div className="form-group">
            <label className="form-label">Qty In Stock *</label>
            <input
              type="number" name="quantity_in_stock"
              value={form.quantity_in_stock} onChange={handleChange}
              className="form-input" min="0" required
            />
          </div>

          {/* Qty spoilt */}
          <div className="form-group">
            <label className="form-label">Qty Spoilt</label>
            <input
              type="number" name="quantity_spoilt"
              value={form.quantity_spoilt} onChange={handleChange}
              className="form-input" min="0"
            />
          </div>

          {/* Buying price */}
          <div className="form-group">
            <label className="form-label">Buying Price (KES) *</label>
            <input
              type="number" name="buying_price"
              value={form.buying_price} onChange={handleChange}
              className="form-input" min="0" step="0.01" required
            />
          </div>

          {/* Selling price */}
          <div className="form-group">
            <label className="form-label">Selling Price (KES) *</label>
            <input
              type="number" name="selling_price"
              value={form.selling_price} onChange={handleChange}
              className="form-input" min="0" step="0.01" required
            />
          </div>

          {/* Payment status */}
          <div className="form-group">
            <label className="form-label">Payment Status</label>
            <select
              name="payment_status"
              value={form.payment_status}
              onChange={handleChange}
              className="form-input"
            >
              <option value="unpaid">Unpaid</option>
              <option value="paid">Paid</option>
            </select>
          </div>

          {/* Entry date (optional — defaults to today on the backend) */}
          <div className="form-group">
            <label className="form-label">Entry Date</label>
            <input
              type="date" name="entry_date"
              value={form.entry_date} onChange={handleChange}
              className="form-input"
            />
          </div>

          {/* Notes — full width */}
          <div className="form-group" style={{ gridColumn: "1 / -1" }}>
            <label className="form-label">Notes (optional)</label>
            <textarea
              name="notes" value={form.notes} onChange={handleChange}
              className="form-input form-input--textarea"
              placeholder="Any relevant notes about this delivery…"
              rows={2}
            />
          </div>

          {/* Actions — full width */}
          <div style={{ gridColumn: "1 / -1", display: "flex", gap: 12 }}>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={loading}
            >
              {loading ? <span className="btn__spinner" /> : "Save Entry"}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setForm(EMPTY_FORM)}
            >
              Clear
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}