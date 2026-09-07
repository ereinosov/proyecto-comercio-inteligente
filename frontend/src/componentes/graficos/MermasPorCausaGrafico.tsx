/**
 * US5 de 006-caja-mermas-fraude: mermas por causa en el tiempo, barras apiladas por semana.
 * Lectura pura sobre `GET /caja/mermas/resumen`, que el backend ya agrega por semana y causa
 * (nunca por día: el cuadre es frecuente pero no diario).
 *
 * Cada causa del ENUM `merma.causa` es una serie. NO se usan los colores semánticos
 * (#9A5B08/#8E2A2A/#0F5132) como paleta de categorías —violaría La Regla del Significado, esos
 * colores están reservados a su significado—: se usan variaciones de opacidad/tono de #1F5673 y
 * #5A6862 (`SERIES_NEUTRAS`), con leyenda.
 */

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorApi } from "../../servicios/clienteHttp";
import { obtenerResumenMermas, type ResumenMermaSemana } from "../../servicios/caja";
import { GraficoContenedor } from "./GraficoContenedor";
import { TooltipPropio } from "./TooltipPropio";
import { SERIES_NEUTRAS, ejeProps, fontFamily, gridProps } from "./temaGraficos";

const CAUSAS: { clave: keyof ResumenMermaSemana; etiqueta: string }[] = [
  { clave: "vencimiento", etiqueta: "Vencimiento" },
  { clave: "dano", etiqueta: "Daño" },
  { clave: "robo_externo", etiqueta: "Robo externo" },
  { clave: "error_conteo", etiqueta: "Error de conteo" },
  { clave: "merma_granel", etiqueta: "Merma de granel" },
];

export function MermasPorCausaGrafico({ idSucursal }: { idSucursal: number }) {
  const [datos, setDatos] = useState<ResumenMermaSemana[] | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setCargando(true);
    setError(false);
    setDatos(null);
    obtenerResumenMermas(idSucursal)
      .then(setDatos)
      .catch((e) => setError(!(e instanceof ErrorApi) || e.status >= 500))
      .finally(() => setCargando(false));
  }, [idSucursal]);

  const filas = datos ?? [];
  const sinValorTotal = filas.reduce((acc, f) => acc + (f.sin_valor ?? 0), 0);

  return (
    <GraficoContenedor
      titulo="Mermas por causa, por semana"
      subtitulo={
        filas.length > 0
          ? `Valoración (${filas.length} semanas)${sinValorTotal > 0 ? ` · ${sinValorTotal} merma(s) sin valoración calculable, no sumadas` : ""}`
          : undefined
      }
      registro="analisis"
      cargando={cargando}
      vacio={!cargando && (error || filas.length === 0)}
      vacioTitulo={error ? "No se pudo cargar el resumen de mermas" : "Todavía no hay mermas que graficar"}
      vacioDescripcion={
        error
          ? "Vuelve a abrir esta pantalla; si persiste, revisa el servicio de caja."
          : "Aquí aparecerá la valoración de las mermas de esta sucursal apilada por causa y agrupada por semana, en cuanto se registre alguna."
      }
      alto={280}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="periodo" {...ejeProps("analisis")} minTickGap={20} />
          <YAxis {...ejeProps("analisis")} width={52} />
          <Tooltip
            cursor={{ fill: "rgba(31, 86, 115, 0.06)" }}
            content={<TooltipPropio registro="analisis" formato={(v) => String(v)} />}
          />
          <Legend wrapperStyle={{ fontFamily: fontFamily("analisis"), fontSize: 12, color: "#5A6862" }} />
          {CAUSAS.map((c, i) => (
            <Bar
              key={c.clave}
              dataKey={c.clave}
              name={c.etiqueta}
              stackId="mermas"
              fill={SERIES_NEUTRAS[i % SERIES_NEUTRAS.length]}
              isAnimationActive={false}
              maxBarSize={56}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </GraficoContenedor>
  );
}
