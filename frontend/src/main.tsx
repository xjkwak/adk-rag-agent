import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./global.css";
import App from "./App.tsx";
import { FontSizeProvider } from "@/hooks/use-font-size";
import { ThemeProvider } from "@/hooks/use-theme";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <FontSizeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </FontSizeProvider>
    </ThemeProvider>
  </StrictMode>
);
