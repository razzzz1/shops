// src/pages/merchant/StoreReportPage.js
// ───────────────────────────────────────
// Detailed report for a single store — navigated to from MerchantDashboard.
//
// Shows:
//   • Annual bar chart   — stock received/in-stock/spoilt by month
//   • Annual line chart  — paid vs unpaid costs by month
//   • Period toggle to switch between annual and monthly views
//   • Paid / Unpaid payment breakdown tables (side by side)
//
// The store id comes from the URL: /merchant/stores/:id

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  BarChart,  Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { ArrowLeft, Clock, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

import api from "../../utils/api";

// ── Shared Recharts tooltip style ─────────────────────────────────────────────
const TOOLTIP_STYLE = {
  contentStyle: {
    background:   "var(--surface-2)",
    border:       "1px solid var(--border)",
    borderRadius: "var(--radius)",
    fontSize:     "0.82rem",
  },
  labelStyle: { color: "var(--text-muted)" },
  itemStyle:  { color: "var(--text)" },
};

export default function StoreReportPage() {
  const { id }   = useParams();   // store_id from the URL
  const navigate = useNavigate();

  const [annual,   setAnnual]   = useState(null);
  const [monthly,  setMonthly]  = useState(null);
  const [payment,  setPayment]  = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [period,   setPeriod]   = useState("annual");
  const [storeName, setStoreName] = useState(`Store #${id}`);

  // ── Load reports for this store ───────────────────────────────────────────
  useEffect(() => {
    loadReports();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function loadReports() {
    setLoading(true);
    try {
      const params = { store_id: id };

      const [annualRes, monthlyRes, paymentRes] = await Promise.all([
        api.get("/reports/annual",         { params }),
        api.get("/reports/monthly",        { params }),
        api.get("/reports/payment-status", { params }),
      ]);

      setAnnual(annualRes.data);
      setMonthly(monthlyRes.data);
      setPayment(paymentRes.data);

      // Try to get the store name from admin users
      try {
        const { data: users } = await api.get("/users/", {
          params: { store_id: id, role: "admin" },
        });
        if (users[0]?.store?.name) setStoreName(users[0].store.name);
      } catch {
        // Store name is cosmetic — don't fail the whole page
      }

    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to load store reports.");
    } finally {
      setLoading(false);
    }
  }

  // Pick the right dataset
  const reportData = period === "annual" ? annual?.data : monthly?.data;
  const xKey       = period === "annual" ? "label" : "date";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      {/* Header with back button */}
      <div className="page__header">
        <div>
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => navigate("/merchant")}
            style={{ marginBottom: 8 }}
          >
            <ArrowLeft size={15} /> Back to All Stores
          </button>
          <h2 className="page__title">{storeName}</h2>
          <p className="page__sub">Detailed performance report.</p>
        </div>

        {/* Period toggle */}
        <div className="period-toggle">
          <button
            className={`period-toggle__btn${period === "annual"  ? " period-toggle__btn--active" : ""}`}
            onClick={() => setPeriod("annual")}
          >
            Annual
          </button>
          <button
            className={`period-toggle__btn${period === "monthly" ? " period-toggle__btn--active" : ""}`}
            onClick={() => setPeriod("monthly")}
          >
            Monthly
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="page-loading">
          <div className="spinner spinner--lg" />
        </div>
      )}

      {!loading && (
        <>
          {/* ── Bar chart: stock movement ──────────────────────────────── */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">
                {period === "annual"
                  ? "Annual Stock Movement (by month)"
                  : "Monthly Stock Movement (by day)"}
              </h3>
            </div>
            <div style={{ padding: "16px 20px 20px" }}>
              {reportData && reportData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={reportData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis
                      dataKey={xKey}
                      tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                      interval="preserveStartEnd"
                    />
                    <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                    <Bar dataKey="received" name="Received" fill="var(--blue)"  radius={[4, 4, 0, 0]} />
                    <Bar dataKey="in_stock" name="In Stock" fill="var(--green)" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="spoilt"   name="Spoilt"   fill="var(--red)"   radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No data for this period.</div>
              )}
            </div>
          </div>

          {/* ── Line chart: supplier costs ─────────────────────────────── */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">Supplier Costs — Paid vs Unpaid (KES)</h3>
            </div>
            <div style={{ padding: "16px 20px 20px" }}>
              {reportData && reportData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={reportData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis
                      dataKey={xKey}
                      tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                      tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={(v) => `KES ${Number(v).toLocaleString()}`}
                    />
                    <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                    <Line type="monotone" dataKey="paid_cost"   name="Paid"   stroke="var(--green)" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="unpaid_cost" name="Unpaid" stroke="var(--amber)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">No data for this period.</div>
              )}
            </div>
          </div>

          {/* ── Payment breakdown (two columns) ───────────────────────── */}
          {payment && (
            <div className="two-col-grid">

              {/* Unpaid */}
              <div className="card card--attention" style={{ marginBottom: 0 }}>
                <div className="card__header">
                  <Clock size={15} style={{ color: "var(--amber)" }} />
                  <h3 className="card__title">Unpaid Invoices</h3>
                  <span className="badge badge--amber">{payment.unpaid.count}</span>
                  <span className="card__total">
                    KES {Number(payment.unpaid.total_cost).toLocaleString()}
                  </span>
                </div>
                <div className="table-wrapper table-wrapper--compact">
                  {payment.unpaid.entries.length === 0 ? (
                    <div className="table-empty" style={{ padding: 24 }}>All paid ✓</div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>Date</th>
                          <th>Amount (KES)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {payment.unpaid.entries.slice(0, 15).map((e) => (
                          <tr key={e.id} className="tr--unpaid">
                            <td><strong>{e.product?.name || "—"}</strong></td>
                            <td className="td--mono">{e.entry_date}</td>
                            <td className="td--bold">
                              {(Number(e.buying_price) * e.quantity_received).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Paid */}
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card__header">
                  <CheckCircle size={15} style={{ color: "var(--green)" }} />
                  <h3 className="card__title">Paid Invoices</h3>
                  <span className="badge badge--green">{payment.paid.count}</span>
                  <span className="card__total">
                    KES {Number(payment.paid.total_cost).toLocaleString()}
                  </span>
                </div>
                <div className="table-wrapper table-wrapper--compact">
                  {payment.paid.entries.length === 0 ? (
                    <div className="table-empty" style={{ padding: 24 }}>No paid entries yet.</div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>Date</th>
                          <th>Amount (KES)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {payment.paid.entries.slice(0, 15).map((e) => (
                          <tr key={e.id} className="tr--paid">
                            <td><strong>{e.product?.name || "—"}</strong></td>
                            <td className="td--mono">{e.entry_date}</td>
                            <td className="td--bold">
                              {(Number(e.buying_price) * e.quantity_received).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

            </div>
          )}
        </>
      )}
    </div>
  );
}