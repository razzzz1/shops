// src/pages/admin/ProductsPage.js
// ─────────────────────────────────
// Admin page to manage the product catalogue.
// Create, edit and deactivate products.
// Products must exist before clerks can record stock entries.

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Package, Plus, Pencil, X, Check } from "lucide-react";
import toast from "react-hot-toast";

import {
  fetchProducts,
  createProduct,
  updateProduct,
} from "../../store/slices/inventorySlice";
import api from "../../utils/api";

const EMPTY_FORM = {
  name:          "",
  sku:           "",
  category:      "",
  unit:          "",
  buying_price:  "",
  selling_price: "",
  reorder_level: "10",
};

export default function ProductsPage() {
  const dispatch = useDispatch();
  const { products, loading } = useSelector((s) => s.inventory);

  const [showForm,  setShowForm]  = useState(false);
  const [form,      setForm]      = useState(EMPTY_FORM);
  const [saving,    setSaving]    = useState(false);
  const [editingId, setEditingId] = useState(null); // product id being edited

  useEffect(() => {
    dispatch(fetchProducts({ include_inactive: 1 }));
  }, [dispatch]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  // ── Start editing an existing product ─────────────────────────────────────
  function startEdit(product) {
    setEditingId(product.id);
    setForm({
      name:          product.name,
      sku:           product.sku           || "",
      category:      product.category      || "",
      unit:          product.unit          || "",
      buying_price:  String(product.buying_price),
      selling_price: String(product.selling_price),
      reorder_level: String(product.reorder_level || 10),
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  // ── Save product (create or update) ───────────────────────────────────────
  async function handleSave(e) {
    e.preventDefault();

    if (!form.name.trim() || !form.buying_price || !form.selling_price) {
      toast.error("Name, buying price and selling price are required.");
      return;
    }

    if (Number(form.buying_price) < 0 || Number(form.selling_price) < 0) {
      toast.error("Prices cannot be negative.");
      return;
    }

    const payload = {
      name:          form.name.trim(),
      sku:           form.sku.trim()      || undefined,
      category:      form.category.trim() || undefined,
      unit:          form.unit.trim()     || undefined,
      buying_price:  Number(form.buying_price),
      selling_price: Number(form.selling_price),
      reorder_level: Number(form.reorder_level || 10),
    };

    setSaving(true);
    try {
      if (editingId) {
        await dispatch(updateProduct({ id: editingId, payload })).unwrap();
        toast.success("Product updated.");
      } else {
        await dispatch(createProduct(payload)).unwrap();
        toast.success("Product created! Clerks can now select it in stock entries.");
      }
      cancelForm();
      dispatch(fetchProducts({ include_inactive: 1 }));
    } catch (err) {
      toast.error(err || "Failed to save product.");
    } finally {
      setSaving(false);
    }
  }

  // ── Deactivate product ────────────────────────────────────────────────────
  async function handleDeactivate(id, name) {
    if (!window.confirm(`Deactivate "${name}"? It will no longer appear in stock entry forms.`)) return;
    try {
      await api.delete(`/products/${id}`);
      toast.success(`"${name}" deactivated.`);
      dispatch(fetchProducts({ include_inactive: 1 }));
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed.");
    }
  }

  const activeProducts   = products.filter((p) => p.is_active);
  const inactiveProducts = products.filter((p) => !p.is_active);

  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">Product Catalogue</h2>
          <p className="page__sub">
            Add products here first — clerks select from this list when recording stock entries.
          </p>
        </div>
        <button className="btn btn--primary" onClick={() => { cancelForm(); setShowForm((v) => !v); }}>
          <Plus size={15} /> Add Product
        </button>
      </div>

      {/* ── Create / Edit form ────────────────────────────────────────── */}
      {showForm && (
        <div className="card card--highlighted">
          <div className="card__header">
            <Package size={17} />
            <h3 className="card__title">
              {editingId ? "Edit Product" : "New Product"}
            </h3>
          </div>

          <form
            onSubmit={handleSave}
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, padding: 20 }}
          >
            {/* Name — full width */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label className="form-label">Product Name *</label>
              <input
                type="text" name="name" value={form.name}
                onChange={handleChange} className="form-input"
                placeholder="e.g. Full Cream Milk 1L"
                autoFocus required
              />
            </div>

            {/* SKU */}
            <div className="form-group">
              <label className="form-label">SKU / Code</label>
              <input
                type="text" name="sku" value={form.sku}
                onChange={handleChange} className="form-input"
                placeholder="e.g. MILK-001"
              />
            </div>

            {/* Category */}
            <div className="form-group">
              <label className="form-label">Category</label>
              <input
                type="text" name="category" value={form.category}
                onChange={handleChange} className="form-input"
                placeholder="e.g. Dairy, Bakery, Drinks"
              />
            </div>

            {/* Unit */}
            <div className="form-group">
              <label className="form-label">Unit</label>
              <input
                type="text" name="unit" value={form.unit}
                onChange={handleChange} className="form-input"
                placeholder="e.g. litres, pieces, kg"
              />
            </div>

            {/* Buying price */}
            <div className="form-group">
              <label className="form-label">Buying Price (KES) *</label>
              <input
                type="number" name="buying_price" value={form.buying_price}
                onChange={handleChange} className="form-input"
                placeholder="0.00" min="0" step="0.01" required
              />
            </div>

            {/* Selling price */}
            <div className="form-group">
              <label className="form-label">Selling Price (KES) *</label>
              <input
                type="number" name="selling_price" value={form.selling_price}
                onChange={handleChange} className="form-input"
                placeholder="0.00" min="0" step="0.01" required
              />
            </div>

            {/* Reorder level */}
            <div className="form-group">
              <label className="form-label">
                Reorder Level
                <span style={{ color: "var(--text-dim)", fontWeight: 400, marginLeft: 6 }}>
                  (alert threshold)
                </span>
              </label>
              <input
                type="number" name="reorder_level" value={form.reorder_level}
                onChange={handleChange} className="form-input"
                placeholder="10" min="0"
              />
            </div>

            {/* Actions */}
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving
                  ? <span className="btn__spinner" />
                  : <><Check size={14} /> {editingId ? "Save Changes" : "Create Product"}</>
                }
              </button>
              <button type="button" className="btn btn--ghost" onClick={cancelForm}>
                <X size={14} /> Cancel
              </button>
            </div>

          </form>
        </div>
      )}

      {/* ── Active products table ─────────────────────────────────────── */}
      <div className="card">
        <div className="card__header">
          <Package size={17} />
          <h3 className="card__title">Active Products</h3>
          <span className="badge badge--green">{activeProducts.length}</span>
        </div>

        <div className="table-wrapper">
          {loading ? (
            <div className="table-loading"><div className="spinner" /></div>
          ) : activeProducts.length === 0 ? (
            <div className="table-empty">
              No products yet. Click "Add Product" to create your first one.
              <br />
              <span style={{ fontSize: "0.82rem", marginTop: 6, display: "block" }}>
                Clerks need at least one product before they can record stock entries.
              </span>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Unit</th>
                  <th>Buying (KES)</th>
                  <th>Selling (KES)</th>
                  <th>Reorder At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeProducts.map((p) => (
                  <tr key={p.id}>
                    <td><strong>{p.name}</strong></td>
                    <td className="td--mono">{p.sku || "—"}</td>
                    <td>{p.category || "—"}</td>
                    <td>{p.unit || "—"}</td>
                    <td>{Number(p.buying_price).toLocaleString()}</td>
                    <td>{Number(p.selling_price).toLocaleString()}</td>
                    <td>{p.reorder_level}</td>
                    <td className="td--actions">
                      <button
                        className="btn btn--xs btn--outline"
                        onClick={() => startEdit(p)}
                      >
                        <Pencil size={12} /> Edit
                      </button>
                      <button
                        className="btn btn--xs btn--ghost-red"
                        onClick={() => handleDeactivate(p.id, p.name)}
                      >
                        <X size={12} /> Deactivate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Inactive products (collapsed) ────────────────────────────── */}
      {inactiveProducts.length > 0 && (
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card__header">
            <h3 className="card__title" style={{ color: "var(--text-muted)" }}>
              Deactivated Products
            </h3>
            <span className="badge badge--red">{inactiveProducts.length}</span>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Buying (KES)</th>
                  <th>Selling (KES)</th>
                </tr>
              </thead>
              <tbody>
                {inactiveProducts.map((p) => (
                  <tr key={p.id} className="tr--inactive">
                    <td>{p.name}</td>
                    <td className="td--mono">{p.sku || "—"}</td>
                    <td>{p.category || "—"}</td>
                    <td>{Number(p.buying_price).toLocaleString()}</td>
                    <td>{Number(p.selling_price).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}