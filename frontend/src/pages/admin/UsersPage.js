// src/pages/admin/UsersPage.js
// ──────────────────────────────
// User management page for admins (manage clerks) and merchants (manage admins).
//
// Features:
//   • Invite a new user by email (sends tokenised link)
//   • View all visible users in a table
//   • Activate / Deactivate accounts (soft disable — preserves history)
//   • Permanently delete accounts
//
// The API call is made directly with the `api` util here rather than via
// Redux because this page has self-contained local state (the user list)
// and doesn't need to be shared globally.

import React, { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { Users, UserPlus, UserX, UserCheck, Trash2, Mail } from "lucide-react";
import toast from "react-hot-toast";

import api from "../../utils/api";

export default function UsersPage() {
  const { user: currentUser } = useSelector((s) => s.auth);

  const [users,      setUsers]      = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "clerk" });
  const [inviting,   setInviting]   = useState(false);

  // ── Load users on mount ───────────────────────────────────────────────────
  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setLoading(true);
    try {
      const { data } = await api.get("/users/", {
        params: { include_inactive: 1 },
      });
      setUsers(data);
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  // ── Send invitation ───────────────────────────────────────────────────────
  async function handleInvite(e) {
    e.preventDefault();
    setInviting(true);
    try {
      await api.post("/auth/invite", {
        email:    inviteForm.email.trim().toLowerCase(),
        role:     inviteForm.role,
        store_id: currentUser.store_id,
      });
      toast.success(`Invitation sent to ${inviteForm.email}.`);
      setInviteForm({ email: "", role: "clerk" });
      setShowInvite(false);
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to send invitation.");
    } finally {
      setInviting(false);
    }
  }

  // ── Deactivate user ───────────────────────────────────────────────────────
  async function handleDeactivate(userId, email) {
    try {
      await api.patch(`/users/${userId}/deactivate`);
      toast.success(`${email} has been deactivated.`);
      setUsers((prev) =>
        prev.map((u) => u.id === userId ? { ...u, is_active: false } : u)
      );
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to deactivate.");
    }
  }

  // ── Activate user ─────────────────────────────────────────────────────────
  async function handleActivate(userId, email) {
    try {
      await api.patch(`/users/${userId}/activate`);
      toast.success(`${email} has been reactivated.`);
      setUsers((prev) =>
        prev.map((u) => u.id === userId ? { ...u, is_active: true } : u)
      );
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to activate.");
    }
  }

  // ── Delete user ───────────────────────────────────────────────────────────
  async function handleDelete(userId, email) {
    if (!window.confirm(`Permanently delete ${email}? This cannot be undone.`)) return;
    try {
      await api.delete(`/users/${userId}`);
      toast.success(`${email} has been deleted.`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to delete user.");
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      <div className="page__header">
        <div>
          <h2 className="page__title">User Management</h2>
          <p className="page__sub">
            {currentUser?.role === "merchant"
              ? "Manage admins across all stores."
              : "Manage clerks in your store."}
          </p>
        </div>
        <button
          className="btn btn--primary"
          onClick={() => setShowInvite((v) => !v)}
        >
          <UserPlus size={15} /> Invite User
        </button>
      </div>

      {/* ── Invite form ───────────────────────────────────────────────── */}
      {showInvite && (
        <div className="card card--highlighted">
          <div className="card__header">
            <Mail size={17} />
            <h3 className="card__title">Send Invitation</h3>
          </div>

          <form
            onSubmit={handleInvite}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              padding: 20,
            }}
          >
            {/* Email */}
            <div className="form-group">
              <label className="form-label">Email address *</label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) =>
                  setInviteForm((prev) => ({ ...prev, email: e.target.value }))
                }
                className="form-input"
                placeholder="colleague@example.com"
                autoFocus
                required
              />
            </div>

            {/* Role — merchant can invite admins; admin can only invite clerks */}
            <div className="form-group">
              <label className="form-label">Role</label>
              <select
                value={inviteForm.role}
                onChange={(e) =>
                  setInviteForm((prev) => ({ ...prev, role: e.target.value }))
                }
                className="form-input"
                disabled={currentUser?.role === "admin"}
              >
                {currentUser?.role === "merchant" && (
                  <option value="admin">Admin</option>
                )}
                <option value="clerk">Clerk</option>
              </select>
            </div>

            {/* Actions */}
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
              <button
                type="submit"
                className="btn btn--primary"
                disabled={inviting}
              >
                {inviting ? <span className="btn__spinner" /> : <><Mail size={14} /> Send Invite</>}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setShowInvite(false)}
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
              No users found. Click "Invite User" to add someone.
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
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={!u.is_active ? "tr--inactive" : ""}>

                    {/* Avatar + name */}
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

                    <td className="td--mono" style={{ fontSize: "0.8rem" }}>
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString()
                        : "—"}
                    </td>

                    {/* Actions — disabled for the current user's own account */}
                    <td className="td--actions">
                      {u.id !== currentUser?.id ? (
                        <>
                          {u.is_active ? (
                            <button
                              className="btn btn--xs btn--amber"
                              onClick={() => handleDeactivate(u.id, u.email)}
                              title="Deactivate (probation)"
                            >
                              <UserX size={12} /> Deactivate
                            </button>
                          ) : (
                            <button
                              className="btn btn--xs btn--green"
                              onClick={() => handleActivate(u.id, u.email)}
                              title="Reactivate account"
                            >
                              <UserCheck size={12} /> Activate
                            </button>
                          )}
                          <button
                            className="btn btn--xs btn--ghost-red"
                            onClick={() => handleDelete(u.id, u.email)}
                            title="Permanently delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        </>
                      ) : (
                        <span style={{ color: "var(--text-dim)", fontSize: "0.78rem" }}>
                          (you)
                        </span>
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