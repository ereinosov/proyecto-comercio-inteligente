/**
 * Configuración de la suite de pruebas de componentes (vitest + Testing Library).
 * Excepción puntual al Principio III — ver vite.config.ts.
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
