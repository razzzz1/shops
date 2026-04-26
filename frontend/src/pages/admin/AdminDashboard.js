
// src/pages/admin/AdminDashboard.js
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  Package, CreditCard, AlertCircle, TrendingDown, CheckCircle, XCircle, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchSummary, fetchWeeklyReport, fetchMonthlyReport,
  fetchSupplyRequests, actionSupplyRequest,
} from "../../store/slices/inventorySlice";

const TOOLTIP_STYLE = {
  contentStyle: {
    background: "var(--surface-2)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", fontSize: "0.82rem",
  },
  labelStyle: { color: "var(--text-muted)" },
};

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

export default function AdminDashboard() {
  const dispatch = useDispatch();
  const { summary, weeklyReport, monthlyReport, supplyRequests, loading } = useSelector((s) => s.inventory);
  const [chartPeriod, setChartPeriod] = useState("weekly");
  const [notes, setNotes] = useState({});

  useEffect(() => {
    dispatch(fetchSummary());
    dispatch(fetchWeeklyReport({}));
    dispatch(fetchMonthlyReport({}));
    dispatch(fetchSupplyRequests({ status: "pending" }));
  }, [dispatch]);

  async function handleAction(id, action) {
    try {
      await dispatch(actionSupplyRequest({ id, action, note: notes[id] || "" })).unwrap();
      toast.success(`Request ${action}.`);
      dispatch(fetchSupplyRequests({ status: "pending" }));
      dispatch(fetchSummary());
    } catch (err) {
      toast.error(err || "Failed.");
    }
  }

  const chartData = chartPeriod === "weekly" ? weeklyReport?.data : monthlyReport?.data;
  const pending   = supplyRequests.filter((r) => r.status === "pending");

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h2 className="page__title">Store Dashboard</h2>
          <p className="page__sub">Your store performance and pending supply requests.</p>
        </div>
        <div className="page__header-actions">
          <button className="btn btn--outline btn--sm" onClick={() => {
            dispatch(fetchSummary());
            dispatch(fetchWeeklyReport({}));
            dispatch(fetchMonthlyReport({}));
            dispatch(fetchSupplyRequests({ status: "pending" }));
            toast.success("Data refreshed.");
          }}>
            <RefreshCw size={14} /> Refresh
          </button>
          <Link to="/admin/reports" className="btn btn--outline btn--sm">View Full Reports</Link>
          <Link to="/admin/products" className="btn btn--primary btn--sm">
            <Package size={14} /> Manage Products
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard icon={Package}      label="Total Received"     value={summary?.total_received?.toLocaleString()}                        color="blue" />
        <KpiCard icon={Package}      label="In Stock"           value={summary?.total_in_stock?.toLocaleString()}                        color="green" />
        <KpiCard icon={TrendingDown} label="Total Spoilt"       value={summary?.total_spoilt?.toLocaleString()}                          color="red" />
        <KpiCard
          icon={CreditCard}
          label="Paid to Suppliers"
          value={summary ? `KES ${Number(summary.paid_cost).toLocaleString()}` : null}
          sub={summary ? `Unpaid: KES ${Number(summary.unpaid_cost).toLocaleString()}` : null}
          color="green"
        />
        <KpiCard icon={AlertCircle} label="Pending Requests" value={pending.length} color="amber" />
      </div>

      {/* Charts */}
      <div className="card">
        <div className="card__header">
          <h3 className="card__title">Stock Movement</h3>
          <div className="period-toggle">
            {["weekly", "monthly"].map((p) => (
              <button key={p}
                className={`period-toggle__btn${chartPeriod === p ? " period-toggle__btn--active" : ""}`}
                onClick={() => setChartPeriod(p)}
              >{p.charAt(0).toUpperCase() + p.slice(1)}</button>
            ))}
          </div>
        </div>

        {chartData && chartData.some(d => d.received > 0) ? (
          <div className="chart-row">
            <div>
              <p className="chart-title">Received vs Spoilt (units)</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                  <Bar dataKey="received" name="Received" fill="var(--blue)"  radius={[4,4,0,0]} />
                  <Bar dataKey="spoilt"   name="Spoilt"   fill="var(--red)"   radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="chart-title">Supplier Costs (KES)</p>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} tickFormatter={v => `${(v/1000).toFixed(0)}K`} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={v => `KES ${Number(v).toLocaleString()}`} />
                  <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                  <Line type="monotone" dataKey="paid_cost"   name="Paid"   stroke="var(--green)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="unpaid_cost" name="Unpaid" stroke="var(--amber)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <div className="chart-empty">
            {loading
              ? <div className="spinner" />
              : <span>No data yet. <Link to="/clerk">Record stock entries</Link> to see charts.</span>
            }
          </div>
        )}
      </div>

      {/* Pending supply requests */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card__header">
          <AlertCircle size={17} />
          <h3 className="card__title">Pending Supply Requests</h3>
          <span className="badge badge--amber">{pending.length}</span>
        </div>

        <div className="table-wrapper">
          {pending.length === 0 ? (
            <div className="table-empty">No pending requests — all caught up! 🎉</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th><th>Clerk</th><th>Qty</th>
                  <th>Reason</th><th>Date</th>
                  <th>Note (optional)</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((req) => (
                  <tr key={req.id}>
                    <td><strong>{req.product?.name || "—"}</strong></td>
                    <td>{req.clerk ? `${req.clerk.first_name} ${req.clerk.last_name}` : "—"}</td>
                    <td>{req.quantity_requested}</td>
                    <td style={{ maxWidth: 160, wordBreak: "break-word" }}>{req.reason || "—"}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {req.created_at ? new Date(req.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td>
                      <input
                        type="text" className="form-input form-input--xs"
                        placeholder="Add a note…" style={{ minWidth: 140 }}
                        value={notes[req.id] || ""}
                        onChange={(e) => setNotes(prev => ({ ...prev, [req.id]: e.target.value }))}
                      />
                    </td>
                    <td className="td--actions">
                      <button className="btn btn--xs btn--green" onClick={() => handleAction(req.id, "approved")}>
                        <CheckCircle size={12} /> Approve
                      </button>
                      <button className="btn btn--xs btn--ghost-red" onClick={() => handleAction(req.id, "declined")}>
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