// src/store/slices/authSlice.js
// ──────────────────────────────
// Redux Toolkit slice that owns all authentication state.
//
// State shape
// ───────────
// {
//   user:            object | null   — the logged-in user (null when logged out)
//   isAuthenticated: boolean         — true once we have a valid user
//   isInitialising:  boolean         — true while we're restoring a stored session
//   loading:         boolean         — true while an async action is in-flight
//   error:           string | null   — last error message (cleared on new actions)
//   inviteData:      object | null   — decoded invitation token metadata
// }
//
// Async thunks
// ────────────
// Each thunk wraps one API call.  They follow the same pattern:
//   pending   → set loading = true,  clear error
//   fulfilled → set loading = false, update state with response data
//   rejected  → set loading = false, set error = server message

import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../../utils/api";


// ═════════════════════════════════════════════════════════════════════════════
// Async thunks
// ═════════════════════════════════════════════════════════════════════════════

/**
 * loginUser — POST /api/auth/login
 *
 * On success the tokens are written to localStorage so they survive
 * a page reload.  The user object is stored in Redux state.
 */
export const loginUser = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/auth/login", { email, password });

      // Persist tokens outside Redux — the Axios interceptor reads them
      localStorage.setItem("access_token",  data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      return data; // { access_token, refresh_token, user }
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || "Login failed. Please try again."
      );
    }
  }
);

/**
 * logoutUser — POST /api/auth/logout
 *
 * Tells the server about the logout (informational — JWTs are stateless),
 * then clears tokens from localStorage regardless of server response.
 */
export const logoutUser = createAsyncThunk(
  "auth/logout",
  async (_, { rejectWithValue }) => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Even if the server call fails, we still clear local tokens
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }
);

/**
 * fetchCurrentUser — GET /api/users/me
 *
 * Called on app startup.  If a token exists in localStorage we fetch
 * the user profile to restore the session without re-asking for a password.
 * If this fails (token expired and refresh also fails), the interceptor
 * handles the redirect to /login automatically.
 */
export const fetchCurrentUser = createAsyncThunk(
  "auth/fetchCurrentUser",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get("/users/me");
      return data; // user object
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || "Session expired."
      );
    }
  }
);

/**
 * verifyInviteToken — GET /api/auth/verify-invite?token=...
 *
 * Called when the user lands on /register?token=...
 * Validates the token and returns the encoded email, role, and store.
 */
export const verifyInviteToken = createAsyncThunk(
  "auth/verifyInviteToken",
  async (token, { rejectWithValue }) => {
    try {
      const { data } = await api.get(`/auth/verify-invite?token=${token}`);
      return data; // { valid, email, role, store_id }
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || "Invalid invitation link."
      );
    }
  }
);

/**
 * registerUser — POST /api/auth/register
 *
 * Completes registration from an invitation link.
 * On success the user is logged in immediately.
 */
export const registerUser = createAsyncThunk(
  "auth/register",
  async ({ token, first_name, last_name, password }, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/auth/register", {
        token, first_name, last_name, password,
      });

      localStorage.setItem("access_token",  data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      return data; // { access_token, refresh_token, user }
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || "Registration failed."
      );
    }
  }
);

/**
 * sendInvitation — POST /api/auth/invite
 *
 * Merchant or admin sends an invitation email to a new user.
 */
export const sendInvitation = createAsyncThunk(
  "auth/sendInvitation",
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/auth/invite", payload);
      return data;
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.message || "Failed to send invitation."
      );
    }
  }
);


// ═════════════════════════════════════════════════════════════════════════════
// Slice
// ═════════════════════════════════════════════════════════════════════════════

const initialState = {
  user:            null,
  isAuthenticated: false,
  isInitialising:  true,   // true until first fetchCurrentUser settles
  loading:         false,
  error:           null,
  inviteData:      null,   // populated after verifyInviteToken succeeds
};

const authSlice = createSlice({
  name: "auth",
  initialState,

  reducers: {
    // Call this when the user starts typing in a form to clear stale errors
    clearError(state) {
      state.error = null;
    },

    // Call this to update the cached user object after a profile edit
    updateUser(state, action) {
      state.user = { ...state.user, ...action.payload };
    },
  },

  extraReducers: (builder) => {

    // ── loginUser ────────────────────────────────────────────────────────────
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error   = null;
      })
      .addCase(loginUser.fulfilled, (state, { payload }) => {
        state.loading        = false;
        state.user           = payload.user;
        state.isAuthenticated = true;
      })
      .addCase(loginUser.rejected, (state, { payload }) => {
        state.loading = false;
        state.error   = payload;
      });

    // ── logoutUser ───────────────────────────────────────────────────────────
    builder
      .addCase(logoutUser.fulfilled, (state) => {
        state.user            = null;
        state.isAuthenticated = false;
        state.inviteData      = null;
        state.error           = null;
      });

    // ── fetchCurrentUser ─────────────────────────────────────────────────────
    builder
      .addCase(fetchCurrentUser.pending, (state) => {
        state.isInitialising = true;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, { payload }) => {
        state.isInitialising  = false;
        state.loading         = false;
        state.user            = payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        // Token was invalid / expired — treat as logged out
        state.isInitialising  = false;
        state.user            = null;
        state.isAuthenticated = false;
      });

    // ── verifyInviteToken ────────────────────────────────────────────────────
    builder
      .addCase(verifyInviteToken.pending, (state) => {
        state.loading    = true;
        state.error      = null;
        state.inviteData = null;
      })
      .addCase(verifyInviteToken.fulfilled, (state, { payload }) => {
        state.loading    = false;
        state.inviteData = payload; // { email, role, store_id }
      })
      .addCase(verifyInviteToken.rejected, (state, { payload }) => {
        state.loading    = false;
        state.error      = payload;
        state.inviteData = null;
      });

    // ── registerUser ─────────────────────────────────────────────────────────
    builder
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error   = null;
      })
      .addCase(registerUser.fulfilled, (state, { payload }) => {
        state.loading         = false;
        state.user            = payload.user;
        state.isAuthenticated = true;
      })
      .addCase(registerUser.rejected, (state, { payload }) => {
        state.loading = false;
        state.error   = payload;
      });

    // ── sendInvitation ───────────────────────────────────────────────────────
    builder
      .addCase(sendInvitation.pending, (state) => {
        state.loading = true;
        state.error   = null;
      })
      .addCase(sendInvitation.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(sendInvitation.rejected, (state, { payload }) => {
        state.loading = false;
        state.error   = payload;
      });
  },
});

export const { clearError, updateUser } = authSlice.actions;
export default authSlice.reducer;