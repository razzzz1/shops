// src/pages/merchant/MerchantDashboard.js
// ──────────────────────────────────────────
// Merchant's top-level view — a grid of store cards, each showing
// key metrics for that store. Clicking a card drills into the full
// StoreReportPage for that store.
//
// Because the API doesn't have a dedicated /stores/ endpoint yet,
// we derive the store list from the admin users endpoint (each admin
// belongs to one store). The merchant then fetches a summary for each
// store in parallel.

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Store, TrendingUp, Package, AlertCircle, ChevronRight,
} from "lucide-react";
import toast from "react-hot-toast";

import api from "../../utils/api";

export default function MerchantDashboard() {
  const navigate = useNavigate();

  const [stores,    setStores]    = useState([]);
  const [summaries, setSummaries] = useState({}); // { [store_id]: summaryObj }
  const [loading,   setLoading]   = useState(true);

  // ── Load stores and their summaries on mount ──────────────────────────────
  useEffect(() => {
    loadStores();
  }, []);

  async function loadStores() {
    setLoading(true);
    try {
      // Fetch all admin users — each admin belongs to a store
      const { data: adminUsers } = await api.get("/users/", {
        params: { role: "admin", include_inactive: 1 },
      });

      // Deduplicate stores (multiple admins can share a store)
      const storeMap = {};
      adminUsers.forEach((u) => {
        if (u.store && !storeMap[u.store.id]) {
          storeMap[u.store.id] = u.store;
        }
      });
      const uniqueStores = Object.values(storeMap);
      setStores(uniqueStores);

      // Fetch a KPI summary for each store in parallel
      const summaryResults = await Promise.allSettled(
        uniqueStores.map((store) =>
          api.get("/reports/summary", { params: { store_id: store.id } })
        )
      );

      const summaryMap = {};
      summaryResults.forEach((result, i) => {
        if (result.status === "fulfilled") {
          summaryMap[uniqueStores[i].id] = result.value.data;
        }
      });
      setSummaries(summaryMap);

    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to load stores.");
    } finally {
      setLoading(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">All Stores</h2>
          <p className="page__sub">
            Click a store to view its detailed performance report.
          </p>
        </div>
      </div>

      {/* ── Loading ───────────────────────────────────────────────────── */}
      {loading && (
        <div className="page-loading">
          <div className="spinner spinner--lg" />
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && stores.length === 0 && (
        <div className="card">
          <div className="table-empty">
            No stores found. Invite admins to set up store locations.
          </div>
        </div>
      )}

      {/* ── Store grid ────────────────────────────────────────────────── */}
      {!loading && stores.length > 0 && (
        <div className="store-grid">
          {stores.map((store) => {
            const s = summaries[store.id];
            return (
              <div
                key={store.id}
                className="store-card"
                onClick={() => navigate(`/merchant/stores/${store.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") navigate(`/merchant/stores/${store.id}`);
                }}
              >
                {/* Store header */}
                <div className="store-card__header">
                  <Store size={26} className="store-card__icon" />
                  <div>
                    <h3 className="store-card__name">{store.name}</h3>
                    <p className="store-card__location">
                      {store.location || "No location set"}
                    </p>
                  </div>
                </div>

                {/* KPI mini-stats */}
                {s ? (
                  <div className="store-card__stats">
                    <div className="store-card__stat">
                      <Package size={13} />
                      <span>
                        In Stock: <strong>{s.total_in_stock?.toLocaleString()}</strong>
                      </span>
                    </div>
                    <div className="store-card__stat">
                      <TrendingUp size={13} />
                      <span>
                        Revenue Potential:{" "}
                        <strong>KES {Number(s.revenue_potential).toLocaleString()}</strong>
                      </span>
                    </div>
                    <div className="store-card__stat store-card__stat--unpaid">
                      <AlertCircle size={13} />
                      <span>
                        Unpaid:{" "}
                        <strong>KES {Number(s.unpaid_cost).toLocaleString()}</strong>
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="store-card__no-data">No data yet</div>
                )}

                <div className="store-card__footer">
                  View detailed report <ChevronRight size={13} style={{ display: "inline", verticalAlign: "middle" }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}