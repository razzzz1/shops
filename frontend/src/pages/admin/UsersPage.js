
// src/pages/admin/UsersPage.js
// ──────────────────────────────
// User management — create users directly without email invitations.

import React, { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import {
  Users, UserPlus, UserX, UserCheck, Trash2, Eye, EyeOff,
} from "lucide-react";
import toast from "react-hot-toast";

import api from "../../utils/api";

const EMPTY_FORM = {
  email: "", first_name: "", last_name: "",
  password: "", role: "clerk",
};

export default function UsersPage() {
  const { user: currentUser } = useSelector((s) => s.auth);

  const [users,      setUsers]      = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [showForm,   setShowForm]   = useState(false);
  const [form,       setForm]       = useState(EMPTY_FORM);
  const [saving,     setSaving]     = useState(false);
  const [showPass,   setShowPass]   = useState(false);

  useEffect(() => { loadUsers(); }, []);

  async function loadUsers() {
    setLoading(true);
    try {
      const { data } = await api.get("/users/", { params: { include_inactive: 1 } });
      setUsers(data);
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  // ── Create user directly ──────────────────────────────────────────────────
  async function handleCreate(e) {
    e.preventDefault();

    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }

    setSaving(true);
    try {
      const { data } = await api.post("/auth/create-user", {
        email:      form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name:  form.last_name.trim(),
        password:   form.password,
        role:       form.role,
        store_id:   currentUser.store_id,
      });

      toast.success(`${data.user.first_name} ${data.user.last_name} created successfully!`);
      setForm(EMPTY_FORM);
      setShowForm(false);
      setUsers((prev) => [...prev, data.user]);

    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to create user.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(userId, email) {
    try {
      await api.patch(`/users/${userId}/deactivate`);
      toast.success(`${email} deactivated.`);
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, is_active: false } : u));
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed.");
    }
  }

  async function handleActivate(userId, email) {
    try {
      await api.patch(`/users/${userId}/activate`);
      toast.success(`${email} reactivated.`);
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, is_active: true } : u));
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed.");
    }
  }

  async function handleDelete(userId, email) {
    if (!window.confirm(`Permanently delete ${email}?`)) return;
    try {
      await api.delete(`/users/${userId}`);
      toast.success(`${email} deleted.`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed.");
    }
  }

  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">User Management</h2>
          <p className="page__sub">
            {currentUser?.role === "merchant"
              ? "Create and manage admins and clerks."
              : "Create and manage clerks in your store."}
          </p>
        </div>
        <button className="btn btn--primary" onClick={() => setShowForm((v) => !v)}>
          <UserPlus size={15} /> Create User
        </button>
      </div>

      {/* ── Create user form ──────────────────────────────────────────── */}
      {showForm && (
        <div className="card card--highlighted">
          <div className="card__header">
            <UserPlus size={17} />
            <h3 className="card__title">Create New User</h3>
          </div>

          <form
            onSubmit={handleCreate}
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: 20 }}
          >
            {/* First name */}
            <div className="form-group">
              <label className="form-label">First name *</label>
              <input
                type="text" name="first_name" value={form.first_name}
                onChange={handleChange} className="form-input"
                placeholder="Jane" autoFocus required
              />
            </div>

            {/* Last name */}
            <div className="form-group">
              <label className="form-label">Last name *</label>
              <input
                type="text" name="last_name" value={form.last_name}
                onChange={handleChange} className="form-input"
                placeholder="Smith" required
              />
            </div>

            {/* Email */}
            <div className="form-group">
              <label className="form-label">Email address *</label>
              <input
                type="email" name="email" value={form.email}
                onChange={handleChange} className="form-input"
                placeholder="jane@example.com" required
              />
            </div>

            {/* Role */}
            <div className="form-group">
              <label className="form-label">Role *</label>
              <select
                name="role" value={form.role}
                onChange={handleChange} className="form-input"
                disabled={currentUser?.role === "admin"}
              >
                {currentUser?.role === "merchant" && (
                  <option value="admin">Admin</option>
                )}
                <option value="clerk">Clerk</option>
              </select>
            </div>

            {/* Password */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label className="form-label">
                Password *
                <span style={{ color: "var(--text-dim)", fontWeight: 400, marginLeft: 6 }}>
                  (min. 8 characters)
                </span>
              </label>
              <div className="form-input-wrapper">
                <input
                  type={showPass ? "text" : "password"}
                  name="password" value={form.password}
                  onChange={handleChange}
                  className="form-input form-input--padded-r"
                  placeholder="Choose a strong password"
                  required minLength={8}
                />
                <button
                  type="button" className="form-input-eye"
                  onClick={() => setShowPass((v) => !v)}
                  aria-label={showPass ? "Hide" : "Show"}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Actions */}
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? <span className="btn__spinner" /> : <><UserPlus size={14} /> Create User</>}
              </button>
              <button
                type="button" className="btn btn--ghost"
                onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}
              >
                Cancel
              </button>
            </div>

          </form>
        </div>
      )}

      {/* ── Users table ───────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card__header">
          <Users size={17} />
          <h3 className="card__title">Users</h3>
          <span className="badge badge--blue">{users.length}</span>
        </div>

        <div className="table-wrapper">
          {loading ? (
            <div className="table-loading"><div className="spinner" /></div>
          ) : users.length === 0 ? (
            <div className="table-empty">
              No users yet. Click "Create User" to add someone.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Store</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={!u.is_active ? "tr--inactive" : ""}>

                    <td className="td__user">
                      <div className="td__avatar">
                        {u.first_name?.[0]}{u.last_name?.[0]}
                      </div>
                      {u.first_name} {u.last_name}
                    </td>

                    <td>{u.email}</td>

                    <td>
                      <span className={`badge badge--${u.role}`}>{u.role}</span>
                    </td>

                    <td>{u.store?.name || "—"}</td>

                    <td>
                      {u.is_active
                        ? <span className="badge badge--green">Active</span>
                        : <span className="badge badge--red">Inactive</span>
                      }
                    </td>

                    <td className="td--actions">
                      {u.id !== currentUser?.id ? (
                        <>
                          {u.is_active ? (
                            <button
                              className="btn btn--xs btn--amber"
                              onClick={() => handleDeactivate(u.id, u.email)}
                            >
                              <UserX size={12} /> Deactivate
                            </button>
                          ) : (
                            <button
                              className="btn btn--xs btn--green"
                              onClick={() => handleActivate(u.id, u.email)}
                            >
                              <UserCheck size={12} /> Activate
                            </button>
                          )}
                          <button
                            className="btn btn--xs btn--ghost-red"
                            onClick={() => handleDelete(u.id, u.email)}
                          >
                            <Trash2 size={12} />
                          </button>
                        </>
                      ) : (
                        <span style={{ color: "var(--text-dim)", fontSize: "0.78rem" }}>(you)</span>
                      )}
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