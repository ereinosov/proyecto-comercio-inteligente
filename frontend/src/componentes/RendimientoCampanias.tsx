/**
 * Rendimiento de campañas (005, apoyo transversal). Registro de Análisis. Cierra el ciclo de la
 * pantalla: hoy se generan cupones y se detectan ofertas, pero nunca se ve si funcionaron.
 * Sólo lectura sobre `redencion_promocion` / `cupon` / `oferta_recompra` — no toca el modelo.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { rendimientoCampanias, type RendimientoCampanias as Datos } from "../servicios/promociones";
import { formatearMoneda, formatearPorcentaje } from "../utilidades/formato";
import estilos from "./GeneracionCupones.module.css";

function haceDias(dias: number): string {
  return new Date(Date.now() - dias * 86_400_000).toISOString().slice(0, 10);
}

const ETIQUETA_MECANISMO: Record<string, string> = {
  cupon: "Cupones por fecha fija",
  oferta_recompra: "Ofertas de recompra",
  reactivacion: "Experimento de reactivación",
};

export function RendimientoCampanias({ idSucursal }: { idSucursal: number }) {
  const [desde, setDesde] = useState(haceDias(90));
  const [hasta, setHasta] = useState(new Date().toISOString().slice(0, 10));
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    setCargando(true);
    setError(null);
    rendimientoCampanias(idSucursal, desde, hasta)
      .then(setDatos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el rendimiento.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal, desde, hasta]);

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.instruccion}>
        ¿Sirvió la promoción? Cupones emitidos frente a redimidos, descuento realmente otorgado
        y ventas influidas, en la ventana elegida.
      </p>

      <div className={estilos.formulario}>
        <label className={estilos.campo}>
          <span>Desde</span>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className={estilos.campo}>
          <span>Hasta</span>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
      </div>

      {error && <p className={estilos.error}>{error}</p>}
      {cargando && <p className={estilos.instruccion}>Cargando…</p>}

      {datos && !cargando && (
        <>
          <p className={estilos.resumen}>
            Cupones: {datos.cupones.emitidos} emitidos · {datos.cupones.redimidos} redimidos ·{" "}
            {datos.cupones.vencidos} vencidos · {datos.cupones.anulados} anulados · tasa de
            redención {formatearPorcentaje(datos.cupones.tasa_redencion)}
          </p>
          <p className={estilos.resumen}>
            Ofertas de recompra: {datos.ofertas_recompra.propuestas} propuestas ·{" "}
            {datos.ofertas_recompra.compradas} compradas ·{" "}
            {datos.ofertas_recompra.reserva_vencida} con reserva vencida
          </p>

          <h3 className={estilos.subtitulo}>Por mecanismo</h3>
          {datos.por_mecanismo.length === 0 ? (
            <p className={estilos.instruccion}>
              Ninguna redención de promoción en esta ventana.
            </p>
          ) : (
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Mecanismo</th>
                  <th>Descuento otorgado</th>
                  <th>Ventas influidas</th>
                </tr>
              </thead>
              <tbody>
                {datos.por_mecanismo.map((m) => (
                  <tr key={m.tipo_origen}>
                    <td>{ETIQUETA_MECANISMO[m.tipo_origen] ?? m.tipo_origen}</td>
                    <td>{formatearMoneda(m.descuento_otorgado)}</td>
                    <td>{m.ventas_influidas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
