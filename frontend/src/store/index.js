// src/store/index.js
// ───────────────────
// Configures and exports the Redux store.
//
// What is Redux Toolkit's configureStore?
// ────────────────────────────────────────
// It's a wrapper around Redux's createStore that automatically:
//   • Combines our reducer slices into a root reducer
//   • Adds the Redux DevTools browser extension (in development builds only)
//   • Adds thunk middleware (needed for our async action creators)
//   • Adds checks for accidental state mutations (development only)
//
// Adding a new slice:
//   1. Create your slice file in src/store/slices/
//   2. Import the reducer here and add it to the reducer map

import { configureStore } from "@reduxjs/toolkit";
import authReducer      from "./slices/authSlice";
import inventoryReducer from "./slices/inventorySlice";

const store = configureStore({
  reducer: {
    // auth slice — user session, tokens, invite flow
    auth:      authReducer,

    // inventory slice — entries, products, supply requests, reports
    inventory: inventoryReducer,
  },
});

export default store;