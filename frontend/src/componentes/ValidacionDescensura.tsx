/**
 * Validación de la descensura contra datos sintéticos con demanda latente conocida (T030, User
 * Story 2 de 004-pronostico-demanda). Vista de analista, registro de Análisis.
 *
 * Muestra, para una serie sintética generada (demanda latente VERDADERA conocida de antemano),
 * cuánto se acerca la demanda corregida por el método base de FR-009 a esa verdad, frente a no
 * corregir nada (SC-002). La vista está rotulada de forma inequívoca como DATOS SINTÉTICOS: no
 * se puede confundir con una vista de producción (FR-017).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  cargarSerieSintetica,
  construirSerieSinteticaDemo,
  obtenerValidacionDescensura,
  type ReporteValidacion,
} from "../servicios/pronostico";
import estilos from "./ValidacionDescensura.module.css";

const NOMBRE_CAMINO: Record<string, string> = {
  con_consulta_no_atendida: "Con consultas no atendidas (camino FR-007)",
  solo_metodo_base: "Sólo método base (camino FR-008)",
};

export function ValidacionDescensura({
  idProducto,
  idSucursal,
}: {
  idProducto: number;
  idSucursal: number;
}) {
  const [reporte, setReporte] = useState<ReporteValidacion | null>(null);
  const [sinSerie, setSinSerie] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [generando, setGenerando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    setSinSerie(false);
    obtenerValidacionDescensura(idSucursal, idProducto)
      .then(setReporte)
      .catch((e) => {
        if (e instanceof ErrorApi && e.status === 404) {
          setReporte(null);
          setSinSerie(true);
        } else {
          setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la validación.");
        }
      })
      .finally(() => setCargando(false));
  }

  useEffect(cargar, [idProducto, idSucursal]);

  async function generarYCargar() {
    setGenerando(true);
    setError(null);
    try {
      await cargarSerieSintetica(construirSerieSinteticaDemo(idProducto, idSucursal));
      cargar();
    } catch (e) {
      setError(
        e instanceof ErrorApi ? e.message : "No se pudo cargar la serie sintética de demostración."
      );
    } finally {
      setGenerando(false);
    }
  }

  if (cargando) return <p className={estilos.instruccion}>Cargando validación…</p>;
  if (error) return <p className={estilos.error}>{error}</p>;

  return (
    <div className={estilos.contenedor}>
      <span className={estilos.rotulo}>Datos sintéticos</span>
      <p className={estilos.explicacion}>
        Serie generada con la demanda latente verdadera de cada día de quiebre conocida de
        antemano. Compara la demanda corregida por el método base de FR-009 contra esa verdad, y
        contra no corregir nada. Es la prueba de fondo de que la descensura acerca la serie a la
        realidad mientras 001 no implemente las consultas no atendidas.
      </p>

      {sinSerie && (
        <>
          <p className={estilos.instruccion}>
            Este producto todavía no tiene una serie sintética cargada.
          </p>
          <button className={estilos.boton} onClick={generarYCargar} disabled={generando}>
            {generando ? "Cargando…" : "Cargar serie sintética de demostración"}
          </button>
        </>
      )}

      {reporte && (
        <>
          <p
            className={`${estilos.veredicto} ${
              reporte.descensura_mejora_sobre_no_corregir
                ? estilos.veredictoOk
                : estilos.veredictoMal
            }`}
          >
            {reporte.descensura_mejora_sobre_no_corregir
              ? "La descensura acerca la serie a la demanda real."
              : "La descensura NO mejora sobre no corregir — revisar el método."}
          </p>

          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Camino</th>
                <th>Períodos</th>
                <th>Error medio corregida</th>
                <th>Error medio sin corregir</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Total</td>
                <td>{reporte.periodos_quiebre_evaluados}</td>
                <td>{reporte.error_medio_descensura}</td>
                <td>{reporte.error_medio_sin_corregir}</td>
              </tr>
              {Object.entries(reporte.detalle_por_camino).map(([camino, det]) => (
                <tr key={camino}>
                  <td>{NOMBRE_CAMINO[camino] ?? camino}</td>
                  <td>{det.periodos}</td>
                  <td>{det.error_medio_descensura}</td>
                  <td>{det.error_medio_sin_corregir}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p className={estilos.nota}>
            El error es la diferencia media, en unidades por día, contra la demanda latente
            verdadera. Hoy los dos caminos usan el método base: la magnitud por evidencia real
            (FR-007) está bloqueada por 001, así que sus números son parecidos hasta que se
            desbloquee.
          </p>
        </>
      )}
    </div>
  );
}
