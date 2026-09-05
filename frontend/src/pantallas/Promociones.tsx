/**
 * Pantalla de Promociones Inteligentes (005-promociones-inteligentes). Registro de Análisis: una
 * decisión por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md). Tres mecanismos
 * distintos (Lectura Crítica n.º 6), cada uno en su vista:
 *
 *  - Cupones por fecha fija (US1): regla directa, sin grupo de control.
 *  - Ofertas de recompra (US2): reserva de PRECIO, nunca de inventario.
 *  - Experimento de reactivación (US3): grupo de control obligatorio, aleatorización con semilla
 *    fija, veredicto por prueba z.
 *
 * La marca agregada de "promoción activa" (US4) no tiene superficie propia: la consume
 * 004-pronostico-demanda máquina a máquina.
 *
 * El único momento de animación de la pantalla ocurre al cambiar de vista (remount por `key`) —
 * sin hover por fila ni fade-in por tarjeta (T046, registro de Análisis).
 */

import { useState } from "react";
import { GeneracionCupones } from "../componentes/GeneracionCupones";
import { OfertasRecompra } from "../componentes/OfertasRecompra";
import { ResultadoExperimento } from "../componentes/ResultadoExperimento";
import estilos from "./Promociones.module.css";

type Vista = "cupones" | "recompra" | "reactivacion";

const VISTAS: { clave: Vista; texto: string }[] = [
  { clave: "cupones", texto: "Cupones por fecha fija" },
  { clave: "recompra", texto: "Ofertas de recompra" },
  { clave: "reactivacion", texto: "Experimento de reactivación" },
];

export function Promociones({ idSucursal }: { idSucursal: number }) {
  const [vista, setVista] = useState<Vista>("cupones");

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Promociones Inteligentes</h1>
      </div>

      <div className={estilos.cuerpo}>
        <div className={estilos.selectorVista}>
          {VISTAS.map((v) => (
            <button
              key={v.clave}
              className={vista === v.clave ? estilos.vistaActiva : estilos.vistaInactiva}
              onClick={() => setVista(v.clave)}
            >
              {v.texto}
            </button>
          ))}
        </div>

        <div key={vista} className={estilos.panel}>
          {vista === "cupones" && <GeneracionCupones />}
          {vista === "recompra" && <OfertasRecompra idSucursal={idSucursal} />}
          {vista === "reactivacion" && <ResultadoExperimento />}
        </div>
      </div>
    </div>
  );
}
