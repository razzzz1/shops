

import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Clock, CheckCircle, DollarSign } from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchPaymentReport,
  updatePaymentStatus,
} from "../../store/slices/inventorySlice";

// ── Stat box ──────────────────────────────────────────────────────────────────
function StatBox({ icon: Icon, label, value, color }) {
  return (
    <div className={`stat-box stat-box--${color}`}>
      <Icon size={20} style={{ color: `var(--${color})`, flexShrink: 0 }} />
      <div>
        <div className="stat-box__label">{label}</div>
        <div className="stat-box__value">{value}</div>
      </div>
    </div>
  );
}

// ── Entry row (shared between paid and unpaid tables) ─────────────────────────
function EntryRow({ entry, onMarkPaid }) {
  const totalCost = (
    Number(entry.buying_price) * entry.quantity_received
  ).toLocaleString();

  return (
    <tr>
      <td className="td--product">
        <strong>{entry.product?.name || "—"}</strong>
        {entry.product?.sku && (
          <span className="td__sku">{entry.product.sku}</span>
        )}
      </td>
      <td className="td--mono">{entry.entry_date || "—"}</td>
      <td>{entry.quantity_received.toLocaleString()}</td>
      <td>{Number(entry.buying_price).toLocaleString()}</td>
      <td className="td--bold">KES {totalCost}</td>
      <td>
        {entry.clerk
          ? `${entry.clerk.first_name} ${entry.clerk.last_name}`
          : "—"}
      </td>
      {onMarkPaid && (
        <td>
          <button
            className="btn btn--xs btn--green"
            onClick={() => onMarkPaid(entry.id)}
          >
            <CheckCircle size={12} /> Mark Paid
          </button>
        </td>
      )}
      {!onMarkPaid && (
        <td className="td--mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
          {entry.payment_updated_at
            ? new Date(entry.payment_updated_at).toLocaleDateString()
            : "—"}
        </td>
      )}
    </tr>
  );
}

export default function PaymentPage() {
  const dispatch = useDispatch();
  const { paymentReport, loading } = useSelector((s) => s.inventory);

  // ── Load payment report on mount ──────────────────────────────────────────
  useEffect(() => {
    dispatch(fetchPaymentReport({}));
  }, [dispatch]);

  // ── Mark an entry as paid ─────────────────────────────────────────────────
  async function handleMarkPaid(id) {
    try {
      await dispatch(updatePaymentStatus({ id, payment_status: "paid" })).unwrap();
      toast.success("Payment marked as paid.");
      // Refresh the report so the entry moves from unpaid → paid section
      dispatch(fetchPaymentReport({}));
    } catch (err) {
      toast.error(err || "Failed to update payment.");
    }
  }

  if (loading && !paymentReport) {
    return (
      <div className="page-loading">
        <div className="spinner spinner--lg" />
      </div>
    );
  }

  const paid   = paymentReport?.paid   || { entries: [], total_cost: 0, count: 0 };
  const unpaid = paymentReport?.unpaid || { entries: [], total_cost: 0, count: 0 };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Payment Tracker</h2>
          <p className="page__sub">
            Track supplier payment status for all deliveries.
            Mark invoices as paid after settling with suppliers.
          </p>
        </div>
      </div>

      {/* ── Summary stat boxes ────────────────────────────────────────── */}
      <div className="stat-boxes">
        <StatBox
          icon={Clock}
          label="Outstanding (Unpaid)"
          value={`KES ${Number(unpaid.total_cost).toLocaleString()}`}
          color="amber"
        />
        <StatBox
          icon={CheckCircle}
          label="Settled (Paid)"
          value={`KES ${Number(paid.total_cost).toLocaleString()}`}
          color="green"
        />
        <StatBox
          icon={DollarSign}
          label="Total Deliveries"
          value={(paid.entries.length + unpaid.entries.length).toLocaleString()}
          color="blue"
        />
      </div>

      {/* ══ UNPAID SECTION (shown first — needs attention) ════════════ */}
      <div className="card card--attention">
        <div className="card__header">
          <Clock size={17} style={{ color: "var(--amber)" }} />
          <h3 className="card__title">⚠ Unpaid Invoices</h3>
          <span className="badge badge--amber">{unpaid.entries.length} entries</span>
          <span className="card__total">
            Total: KES {Number(unpaid.total_cost).toLocaleString()}
          </span>
        </div>

        <div className="table-wrapper">
          {unpaid.entries.length === 0 ? (
            <div className="table-empty">
              All supplier invoices are paid! ✓
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Entry Date</th>
                  <th>Qty Received</th>
                  <th>Unit Price (KES)</th>
                  <th>Total Cost</th>
                  <th>Recorded By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {unpaid.entries.map((entry) => (
                  <tr key={entry.id} className="tr--unpaid">
                    <td className="td--product">
                      <strong>{entry.product?.name || "—"}</strong>
                      {entry.product?.sku && (
                        <span className="td__sku">{entry.product.sku}</span>
                      )}
                    </td>
                    <td className="td--mono">{entry.entry_date || "—"}</td>
                    <td>{entry.quantity_received.toLocaleString()}</td>
                    <td>{Number(entry.buying_price).toLocaleString()}</td>
                    <td className="td--bold">
                      KES {(Number(entry.buying_price) * entry.quantity_received).toLocaleString()}
                    </td>
                    <td>
                      {entry.clerk
                        ? `${entry.clerk.first_name} ${entry.clerk.last_name}`
                        : "—"}
                    </td>
                    <td>
                      {/* Clicking this means the supplier has been paid */}
                      <button
                        className="btn btn--xs btn--green"
                        onClick={() => handleMarkPaid(entry.id)}
                      >
                        <CheckCircle size={12} /> Mark Paid
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ══ PAID SECTION ══════════════════════════════════════════════ */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card__header">
          <CheckCircle size={17} style={{ color: "var(--green)" }} />
          <h3 className="card__title">✓ Paid Invoices</h3>
          <span className="badge badge--green">{paid.entries.length} entries</span>
          <span className="card__total">
            Total: KES {Number(paid.total_cost).toLocaleString()}
          </span>
        </div>

        <div className="table-wrapper">
          {paid.entries.length === 0 ? (
            <div className="table-empty">No paid invoices yet.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Entry Date</th>
                  <th>Qty Received</th>
                  <th>Unit Price (KES)</th>
                  <th>Total Cost</th>
                  <th>Recorded By</th>
                  <th>Paid On</th>
                </tr>
              </thead>
              <tbody>
                {paid.entries.map((entry) => (
                  <tr key={entry.id} className="tr--paid">
                    <td className="td--product">
                      <strong>{entry.product?.name || "—"}</strong>
                      {entry.product?.sku && (
                        <span className="td__sku">{entry.product.sku}</span>
                      )}
                    </td>
                    <td className="td--mono">{entry.entry_date || "—"}</td>
                    <td>{entry.quantity_received.toLocaleString()}</td>
                    <td>{Number(entry.buying_price).toLocaleString()}</td>
                    <td className="td--bold">
                      KES {(Number(entry.buying_price) * entry.quantity_received).toLocaleString()}
                    </td>
                    <td>
                      {entry.clerk
                        ? `${entry.clerk.first_name} ${entry.clerk.last_name}`
                        : "—"}
                    </td>
                    <td className="td--mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                      {entry.payment_updated_at
                        ? new Date(entry.payment_updated_at).toLocaleDateString()
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