/**
 * Contenedor de la superficie de competencia (US4): captura de observaciones y comparación de
 * precios. Registro de Análisis. Dos vistas, un solo lugar en la navegación.
 */

import { useState } from "react";
import { ComparacionPrecios } from "./ComparacionPrecios";
import { ObservacionPrecio } from "./ObservacionPrecio";
import { Segmentado } from "../componentes/Segmentado";
import estilos from "./Competencia.module.css";

interface Props {
  idSucursal: number;
  idTurno?: number;
}

type Vista = "comparacion" | "captura";

const VISTAS: { valor: Vista; texto: string }[] = [
  { valor: "comparacion", texto: "Comparar" },
  { valor: "captura", texto: "Capturar observación" },
];

export function Competencia({ idSucursal, idTurno }: Props) {
  const [vista, setVista] = useState<Vista>("comparacion");

  return (
    <div className={estilos.contenedorSubvistas}>
      <div className={estilos.subnav}>
        <Segmentado
          opciones={VISTAS}
          activa={vista}
          onCambiar={setVista}
          registro="analisis"
          etiqueta="Vista de competencia"
        />
      </div>
      {vista === "comparacion" ? (
        <ComparacionPrecios idSucursal={idSucursal} />
      ) : (
        <ObservacionPrecio idTurno={idTurno} />
      )}
    </div>
  );
}
