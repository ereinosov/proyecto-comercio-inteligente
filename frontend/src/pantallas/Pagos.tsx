/**
 * Contenedor "Pagos" (007-pagos-seguridad — US1/US4). Agrupa la Cobertura de medios de pago
 * (registro de ANÁLISIS) y la Bitácora de auditoría de pagos (registro de OPERACIÓN) bajo un
 * segmentado de texto, mismo patrón que "Caja y fraude". Las Terminales tienen su propia pestaña
 * (T026). Sin Verde Rasero: 007 no mueve dinero (La Regla del Registro Sin Dinero).
 */

import { useState } from "react";
import { BitacoraPagos } from "./BitacoraPagos";
import { CobrosPorVenta } from "./CobrosPorVenta";
import { CoberturaPago } from "./CoberturaPago";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import { Segmentado } from "../componentes/Segmentado";
import estilos from "./CajaFraude.module.css";

type Vista = "cobertura" | "cobros" | "bitacora";

const VISTAS: { valor: Vista; texto: string }[] = [
  { valor: "cobertura", texto: "Cobertura de medios" },
  { valor: "cobros", texto: "Cobros por venta" },
  { valor: "bitacora", texto: "Registro de seguridad" },
];

export function Pagos({ idSucursal, idOperador }: { idSucursal: number; idOperador: number }) {
  const [vista, setVista] = useState<Vista>("cobertura");

  return (
    <div className={estilos.pantalla}>
      <EncabezadoPantalla titulo="Pagos" registro="analisis" />
      <div className={estilos.selectorVista}>
        <Segmentado
          opciones={VISTAS}
          activa={vista}
          onCambiar={setVista}
          registro="analisis"
          etiqueta="Vista de pagos"
        />
      </div>
      <div className={estilos.contenido}>
        {vista === "cobertura" && (
          <CoberturaPago idSucursal={idSucursal} idOperador={idOperador} />
        )}
        {vista === "cobros" && <CobrosPorVenta idSucursal={idSucursal} />}
        {vista === "bitacora" && <BitacoraPagos idSucursal={idSucursal} />}
      </div>
    </div>
  );
}
