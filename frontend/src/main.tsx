import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "@fontsource/instrument-sans/latin-400.css";
import "@fontsource/instrument-sans/latin-500.css";
import "@fontsource/instrument-sans/latin-600.css";
import "@fontsource/instrument-sans/latin-700.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/catalog.css";
import "./styles/job.css";
import "./styles/hljs.css";

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
