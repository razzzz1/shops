// src/App.js
// ───────────
// Root component — sets up:
//   1. React Router (client-side navigation)
//   2. Session restoration (reads stored JWT on load)
//   3. Route guards (unauthenticated → /login)
//   4. Role guards (wrong role → home page for their role)
//   5. Hot-toast notification stack

import React, { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { Toaster } from "react-hot-toast";

import { fetchCurrentUser } from "./store/slices/authSlice";

// ── Shared layout (sidebar + topbar) ──────────────────────────────────────
import Layout from "./components/shared/Layout";

// ── Auth pages ────────────────────────────────────────────────────────────
import LoginPage    from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// ── Clerk pages ───────────────────────────────────────────────────────────
import ClerkDashboard from "./pages/clerk/ClerkDashboard";
import InventoryPage  from "./pages/clerk/InventoryPage";
import SupplyPage     from "./pages/clerk/SupplyPage";

// ── Admin pages ───────────────────────────────────────────────────────────
import AdminDashboard    from "./pages/admin/AdminDashboard";
import AdminReportsPage  from "./pages/admin/AdminReportsPage";
import PaymentPage       from "./pages/admin/PaymentPage";
import UsersPage         from "./pages/admin/UsersPage";

// ── Merchant pages ────────────────────────────────────────────────────────
import MerchantDashboard from "./pages/merchant/MerchantDashboard";
import StoreReportPage   from "./pages/merchant/StoreReportPage";


// ─────────────────────────────────────────────────────────────────────────────
// Route guards
// ─────────────────────────────────────────────────────────────────────────────

/**
 * RequireAuth
 * Wraps any subtree that requires the user to be logged in.
 * Shows a full-screen spinner while session restoration is in progress,
 * then redirects to /login if unauthenticated.
 */
function RequireAuth() {
  const { isAuthenticated, isInitialising } = useSelector((s) => s.auth);

  if (isInitialising) {
    // We're still checking whether a stored token is valid — don't redirect yet
    return (
      <div className="app-loading">
        <div className="spinner spinner--lg" />
      </div>
    );
  }

  return isAuthenticated
    ? <Outlet />                              // logged in → render child routes
    : <Navigate to="/login" replace />;       // not logged in → login page
}

/**
 * RequireRole
 * Within the authenticated zone, further restricts a subtree to specific roles.
 * Users with a different role are redirected to their own home page rather
 * than getting a blank 403 screen.
 */
function RequireRole({ allowedRoles }) {
  const { user } = useSelector((s) => s.auth);

  if (!user) return <Navigate to="/login" replace />;

  if (!allowedRoles.includes(user.role)) {
    // Send them to the correct home page for their role
    return <Navigate to={roleHome(user.role)} replace />;
  }

  return <Outlet />;
}

/** Map a role string to its home route. */
function roleHome(role) {
  const map = { merchant: "/merchant", admin: "/admin", clerk: "/clerk" };
  return map[role] || "/login";
}


// ─────────────────────────────────────────────────────────────────────────────
// Root redirect
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Visiting "/" redirects to the correct dashboard for the logged-in role,
 * or to /login if not authenticated.
 */
function RootRedirect() {
  const { isAuthenticated, user } = useSelector((s) => s.auth);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={roleHome(user?.role)} replace />;
}


// ─────────────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────────────

export default function App() {
  const dispatch       = useDispatch();
  const { isAuthenticated } = useSelector((s) => s.auth);

  /**
   * Session restoration on app boot.
   * If an access_token is in localStorage, try to fetch the user profile.
   * The Axios interceptor will attempt a token refresh if the access token
   * has expired, then redirect to /login if that also fails.
   */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token && !isAuthenticated) {
      dispatch(fetchCurrentUser());
    } else {
      // No token stored — mark initialisation as done so the spinner stops
      // We do this by dispatching fetchCurrentUser anyway; it will reject
      // cleanly and the rejected handler sets isInitialising=false
      dispatch(fetchCurrentUser());
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <BrowserRouter>

      {/*
        react-hot-toast renders toasts here.
        Position: top-right, styled to match our dark theme.
      */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background:   "var(--surface-2)",
            color:        "var(--text)",
            borderRadius: "var(--radius)",
            border:       "1px solid var(--border)",
            fontSize:     "0.875rem",
          },
          success: { iconTheme: { primary: "var(--green)",  secondary: "var(--surface-2)" } },
          error:   { iconTheme: { primary: "var(--red)",    secondary: "var(--surface-2)" } },
        }}
      />

      <Routes>

        {/* ── Public routes ─────────────────────────────────────────────── */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ── Protected routes ──────────────────────────────────────────── */}
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>

            {/* Root → role-based redirect */}
            <Route index element={<RootRedirect />} />

            {/* ── Clerk section ────────────────────────────────────────── */}
            <Route element={<RequireRole allowedRoles={["clerk", "admin", "merchant"]} />}>
              <Route path="clerk">
                <Route index            element={<ClerkDashboard />} />
                <Route path="inventory" element={<InventoryPage />} />
                <Route path="supply"    element={<SupplyPage />} />
              </Route>
            </Route>

            {/* ── Admin section ────────────────────────────────────────── */}
            <Route element={<RequireRole allowedRoles={["admin", "merchant"]} />}>
              <Route path="admin">
                <Route index          element={<AdminDashboard />} />
                <Route path="reports" element={<AdminReportsPage />} />
                <Route path="payment" element={<PaymentPage />} />
                <Route path="users"   element={<UsersPage />} />
              </Route>
            </Route>

            {/* ── Merchant section ─────────────────────────────────────── */}
            <Route element={<RequireRole allowedRoles={["merchant"]} />}>
              <Route path="merchant">
                <Route index             element={<MerchantDashboard />} />
                <Route path="stores/:id" element={<StoreReportPage />} />
              </Route>
            </Route>

          </Route>
        </Route>

        {/* Catch-all → root redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}