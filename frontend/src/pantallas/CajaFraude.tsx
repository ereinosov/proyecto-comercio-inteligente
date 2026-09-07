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
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import { Segmentado } from "../componentes/Segmentado";
import estilos from "./CajaFraude.module.css";

type Vista = "anomalias" | "mermas" | "indicadores";

const VISTAS: { valor: Vista; texto: string }[] = [
  { valor: "anomalias", texto: "Anomalías" },
  { valor: "mermas", texto: "Mermas y caducidad" },
  { valor: "indicadores", texto: "Indicadores por operador" },
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
      <EncabezadoPantalla titulo="Caja y fraude" registro="analisis" />
      <div className={estilos.selectorVista}>
        <Segmentado
          opciones={VISTAS}
          activa={vista}
          onCambiar={setVista}
          registro="analisis"
          etiqueta="Vista de caja y fraude"
        />
      </div>

      {vista === "anomalias" && (
        <AnomaliasCaja idSucursal={idSucursal} idOperador={idOperador} />
      )}
      {vista === "mermas" && <Mermas idSucursal={idSucursal} idOperador={idOperador} />}
      {vista === "indicadores" && <IndicadoresOperador idSucursal={idSucursal} />}
    </div>
  );
}
