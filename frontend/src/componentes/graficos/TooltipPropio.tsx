/**
 * Tooltip custom para todos los gráficos Recharts (`<Tooltip content={<TooltipPropio ... />} />`).
 * Nunca el tooltip por defecto de Recharts: ese trae `box-shadow`, prohibido por La Regla del
 * Filo. Superficie Alta, borde 2px, sin sombra.
 */

import type { Registro } from "./temaGraficos";
import estilos from "./TooltipPropio.module.css";

interface Entrada {
  name?: string | number;
  value?: string | number;
  color?: string;
  payload?: Record<string, unknown>;
}

interface Props {
  active?: boolean;
  label?: string | number;
  payload?: Entrada[];
  registro: Registro;
  /** Formatea el valor de cada serie (p. ej. `(v) => v + " %"`). */
  formato?: (valor: number | string, entrada: Entrada) => string;
  /** Reemplaza la etiqueta superior (por defecto el `label` del eje X). */
  etiqueta?: (label: string | number | undefined) => string;
}

export function TooltipPropio({
  active,
  label,
  payload,
  registro,
  formato,
  etiqueta,
}: Props) {
  if (!active || !payload || payload.length === 0) return null;
  const clase = registro === "analisis" ? estilos.analisis : estilos.operacion;
  return (
    <div className={`${estilos.caja} ${clase}`}>
      <p className={estilos.etiqueta}>{etiqueta ? etiqueta(label) : String(label ?? "")}</p>
      {payload.map((e, i) => (
        <div key={i} className={estilos.fila}>
          <span>{e.name}</span>
          <span className={estilos.valor}>
            {formato && e.value !== undefined ? formato(e.value, e) : String(e.value ?? "")}
          </span>
        </div>
      ))}
    </div>
  );
}
