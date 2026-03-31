// src/store/slices/inventorySlice.js
// ────────────────────────────────────
// Redux Toolkit slice that owns all inventory-related state:
//   • Stock entries (InventoryEntry rows)
//   • Products (catalogue)
//   • Supply requests
//   • Report data (weekly, monthly, annual, summary, payment breakdown)
//
// Every thunk follows the same pattern as authSlice — see comments there
// for an explanation of pending/fulfilled/rejected handlers.

import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../../utils/api";


// ═════════════════════════════════════════════════════════════════════════════
// Inventory entry thunks
// ═════════════════════════════════════════════════════════════════════════════

/** Fetch entries with optional filters (?store_id, ?payment_status, etc.) */
export const fetchEntries = createAsyncThunk(
  "inventory/fetchEntries",
  async (params = {}, { rejectWithValue }) => {
    try {
      const { data } = await api.get("/inventory/", { params });
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to load entries.");
    }
  }
);

/** Clerk creates a new stock-taking entry */
export const createEntry = createAsyncThunk(
  "inventory/createEntry",
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/inventory/", payload);
      return data.entry;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to create entry.");
    }
  }
);

/** Partial update on an existing entry */
export const updateEntry = createAsyncThunk(
  "inventory/updateEntry",
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      const { data } = await api.patch(`/inventory/${id}`, payload);
      return data.entry;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to update entry.");
    }
  }
);

/** Admin marks a supplier invoice as paid or unpaid */
export const updatePaymentStatus = createAsyncThunk(
  "inventory/updatePaymentStatus",
  async ({ id, payment_status }, { rejectWithValue }) => {
    try {
      const { data } = await api.patch(`/inventory/${id}/payment`, { payment_status });
      return data.entry;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to update payment.");
    }
  }
);

/** Admin/merchant permanently deletes an entry */
export const deleteEntry = createAsyncThunk(
  "inventory/deleteEntry",
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/inventory/${id}`);
      return id; // return the id so the reducer can remove it from state
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to delete entry.");
    }
  }
);


// ═════════════════════════════════════════════════════════════════════════════
// Product thunks
// ═════════════════════════════════════════════════════════════════════════════

export const fetchProducts = createAsyncThunk(
  "inventory/fetchProducts",
  async (params = {}, { rejectWithValue }) => {
    try {
      const { data } = await api.get("/products/", { params });
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to load products.");
    }
  }
);

export const createProduct = createAsyncThunk(
  "inventory/createProduct",
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/products/", payload);
      return data.product;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to create product.");
    }
  }
);

export const updateProduct = createAsyncThunk(
  "inventory/updateProduct",
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      const { data } = await api.patch(`/products/${id}`, payload);
      return data.product;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to update product.");
    }
  }
);


// ═════════════════════════════════════════════════════════════════════════════
// Supply request thunks
// ═════════════════════════════════════════════════════════════════════════════

export const fetchSupplyRequests = createAsyncThunk(
  "inventory/fetchSupplyRequests",
  async (params = {}, { rejectWithValue }) => {
    try {
      const { data } = await api.get("/supply/", { params });
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to load supply requests.");
    }
  }
);

export const createSupplyRequest = createAsyncThunk(
  "inventory/createSupplyRequest",
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await api.post("/supply/", payload);
      return data.request;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to submit request.");
    }
  }
);

export const actionSupplyRequest = createAsyncThunk(
  "inventory/actionSupplyRequest",
  async ({ id, action, note }, { rejectWithValue }) => {
    try {
      const { data } = await api.patch(`/supply/${id}/action`, { action, note });
      return data.request;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || "Failed to process request.");
    }
  }
);


// ═════════════════════════════════════════════════════════════════════════════
// Report thunks — all follow the same GET pattern
// ═════════════════════════════════════════════════════════════════════════════

const makeReportThunk = (name, endpoint) =>
  createAsyncThunk(`inventory/${name}`, async (params = {}, { rejectWithValue }) => {
    try {
      const { data } = await api.get(endpoint, { params });
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || `Failed to load ${name}.`);
    }
  });

export const fetchSummary       = makeReportThunk("fetchSummary",       "/reports/summary");
export const fetchWeeklyReport  = makeReportThunk("fetchWeeklyReport",  "/reports/weekly");
export const fetchMonthlyReport = makeReportThunk("fetchMonthlyReport", "/reports/monthly");
export const fetchAnnualReport  = makeReportThunk("fetchAnnualReport",  "/reports/annual");
export const fetchPaymentReport = makeReportThunk("fetchPaymentReport", "/reports/payment-status");
export const fetchProductReport = makeReportThunk("fetchProductReport", "/reports/products");


// ═════════════════════════════════════════════════════════════════════════════
// Slice
// ═════════════════════════════════════════════════════════════════════════════

const inventorySlice = createSlice({
  name: "inventory",
  initialState: {
    // Lists
    entries:        [],
    products:       [],
    supplyRequests: [],
    // Reports
    summary:        null,
    weeklyReport:   null,
    monthlyReport:  null,
    annualReport:   null,
    paymentReport:  null,
    productReport:  null,
    // UI state
    loading:        false,
    error:          null,
  },

  reducers: {
    clearInventoryError(state) { state.error = null; },

    // Optimistically clear report data when switching store/period
    // so stale data doesn't flash before new data loads
    clearReports(state) {
      state.summary       = null;
      state.weeklyReport  = null;
      state.monthlyReport = null;
      state.annualReport  = null;
      state.paymentReport = null;
      state.productReport = null;
    },
  },

  extraReducers: (builder) => {

    // Shared pending/rejected handlers — DRY helper
    const onPending  = (state)         => { state.loading = true;  state.error = null; };
    const onRejected = (state, action) => { state.loading = false; state.error = action.payload; };

    // ── Entries ──────────────────────────────────────────────────────────────
    builder
      .addCase(fetchEntries.pending,   onPending)
      .addCase(fetchEntries.fulfilled, (state, { payload }) => {
        state.loading = false;
        state.entries = payload;
      })
      .addCase(fetchEntries.rejected,  onRejected)

      // Prepend new entry so it appears at the top of the list
      .addCase(createEntry.fulfilled, (state, { payload }) => {
        state.entries.unshift(payload);
      })
      .addCase(createEntry.rejected, onRejected)

      // Replace the matching entry in-place
      .addCase(updateEntry.fulfilled, (state, { payload }) => {
        const idx = state.entries.findIndex((e) => e.id === payload.id);
        if (idx !== -1) state.entries[idx] = payload;
      })

      // Same for payment status update
      .addCase(updatePaymentStatus.fulfilled, (state, { payload }) => {
        const idx = state.entries.findIndex((e) => e.id === payload.id);
        if (idx !== -1) state.entries[idx] = payload;
      })

      // Remove deleted entry by id
      .addCase(deleteEntry.fulfilled, (state, { payload: id }) => {
        state.entries = state.entries.filter((e) => e.id !== id);
      });

    // ── Products ─────────────────────────────────────────────────────────────
    builder
      .addCase(fetchProducts.pending,   onPending)
      .addCase(fetchProducts.fulfilled, (state, { payload }) => {
        state.loading  = false;
        state.products = payload;
      })
      .addCase(fetchProducts.rejected,  onRejected)

      .addCase(createProduct.fulfilled, (state, { payload }) => {
        state.products.push(payload);
      })

      .addCase(updateProduct.fulfilled, (state, { payload }) => {
        const idx = state.products.findIndex((p) => p.id === payload.id);
        if (idx !== -1) state.products[idx] = payload;
      });

    // ── Supply requests ───────────────────────────────────────────────────────
    builder
      .addCase(fetchSupplyRequests.pending,   onPending)
      .addCase(fetchSupplyRequests.fulfilled, (state, { payload }) => {
        state.loading        = false;
        state.supplyRequests = payload;
      })
      .addCase(fetchSupplyRequests.rejected,  onRejected)

      .addCase(createSupplyRequest.fulfilled, (state, { payload }) => {
        state.supplyRequests.unshift(payload);
      })

      // Update the resolved request in-place
      .addCase(actionSupplyRequest.fulfilled, (state, { payload }) => {
        const idx = state.supplyRequests.findIndex((r) => r.id === payload.id);
        if (idx !== -1) state.supplyRequests[idx] = payload;
      });

    // ── Reports ───────────────────────────────────────────────────────────────
    builder
      .addCase(fetchSummary.pending,   onPending)
      .addCase(fetchSummary.fulfilled, (state, { payload }) => {
        state.loading = false;
        state.summary = payload;
      })
      .addCase(fetchSummary.rejected, onRejected)

      .addCase(fetchWeeklyReport.fulfilled,  (state, { payload }) => { state.weeklyReport  = payload; })
      .addCase(fetchMonthlyReport.fulfilled, (state, { payload }) => { state.monthlyReport = payload; })
      .addCase(fetchAnnualReport.fulfilled,  (state, { payload }) => { state.annualReport  = payload; })
      .addCase(fetchPaymentReport.fulfilled, (state, { payload }) => { state.paymentReport = payload; })
      .addCase(fetchProductReport.fulfilled, (state, { payload }) => { state.productReport = payload; });
  },
});

export const { clearInventoryError, clearReports } = inventorySlice.actions;
export default inventorySlice.reducer;