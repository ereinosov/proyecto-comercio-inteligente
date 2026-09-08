/**
 * Tarjetas de sugerencia de precio (T035, User Story 3) y de colocación (T046, User Story 4).
 * Registro de Análisis, integradas en el panel de detalle de `Precios.tsx`. Muestran los insumos
 * que originaron cada sugerencia (margen, rol, observación de competencia con sus tres
 * portadores de antigüedad) para que sea explicable (FR-014, Principio V). El sistema nunca
 * aplica una sugerencia por su cuenta: cada tarjeta exige el toque explícito del encargado.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  aplicarSugerenciaColocacion,
  aplicarSugerenciaPrecio,
  obtenerSugerenciaColocacion,
  obtenerSugerenciaPrecio,
  type RolProducto,
  type SugerenciaColocacion,
  type SugerenciaPrecio,
} from "../servicios/precios";
import estilos from "./SugerenciaPrecioColocacion.module.css";

const ETIQUETAS_ROL: Record<RolProducto, string> = {
  gancho_trafico: "Gancho de tráfico",
  generador_margen: "Generador de margen",
};

function textoRol(rol: RolProducto | null): string {
  return rol === null ? "sin clasificar" : ETIQUETAS_ROL[rol];
}

function textoMargen(margen: number | null): string {
  return margen === null ? "no calculable" : `${Math.round(margen * 100)}%`;
}

export function SugerenciaPrecioColocacion({
  idProducto,
  idSucursal,
  costoVigente = null,
  precioVigente = null,
}: {
  idProducto: number;
  idSucursal: number;
  /** Costo y precio vigentes del producto en la sucursal, para comparar contra el sugerido. */
  costoVigente?: string | null;
  precioVigente?: string | null;
}) {
  const [sugerenciaPrecio, setSugerenciaPrecio] = useState<SugerenciaPrecio | null>(null);
  const [errorPrecio, setErrorPrecio] = useState<string | null>(null);
  const [aplicandoPrecio, setAplicandoPrecio] = useState(false);

  const [sugerenciaColocacion, setSugerenciaColocacion] = useState<SugerenciaColocacion | null>(null);
  const [errorColocacion, setErrorColocacion] = useState<string | null>(null);
  const [aplicandoColocacion, setAplicandoColocacion] = useState(false);

  useEffect(() => {
    setSugerenciaPrecio(null);
    setErrorPrecio(null);
    obtenerSugerenciaPrecio(idProducto, idSucursal)
      .then(setSugerenciaPrecio)
      .catch((e) =>
        setErrorPrecio(e instanceof ErrorApi ? e.message : "No se pudo generar la sugerencia de precio.")
      );
  }, [idProducto, idSucursal]);

  useEffect(() => {
    setSugerenciaColocacion(null);
    setErrorColocacion(null);
    obtenerSugerenciaColocacion(idProducto, idSucursal)
      .then(setSugerenciaColocacion)
      .catch((e) =>
        setErrorColocacion(
          e instanceof ErrorApi ? e.message : "No se pudo generar la sugerencia de colocación."
        )
      );
  }, [idProducto, idSucursal]);

  async function aplicarPrecio() {
    if (!sugerenciaPrecio) return;
    setAplicandoPrecio(true);
    try {
      setSugerenciaPrecio(await aplicarSugerenciaPrecio(idProducto, sugerenciaPrecio.id_sugerencia_precio));
    } catch (e) {
      setErrorPrecio(e instanceof ErrorApi ? e.message : "No se pudo aplicar la sugerencia.");
    } finally {
      setAplicandoPrecio(false);
    }
  }

  async function confirmarColocacion() {
    if (!sugerenciaColocacion) return;
    setAplicandoColocacion(true);
    try {
      setSugerenciaColocacion(
        await aplicarSugerenciaColocacion(idProducto, sugerenciaColocacion.id_sugerencia_colocacion)
      );
    } catch (e) {
      setErrorColocacion(e instanceof ErrorApi ? e.message : "No se pudo confirmar la colocación.");
    } finally {
      setAplicandoColocacion(false);
    }
  }

  return (
    <div className={estilos.contenedor}>
      <section className={estilos.tarjeta}>
        <h3 className={estilos.tituloTarjeta}>Precio sugerido</h3>
        {errorPrecio && <p className={estilos.error}>{errorPrecio}</p>}
        {!errorPrecio && !sugerenciaPrecio && <p className={estilos.instruccion}>Calculando…</p>}
        {!errorPrecio && sugerenciaPrecio && (
          <div className={sugerenciaPrecio.aplicada ? estilos.confirmada : undefined}>
            <p className={estilos.precioSugerido}>${sugerenciaPrecio.precio_sugerido}</p>
            {(() => {
              const sug = Number(sugerenciaPrecio.precio_sugerido);
              const pv = precioVigente != null ? Number(precioVigente) : null;
              const cv = costoVigente != null ? Number(costoVigente) : null;
              const delta = pv != null ? sug - pv : null;
              const margenResultante =
                cv != null && sug > 0 ? ((sug - cv) / sug) * 100 : null;
              return (
                <p className={estilos.instruccion}>
                  {delta != null && (
                    <>
                      vs. precio vigente:{" "}
                      {delta === 0
                        ? "sin cambio"
                        : `${delta > 0 ? "+" : ""}$${delta.toFixed(2)}`}
                    </>
                  )}
                  {margenResultante != null && (
                    <> · margen resultante: {margenResultante.toFixed(0)}%</>
                  )}
                </p>
              );
            })()}
            <dl className={estilos.insumos}>
              <div>
                <dt>Margen usado</dt>
                <dd>{textoMargen(sugerenciaPrecio.margen_usado)}</dd>
              </div>
              <div>
                <dt>Rol usado</dt>
                <dd>{textoRol(sugerenciaPrecio.rol_usado)}</dd>
              </div>
              <div>
                <dt>Competencia</dt>
                <dd>
                  {sugerenciaPrecio.observacion_competencia_usada === null ? (
                    "sin referencia de competencia"
                  ) : (
                    <span className={estilos.observacion}>
                      <span className={estilos.puntoAntiguedad} aria-hidden="true" />
                      {sugerenciaPrecio.observacion_competencia_usada.canal}: $
                      {sugerenciaPrecio.observacion_competencia_usada.precio_por_unidad_medida}{" "}
                      (hace {sugerenciaPrecio.observacion_competencia_usada.dias_de_antiguedad} d)
                    </span>
                  )}
                </dd>
              </div>
            </dl>
            <button
              className={estilos.boton}
              disabled={sugerenciaPrecio.aplicada || aplicandoPrecio}
              onClick={aplicarPrecio}
            >
              {sugerenciaPrecio.aplicada ? "Aplicada" : "Aplicar precio"}
            </button>
          </div>
        )}
      </section>

      <section className={estilos.tarjeta}>
        <h3 className={estilos.tituloTarjeta}>Colocación sugerida</h3>
        {errorColocacion && <p className={estilos.error}>{errorColocacion}</p>}
        {!errorColocacion && !sugerenciaColocacion && <p className={estilos.instruccion}>Calculando…</p>}
        {!errorColocacion && sugerenciaColocacion && (
          <div className={sugerenciaColocacion.aplicada ? estilos.confirmada : undefined}>
            <p className={estilos.zonaSugerida}>{sugerenciaColocacion.zona_nombre}</p>
            <dl className={estilos.insumos}>
              <div>
                <dt>Margen usado</dt>
                <dd>{textoMargen(sugerenciaColocacion.margen_usado)}</dd>
              </div>
              <div>
                <dt>Rol usado</dt>
                <dd>{textoRol(sugerenciaColocacion.rol_usado)}</dd>
              </div>
            </dl>
            <button
              className={estilos.boton}
              disabled={sugerenciaColocacion.aplicada || aplicandoColocacion}
              onClick={confirmarColocacion}
            >
              {sugerenciaColocacion.aplicada ? "Ejecutada" : "Confirmar ejecución física"}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
