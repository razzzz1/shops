
// src/pages/merchant/MerchantDashboard.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Store, TrendingUp, Package, AlertCircle, ChevronRight, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import api from "../../utils/api";

export default function MerchantDashboard() {
  const navigate = useNavigate();
  const [stores,    setStores]    = useState([]);
  const [summaries, setSummaries] = useState({});
  const [loading,   setLoading]   = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      // Step 1 — get all users to find stores
      const { data: allUsers } = await api.get("/users/", {
        params: { include_inactive: 1 },
      });

      // Collect unique stores from all users
      const storeMap = {};
      allUsers.forEach((u) => {
        if (u.store && u.store.id && !storeMap[u.store.id]) {
          storeMap[u.store.id] = u.store;
        }
      });

      const uniqueStores = Object.values(storeMap);

      // If still no stores, try to get the merchant's own store
      if (uniqueStores.length === 0) {
        const { data: me } = await api.get("/users/me");
        if (me.store) uniqueStores.push(me.store);
      }

      setStores(uniqueStores);

      // Step 2 — fetch summary for each store in parallel
      if (uniqueStores.length > 0) {
        const results = await Promise.allSettled(
          uniqueStores.map((s) =>
            api.get("/reports/summary", { params: { store_id: s.id } })
          )
        );
        const map = {};
        results.forEach((res, i) => {
          if (res.status === "fulfilled") {
            map[uniqueStores[i].id] = res.value.data;
          }
        });
        setSummaries(map);
      }

    } catch (err) {
      toast.error("Failed to load stores.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h2 className="page__title">All Stores</h2>
          <p className="page__sub">Overview of all store locations. Click a store to view its full report.</p>
        </div>
        <button className="btn btn--outline" onClick={loadData}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {loading && (
        <div className="page-loading"><div className="spinner spinner--lg" /></div>
      )}

      {!loading && stores.length === 0 && (
        <div className="card">
          <div className="table-empty">
            <p>No stores found.</p>
            <p style={{ marginTop: 8, fontSize: "0.85rem" }}>
              Run <code style={{ background: "var(--surface-2)", padding: "2px 6px", borderRadius: 4 }}>
                flask seed-demo
              </code> in the backend terminal to populate demo data.
            </p>
          </div>
        </div>
      )}

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
                onKeyDown={(e) => e.key === "Enter" && navigate(`/merchant/stores/${store.id}`)}
              >
                <div className="store-card__header">
                  <Store size={26} className="store-card__icon" />
                  <div>
                    <h3 className="store-card__name">{store.name}</h3>
                    <p className="store-card__location">{store.location || "No location set"}</p>
                  </div>
                </div>

                {s ? (
                  <div className="store-card__stats">
                    <div className="store-card__stat">
                      <Package size={13} />
                      <span>In Stock: <strong>{Number(s.total_in_stock).toLocaleString()}</strong></span>
                    </div>
                    <div className="store-card__stat">
                      <TrendingUp size={13} />
                      <span>Revenue Potential: <strong>KES {Number(s.revenue_potential).toLocaleString()}</strong></span>
                    </div>
                    <div className="store-card__stat store-card__stat--unpaid">
                      <AlertCircle size={13} />
                      <span>Unpaid: <strong>KES {Number(s.unpaid_cost).toLocaleString()}</strong></span>
                    </div>
                    <div className="store-card__stat">
                      <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                        {s.entry_count} entries recorded
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="store-card__no-data">No data yet for this store</div>
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