// src/pages/LoginPage.js
// ───────────────────────
// Public login page — the first screen any user sees.
//
// Flow:
//   1. User enters email + password and submits.
//   2. loginUser thunk calls POST /api/auth/login.
//   3. On success → tokens stored in localStorage, user stored in Redux.
//   4. useEffect detects isAuthenticated → redirects to the correct dashboard.
//   5. On failure → error toast, form stays editable.
//
// Already-authenticated users who land on /login are immediately
// sent to their role dashboard (handles browser back-button after login).

import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Package, Eye, EyeOff, LogIn } from "lucide-react";
import toast from "react-hot-toast";

import { loginUser, clearError } from "../store/slices/authSlice";

// Maps a role to its home route
const ROLE_HOME = { merchant: "/merchant", admin: "/admin", clerk: "/clerk" };

export default function LoginPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const { loading, error, isAuthenticated, user } = useSelector((s) => s.auth);

  // ── Local form state ───────────────────────────────────────────────────────
  const [form,     setForm]     = useState({ email: "", password: "" });
  const [showPass, setShowPass] = useState(false);

  // ── Redirect when authenticated ────────────────────────────────────────────
  // Fires after login succeeds (Redux state updates → this effect runs)
  // and also on first render if the user is already logged in.
  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(ROLE_HOME[user.role] || "/", { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // ── Show backend error as a toast then clear it ───────────────────────────
  useEffect(() => {
    if (error) {
      toast.error(error);
      dispatch(clearError());
    }
  }, [error, dispatch]);

  // ── Handlers ───────────────────────────────────────────────────────────────
  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();

    if (!form.email.trim() || !form.password) {
      toast.error("Please enter your email and password.");
      return;
    }

    dispatch(loginUser({
      email:    form.email.trim().toLowerCase(),
      password: form.password,
    }));
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="auth-page">

      {/* ── Left panel: branding ─────────────────────────────────────────── */}
      <div className="auth-page__brand">
        <div className="auth-page__brand-inner">

          <Package size={52} className="auth-page__brand-icon" />
          <h1 className="auth-page__brand-title">StockFlow</h1>

          <p className="auth-page__brand-sub">
            Smart inventory management for growing businesses.
            Track stock, manage suppliers, and generate reports — all in one place.
          </p>

          <ul className="auth-page__features">
            <li>Real-time stock tracking across all stores</li>
            <li>Automated weekly, monthly &amp; annual reports</li>
            <li>Supplier payment tracking &amp; alerts</li>
            <li>Role-based access for your whole team</li>
          </ul>

        </div>
      </div>

      {/* ── Right panel: login form ───────────────────────────────────────── */}
      <div className="auth-page__form-panel">
        <div className="auth-card">

          <h2 className="auth-card__title">Welcome back</h2>
          <p className="auth-card__sub">Sign in to your StockFlow account</p>

          <form onSubmit={handleSubmit} noValidate>

            {/* Email */}
            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                Email address
              </label>
              <input
                id="login-email"
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                className="form-input"
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
                required
              />
            </div>

            {/* Password with show/hide toggle */}
            <div className="form-group">
              <label htmlFor="login-password" className="form-label">
                Password
              </label>
              <div className="form-input-wrapper">
                <input
                  id="login-password"
                  type={showPass ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  className="form-input form-input--padded-r"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="form-input-eye"
                  onClick={() => setShowPass((v) => !v)}
                  aria-label={showPass ? "Hide password" : "Show password"}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit button — shows spinner while loading */}
            <button
              type="submit"
              className="btn btn--primary btn--full"
              disabled={loading}
            >
              {loading
                ? <span className="btn__spinner" />
                : <><LogIn size={16} /> Sign in</>
              }
            </button>

          </form>

          {/* No public registration — invite only */}
          <p className="auth-card__note">
            Don't have an account? Ask your administrator to send you an
            invitation link.
          </p>

        </div>
      </div>
    </div>
  );
}