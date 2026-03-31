// src/utils/api.js
// ─────────────────
// Centralised Axios instance for all HTTP calls to the Flask backend.
//
// What this file does
// ───────────────────
// 1. Creates an Axios instance pre-configured with the API base URL.
// 2. REQUEST interceptor  — attaches the stored JWT access token to every
//    outgoing request as an Authorization header.
// 3. RESPONSE interceptor — when the server returns 401 (token expired),
//    silently attempts a token refresh using the stored refresh token.
//    If the refresh succeeds, the original request is retried with the
//    new access token — the calling code never knows this happened.
//    If the refresh fails (refresh token also expired), the user is logged
//    out and redirected to /login.
//
// Why centralise this?
// ────────────────────
// Without this file every component would need to manually add auth headers
// and handle token expiry.  By doing it once here, all other code just calls
// api.get() / api.post() and gets authentication for free.

import axios from "axios";

// Base URL — during development the package.json "proxy" field forwards
// /api/* requests to http://localhost:5000, so we only need "/api" here.
// In production REACT_APP_API_URL should be set to the deployed API origin.
const BASE_URL = process.env.REACT_APP_API_URL || "/api";

// ── Create the Axios instance ──────────────────────────────────────────────
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor ────────────────────────────────────────────────────
// Runs before EVERY outgoing request.
// Reads the stored access token and attaches it as a Bearer token.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor — silent token refresh ────────────────────────────
// Runs after EVERY response.
//
// Normal case (not 401):  pass the response straight through unchanged.
// 401 case:  the access token has expired.  We:
//   1. Pause the failed request.
//   2. Call /api/auth/refresh using the stored refresh token.
//   3. Store the new access token.
//   4. Retry the original request with the new token.
//   5. If refresh itself fails → clear tokens and redirect to /login.
//
// isRefreshing and refreshSubscribers handle the case where MULTIPLE requests
// fail at the same time with 401.  Without this guard each of them would try
// to refresh simultaneously, causing race conditions.  Instead, only the
// first failure triggers a refresh; all others queue up and wait.

let isRefreshing  = false;     // true while a refresh call is in-flight
let refreshQueue  = [];        // callbacks waiting for the new token

/** Call every queued callback with the new token, then empty the queue. */
function drainQueue(newToken) {
  refreshQueue.forEach((cb) => cb(newToken));
  refreshQueue = [];
}

api.interceptors.response.use(
  // Pass successful (non-error) responses straight through
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    // Only intercept 401 responses that haven't already been retried
    // (_retry flag prevents infinite loops if /refresh itself returns 401)
    if (error.response?.status === 401 && !originalRequest._retry) {

      if (isRefreshing) {
        // Another refresh is already in-flight — queue this request.
        // When the refresh completes, drainQueue() will call our callback
        // with the new token and we'll retry the original request.
        return new Promise((resolve) => {
          refreshQueue.push((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(api(originalRequest));
          });
        });
      }

      // Mark this request as retried and start the refresh
      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        // No refresh token stored — can't recover, force re-login
        clearAuthAndRedirect();
        return Promise.reject(error);
      }

      try {
        // Call /refresh directly with axios (not our api instance) to avoid
        // triggering this interceptor again
        const { data } = await axios.post(
          `${BASE_URL}/auth/refresh`,
          null,
          { headers: { Authorization: `Bearer ${refreshToken}` } }
        );

        const newAccessToken = data.access_token;

        // Persist the new access token
        localStorage.setItem("access_token", newAccessToken);

        // Wake up all queued requests with the new token
        drainQueue(newAccessToken);
        isRefreshing = false;

        // Retry the original request that triggered the 401
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);

      } catch (refreshError) {
        // Refresh itself failed (refresh token expired or revoked)
        isRefreshing = false;
        refreshQueue = [];
        clearAuthAndRedirect();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Remove stored tokens and redirect the user to the login page.
 * Called when both the access token AND the refresh token are invalid.
 */
function clearAuthAndRedirect() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  // window.location causes a full page reload which also resets Redux state
  window.location.href = "/login";
}

export default api;