/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts (visualización de datos, Bloque A) suma ~250 KB al bundle — un coste aceptado
    // para los gráficos de reportes. Se sube el umbral del aviso para que `vite build` quede
    // limpio; si el bundle creciera mucho más, code-split de la ruta de gráficos.
    chunkSizeWarningLimit: 900,
  },
  test: {
    // Excepción puntual al Principio III (US12): sólo pruebas de COMPORTAMIENTO de componentes
    // con lógica de estado (el fallback imagen <-> ícono de `ImagenProducto`). No pruebas de
    // maquetación ni de estilos.
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/configuracion.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: true,
  },
});
