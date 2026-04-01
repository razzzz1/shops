// src/pages/admin/AdminReportsPage.js
// ──────────────────────────────────────
// Full reporting page for admins (and merchants viewing a single store).
//
// Features:
//   • Period selector — Weekly / Monthly / Annual
//   • Line chart  — stock received, in-stock, spoilt over time
//   • Bar chart   — paid vs unpaid supplier costs over time
//   • Raw data table below the charts
//   • CSV export button — downloads the current period's data

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  LineChart, Line,
  BarChart,  Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { Download } from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchWeeklyReport,
  fetchMonthlyReport,
  fetchAnnualReport,
} from "../../store/slices/inventorySlice";

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

// ── Period options ────────────────────────────────────────────────────────────
const PERIODS = [
  { key: "weekly",  label: "Weekly"  },
  { key: "monthly", label: "Monthly" },
  { key: "annual",  label: "Annual"  },
];

export default function AdminReportsPage() {
  const dispatch = useDispatch();
  const { weeklyReport, monthlyReport, annualReport, loading }
    = useSelector((s) => s.inventory);

  const [period, setPeriod] = useState("weekly");

  // ── Fetch all three periods on mount so switching is instant ─────────────
  useEffect(() => {
    dispatch(fetchWeeklyReport({}));
    dispatch(fetchMonthlyReport({}));
    dispatch(fetchAnnualReport({}));
  }, [dispatch]);

  // ── Pick the right dataset ────────────────────────────────────────────────
  const reportMap = { weekly: weeklyReport, monthly: monthlyReport, annual: annualReport };
  const report    = reportMap[period];
  const data      = report?.data || [];

  // Annual uses "label" (Jan, Feb…) on the X-axis; others use "date"
  const xKey = period === "annual" ? "label" : "date";

  // ── CSV export ────────────────────────────────────────────────────────────
  function handleExportCSV() {
    if (!data.length) {
      toast.error("No data to export for this period.");
      return;
    }

    const headers = Object.keys(data[0]).join(",");
    const rows    = data.map((row) => Object.values(row).join(",")).join("\n");
    const blob    = new Blob([`${headers}\n${rows}`], { type: "text/csv" });
    const url     = URL.createObjectURL(blob);
    const a       = document.createElement("a");
    a.href        = url;
    a.download    = `stockflow-${period}-report.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV downloaded.");
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Reports</h2>
          <p className="page__sub">Visual performance analysis for your store.</p>
        </div>

        <div className="page__header-actions">
          {/* Period selector */}
          <div className="period-toggle">
            {PERIODS.map(({ key, label }) => (
              <button
                key={key}
                className={`period-toggle__btn${period === key ? " period-toggle__btn--active" : ""}`}
                onClick={() => setPeriod(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* CSV export */}
          <button className="btn btn--outline btn--sm" onClick={handleExportCSV}>
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* ── Loading ───────────────────────────────────────────────────── */}
      {loading && (
        <div className="page-loading"><div className="spinner spinner--lg" /></div>
      )}

      {/* ── No data ───────────────────────────────────────────────────── */}
      {!loading && data.length === 0 && (
        <div className="card">
          <div className="chart-empty">
            No data available for this period. Start recording stock entries to see reports.
          </div>
        </div>
      )}

      {/* ── Charts (only shown when data exists) ─────────────────────── */}
      {!loading && data.length > 0 && (
        <>

          {/* Chart 1: Stock movement — Line chart */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">
                {period === "annual"
                  ? "Monthly Stock Movement"
                  : period === "monthly"
                  ? "Daily Stock Movement"
                  : "7-Day Stock Movement"}
              </h3>
            </div>
            <div style={{ padding: "16px 20px 20px" }}>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey={xKey}
                    tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                  <Line
                    type="monotone" dataKey="received" name="Received"
                    stroke="var(--blue)"  strokeWidth={2}
                    dot={{ r: 3 }} activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone" dataKey="in_stock" name="In Stock"
                    stroke="var(--green)" strokeWidth={2}
                    dot={{ r: 3 }} activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone" dataKey="spoilt"   name="Spoilt"
                    stroke="var(--red)"   strokeWidth={2}
                    dot={{ r: 3 }} activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Supplier costs — Bar chart */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">Supplier Costs — Paid vs Unpaid (KES)</h3>
            </div>
            <div style={{ padding: "16px 20px 20px" }}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
                  <Bar dataKey="paid_cost"   name="Paid"   fill="var(--green)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="unpaid_cost" name="Unpaid" fill="var(--amber)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Raw data table */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card__header">
              <h3 className="card__title">Data Table</h3>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Received</th>
                    <th>In Stock</th>
                    <th>Spoilt</th>
                    <th>Paid (KES)</th>
                    <th>Unpaid (KES)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, i) => (
                    <tr key={i}>
                      <td className="td--mono">{row[xKey]}</td>
                      <td>{row.received.toLocaleString()}</td>
                      <td>{row.in_stock.toLocaleString()}</td>
                      <td className={row.spoilt > 0 ? "td--red" : ""}>
                        {row.spoilt.toLocaleString()}
                      </td>
                      <td>{Number(row.paid_cost).toLocaleString()}</td>
                      <td>{Number(row.unpaid_cost).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </>
      )}
    </div>
  );
}