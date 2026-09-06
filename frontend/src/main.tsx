import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { iniciarColaOffline } from "./servicios/colaOffline";

// US8: al volver la conectividad, lo trabajado offline sube en orden de marca de origen.
iniciarColaOffline();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
