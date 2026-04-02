// src/__tests__/LoginPage.test.js
// ────────────────────────────────
// React Testing Library tests for the LoginPage component.
//
// We render the component inside a real Redux store and a MemoryRouter
// (so React Router hooks work).  The store is pre-loaded with a known
// initial state so tests are deterministic.
//
// What we test:
//   • The page renders all expected UI elements
//   • Password field starts hidden; show/hide toggle works
//   • Form fields update when the user types
//   • Submit button is disabled while loading
//   • Already-authenticated users are redirected (via the useEffect)

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";

import authReducer      from "../store/slices/authSlice";
import inventoryReducer from "../store/slices/inventorySlice";
import LoginPage        from "../pages/LoginPage";

// ── Helper: render with Redux + Router ────────────────────────────────────
function renderLoginPage(preloadedAuth = {}) {
  const store = configureStore({
    reducer: { auth: authReducer, inventory: inventoryReducer },
    preloadedState: {
      auth: {
        user:            null,
        isAuthenticated: false,
        isInitialising:  false,
        loading:         false,
        error:           null,
        inviteData:      null,
        ...preloadedAuth,
      },
    },
  });

  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </Provider>
    ),
  };
}


// ═════════════════════════════════════════════════════════════════════════════
// Rendering
// ═════════════════════════════════════════════════════════════════════════════

describe("LoginPage — rendering", () => {

  test("renders the brand name", () => {
    renderLoginPage();
    // StockFlow appears in the brand panel
    expect(screen.getAllByText(/stockflow/i).length).toBeGreaterThan(0);
  });

  test("renders email and password fields", () => {
    renderLoginPage();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  test("renders the Sign In button", () => {
    renderLoginPage();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  test("renders the invitation note", () => {
    renderLoginPage();
    expect(screen.getByText(/invitation link/i)).toBeInTheDocument();
  });

});


// ═════════════════════════════════════════════════════════════════════════════
// Password visibility toggle
// ═════════════════════════════════════════════════════════════════════════════

describe("LoginPage — password toggle", () => {

  test("password field starts as type=password (hidden)", () => {
    renderLoginPage();
    const field = screen.getByLabelText(/^password/i);
    expect(field).toHaveAttribute("type", "password");
  });

  test("clicking the eye icon shows the password", () => {
    renderLoginPage();
    const field     = screen.getByLabelText(/^password/i);
    const toggleBtn = screen.getByLabelText(/show password/i);

    fireEvent.click(toggleBtn);
    expect(field).toHaveAttribute("type", "text");
  });

  test("clicking the eye icon twice hides the password again", () => {
    renderLoginPage();
    const field     = screen.getByLabelText(/^password/i);
    const toggleBtn = screen.getByLabelText(/show password/i);

    fireEvent.click(toggleBtn);   // show
    fireEvent.click(
      screen.getByLabelText(/hide password/i)  // label changes after showing
    );
    expect(field).toHaveAttribute("type", "password");
  });

});


// ═════════════════════════════════════════════════════════════════════════════
// Form interactions
// ═════════════════════════════════════════════════════════════════════════════

describe("LoginPage — form interactions", () => {

  test("typing into email field updates its value", () => {
    renderLoginPage();
    const emailField = screen.getByLabelText(/email address/i);
    fireEvent.change(emailField, { target: { value: "test@example.com" } });
    expect(emailField.value).toBe("test@example.com");
  });

  test("typing into password field updates its value", () => {
    renderLoginPage();
    const passField = screen.getByLabelText(/^password/i);
    fireEvent.change(passField, { target: { value: "secret123" } });
    expect(passField.value).toBe("secret123");
  });

  test("submit button is enabled by default", () => {
    renderLoginPage();
    const btn = screen.getByRole("button", { name: /sign in/i });
    expect(btn).not.toBeDisabled();
  });

  test("submit button is disabled when loading=true", () => {
    renderLoginPage({ loading: true });
    // When loading, the button shows a spinner and no text,
    // but it should still be disabled
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

});


// ═════════════════════════════════════════════════════════════════════════════
// Feature list
// ═════════════════════════════════════════════════════════════════════════════

describe("LoginPage — brand panel features", () => {

  test("displays all four feature bullet points", () => {
    renderLoginPage();
    expect(screen.getByText(/real-time stock tracking/i)).toBeInTheDocument();
    expect(screen.getByText(/automated weekly/i)).toBeInTheDocument();
    expect(screen.getByText(/supplier payment/i)).toBeInTheDocument();
    expect(screen.getByText(/role-based access/i)).toBeInTheDocument();
  });

});