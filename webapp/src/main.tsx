import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { initTelegram } from "./lib/telegram";

// Catch ANY uncaught error so the app at least shows *something*
window.addEventListener("error", (e) => {
  console.error("[GlobalError]", e.message, e.filename, e.lineno, e.colno, e.error);
  document.getElementById("root")!.innerHTML =
    '<div style="padding:24px;color:red;font-family:monospace"><b>App Error:</b><pre>' +
    (e.error?.stack || e.message) + "</pre></div>";
});

window.addEventListener("unhandledrejection", (e) => {
  console.error("[UnhandledRejection]", e.reason);
  document.getElementById("root")!.innerHTML =
    '<div style="padding:24px;color:red;font-family:monospace"><b>App Error:</b><pre>' +
    String(e.reason) + "</pre></div>";
});

try {
  initTelegram();
} catch (err) {
  console.error("[initTelegram] failed:", err);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
