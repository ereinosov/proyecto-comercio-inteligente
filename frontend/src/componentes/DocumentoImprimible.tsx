/**
 * "Ver como documento" (009, FR-014). Abre la factura simulada —y su nota de crédito, si la
 * hay— en una hoja a pantalla completa con `window.print()`, que en cualquier navegador ofrece
 * también "Guardar como PDF". No hay PDF de servidor (research §8): el costo de esta vía es
 * cero con lo que el navegador ya trae.
 *
 * La hoja se monta en un portal a `document.body` (fuera de `#root`) y, mientras está abierta,
 * marca `body.imprimiendo-doc`. Así, al imprimir, el CSS oculta TODO el resto de la app —nav,
 * pantalla de fondo— y sólo sale la factura, sin páginas en blanco ni la barra de acciones.
 *
 * Registro de Operación. Sin Verde Rasero (La Regla de la Sola Voz).
 */

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Boton } from "./Boton";
import { FacturaSimulada } from "./FacturaSimulada";
import type { Factura } from "../servicios/facturas";
import estilos from "./DocumentoImprimible.module.css";

export function DocumentoImprimible({
  factura,
  notaCredito,
}: {
  factura: Factura;
  notaCredito?: Factura | null;
}) {
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    document.body.classList.add("imprimiendo-doc");
    return () => document.body.classList.remove("imprimiendo-doc");
  }, [abierto]);

  return (
    <>
      <Boton variante="secundaria" tamano="sm" onClick={() => setAbierto(true)}>
        Ver como documento
      </Boton>
      {abierto &&
        createPortal(
          <div
            className={estilos.telon}
            role="dialog"
            aria-modal="true"
            aria-label="Documento de la factura simulada"
            onClick={() => setAbierto(false)}
          >
            <div className={estilos.hoja} onClick={(e) => e.stopPropagation()}>
              <div className={estilos.barra} data-noprint>
                <Boton variante="secundaria" tamano="sm" onClick={() => window.print()}>
                  Imprimir o guardar PDF
                </Boton>
                <Boton variante="neutra" tamano="sm" onClick={() => setAbierto(false)}>
                  Cerrar
                </Boton>
              </div>
              <div className={estilos.contenido}>
                <FacturaSimulada factura={factura} />
                {notaCredito && <FacturaSimulada factura={notaCredito} />}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
