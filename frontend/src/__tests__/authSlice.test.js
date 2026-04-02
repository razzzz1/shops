// src/__tests__/authSlice.test.js
// ────────────────────────────────
// Unit tests for the Redux auth slice.
//
// We test the REDUCERS (pure functions) directly — no network calls needed.
// The pattern for each test:
//   1. Build an initial state
//   2. Call the reducer with an action
//   3. Assert the returned state matches expectations
//
// Async thunks are tested by dispatching the .pending / .fulfilled / .rejected
// action creators directly, which avoids mocking the network.

import authReducer, {
    clearError,
    updateUser,
    loginUser,
    logoutUser,
    fetchCurrentUser,
    verifyInviteToken,
    registerUser,
  } from "../store/slices/authSlice";
  
  // ── Shared initial state ───────────────────────────────────────────────────
  const initialState = {
    user:            null,
    isAuthenticated: false,
    isInitialising:  true,
    loading:         false,
    error:           null,
    inviteData:      null,
  };
  
  // ── Helper: build a realistic user object ─────────────────────────────────
  const mockUser = (overrides = {}) => ({
    id:         1,
    email:      "clerk@test.com",
    first_name: "Test",
    last_name:  "Clerk",
    role:       "clerk",
    is_active:  true,
    store_id:   1,
    ...overrides,
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Synchronous reducers
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — synchronous reducers", () => {
  
    test("initial state has the correct shape", () => {
      const state = authReducer(undefined, { type: "@@INIT" });
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isInitialising).toBe(true);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.inviteData).toBeNull();
    });
  
    test("clearError sets error to null", () => {
      const state = { ...initialState, error: "Something went wrong." };
      const next  = authReducer(state, clearError());
      expect(next.error).toBeNull();
    });
  
    test("clearError does not affect other state fields", () => {
      const state = { ...initialState, error: "err", loading: true };
      const next  = authReducer(state, clearError());
      expect(next.loading).toBe(true);  // unchanged
    });
  
    test("updateUser merges new fields into user", () => {
      const state = {
        ...initialState,
        user: mockUser(),
      };
      const next = authReducer(state, updateUser({ first_name: "Updated" }));
      expect(next.user.first_name).toBe("Updated");
      expect(next.user.last_name).toBe("Clerk");  // unchanged
      expect(next.user.email).toBe("clerk@test.com");  // unchanged
    });
  
    test("updateUser with no user in state does not crash", () => {
      const next = authReducer(initialState, updateUser({ first_name: "Ghost" }));
      // user was null — merging into null should produce the patch object
      expect(next.user).toMatchObject({ first_name: "Ghost" });
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // loginUser thunk state transitions
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — loginUser", () => {
  
    test("pending: sets loading=true, clears error", () => {
      const state = { ...initialState, error: "old error" };
      const next  = authReducer(state, { type: loginUser.pending.type });
      expect(next.loading).toBe(true);
      expect(next.error).toBeNull();
    });
  
    test("fulfilled: sets user, isAuthenticated=true, loading=false", () => {
      const user    = mockUser();
      const action  = {
        type:    loginUser.fulfilled.type,
        payload: { user, access_token: "tok", refresh_token: "rtok" },
      };
      const next = authReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.isAuthenticated).toBe(true);
      expect(next.user).toEqual(user);
    });
  
    test("rejected: sets error message, loading=false", () => {
      const action = {
        type:    loginUser.rejected.type,
        payload: "Invalid email or password.",
      };
      const next = authReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.error).toBe("Invalid email or password.");
      expect(next.isAuthenticated).toBe(false);
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // logoutUser thunk state transitions
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — logoutUser", () => {
  
    test("fulfilled: clears user, isAuthenticated, inviteData, error", () => {
      const loggedInState = {
        ...initialState,
        user:            mockUser(),
        isAuthenticated: true,
        inviteData:      { email: "x@x.com", role: "clerk" },
        error:           "stale error",
      };
      const next = authReducer(
        loggedInState,
        { type: logoutUser.fulfilled.type }
      );
      expect(next.user).toBeNull();
      expect(next.isAuthenticated).toBe(false);
      expect(next.inviteData).toBeNull();
      expect(next.error).toBeNull();
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // fetchCurrentUser thunk state transitions
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — fetchCurrentUser", () => {
  
    test("pending: sets isInitialising=true", () => {
      const state = { ...initialState, isInitialising: false };
      const next  = authReducer(state, { type: fetchCurrentUser.pending.type });
      expect(next.isInitialising).toBe(true);
    });
  
    test("fulfilled: sets user, isAuthenticated=true, isInitialising=false", () => {
      const user   = mockUser({ role: "admin" });
      const action = { type: fetchCurrentUser.fulfilled.type, payload: user };
      const next   = authReducer(initialState, action);
      expect(next.isInitialising).toBe(false);
      expect(next.isAuthenticated).toBe(true);
      expect(next.user.role).toBe("admin");
    });
  
    test("rejected: clears user, isAuthenticated=false, isInitialising=false", () => {
      const loggedInState = {
        ...initialState,
        user:            mockUser(),
        isAuthenticated: true,
      };
      const next = authReducer(
        loggedInState,
        { type: fetchCurrentUser.rejected.type }
      );
      expect(next.isInitialising).toBe(false);
      expect(next.user).toBeNull();
      expect(next.isAuthenticated).toBe(false);
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // verifyInviteToken thunk state transitions
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — verifyInviteToken", () => {
  
    test("pending: sets loading=true, clears error and inviteData", () => {
      const state = {
        ...initialState,
        error:      "old",
        inviteData: { email: "x@x.com" },
      };
      const next = authReducer(state, { type: verifyInviteToken.pending.type });
      expect(next.loading).toBe(true);
      expect(next.error).toBeNull();
      expect(next.inviteData).toBeNull();
    });
  
    test("fulfilled: stores inviteData, loading=false", () => {
      const payload = { valid: true, email: "new@test.com", role: "clerk", store_id: 2 };
      const action  = { type: verifyInviteToken.fulfilled.type, payload };
      const next    = authReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.inviteData).toEqual(payload);
    });
  
    test("rejected: sets error, clears inviteData", () => {
      const action = {
        type:    verifyInviteToken.rejected.type,
        payload: "Token has expired.",
      };
      const next = authReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.error).toBe("Token has expired.");
      expect(next.inviteData).toBeNull();
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // registerUser thunk state transitions
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("authSlice — registerUser", () => {
  
    test("pending: loading=true, clears error", () => {
      const next = authReducer(
        { ...initialState, error: "old" },
        { type: registerUser.pending.type }
      );
      expect(next.loading).toBe(true);
      expect(next.error).toBeNull();
    });
  
    test("fulfilled: sets user and isAuthenticated=true", () => {
      const user   = mockUser({ role: "admin" });
      const action = {
        type:    registerUser.fulfilled.type,
        payload: { user, access_token: "tok", refresh_token: "rtok" },
      };
      const next = authReducer(initialState, action);
      expect(next.isAuthenticated).toBe(true);
      expect(next.user).toEqual(user);
      expect(next.loading).toBe(false);
    });
  
    test("rejected: sets error message", () => {
      const action = {
        type:    registerUser.rejected.type,
        payload: "Registration failed.",
      };
      const next = authReducer(initialState, action);
      expect(next.error).toBe("Registration failed.");
      expect(next.isAuthenticated).toBe(false);
    });
  
  });