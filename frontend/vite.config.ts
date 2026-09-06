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
});
