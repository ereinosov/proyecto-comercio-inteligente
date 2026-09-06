/**
 * US6 de 002-clientes-fidelizacion: distribución de la base de clientes por segmento de fuga.
 *
 * `senal_fuga` no guarda un histórico periódico, así que esto es un SNAPSHOT del estado actual
 * (barras por segmento), no una serie temporal — no se inventa histórico que no existe.
 *
 * Colores: los MISMOS que `Clientes.tsx` ya usa en `InsigniaFuga` — `activa` en Atención
 * (#9A5B08), `confirmada` en Crítico (#8E2A2A, sancionado por DESIGN.md para este caso: la
 * anonimización inminente es un acto irreversible), el resto en la voz neutra. Nunca una paleta
 * decorativa.
 */

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorApi } from "../../servicios/clienteHttp";
import { obtenerResumenFuga, type ResumenFuga } from "../../servicios/clientes";
import { GraficoContenedor } from "./GraficoContenedor";
import { TooltipPropio } from "./TooltipPropio";
import { COLOR, ejeProps, gridProps } from "./temaGraficos";

const SEGMENTOS: { clave: keyof ResumenFuga; etiqueta: string; color: string }[] = [
  { clave: "sin_senal", etiqueta: "Sin señal", color: COLOR.neutro },
  { clave: "datos_insuficientes", etiqueta: "Datos insuf.", color: COLOR.neutro },
  { clave: "activa", etiqueta: "En riesgo", color: COLOR.atencion },
  { clave: "confirmada", etiqueta: "Fuga confirmada", color: COLOR.critico },
  { clave: "resuelta", etiqueta: "Resuelta", color: COLOR.neutro },
];

export function FugaPorSegmentoGrafico() {
  const [resumen, setResumen] = useState<ResumenFuga | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setCargando(true);
    setError(false);
    obtenerResumenFuga()
      .then(setResumen)
      .catch((e) => setError(!(e instanceof ErrorApi) || e.status >= 500))
      .finally(() => setCargando(false));
  }, []);

  const filas = resumen
    ? SEGMENTOS.map((s) => ({ etiqueta: s.etiqueta, clientes: resumen[s.clave], color: s.color }))
    : [];
  const total = filas.reduce((acc, f) => acc + f.clientes, 0);

  return (
    <GraficoContenedor
      titulo="Clientes por segmento de fuga"
      subtitulo={total > 0 ? `${total} clientes · foto actual, no una serie en el tiempo` : undefined}
      registro="analisis"
      cargando={cargando}
      vacio={!cargando && (error || total === 0)}
      vacioTitulo={error ? "No se pudo cargar el resumen de fuga" : "Todavía no hay clientes que segmentar"}
      vacioDescripcion={
        error
          ? "Vuelve a abrir esta pantalla; si persiste, revisa el servicio de clientes."
          : "Aquí aparecerá cuántos clientes están en cada segmento de fuga (sin señal, en riesgo, confirmada, resuelta) en cuanto haya clientes con historial."
      }
      alto={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="etiqueta" {...ejeProps("analisis")} interval={0} />
          <YAxis allowDecimals={false} {...ejeProps("analisis")} width={36} />
          <Tooltip
            cursor={{ fill: "rgba(31, 86, 115, 0.06)" }}
            content={<TooltipPropio registro="analisis" formato={(v) => `${v} clientes`} />}
          />
          <Bar dataKey="clientes" name="Clientes" isAnimationActive={false} maxBarSize={72}>
            {filas.map((f, i) => (
              <Cell key={i} fill={f.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </GraficoContenedor>
  );
}
