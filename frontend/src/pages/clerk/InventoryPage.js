// src/pages/clerk/InventoryPage.js
// ──────────────────────────────────
// Full inventory entry list for the current store.
//
// Features:
//   • Search by product name (client-side filter)
//   • Filter by payment status (paid / unpaid / all)
//   • Filter by date range
//   • Admin/merchant can mark entries as paid and delete them
//   • Clerk can only view (no delete / payment actions)

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Search, Filter, CheckCircle, Clock, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchEntries,
  updatePaymentStatus,
  deleteEntry,
} from "../../store/slices/inventorySlice";

// ── Payment status badge ──────────────────────────────────────────────────────
function PaymentBadge({ status }) {
  return status === "paid" ? (
    <span className="badge badge--green">
      <CheckCircle size={11} /> Paid
    </span>
  ) : (
    <span className="badge badge--amber">
      <Clock size={11} /> Unpaid
    </span>
  );
}

export default function InventoryPage() {
  const dispatch = useDispatch();
  const { entries, loading } = useSelector((s) => s.inventory);
  const { user }             = useSelector((s) => s.auth);

  // ── Filter state ──────────────────────────────────────────────────────────
  const [search,        setSearch]        = useState("");
  const [paymentFilter, setPaymentFilter] = useState("all");
  const [fromDate,      setFromDate]      = useState("");
  const [toDate,        setToDate]        = useState("");
  const [confirmDelete, setConfirmDelete] = useState(null); // entry id awaiting confirm

  const isAdminOrMerchant = ["admin", "merchant"].includes(user?.role);

  // ── Load entries on mount ─────────────────────────────────────────────────
  useEffect(() => {
    dispatch(fetchEntries({}));
  }, [dispatch]);

  // ── Client-side filtering ─────────────────────────────────────────────────
  const filtered = entries.filter((e) => {
    const name = e.product?.name?.toLowerCase() || "";

    if (search && !name.includes(search.toLowerCase())) return false;
    if (paymentFilter !== "all" && e.payment_status !== paymentFilter) return false;
    if (fromDate && e.entry_date < fromDate) return false;
    if (toDate   && e.entry_date > toDate)   return false;

    return true;
  });

  // ── Mark as paid ──────────────────────────────────────────────────────────
  async function handleMarkPaid(id) {
    try {
      await dispatch(updatePaymentStatus({ id, payment_status: "paid" })).unwrap();
      toast.success("Marked as paid.");
    } catch (err) {
      toast.error(err || "Failed to update payment.");
    }
  }

  // ── Delete entry ──────────────────────────────────────────────────────────
  async function handleDelete(id) {
    try {
      await dispatch(deleteEntry(id)).unwrap();
      toast.success("Entry deleted.");
      setConfirmDelete(null);
    } catch (err) {
      toast.error(err || "Failed to delete entry.");
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Inventory Entries</h2>
          <p className="page__sub">All stock-taking records for your store.</p>
        </div>
      </div>

      {/* ── Filter bar ────────────────────────────────────────────────── */}
      <div className="filter-bar">

        {/* Search */}
        <div className="filter-bar__search">
          <Search size={15} className="filter-bar__search-icon" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by product name…"
            className="filter-bar__input"
          />
        </div>

        {/* Payment status filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Filter size={14} style={{ color: "var(--text-muted)" }} />
          <select
            value={paymentFilter}
            onChange={(e) => setPaymentFilter(e.target.value)}
            className="filter-bar__select"
          >
            <option value="all">All payments</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
          </select>
        </div>

        {/* Date range */}
        <input
          type="date" value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          className="filter-bar__select"
          title="From date"
        />
        <input
          type="date" value={toDate}
          onChange={(e) => setToDate(e.target.value)}
          className="filter-bar__select"
          title="To date"
        />

        <span className="filter-bar__count">{filtered.length} entries</span>
      </div>

      {/* ── Entry table ───────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="table-wrapper">
          {loading ? (
            <div className="table-loading"><div className="spinner" /></div>
          ) : filtered.length === 0 ? (
            <div className="table-empty">No entries found.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Date</th>
                  <th>Received</th>
                  <th>In Stock</th>
                  <th>Spoilt</th>
                  <th>Buying (KES)</th>
                  <th>Selling (KES)</th>
                  <th>Payment</th>
                  <th>Clerk</th>
                  {isAdminOrMerchant && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((entry) => (
                  <tr key={entry.id}>

                    {/* Product */}
                    <td className="td--product">
                      <strong>{entry.product?.name || "—"}</strong>
                      {entry.product?.sku && (
                        <span className="td__sku">{entry.product.sku}</span>
                      )}
                    </td>

                    <td>{entry.entry_date || "—"}</td>
                    <td>{entry.quantity_received}</td>
                    <td>{entry.quantity_in_stock}</td>

                    {/* Highlight non-zero spoilage in red */}
                    <td className={entry.quantity_spoilt > 0 ? "td--red" : ""}>
                      {entry.quantity_spoilt}
                    </td>

                    <td>{Number(entry.buying_price).toLocaleString()}</td>
                    <td>{Number(entry.selling_price).toLocaleString()}</td>

                    <td><PaymentBadge status={entry.payment_status} /></td>

                    <td>
                      {entry.clerk
                        ? `${entry.clerk.first_name} ${entry.clerk.last_name}`
                        : "—"}
                    </td>

                    {/* Admin / merchant action column */}
                    {isAdminOrMerchant && (
                      <td className="td--actions">

                        {/* Mark paid — only for unpaid entries */}
                        {entry.payment_status === "unpaid" && (
                          <button
                            className="btn btn--xs btn--green"
                            onClick={() => handleMarkPaid(entry.id)}
                            title="Mark as paid"
                          >
                            <CheckCircle size={12} /> Pay
                          </button>
                        )}

                        {/* Delete with inline confirmation */}
                        {confirmDelete === entry.id ? (
                          <span style={{ display: "flex", gap: 4, alignItems: "center", fontSize: "0.8rem" }}>
                            Sure?
                            <button className="btn btn--xs btn--red" onClick={() => handleDelete(entry.id)}>Yes</button>
                            <button className="btn btn--xs btn--ghost" onClick={() => setConfirmDelete(null)}>No</button>
                          </span>
                        ) : (
                          <button
                            className="btn btn--xs btn--ghost-red"
                            onClick={() => setConfirmDelete(entry.id)}
                            title="Delete entry"
                          >
                            <Trash2 size={12} />
                          </button>
                        )}

                      </td>
                    )}
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