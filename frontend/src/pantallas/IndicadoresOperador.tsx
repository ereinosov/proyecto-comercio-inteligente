/**
 * Indicadores por operador (006-caja-mermas-fraude, US3 — T040). Registro de ANÁLISIS: 6px, Source
 * Serif 4, una decisión por bloque. Sin Verde Rasero.
 *
 * La tasa de anulaciones y la concentración bajo precio de lista son DATO OBSERVADO (tinta). La
 * señal "se desvía de la línea base de sus pares" es INFERENCIA (color estimado #1F5673 + forma +
 * texto). La respuesta NUNCA dice "fraude" (FR-023): dice "se desvía de sus pares".
 *
 * El cruce contra el faltante de inventario está BLOQUEADO por 001 User Story 5: el botón se
 * muestra con el texto explícito, no se oculta.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  ejecutarCruceOperador,
  obtenerIndicadoresOperador,
  type IndicadoresRespuesta,
} from "../servicios/caja";
import estilos from "./CajaFraude.module.css";

function haceUnasSemanas(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() - dias);
  return d.toISOString().slice(0, 10);
}

export function IndicadoresOperador({ idSucursal }: { idSucursal: number }) {
  const [desde, setDesde] = useState(haceUnasSemanas(30));
  const [hasta, setHasta] = useState(new Date().toISOString().slice(0, 10));
  const [datos, setDatos] = useState<IndicadoresRespuesta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [avisoCruce, setAvisoCruce] = useState<string | null>(null);

  function recargar() {
    setError(null);
    obtenerIndicadoresOperador(idSucursal, desde, hasta)
      .then(setDatos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los indicadores.")
      );
  }

  useEffect(recargar, [idSucursal, desde, hasta]);

  async function intentarCruce() {
    setAvisoCruce(null);
    try {
      await ejecutarCruceOperador({ id_sucursal: idSucursal, desde, hasta });
    } catch (e) {
      setAvisoCruce(
        e instanceof ErrorApi
          ? e.message
          : "El cruce con el inventario no está disponible todavía."
      );
    }
  }

  return (
    <div className={estilos.contenido}>
      <section className={estilos.bloque}>
        <div className={estilos.filaCampos}>
          <label className={estilos.campo}>
            Desde
            <input
              className={estilos.entrada}
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
          </label>
          <label className={estilos.campo}>
            Hasta
            <input
              className={estilos.entrada}
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </label>
        </div>
        {error && <p className={estilos.error}>{error}</p>}
        {datos && (
          <p className={estilos.nota}>
            Línea base de pares — anulaciones:{" "}
            <strong>{datos.mediana_pares_tasa_anulaciones ?? "sin pares comparables"}</strong> ·
            bajo precio de lista:{" "}
            <strong>
              {datos.mediana_pares_concentracion_bajo_lista ?? "sin pares comparables"}
            </strong>
            . Un operador se señala al superar {datos.factor_desviacion_anulaciones}× esa mediana.
          </p>
        )}
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Por operador</h2>
        <ul className={estilos.lista}>
          {(datos?.operadores ?? []).map((o) => (
            <li key={o.id_operador} className={estilos.bloqueOperador}>
              <div className={estilos.filaLista}>
                <span className={estilos.nombreOperador}>{o.nombre}</span>
                <span className={estilos.valor}>{o.ventas_periodo} ventas</span>
              </div>
              <div className={estilos.metricas}>
                <span>Anulaciones: {o.tasa_anulaciones}</span>
                <span>Bajo precio de lista: {o.concentracion_bajo_lista}</span>
              </div>
              {!o.comparable && (
                <p className={estilos.nota}>
                  Sin ventas suficientes para comparar contra sus pares.
                </p>
              )}
              {o.se_desvia && o.detalle_desviacion && (
                <p className={estilos.desviacion}>
                  <span className={estilos.puntoHueco} aria-hidden="true" />
                  Se desvía de la línea base de sus pares: {o.detalle_desviacion.join("; ")}
                </p>
              )}
            </li>
          ))}
          {datos?.operadores.length === 0 && (
            <li className={estilos.nota}>Sin actividad de operadores en el período.</li>
          )}
        </ul>
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Cruce con el faltante de inventario</h2>
        <p className={estilos.notaBloqueada}>
          <span className={estilos.puntoHueco} aria-hidden="true" />
          Requiere el conteo físico de inventario de 001, que todavía no está disponible.
        </p>
        <button className={estilos.boton} type="button" onClick={intentarCruce}>
          Ejecutar cruce inventario-ventas
        </button>
        {avisoCruce && <p className={estilos.nota}>{avisoCruce}</p>}
      </section>
    </div>
  );
}
