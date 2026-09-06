/**
 * Contenedor "Pagos" (007-pagos-seguridad — US1/US4). Agrupa la Cobertura de medios de pago
 * (registro de ANÁLISIS) y la Bitácora de auditoría de pagos (registro de OPERACIÓN) bajo un
 * segmentado de texto, mismo patrón que "Caja y fraude". Las Terminales tienen su propia pestaña
 * (T026). Sin Verde Rasero: 007 no mueve dinero (La Regla del Registro Sin Dinero).
 */

import { useState } from "react";
import { BitacoraPagos } from "./BitacoraPagos";
import { CoberturaPago } from "./CoberturaPago";
import estilos from "./CajaFraude.module.css";

type Vista = "cobertura" | "bitacora";

const VISTAS: { valor: Vista; etiqueta: string }[] = [
  { valor: "cobertura", etiqueta: "Cobertura de medios" },
  { valor: "bitacora", etiqueta: "Bitácora de pagos" },
];

export function Pagos({ idSucursal, idOperador }: { idSucursal: number; idOperador: number }) {
  const [vista, setVista] = useState<Vista>("cobertura");

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Pagos</h1>
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
      <div className={estilos.contenido}>
        {vista === "cobertura" && (
          <CoberturaPago idSucursal={idSucursal} idOperador={idOperador} />
        )}
        {vista === "bitacora" && <BitacoraPagos idSucursal={idSucursal} />}
      </div>
    </div>
  );
}
