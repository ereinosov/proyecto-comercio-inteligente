/**
 * Contenedor de la superficie de competencia (US4): captura de observaciones y comparación de
 * precios. Registro de Análisis. Dos vistas, un solo lugar en la navegación.
 */

import { useState } from "react";
import { ComparacionPrecios } from "./ComparacionPrecios";
import { ObservacionPrecio } from "./ObservacionPrecio";
import estilos from "./Competencia.module.css";

interface Props {
  idSucursal: number;
  idTurno?: number;
}

export function Competencia({ idSucursal, idTurno }: Props) {
  const [vista, setVista] = useState<"comparacion" | "captura">("comparacion");

  return (
    <div className={estilos.contenedorSubvistas}>
      <div className={estilos.subnav}>
        <button
          className={vista === "comparacion" ? estilos.subtabActiva : estilos.subtab}
          onClick={() => setVista("comparacion")}
        >
          Comparar
        </button>
        <button
          className={vista === "captura" ? estilos.subtabActiva : estilos.subtab}
          onClick={() => setVista("captura")}
        >
          Capturar observación
        </button>
      </div>
      {vista === "comparacion" ? (
        <ComparacionPrecios idSucursal={idSucursal} />
      ) : (
        <ObservacionPrecio idTurno={idTurno} />
      )}
    </div>
  );
}
