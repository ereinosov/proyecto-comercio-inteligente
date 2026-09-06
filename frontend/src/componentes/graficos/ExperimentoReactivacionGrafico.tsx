/**
 * US4 de 005-promociones-inteligentes: visual del resultado del experimento de reactivación.
 * Dos barras — retorno observado de control vs. tratamiento — más el texto de la inferencia
 * (z, p, veredicto) con los mismos portadores de forma (▲/▬/◇) que ya usa
 * `ResultadoExperimento.tsx`. Lectura pura del experimento ya calculado; no dispara ni corre
 * nada.
 *
 * Las dos barras NO tienen significado semántico entre sí (ninguna es "buena" o "mala"): mismo
 * color de serie (#1F5673) para ambas, se distinguen por su etiqueta. Nunca verde/rojo (La
 * Regla del Significado).
 *
 * Si la semilla activa da "muestra insuficiente" o el experimento sigue en curso, no hay tasas
 * que graficar: el gráfico muestra ese estado con honestidad, sin forzar un veredicto falso.
 */

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Experimento } from "../../servicios/promociones";
import { GraficoContenedor } from "./GraficoContenedor";
import { TooltipPropio } from "./TooltipPropio";
import { COLOR, ejeProps, gridProps } from "./temaGraficos";

interface Props {
  experimento: Experimento | null;
  cargando?: boolean;
}

export function ExperimentoReactivacionGrafico({ experimento, cargando = false }: Props) {
  const hayTasas =
    experimento?.retorno_control != null && experimento?.retorno_tratamiento != null;

  const filas = hayTasas
    ? [
        {
          grupo: "Control",
          tasa: Math.round(Number(experimento!.retorno_control) * 1000) / 10,
        },
        {
          grupo: "Tratamiento",
          tasa: Math.round(Number(experimento!.retorno_tratamiento) * 1000) / 10,
        },
      ]
    : [];

  const motivoVacio =
    experimento?.veredicto === "muestra_insuficiente"
      ? experimento.motivo_muestra_insuficiente ?? "Muestra insuficiente para medir el retorno."
      : experimento?.veredicto === "en_curso"
        ? "La ventana de medición todavía no ha cerrado; aún no hay tasas de retorno."
        : "Aquí aparecerá el retorno observado de cada grupo cuando el experimento cierre su ventana con muestra suficiente.";

  return (
    <GraficoContenedor
      titulo="Retorno observado: control vs. tratamiento"
      subtitulo={hayTasas ? "Tasa de reactivación (%) de cada grupo · dato observado" : undefined}
      registro="analisis"
      cargando={cargando}
      vacio={!cargando && !hayTasas}
      vacioTitulo={
        experimento?.veredicto === "muestra_insuficiente"
          ? "Muestra insuficiente para graficar"
          : "Sin tasas de retorno todavía"
      }
      vacioDescripcion={motivoVacio}
      alto={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="grupo" {...ejeProps("analisis")} />
          <YAxis unit="%" {...ejeProps("analisis")} width={44} />
          <Tooltip
            cursor={{ fill: "rgba(31, 86, 115, 0.06)" }}
            content={<TooltipPropio registro="analisis" formato={(v) => `${v} %`} />}
          />
          <Bar dataKey="tasa" name="Retorno" fill={COLOR.serie} isAnimationActive={false} maxBarSize={96} />
        </BarChart>
      </ResponsiveContainer>
    </GraficoContenedor>
  );
}
