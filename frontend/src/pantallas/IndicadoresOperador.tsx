/**
 * Indicadores por operador (006-caja-mermas-fraude, US3 — T040). Registro de ANÁLISIS: 6px, Source
 * Serif 4, una decisión por bloque. Sin Verde Rasero.
 *
 * La tasa de anulaciones y la concentración bajo precio de lista son DATO OBSERVADO (tinta). La
 * señal "se desvía de la línea base de sus pares" es INFERENCIA (color estimado #1F5673 + forma +
 * texto). La respuesta NUNCA dice "fraude" (FR-023): dice "se desvía de sus pares".
 *
 * El cruce contra el faltante de inventario ya funciona (001 User Story 5 implementada): se
 * elige un conteo físico resuelto y se cruza su faltante bruto contra mermas y anulaciones.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  ejecutarCruceOperador,
  obtenerIndicadoresOperador,
  type IndicadoresRespuesta,
  type ResultadoCruce,
} from "../servicios/caja";
import { listarConteos, type ConteoFisico } from "../servicios/conteos";
import { formatearNumero, formatearPorcentaje } from "../utilidades/formato";
import { Boton } from "../componentes/Boton";
import { Ayuda } from "../componentes/Ayuda";
import estilos from "./CajaFraude.module.css";

/** Mediana de pares: porcentaje si hay valor, o el texto explícito de "sin pares". */
function medianaPares(valor: string | null): string {
  return valor === null ? "sin pares comparables" : formatearPorcentaje(valor);
}

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
  const [conteos, setConteos] = useState<ConteoFisico[]>([]);
  const [idConteo, setIdConteo] = useState<number | "">("");
  const [cruzando, setCruzando] = useState(false);
  const [resultadoCruce, setResultadoCruce] = useState<ResultadoCruce | null>(null);

  function recargar() {
    setError(null);
    obtenerIndicadoresOperador(idSucursal, desde, hasta)
      .then(setDatos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los indicadores.")
      );
  }

  useEffect(recargar, [idSucursal, desde, hasta]);

  useEffect(() => {
    setIdConteo("");
    setResultadoCruce(null);
    listarConteos({ idSucursal, estado: "resuelto" })
      .then(setConteos)
      .catch(() => setConteos([]));
  }, [idSucursal]);

  async function intentarCruce() {
    setAvisoCruce(null);
    setResultadoCruce(null);
    setCruzando(true);
    try {
      const res = await ejecutarCruceOperador({
        id_sucursal: idSucursal,
        desde,
        hasta,
        id_conteo_fisico: idConteo === "" ? null : idConteo,
      });
      setResultadoCruce(res);
    } catch (e) {
      setAvisoCruce(
        e instanceof ErrorApi ? e.message : "No se pudo ejecutar el cruce con el inventario."
      );
    } finally {
      setCruzando(false);
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
            <strong>{medianaPares(datos.mediana_pares_tasa_anulaciones)}</strong> · bajo precio
            de lista:{" "}
            <strong>{medianaPares(datos.mediana_pares_concentracion_bajo_lista)}</strong>. Un
            operador se señala al superar {formatearNumero(datos.factor_desviacion_anulaciones, 1)}×
            esa mediana.
          </p>
        )}
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>
          Por operador{" "}
          <Ayuda
            etiqueta="Qué significan estos indicadores"
            texto="Anulaciones = cuántas ventas de sus turnos se anularon. Bajo precio de lista = cuántos renglones cobró por debajo del precio efectivo. Un operador se «señala» sólo si supera el múltiplo indicado de la mediana de sus pares comparables — es una señal para revisar, nunca una acusación de fraude."
          />
        </h2>
        <ul className={estilos.lista}>
          {(datos?.operadores ?? []).map((o) => (
            <li key={o.id_operador} className={estilos.bloqueOperador}>
              <div className={estilos.filaLista}>
                <span className={estilos.nombreOperador}>{o.nombre}</span>
                <span className={estilos.valor}>{o.ventas_periodo} ventas</span>
              </div>
              <div className={estilos.metricas}>
                <span>Anulaciones: {formatearPorcentaje(o.tasa_anulaciones)}</span>
                <span>
                  Bajo precio de lista: {formatearPorcentaje(o.concentracion_bajo_lista)}
                </span>
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
        <p className={estilos.nota}>
          Cruza el faltante bruto de un conteo físico resuelto contra las mermas ya
          clasificadas y las anulaciones del período. Lo que ni una ni otra explican se reparte
          por turno y abre una anomalía en «Anomalías».
        </p>
        <div className={estilos.filaCampos}>
          <label className={estilos.campo}>
            Conteo físico resuelto
            <select
              className={estilos.entrada}
              value={idConteo}
              onChange={(e) => setIdConteo(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">El último resuelto</option>
              {conteos.map((c) => (
                <option key={c.id_conteo_fisico} value={c.id_conteo_fisico}>
                  #{c.id_conteo_fisico} · resuelto{" "}
                  {c.instante_resolucion
                    ? new Date(c.instante_resolucion).toLocaleDateString()
                    : ""}
                </option>
              ))}
            </select>
          </label>
        </div>
        {conteos.length === 0 && (
          <p className={estilos.nota}>
            <span className={estilos.puntoHueco} aria-hidden="true" />
            Esta sucursal todavía no tiene ningún conteo físico resuelto. Resuelve uno en
            «Inventario → Conteo» para poder cruzar.
          </p>
        )}
        <Boton
          variante="primaria"
          registro="analisis"
          onClick={intentarCruce}
          disabled={cruzando || conteos.length === 0}
        >
          {cruzando ? "Cruzando…" : "Ejecutar cruce inventario-ventas"}
        </Boton>
        {avisoCruce && <p className={estilos.error}>{avisoCruce}</p>}
        {resultadoCruce && (
          <div className={estilos.nota}>
            {typeof resultadoCruce.detalle === "string" ? (
              <p>{resultadoCruce.detalle}</p>
            ) : resultadoCruce.detalle.length === 0 ? (
              <p>Ese conteo no tiene faltantes que cruzar.</p>
            ) : (
              <>
                <p>
                  Conteo #{resultadoCruce.id_conteo_fisico} ·{" "}
                  {resultadoCruce.anomalias_creadas.length === 0
                    ? "todo el faltante quedó explicado; no se creó ninguna anomalía."
                    : `${resultadoCruce.anomalias_creadas.length} anomalía(s) creada(s): ${resultadoCruce.anomalias_creadas.join(", ")}.`}
                </p>
                <ul className={estilos.lista}>
                  {resultadoCruce.detalle.map((d) => (
                    <li key={d.id_producto} className={estilos.filaLista}>
                      <span>
                        Producto {d.id_producto} · faltante {d.faltante_bruto} · merma{" "}
                        {d.merma_descontada} · anulaciones {d.anulaciones_descontadas}
                      </span>
                      <span
                        className={
                          Number(d.faltante_no_explicado) > 0 ? estilos.desviacion : estilos.valor
                        }
                      >
                        no explicado: {d.faltante_no_explicado}
                        {d.anomalia ? ` (anomalía ${d.anomalia})` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
