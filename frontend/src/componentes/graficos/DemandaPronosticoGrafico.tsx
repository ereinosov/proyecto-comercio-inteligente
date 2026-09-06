/**
 * US7 de 004-pronostico-demanda: demanda pronosticada vs. histórica censurada, en una línea con
 * dos series — "Demanda observada" (dato) y "Demanda corregida / pronosticada" (estimación).
 * Lectura pura: `GET /demanda` (serie observada + corregida por día, US1) + el `serie_pronosticada`
 * del pronóstico ya cargado por la vista. No pide ni calcula nada nuevo.
 *
 * La serie estimada usa el color Estimado (#1F5673); la observada, Tinta — el mismo contraste
 * dato/estimación que el resto del módulo (La Regla de los Tres Portadores).
 */

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorApi } from "../../servicios/clienteHttp";
import { obtenerSerieDemanda, type Pronostico, type PuntoSerie } from "../../servicios/pronostico";
import { GraficoContenedor } from "./GraficoContenedor";
import { TooltipPropio } from "./TooltipPropio";
import { COLOR, ejeProps, gridProps } from "./temaGraficos";

interface Fila {
  periodo: string;
  observada: number | null;
  corregida: number | null;
}

interface Props {
  idProducto: number;
  idSucursal: number;
  pronostico: Pronostico | null;
}

export function DemandaPronosticoGrafico({ idProducto, idSucursal, pronostico }: Props) {
  const [serie, setSerie] = useState<PuntoSerie[] | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setCargando(true);
    setError(false);
    setSerie(null);
    obtenerSerieDemanda(idSucursal, idProducto)
      .then(setSerie)
      .catch((e) => setError(!(e instanceof ErrorApi) || e.status !== 404))
      .finally(() => setCargando(false));
  }, [idProducto, idSucursal]);

  const filas: Fila[] = [];
  if (serie) {
    for (const p of serie) {
      filas.push({
        periodo: p.periodo,
        observada: Number(p.demanda_observada),
        corregida: p.demanda_corregida !== null ? Number(p.demanda_corregida) : null,
      });
    }
  }
  // El horizonte de pronóstico continúa la serie estimada (observada = null: no hay dato futuro).
  if (pronostico && pronostico.vigente) {
    for (const p of pronostico.serie_pronosticada) {
      filas.push({ periodo: p.periodo, observada: null, corregida: Number(p.valor) });
    }
  }

  return (
    <GraficoContenedor
      titulo="Demanda: observada vs. corregida y pronosticada"
      subtitulo="Línea sólida en Tinta = observada · línea en Estimado = corregida por censura y, al final, pronóstico"
      registro="analisis"
      cargando={cargando}
      vacio={!cargando && (error || filas.length === 0)}
      vacioTitulo={error ? "No se pudo cargar la serie de demanda" : "Sin serie de demanda todavía"}
      vacioDescripcion={
        error
          ? "Vuelve a abrir esta vista; si persiste, revisa que el servicio de pronóstico esté disponible."
          : "Aquí aparecerá la demanda observada día a día y, sobre ella, la serie corregida por quiebre/precio/promoción más el pronóstico, en cuanto este producto tenga ventas registradas."
      }
      alto={300}
    >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filas} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="periodo" {...ejeProps("analisis")} minTickGap={28} />
            <YAxis {...ejeProps("analisis")} width={40} />
            <Tooltip
              content={<TooltipPropio registro="analisis" formato={(v) => String(v)} />}
            />
            <Line
              type="monotone"
              dataKey="observada"
              name="Demanda observada"
              stroke={COLOR.tinta}
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="corregida"
              name="Corregida / pronosticada"
              stroke={COLOR.serie}
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
    </GraficoContenedor>
  );
}
