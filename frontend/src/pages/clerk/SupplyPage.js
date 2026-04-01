// src/pages/clerk/SupplyPage.js
// ──────────────────────────────
// Clerk's supply request page.
//
// Two sections:
//   1. "New Request" form (toggled by a button) — submits a supply request
//      to the store admin for approval.
//   2. History table — shows all the clerk's past requests and their
//      current status (pending / approved / declined).

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { ShoppingCart, Plus, Clock, CheckCircle, XCircle } from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchSupplyRequests,
  fetchProducts,
  createSupplyRequest,
} from "../../store/slices/inventorySlice";

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const config = {
    pending:  { icon: Clock,        color: "amber", label: "Pending"  },
    approved: { icon: CheckCircle,  color: "green", label: "Approved" },
    declined: { icon: XCircle,      color: "red",   label: "Declined" },
  };
  const { icon: Icon, color, label } = config[status] || config.pending;
  return (
    <span className={`badge badge--${color}`}>
      <Icon size={11} /> {label}
    </span>
  );
}

// ── Empty form ────────────────────────────────────────────────────────────────
const EMPTY_FORM = { product_id: "", quantity_requested: "", reason: "" };

export default function SupplyPage() {
  const dispatch = useDispatch();
  const { supplyRequests, products, loading } = useSelector((s) => s.inventory);

  const [showForm, setShowForm] = useState(false);
  const [form,     setForm]     = useState(EMPTY_FORM);

  // ── Load data on mount ────────────────────────────────────────────────────
  useEffect(() => {
    dispatch(fetchSupplyRequests());
    dispatch(fetchProducts());
  }, [dispatch]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  // ── Submit supply request ─────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();

    if (!form.product_id || !form.quantity_requested) {
      toast.error("Please select a product and enter the quantity needed.");
      return;
    }

    try {
      await dispatch(createSupplyRequest({
        product_id:         Number(form.product_id),
        quantity_requested: Number(form.quantity_requested),
        reason:             form.reason || undefined,
      })).unwrap();

      toast.success("Supply request submitted. Your admin will review it.");
      setForm(EMPTY_FORM);
      setShowForm(false);

    } catch (err) {
      toast.error(err || "Failed to submit request.");
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Supply Requests</h2>
          <p className="page__sub">Request more stock and track approvals from your admin.</p>
        </div>
        <button
          className="btn btn--primary"
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus size={15} /> New Request
        </button>
      </div>

      {/* ── New request form (collapsible) ─────────────────────────────── */}
      {showForm && (
        <div className="card card--highlighted">
          <div className="card__header">
            <ShoppingCart size={17} />
            <h3 className="card__title">New Supply Request</h3>
          </div>

          <form
            onSubmit={handleSubmit}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              padding: 20,
            }}
          >
            {/* Product */}
            <div className="form-group">
              <label className="form-label">Product *</label>
              <select
                name="product_id"
                value={form.product_id}
                onChange={handleChange}
                className="form-input"
                required
              >
                <option value="">— Select a product —</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            {/* Quantity */}
            <div className="form-group">
              <label className="form-label">Quantity Needed *</label>
              <input
                type="number"
                name="quantity_requested"
                value={form.quantity_requested}
                onChange={handleChange}
                className="form-input"
                min="1"
                required
              />
            </div>

            {/* Reason — full width */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label className="form-label">Reason (optional)</label>
              <textarea
                name="reason"
                value={form.reason}
                onChange={handleChange}
                className="form-input form-input--textarea"
                placeholder="Why is this stock needed? e.g. Running low — only 5 units left"
                rows={2}
              />
            </div>

            {/* Actions */}
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
              <button
                type="submit"
                className="btn btn--primary"
                disabled={loading}
              >
                {loading ? <span className="btn__spinner" /> : "Submit Request"}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}
              >
                Cancel
              </button>
            </div>

          </form>
        </div>
      )}

      {/* ── Request history ────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card__header">
          <h3 className="card__title">My Requests</h3>
          <span className="badge badge--blue">{supplyRequests.length}</span>
        </div>

        <div className="table-wrapper">
          {loading ? (
            <div className="table-loading"><div className="spinner" /></div>
          ) : supplyRequests.length === 0 ? (
            <div className="table-empty">
              No supply requests yet. Click "New Request" to get started.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Qty Requested</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Admin Note</th>
                  <th>Submitted</th>
                  <th>Resolved</th>
                </tr>
              </thead>
              <tbody>
                {supplyRequests.map((req) => (
                  <tr key={req.id}>
                    <td><strong>{req.product?.name || "—"}</strong></td>
                    <td>{req.quantity_requested}</td>
                    <td style={{ maxWidth: 200, wordBreak: "break-word" }}>
                      {req.reason || "—"}
                    </td>
                    <td><StatusBadge status={req.status} /></td>
                    <td style={{ maxWidth: 180, wordBreak: "break-word", color: req.admin_note ? "inherit" : "var(--text-muted)" }}>
                      {req.admin_note || "—"}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {req.created_at
                        ? new Date(req.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {req.resolved_at
                        ? new Date(req.resolved_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  );
}