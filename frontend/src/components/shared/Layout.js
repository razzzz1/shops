
// src/components/shared/Layout.js
// ──────────────────────────────────
// Persistent app shell rendered for every protected route.
// Contains:
//   • Collapsible sidebar with role-based navigation links
//   • User avatar + name badge
//   • Top bar with page title and store name
//   • <Outlet /> where the active page renders
//
// The sidebar collapses to icon-only mode (64px) when the toggle is clicked,
// giving clerks on smaller screens more working space.

import React, { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  BarChart2,
  CreditCard,
  Users,
  Store,
  LogOut,
  Menu,
  X,
  ChevronRight,
} from "lucide-react";
import toast from "react-hot-toast";

import { logoutUser } from "../../store/slices/authSlice";

// ── Navigation link definitions per role ──────────────────────────────────────
// Each role sees only the links relevant to their responsibilities.
// Admins also get the clerk "Stock Entry" link so they can enter data too.
const NAV_LINKS = {
  clerk: [
    { to: "/clerk",           icon: LayoutDashboard, label: "Dashboard"       },
    { to: "/clerk/inventory", icon: Package,          label: "Inventory"       },
    { to: "/clerk/supply",    icon: ShoppingCart,     label: "Supply Requests" },
  ],
  admin: [
    { to: "/admin",           icon: LayoutDashboard, label: "Dashboard"       },
    { to: "/admin/reports",   icon: BarChart2,        label: "Reports"         },
    { to: "/admin/payment",   icon: CreditCard,       label: "Payments"        },
    { to: "/admin/users",     icon: Users,            label: "Manage Clerks"   },
    { to: "/clerk",           icon: Package,          label: "Stock Entry"     },
  ],
  merchant: [
    { to: "/merchant",        icon: Store,            label: "All Stores"      },
    { to: "/admin",           icon: BarChart2,        label: "Store Reports"   },
    { to: "/admin/payment",   icon: CreditCard,       label: "Payments"        },
    { to: "/admin/users",     icon: Users,            label: "Manage Users"    },
  ],
};

export default function Layout() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((s) => s.auth);

  // Controls whether the sidebar is expanded (240px) or collapsed (64px)
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navLinks = NAV_LINKS[user?.role] || [];

  // ── Logout ────────────────────────────────────────────────────────────────
  async function handleLogout() {
    await dispatch(logoutUser());
    navigate("/login");
    toast.success("Logged out successfully.");
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="layout">

      {/* ── Sidebar ────────────────────────────────────────────────────── */}
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar--collapsed"}`}>

        {/* Brand row */}
        <div className="sidebar__brand">
          {sidebarOpen && (
            <span className="sidebar__brand-text">
              <Package size={18} />
              StockFlow
            </span>
          )}
          <button
            className="sidebar__toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* User badge — hidden when collapsed */}
        {sidebarOpen && user && (
          <div className="sidebar__user">
            <div className="sidebar__avatar">
              {user.first_name?.[0]}{user.last_name?.[0]}
            </div>
            <div className="sidebar__user-info">
              <span className="sidebar__user-name">{user.full_name || `${user.first_name} ${user.last_name}`}</span>
              <span className={`badge badge--${user.role}`}>{user.role}</span>
            </div>
          </div>
        )}

        {/* Navigation links */}
        <nav className="sidebar__nav">
          {navLinks.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              // `end` prevents parent paths matching child routes as active
              end={to.split("/").length === 2}
              className={({ isActive }) =>
                `sidebar__link${isActive ? " sidebar__link--active" : ""}`
              }
              title={!sidebarOpen ? label : undefined}
            >
              <Icon size={18} className="sidebar__link-icon" />
              {sidebarOpen && (
                <>
                  <span className="sidebar__link-label">{label}</span>
                  <ChevronRight size={13} className="sidebar__link-arrow" />
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Logout button pinned to the bottom */}
        <button className="sidebar__logout" onClick={handleLogout}>
          <LogOut size={18} />
          {sidebarOpen && <span>Logout</span>}
        </button>

      </aside>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main className={`main-content${sidebarOpen ? "" : " main-content--collapsed"}`}>

        {/* Top bar */}
        <header className="topbar">
          <span className="topbar__title">Inventory Management System</span>
          {user?.store && (
            <span className="topbar__store">
              <Store size={13} />
              {user.store.name}
            </span>
          )}
        </header>

        {/* Active page renders here */}
        <div className="page-content">
          <Outlet />
        </div>

      </main>
    </div>
  );
}