import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { SearchLabPage } from "./pages/SearchLabPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SearchLabPage />
  </StrictMode>,
);
