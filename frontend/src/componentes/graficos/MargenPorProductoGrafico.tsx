/**
 * US5 de 003-precios-margenes (FR-023..FR-025): resumen visual del margen real por producto,
 * barras horizontales ordenadas de mayor a menor margen. Lectura pura sobre el `margen_calculado`
 * que US1 ya produce — reutiliza el estado ya cargado por `Precios.tsx`, no pide nada nuevo.
 *
 * Color por barra según el MISMO umbral que la lista de Precios (`MARGEN_SALUDABLE = 0.15`):
 * Crítico si el margen es negativo (pérdida), Atención si es bajo, serie neutra en otro caso.
 * Nunca una paleta decorativa (La Regla del Significado).
 */

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import type { MargenProducto } from "../../servicios/precios";
import { GraficoContenedor } from "./GraficoContenedor";
import { TooltipPropio } from "./TooltipPropio";
import { COLOR, ejeProps, gridProps } from "./temaGraficos";

// El mismo umbral que `Precios.tsx` usa para `.bordeBajo` (mantener en sincronía).
const MARGEN_SALUDABLE = 0.15;
const TOP_N = 15;

interface ProductoMin {
  id_producto: number;
  nombre: string;
}

function colorDeMargen(margen: number): string {
  if (margen < 0) return COLOR.critico;
  if (margen < MARGEN_SALUDABLE) return COLOR.atencion;
  return COLOR.serie;
}

interface Props {
  productos: ProductoMin[];
  margenes: Map<number, MargenProducto>;
  cargando?: boolean;
}

export function MargenPorProductoGrafico({ productos, margenes, cargando = false }: Props) {
  const filas = productos
    .map((p) => {
      const m = margenes.get(p.id_producto);
      return m && m.margen !== null && m.confiable
        ? { nombre: p.nombre, margenPct: Math.round(m.margen * 1000) / 10 }
        : null;
    })
    .filter((x): x is { nombre: string; margenPct: number } => x !== null)
    .sort((a, b) => b.margenPct - a.margenPct)
    .slice(0, TOP_N);

  const alto = Math.max(180, filas.length * 26 + 48);

  return (
    <GraficoContenedor
      titulo="Margen real por producto"
      subtitulo={
        filas.length > 0
          ? `Top ${filas.length} por margen · pérdida en Crítico, margen bajo en Atención`
          : undefined
      }
      registro="analisis"
      cargando={cargando}
      vacio={!cargando && filas.length === 0}
      vacioTitulo="Todavía no hay márgenes que graficar"
      vacioDescripcion="Aquí aparecerá el margen real de cada producto en barras ordenadas de mayor a menor, en cuanto haya productos con costo y precio vigentes. La tabla de abajo es el detalle."
      alto={alto}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
          <CartesianGrid {...gridProps} horizontal={false} vertical />
          <XAxis
            type="number"
            unit="%"
            {...ejeProps("analisis")}
          />
          <YAxis
            type="category"
            dataKey="nombre"
            width={140}
            {...ejeProps("analisis")}
          />
          <Tooltip
            cursor={{ fill: "rgba(31, 86, 115, 0.06)" }}
            content={
              <TooltipPropio
                registro="analisis"
                formato={(v) => `${v} %`}
                etiqueta={(l) => String(l ?? "")}
              />
            }
          />
          <Bar dataKey="margenPct" name="Margen" isAnimationActive={false}>
            {filas.map((f, i) => (
              <Cell key={i} fill={colorDeMargen(f.margenPct / 100)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </GraficoContenedor>
  );
}
