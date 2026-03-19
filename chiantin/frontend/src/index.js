// Apply WebView compatibility polyfills FIRST, before anything else
import { initWebViewCompatibility } from "@/utils/webview-compat";
initWebViewCompatibility();

// Now import React and the rest of the app
import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";
import { AppProvider } from "@/contexts/AppContext";

// Render the app
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </React.StrictMode>,
);
