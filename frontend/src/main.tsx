import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { SearchLabPage } from "./pages/SearchLabPage";
import { DemoConfigurationPage } from "./pages/DemoConfigurationPage";
import "./styles.css";

const isConfigurationView =
  new URLSearchParams(window.location.search).get("view") === "configuration";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {isConfigurationView ? <DemoConfigurationPage /> : <SearchLabPage />}
  </StrictMode>,
);
