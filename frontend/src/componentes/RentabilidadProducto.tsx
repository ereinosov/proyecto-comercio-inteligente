/**
 * Rentabilidad real de un producto en una sucursal (003, apoyo a User Story 1). Registro de
 * Análisis. Cruza el costo de adquisición (lote FEFO vigente) contra el precio vigente para
 * mostrar la ganancia por unidad — el dato que faltaba junto al precio sugerido —, y las
 * unidades vendidas de las últimas 4 y 12 semanas (serie de demanda de 004).
 *
 * "no calculable" se comunica con los tres portadores (color + forma + texto). Sin Verde Rasero.
 */

import { useEffect, useState } from "react";
import type { MargenProducto } from "../servicios/precios";
import { unidadesVendidasUltimos } from "../servicios/pronostico";
import { formatearMoneda, formatearPorcentaje } from "../utilidades/formato";
import { Ayuda } from "./Ayuda";
import estilos from "./RentabilidadProducto.module.css";

export function RentabilidadProducto({
  idProducto,
  idSucursal,
  margen,
}: {
  idProducto: number;
  idSucursal: number;
  margen: MargenProducto | undefined;
}) {
  const [v30, setV30] = useState<number | null>(null);
  const [v90, setV90] = useState<number | null>(null);

  useEffect(() => {
    let vivo = true;
    setV30(null);
    setV90(null);
    unidadesVendidasUltimos(idSucursal, idProducto, 30)
      .then((n) => vivo && setV30(n))
      .catch(() => vivo && setV30(null));
    unidadesVendidasUltimos(idSucursal, idProducto, 90)
      .then((n) => vivo && setV90(n))
      .catch(() => vivo && setV90(null));
    return () => {
      vivo = false;
    };
  }, [idProducto, idSucursal]);

  const costo = margen?.costo_vigente != null ? Number(margen.costo_vigente) : null;
  const precio = margen?.precio_vigente != null ? Number(margen.precio_vigente) : null;
  const ganancia = costo != null && precio != null ? precio - costo : null;

  return (
    <section className={estilos.bloque}>
      <h3 className={estilos.titulo}>
        Rentabilidad de este producto{" "}
        <Ayuda
          etiqueta="Cómo se calcula la rentabilidad"
          texto="El costo es el del lote que se vendería primero (FEFO). La ganancia por unidad es precio vigente menos ese costo; el margen es esa ganancia sobre el precio."
        />
      </h3>
      <dl className={estilos.datos}>
        <div>
          <dt>Costo de adquisición</dt>
          <dd>
            {costo == null ? (
              <span className={estilos.noCalculable}>
                <span className={estilos.puntoMedio} aria-hidden="true" /> no calculable
              </span>
            ) : (
              formatearMoneda(costo)
            )}
          </dd>
        </div>
        <div>
          <dt>Precio vigente</dt>
          <dd>{precio == null ? "—" : formatearMoneda(precio)}</dd>
        </div>
        <div>
          <dt>Ganancia por unidad</dt>
          <dd className={ganancia != null && ganancia < 0 ? estilos.perdida : undefined}>
            {ganancia == null ? (
              <span className={estilos.noCalculable}>
                <span className={estilos.puntoMedio} aria-hidden="true" /> no calculable
              </span>
            ) : (
              formatearMoneda(ganancia)
            )}
          </dd>
        </div>
        <div>
          <dt>Margen</dt>
          <dd>{margen?.margen == null ? "—" : formatearPorcentaje(margen.margen)}</dd>
        </div>
        <div>
          <dt>Vendidas (últimos 30 d)</dt>
          <dd>{v30 == null ? "…" : v30}</dd>
        </div>
        <div>
          <dt>Vendidas (últimos 90 d)</dt>
          <dd>{v90 == null ? "…" : v90}</dd>
        </div>
      </dl>
      {v90 === 0 && (
        <p className={estilos.nota}>Sin ventas registradas en la ventana.</p>
      )}
    </section>
  );
}
