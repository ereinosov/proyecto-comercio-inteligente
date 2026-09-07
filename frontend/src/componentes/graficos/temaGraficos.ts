/**
 * Tema centralizado de todos los gráficos Recharts del sistema (Bloque A — Reportes y
 * Gráficos). Existe para que ningún gráfico pueda violar DESIGN.md desde su primer render.
 *
 * Reglas que aplica:
 *  - La Regla del Significado: NUNCA el Verde Rasero (#0F5132, exclusivo del botón de cobro).
 *    #1F5673 (Estimado) es el color primario de toda serie de datos. #9A5B08 (Atención) y
 *    #8E2A2A (Crítico) SÓLO cuando el dato mismo representa atención o criticidad —nunca como
 *    paleta decorativa—. Para distinguir varias series sin significado semántico se usan
 *    variaciones de opacidad de #1F5673 y #5A6862, nunca colores nuevos.
 *  - La Regla del Filo: `CartesianGrid` línea sólida fina en Borde (#D5DCD6), sin
 *    `strokeDasharray`. Cero sombras, cero gradientes de relleno.
 *  - Tipografía por registro: los ejes toman `IBM Plex Sans` (Operación) o `Source Serif 4`
 *    (Análisis) según la pantalla contenedora; se pasa `registro` a cada helper.
 */

export type Registro = "operacion" | "analisis";

export const COLOR = {
  /** Serie de datos primaria. */
  serie: "#1F5673",
  /** El dato representa algo que pide atención (margen bajo, cliente en riesgo). */
  atencion: "#9A5B08",
  /** El dato representa una pérdida / criticidad (margen negativo, merma por robo). */
  critico: "#8E2A2A",
  /** Segunda voz neutra, para series sin significado semántico. */
  neutro: "#5A6862",
  eje: "#5A6862",
  grid: "#D5DCD6",
  tinta: "#1B2621",
  superficieAlta: "#FFFFFF",
} as const;

/**
 * Tonos derivados SÓLO de #1F5673 y #5A6862 por opacidad, para gráficos con varias series sin
 * significado semántico (p. ej. mermas por causa). Nunca introducen un color nuevo.
 */
export const SERIES_NEUTRAS: string[] = [
  "#1F5673",
  "rgba(31, 86, 115, 0.62)",
  "#5A6862",
  "rgba(90, 104, 98, 0.62)",
  "rgba(31, 86, 115, 0.38)",
  "rgba(90, 104, 98, 0.38)",
];

export function fontFamily(registro: Registro): string {
  return registro === "analisis"
    ? '"Source Serif 4", Georgia, serif'
    : '"IBM Plex Sans", system-ui, sans-serif';
}

/** Props comunes de `<XAxis>` / `<YAxis>`: tick en Tinta Suave, sin línea de eje gruesa. */
export function ejeProps(registro: Registro) {
  return {
    tick: { fill: COLOR.eje, fontSize: 12, fontFamily: fontFamily(registro) },
    tickLine: false,
    axisLine: { stroke: COLOR.grid },
  } as const;
}

/** Props de `<CartesianGrid>`: línea sólida fina en Borde, nunca punteada. */
export const gridProps = {
  stroke: COLOR.grid,
  strokeDasharray: undefined,
  vertical: false,
} as const;
