// src/index.js
// ─────────────
// React application entry point.
//
// Responsibilities:
//   1. Mount the React app into the <div id="root"> in public/index.html
//   2. Wrap the app in <Provider> so every component can access the Redux store
//   3. Import global styles (index.css)

import React    from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";

import store from "./store";
import App   from "./App";
import "./index.css";

// Find the root DOM node and create a React root from it.
// ReactDOM.createRoot is the React 18 API — it enables concurrent features
// like automatic batching of state updates.
const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  // StrictMode runs each component twice in development to surface side-effect
  // bugs early.  It has no effect in production builds.
  <React.StrictMode>
    {/*
      Provider makes the Redux store available to every component in the tree.
      Without it, useSelector/useDispatch would throw errors.
    */}
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>
);