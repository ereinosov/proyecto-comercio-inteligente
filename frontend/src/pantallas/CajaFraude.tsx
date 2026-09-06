/**
 * Contenedor "Caja y fraude" (006-caja-mermas-fraude — US2/US3/US4). Registro de ANÁLISIS: agrupa
 * Mermas, Anomalías e Indicadores por operador bajo un segmentado de texto (mismo patrón que las
 * vistas de Pronóstico y Promociones). Sin Verde Rasero (La Regla del Registro Sin Dinero).
 *
 * El arqueo de caja NO vive aquí: es una tarea de Operación y tiene su propia pestaña. Y el arqueo,
 * por sí solo, nunca es señal del fraude de sub-registro (FR-008) — esa señal es el cruce
 * inventario-ventas y los indicadores por operador de esta pantalla.
 */

import { useState } from "react";
import { AnomaliasCaja } from "./AnomaliasCaja";
import { IndicadoresOperador } from "./IndicadoresOperador";
import { Mermas } from "./Mermas";
import estilos from "./CajaFraude.module.css";

type Vista = "anomalias" | "mermas" | "indicadores";

const VISTAS: { valor: Vista; etiqueta: string }[] = [
  { valor: "anomalias", etiqueta: "Anomalías" },
  { valor: "mermas", etiqueta: "Mermas y caducidad" },
  { valor: "indicadores", etiqueta: "Indicadores por operador" },
];

export function CajaFraude({
  idSucursal,
  idOperador,
}: {
  idSucursal: number;
  idOperador: number;
}) {
  const [vista, setVista] = useState<Vista>("anomalias");

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Caja y fraude</h1>
        <nav className={estilos.segmentado}>
          {VISTAS.map((v) => (
            <button
              key={v.valor}
              className={vista === v.valor ? estilos.segActivo : estilos.segInactivo}
              onClick={() => setVista(v.valor)}
            >
              {v.etiqueta}
            </button>
          ))}
        </nav>
      </div>

      {vista === "anomalias" && (
        <AnomaliasCaja idSucursal={idSucursal} idOperador={idOperador} />
      )}
      {vista === "mermas" && <Mermas idSucursal={idSucursal} idOperador={idOperador} />}
      {vista === "indicadores" && <IndicadoresOperador idSucursal={idSucursal} />}
    </div>
  );
}
