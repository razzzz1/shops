// src/pages/RegisterPage.js
// ──────────────────────────
// Invitation-based registration page.
//
// How a user reaches this page:
//   1. A merchant or admin sends an invitation via POST /api/auth/invite.
//   2. The backend generates a signed token and emails a link:
//      https://app.example.com/register?token=<signed-token>
//   3. The user clicks the link — React Router renders this page.
//
// What this page does:
//   1. Reads the ?token= query parameter from the URL.
//   2. Calls GET /api/auth/verify-invite — validates the token and returns
//      the pre-set email, role, and store embedded in the token.
//   3. Shows the email and role as read-only (user cannot change these —
//      the inviter decided them).
//   4. User fills in their first name, last name, and chosen password.
//   5. POST /api/auth/register → user is created and immediately logged in.
//   6. Redirect to the correct role dashboard.
//
// Error states handled:
//   • Missing token param         → "Invalid link" error card
//   • Token not found in DB       → "Invalid link" error card
//   • Token expired or used       → "Expired link" error card
//   • Weak password (< 8 chars)   → inline toast
//   • Passwords don't match       → inline toast

import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Package, Eye, EyeOff, UserPlus, AlertTriangle, Loader } from "lucide-react";
import toast from "react-hot-toast";

import {
  verifyInviteToken,
  registerUser,
  clearError,
} from "../store/slices/authSlice";

const ROLE_HOME = { merchant: "/merchant", admin: "/admin", clerk: "/clerk" };

export default function RegisterPage() {
  const dispatch      = useDispatch();
  const navigate      = useNavigate();
  const [searchParams] = useSearchParams();

  // The raw token string from the URL query param
  const token = searchParams.get("token") || "";

  const { loading, error, inviteData, isAuthenticated, user }
    = useSelector((s) => s.auth);

  // ── Local state ────────────────────────────────────────────────────────────
  const [form, setForm] = useState({
    first_name: "",
    last_name:  "",
    password:   "",
    confirm:    "",
  });
  const [showPass,    setShowPass]    = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  // Tracks whether the token verification has settled (success or failure)
  const [tokenChecked, setTokenChecked] = useState(false);
  const [tokenInvalid, setTokenInvalid] = useState(false);

  // ── Step 1: verify the token on mount ─────────────────────────────────────
  useEffect(() => {
    if (!token) {
      // No token in the URL at all — show error immediately
      setTokenChecked(true);
      setTokenInvalid(true);
      return;
    }

    dispatch(verifyInviteToken(token))
      .unwrap()
      .then(() => {
        // Token is valid — inviteData is now populated in Redux
        setTokenChecked(true);
      })
      .catch(() => {
        // Token invalid, expired, or already used
        setTokenChecked(true);
        setTokenInvalid(true);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // only run once on mount

  // ── Step 2: redirect on successful registration ───────────────────────────
  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(ROLE_HOME[user.role] || "/", { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // ── Show backend errors as toasts ─────────────────────────────────────────
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

    // Client-side validation before hitting the server
    if (!form.first_name.trim() || !form.last_name.trim()) {
      toast.error("Please enter your full name.");
      return;
    }
    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (form.password !== form.confirm) {
      toast.error("Passwords do not match.");
      return;
    }

    dispatch(registerUser({
      token,
      first_name: form.first_name.trim(),
      last_name:  form.last_name.trim(),
      password:   form.password,
    }));
  }

  // ── Loading state: verifying token ────────────────────────────────────────
  if (!tokenChecked) {
    return (
      <div className="auth-page" style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <Loader size={36} style={{ color: "var(--primary)", animation: "spin 1s linear infinite" }} />
          <p style={{ color: "var(--text-muted)" }}>Verifying your invitation…</p>
        </div>
      </div>
    );
  }

  // ── Error state: invalid or expired token ─────────────────────────────────
  if (tokenInvalid) {
    return (
      <div className="auth-page" style={{ justifyContent: "center", alignItems: "center" }}>
        <div className="auth-error-card">
          <AlertTriangle size={52} className="auth-error-card__icon" />
          <h2 className="auth-error-card__title">Invalid Invitation</h2>
          <p className="auth-error-card__text">
            This invitation link is invalid, has already been used, or has
            expired. Please ask your administrator to send you a new invitation.
          </p>
          <a href="/login" className="btn btn--outline">
            Back to Login
          </a>
        </div>
      </div>
    );
  }

  // ── Registration form ─────────────────────────────────────────────────────
  return (
    <div className="auth-page">

      {/* ── Left panel: branding ─────────────────────────────────────────── */}
      <div className="auth-page__brand">
        <div className="auth-page__brand-inner">
          <Package size={52} className="auth-page__brand-icon" />
          <h1 className="auth-page__brand-title">StockFlow</h1>
          <p className="auth-page__brand-sub">
            You've been invited to join StockFlow. Complete your registration
            to get started.
          </p>
        </div>
      </div>

      {/* ── Right panel: registration form ───────────────────────────────── */}
      <div className="auth-page__form-panel">
        <div className="auth-card">

          <h2 className="auth-card__title">Create your account</h2>
          <p className="auth-card__sub">Complete your invitation to get started</p>

          {/* Show the pre-set email + role from the token — read-only */}
          {inviteData && (
            <div className="invite-meta">
              <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Invited as
                </span>
                <span className="invite-meta__email">{inviteData.email}</span>
              </div>
              <span className={`badge badge--${inviteData.role}`}>
                {inviteData.role}
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>

            {/* Name row — first + last side by side */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="reg-first" className="form-label">
                  First name
                </label>
                <input
                  id="reg-first"
                  type="text"
                  name="first_name"
                  value={form.first_name}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="Jane"
                  autoComplete="given-name"
                  autoFocus
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="reg-last" className="form-label">
                  Last name
                </label>
                <input
                  id="reg-last"
                  type="text"
                  name="last_name"
                  value={form.last_name}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="Smith"
                  autoComplete="family-name"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="form-group">
              <label htmlFor="reg-password" className="form-label">
                Password
                <span style={{ color: "var(--text-dim)", fontWeight: 400, marginLeft: 6 }}>
                  (min. 8 characters)
                </span>
              </label>
              <div className="form-input-wrapper">
                <input
                  id="reg-password"
                  type={showPass ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  className="form-input form-input--padded-r"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                  minLength={8}
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

              {/* Live strength indicator */}
              {form.password.length > 0 && (
                <PasswordStrength password={form.password} />
              )}
            </div>

            {/* Confirm password */}
            <div className="form-group">
              <label htmlFor="reg-confirm" className="form-label">
                Confirm password
              </label>
              <div className="form-input-wrapper">
                <input
                  id="reg-confirm"
                  type={showConfirm ? "text" : "password"}
                  name="confirm"
                  value={form.confirm}
                  onChange={handleChange}
                  className="form-input form-input--padded-r"
                  placeholder="Re-enter your password"
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="form-input-eye"
                  onClick={() => setShowConfirm((v) => !v)}
                  aria-label={showConfirm ? "Hide" : "Show"}
                >
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {/* Match indicator */}
              {form.confirm.length > 0 && (
                <span style={{
                  fontSize: "0.78rem",
                  color: form.password === form.confirm
                    ? "var(--green)"
                    : "var(--red)",
                  marginTop: 2,
                }}>
                  {form.password === form.confirm
                    ? "✓ Passwords match"
                    : "✗ Passwords do not match"}
                </span>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="btn btn--primary btn--full"
              disabled={loading}
            >
              {loading
                ? <span className="btn__spinner" />
                : <><UserPlus size={16} /> Create Account</>
              }
            </button>

          </form>

          <p className="auth-card__note">
            Already have an account?{" "}
            <a href="/login" style={{ color: "var(--primary)" }}>Sign in</a>
          </p>

        </div>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// PasswordStrength — small inline strength indicator
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Shows a coloured bar and label indicating password strength.
 * Scoring: length, uppercase, number, special character.
 */
function PasswordStrength({ password }) {
  // Calculate a score 0–4 based on common criteria
  let score = 0;
  if (password.length >= 8)                    score++;
  if (password.length >= 12)                   score++;
  if (/[A-Z]/.test(password))                  score++;
  if (/[0-9]/.test(password))                  score++;
  if (/[^A-Za-z0-9]/.test(password))           score++;

  // Clamp to 0–4 for the visual
  const level = Math.min(score, 4);

  const labels = ["Too short", "Weak", "Fair", "Good", "Strong"];
  const colors = ["var(--red)", "var(--red)", "var(--amber)", "var(--blue)", "var(--green)"];

  return (
    <div style={{ marginTop: 6 }}>
      {/* Four segment bar */}
      <div style={{ display: "flex", gap: 3, marginBottom: 4 }}>
        {[1, 2, 3, 4].map((seg) => (
          <div
            key={seg}
            style={{
              flex: 1,
              height: 3,
              borderRadius: 2,
              background: seg <= level ? colors[level] : "var(--border)",
              transition: "background 0.2s",
            }}
          />
        ))}
      </div>
      <span style={{ fontSize: "0.75rem", color: colors[level] }}>
        {labels[level]}
      </span>
    </div>
  );
}