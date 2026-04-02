// src/__tests__/inventorySlice.test.js
// ──────────────────────────────────────
// Unit tests for the Redux inventory slice.
//
// Tests cover state transitions for:
//   • Inventory entries (fetch, create, update, updatePayment, delete)
//   • Products (fetch, create, update)
//   • Supply requests (fetch, create, action)
//   • Reports (summary, weekly, monthly, annual)
//   • Utility reducers (clearInventoryError, clearReports)

import inventoryReducer, {
    clearInventoryError,
    clearReports,
    fetchEntries,
    createEntry,
    updateEntry,
    updatePaymentStatus,
    deleteEntry,
    fetchProducts,
    createProduct,
    updateProduct,
    fetchSupplyRequests,
    createSupplyRequest,
    actionSupplyRequest,
    fetchSummary,
    fetchWeeklyReport,
    fetchMonthlyReport,
    fetchAnnualReport,
  } from "../store/slices/inventorySlice";
  
  // ── Initial state ──────────────────────────────────────────────────────────
  const initialState = {
    entries:        [],
    products:       [],
    supplyRequests: [],
    summary:        null,
    weeklyReport:   null,
    monthlyReport:  null,
    annualReport:   null,
    paymentReport:  null,
    productReport:  null,
    loading:        false,
    error:          null,
  };
  
  // ── Fixtures ───────────────────────────────────────────────────────────────
  const mockEntry = (overrides = {}) => ({
    id: 1, store_id: 1, product_id: 10, clerk_id: 5,
    quantity_received: 100, quantity_in_stock: 90, quantity_spoilt: 10,
    buying_price: 50, selling_price: 80,
    payment_status: "unpaid", entry_date: "2024-06-01",
    product: { id: 10, name: "Milk 1L", sku: "MLK-001" },
    clerk:   { id: 5,  first_name: "Jane", last_name: "Doe" },
    ...overrides,
  });
  
  const mockProduct = (overrides = {}) => ({
    id: 10, store_id: 1, name: "Milk 1L", sku: "MLK-001",
    buying_price: 50, selling_price: 80, is_active: true,
    ...overrides,
  });
  
  const mockSupplyRequest = (overrides = {}) => ({
    id: 1, store_id: 1, product_id: 10, clerk_id: 5,
    quantity_requested: 200, status: "pending", reason: "Low stock",
    product: { id: 10, name: "Milk 1L" },
    clerk:   { id: 5, first_name: "Jane", last_name: "Doe" },
    ...overrides,
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Utility reducers
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("inventorySlice — utility reducers", () => {
  
    test("clearInventoryError sets error to null", () => {
      const state = { ...initialState, error: "Something failed." };
      const next  = inventoryReducer(state, clearInventoryError());
      expect(next.error).toBeNull();
    });
  
    test("clearReports nulls all report fields", () => {
      const state = {
        ...initialState,
        summary:       { total_received: 100 },
        weeklyReport:  { data: [] },
        monthlyReport: { data: [] },
        annualReport:  { data: [] },
        paymentReport: { paid: {}, unpaid: {} },
        productReport: { entries: [] },
      };
      const next = inventoryReducer(state, clearReports());
      expect(next.summary).toBeNull();
      expect(next.weeklyReport).toBeNull();
      expect(next.monthlyReport).toBeNull();
      expect(next.annualReport).toBeNull();
      expect(next.paymentReport).toBeNull();
      expect(next.productReport).toBeNull();
      // Lists should be unchanged
      expect(next.entries).toEqual([]);
    });
  
    test("initial state has correct shape", () => {
      const state = inventoryReducer(undefined, { type: "@@INIT" });
      expect(state.entries).toEqual([]);
      expect(state.products).toEqual([]);
      expect(state.supplyRequests).toEqual([]);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Inventory entries
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("inventorySlice — inventory entries", () => {
  
    test("fetchEntries.pending: loading=true, clears error", () => {
      const state = { ...initialState, error: "old" };
      const next  = inventoryReducer(state, { type: fetchEntries.pending.type });
      expect(next.loading).toBe(true);
      expect(next.error).toBeNull();
    });
  
    test("fetchEntries.fulfilled: populates entries, loading=false", () => {
      const action = { type: fetchEntries.fulfilled.type, payload: [mockEntry()] };
      const next   = inventoryReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.entries).toHaveLength(1);
      expect(next.entries[0].id).toBe(1);
    });
  
    test("fetchEntries.rejected: sets error", () => {
      const action = { type: fetchEntries.rejected.type, payload: "Network error." };
      const next   = inventoryReducer(initialState, action);
      expect(next.loading).toBe(false);
      expect(next.error).toBe("Network error.");
    });
  
    test("createEntry.fulfilled: prepends new entry to list", () => {
      const state   = { ...initialState, entries: [mockEntry({ id: 99 })] };
      const newEntry = mockEntry({ id: 2, quantity_received: 50 });
      const action  = { type: createEntry.fulfilled.type, payload: newEntry };
      const next    = inventoryReducer(state, action);
      expect(next.entries[0].id).toBe(2);  // new entry is first (unshift)
      expect(next.entries).toHaveLength(2);
    });
  
    test("updateEntry.fulfilled: replaces the matching entry in-place", () => {
      const state = {
        ...initialState,
        entries: [mockEntry(), mockEntry({ id: 2, quantity_received: 50 })],
      };
      const updated = mockEntry({ quantity_received: 150 });  // same id=1
      const action  = { type: updateEntry.fulfilled.type, payload: updated };
      const next    = inventoryReducer(state, action);
      const found   = next.entries.find((e) => e.id === 1);
      expect(found.quantity_received).toBe(150);
      expect(next.entries).toHaveLength(2);  // count unchanged
    });
  
    test("updateEntry.fulfilled: does nothing if id not found", () => {
      const state  = { ...initialState, entries: [mockEntry({ id: 1 })] };
      const action = { type: updateEntry.fulfilled.type, payload: mockEntry({ id: 999 }) };
      const next   = inventoryReducer(state, action);
      expect(next.entries).toHaveLength(1);
      expect(next.entries[0].id).toBe(1);  // original unchanged
    });
  
    test("updatePaymentStatus.fulfilled: updates payment_status field", () => {
      const state  = { ...initialState, entries: [mockEntry({ payment_status: "unpaid" })] };
      const paid   = mockEntry({ payment_status: "paid" });
      const action = { type: updatePaymentStatus.fulfilled.type, payload: paid };
      const next   = inventoryReducer(state, action);
      expect(next.entries[0].payment_status).toBe("paid");
    });
  
    test("deleteEntry.fulfilled: removes entry by id", () => {
      const state  = {
        ...initialState,
        entries: [mockEntry({ id: 1 }), mockEntry({ id: 2 })],
      };
      const action = { type: deleteEntry.fulfilled.type, payload: 1 };  // id to remove
      const next   = inventoryReducer(state, action);
      expect(next.entries).toHaveLength(1);
      expect(next.entries[0].id).toBe(2);
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Products
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("inventorySlice — products", () => {
  
    test("fetchProducts.fulfilled: populates products", () => {
      const action = { type: fetchProducts.fulfilled.type, payload: [mockProduct()] };
      const next   = inventoryReducer(initialState, action);
      expect(next.products).toHaveLength(1);
      expect(next.products[0].name).toBe("Milk 1L");
    });
  
    test("createProduct.fulfilled: appends new product", () => {
      const state  = { ...initialState, products: [mockProduct({ id: 10 })] };
      const newProd = mockProduct({ id: 20, name: "Bread 700g" });
      const action = { type: createProduct.fulfilled.type, payload: newProd };
      const next   = inventoryReducer(state, action);
      expect(next.products).toHaveLength(2);
      expect(next.products[1].name).toBe("Bread 700g");
    });
  
    test("updateProduct.fulfilled: replaces matching product", () => {
      const state  = { ...initialState, products: [mockProduct({ id: 10, name: "Old Name" })] };
      const updated = mockProduct({ id: 10, name: "New Name" });
      const action = { type: updateProduct.fulfilled.type, payload: updated };
      const next   = inventoryReducer(state, action);
      expect(next.products[0].name).toBe("New Name");
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Supply requests
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("inventorySlice — supply requests", () => {
  
    test("fetchSupplyRequests.fulfilled: populates list", () => {
      const action = {
        type:    fetchSupplyRequests.fulfilled.type,
        payload: [mockSupplyRequest()],
      };
      const next = inventoryReducer(initialState, action);
      expect(next.supplyRequests).toHaveLength(1);
      expect(next.supplyRequests[0].status).toBe("pending");
    });
  
    test("createSupplyRequest.fulfilled: prepends new request", () => {
      const state   = { ...initialState, supplyRequests: [mockSupplyRequest({ id: 1 })] };
      const newReq  = mockSupplyRequest({ id: 2, quantity_requested: 50 });
      const action  = { type: createSupplyRequest.fulfilled.type, payload: newReq };
      const next    = inventoryReducer(state, action);
      expect(next.supplyRequests[0].id).toBe(2);  // prepended
      expect(next.supplyRequests).toHaveLength(2);
    });
  
    test("actionSupplyRequest.fulfilled: updates status to approved", () => {
      const state    = { ...initialState, supplyRequests: [mockSupplyRequest({ id: 1 })] };
      const approved = mockSupplyRequest({ id: 1, status: "approved", admin_note: "OK" });
      const action   = { type: actionSupplyRequest.fulfilled.type, payload: approved };
      const next     = inventoryReducer(state, action);
      expect(next.supplyRequests[0].status).toBe("approved");
      expect(next.supplyRequests[0].admin_note).toBe("OK");
    });
  
    test("actionSupplyRequest.fulfilled: updates status to declined", () => {
      const state    = { ...initialState, supplyRequests: [mockSupplyRequest({ id: 1 })] };
      const declined = mockSupplyRequest({ id: 1, status: "declined", admin_note: "Budget" });
      const action   = { type: actionSupplyRequest.fulfilled.type, payload: declined };
      const next     = inventoryReducer(state, action);
      expect(next.supplyRequests[0].status).toBe("declined");
    });
  
  });
  
  
  // ═════════════════════════════════════════════════════════════════════════════
  // Reports
  // ═════════════════════════════════════════════════════════════════════════════
  
  describe("inventorySlice — reports", () => {
  
    test("fetchSummary.fulfilled: stores summary", () => {
      const payload = {
        total_received: 500, total_in_stock: 450, total_spoilt: 50,
        paid_cost: 25000, unpaid_cost: 5000, revenue_potential: 36000,
      };
      const action = { type: fetchSummary.fulfilled.type, payload };
      const next   = inventoryReducer(initialState, action);
      expect(next.summary.total_received).toBe(500);
      expect(next.summary.paid_cost).toBe(25000);
    });
  
    test("fetchWeeklyReport.fulfilled: stores weekly data", () => {
      const payload = {
        period: "weekly",
        start: "2024-06-01",
        end:   "2024-06-07",
        data:  [{ date: "2024-06-01", received: 10, in_stock: 9, spoilt: 1, paid_cost: 500, unpaid_cost: 0 }],
      };
      const action = { type: fetchWeeklyReport.fulfilled.type, payload };
      const next   = inventoryReducer(initialState, action);
      expect(next.weeklyReport.data).toHaveLength(1);
      expect(next.weeklyReport.data[0].received).toBe(10);
    });
  
    test("fetchMonthlyReport.fulfilled: stores monthly data", () => {
      const payload = { period: "monthly", year: 2024, month: 6, data: [] };
      const action  = { type: fetchMonthlyReport.fulfilled.type, payload };
      const next    = inventoryReducer(initialState, action);
      expect(next.monthlyReport.month).toBe(6);
    });
  
    test("fetchAnnualReport.fulfilled: stores 12 monthly data points", () => {
      const data   = Array.from({ length: 12 }, (_, i) => ({
        month: i + 1, label: "Jan", received: 0, in_stock: 0,
        spoilt: 0, paid_cost: 0, unpaid_cost: 0,
      }));
      const action = { type: fetchAnnualReport.fulfilled.type, payload: { year: 2024, data } };
      const next   = inventoryReducer(initialState, action);
      expect(next.annualReport.data).toHaveLength(12);
    });
  
    test("fetchSummary.pending: sets loading=true", () => {
      const next = inventoryReducer(initialState, { type: fetchSummary.pending.type });
      expect(next.loading).toBe(true);
    });
  
    test("fetchSummary.rejected: sets error", () => {
      const action = { type: fetchSummary.rejected.type, payload: "Failed." };
      const next   = inventoryReducer(initialState, action);
      expect(next.error).toBe("Failed.");
      expect(next.loading).toBe(false);
    });
  
  });