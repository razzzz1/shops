// src/pages/admin/AdminDashboard.js
// ────────────────────────────────────
// Admin home page — three sections:
//
//   1. KPI summary cards (stock totals, unpaid amount, pending requests)
//   2. Two Recharts charts — bar (received vs spoilt) + line (paid vs unpaid costs)
//      with a weekly / monthly toggle
//   3. Pending supply requests table — admin can approve or decline inline

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  Package, CreditCard, AlertCircle, TrendingDown,
  CheckCircle, XCircle,
} from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchSummary,
  fetchWeeklyReport,
  fetchMonthlyReport,
  fetchSupplyRequests,
  actionSupplyRequest,
} from "../../store/slices/inventorySlice";

// ── Shared tooltip style that matches our dark theme ─────────────────────────
const TOOLTIP_STYLE = {
  contentStyle: {
    background:   "var(--surface-2)",
    border:       "1px solid var(--border)",
    borderRadius: "var(--radius)",
    fontSize:     "0.82rem",
  },
  labelStyle:   { color: "var(--text-muted)" },
  itemStyle:    { color: "var(--text)" },
};

// ── KPI card ──────────────────────────────────────────────────────────────────
function KpiCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className={`kpi-card kpi-card--${color}`}>
      <div className="kpi-card__icon"><Icon size={22} /></div>
      <div className="kpi-card__body">
        <span className="kpi-card__label">{label}</span>
        <span className="kpi-card__value">{value ?? "—"}</span>
        {sub && <span className="kpi-card__sub">{sub}</span>}
      </div>
    </div>
  );
}

// ── Period toggle ─────────────────────────────────────────────────────────────
function PeriodToggle({ value, onChange }) {
  return (
    <div className="period-toggle">
      {["weekly", "monthly"].map((p) => (
        <button
          key={p}
          className={`period-toggle__btn${value === p ? " period-toggle__btn--active" : ""}`}
          onClick={() => onChange(p)}
        >
          {p.charAt(0).toUpperCase() + p.slice(1)}
        </button>
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const dispatch = useDispatch();
  const {
    summary, weeklyReport, monthlyReport, supplyRequests, loading,
  } = useSelector((s) => s.inventory);

  const [chartPeriod, setChartPeriod] = useState("weekly");
  // Stores the admin note typed for each request: { [requestId]: "note text" }
  const [notes, setNotes] = useState({});

  // ── Load all data on mount ────────────────────────────────────────────────
  useEffect(() => {
    dispatch(fetchSummary());
    dispatch(fetchWeeklyReport({}));
    dispatch(fetchMonthlyReport({}));
    dispatch(fetchSupplyRequests({ status: "pending" }));
  }, [dispatch]);

  // ── Supply request action ─────────────────────────────────────────────────
  async function handleAction(id, action) {
    try {
      await dispatch(actionSupplyRequest({
        id,
        action,
        note: notes[id] || "",
      })).unwrap();
      toast.success(`Request ${action}.`);
      // Refresh pending list and summary
      dispatch(fetchSupplyRequests({ status: "pending" }));
      dispatch(fetchSummary());
    } catch (err) {
      toast.error(err || "Failed to process request.");
    }
  }

  // Pick the correct dataset for the selected period
  const chartData = chartPeriod === "weekly"
    ? weeklyReport?.data
    : monthlyReport?.data;

  // X-axis key differs by period
  const xKey = "date";

  // Only show pending requests
  const pendingRequests = supplyRequests.filter((r) => r.status === "pending");

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Store Dashboard</h2>
          <p className="page__sub">Performance overview and supply request management.</p>
        </div>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────── */}
      <div className="kpi-grid">
        <KpiCard icon={Package}     label="Total Received"    value={summary?.total_received?.toLocaleString()}  color="blue" />
        <KpiCard icon={Package}     label="In Stock"          value={summary?.total_in_stock?.toLocaleString()}  color="green" />
        <KpiCard icon={TrendingDown} label="Total Spoilt"     value={summary?.total_spoilt?.toLocaleString()}    color="red" />
        <KpiCard
          icon={CreditCard}
          label="Paid to Suppliers"
          value={summary ? `KES ${Number(summary.paid_cost).toLocaleString()}` : null}
          sub={summary ? `Unpaid: KES ${Number(summary.unpaid_cost).toLocaleString()}` : null}
          color="green"
        />
        <KpiCard
          icon={AlertCircle}
          label="Pending Requests"
          value={pendingRequests.length}
          color="amber"
        />
      </div>

      {/* ── Charts ───────────────────────────────────────────────────── */}
      <div className="card">
        <div className="card__header">
          <h3 className="card__title">Stock Movement</h3>
          <PeriodToggle value={chartPeriod} onChange={setChartPeriod} />
        </div>

        {chartData && chartData.length > 0 ? (
          <div className="chart-row">

            {/* Bar chart — Received vs Spoilt */}
            <div>
              <p className="chart-title">Received vs Spoilt (units)</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                  <Bar dataKey="received" name="Received" fill="var(--blue)"  radius={[4, 4, 0, 0]} />
                  <Bar dataKey="spoilt"   name="Spoilt"   fill="var(--red)"   radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Line chart — Paid vs Unpaid supplier costs */}
            <div>
              <p className="chart-title">Supplier Costs (KES)</p>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => `KES ${Number(v).toLocaleString()}`} />
                  <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                  <Line type="monotone" dataKey="paid_cost"   name="Paid"   stroke="var(--green)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="unpaid_cost" name="Unpaid" stroke="var(--amber)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

          </div>
        ) : (
          <div className="chart-empty">
            {loading ? <div className="spinner" /> : "No data for this period yet. Start recording stock entries."}
          </div>
        )}
      </div>

      {/* ── Pending supply requests ──────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card__header">
          <AlertCircle size={17} />
          <h3 className="card__title">Pending Supply Requests</h3>
          <span className="badge badge--amber">{pendingRequests.length}</span>
        </div>

        <div className="table-wrapper">
          {pendingRequests.length === 0 ? (
            <div className="table-empty">No pending requests — all caught up! 🎉</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Clerk</th>
                  <th>Qty</th>
                  <th>Reason</th>
                  <th>Date</th>
                  <th>Note (optional)</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingRequests.map((req) => (
                  <tr key={req.id}>
                    <td><strong>{req.product?.name || "—"}</strong></td>
                    <td>
                      {req.clerk
                        ? `${req.clerk.first_name} ${req.clerk.last_name}`
                        : "—"}
                    </td>
                    <td>{req.quantity_requested}</td>
                    <td style={{ maxWidth: 160, wordBreak: "break-word" }}>
                      {req.reason || "—"}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {req.created_at
                        ? new Date(req.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td>
                      {/* Optional note the admin can attach to their decision */}
                      <input
                        type="text"
                        className="form-input form-input--xs"
                        placeholder="Add a note…"
                        value={notes[req.id] || ""}
                        onChange={(e) =>
                          setNotes((prev) => ({ ...prev, [req.id]: e.target.value }))
                        }
                        style={{ minWidth: 140 }}
                      />
                    </td>
                    <td className="td--actions">
                      <button
                        className="btn btn--xs btn--green"
                        onClick={() => handleAction(req.id, "approved")}
                      >
                        <CheckCircle size={12} /> Approve
                      </button>
                      <button
                        className="btn btn--xs btn--ghost-red"
                        onClick={() => handleAction(req.id, "declined")}
                      >
                        <XCircle size={12} /> Decline
                      </button>
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