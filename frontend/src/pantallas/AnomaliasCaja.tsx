/**
 * Anomalías de caja sin explicación (006-caja-mermas-fraude, US4 — T049). Registro de ANÁLISIS:
 * 6px, Source Serif 4, una decisión por bloque, panel de detalle junto a la lista (nunca modal).
 * Sin Verde Rasero.
 *
 * Una anomalía `sin_explicacion` se marca en crítico #8E2A2A con PUNTO HUECO — mismo patrón que
 * `senal_fuga` 'confirmada' de 002: el hueco dice que ese dato está pendiente de que una persona
 * lo cierre. La resolución es TEXTO LIBRE, no un desplegable cerrado (research.md #18). El sistema
 * NUNCA cierra una anomalía por su cuenta (FR-029).
 *
 * Único momento de animación de la pantalla: al revelar el detalle de una anomalía (remount por
 * `key`), sin hover por fila ni fade-in por bloque.
 */

import { useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarAnomalias, resolverAnomalia, type AnomaliaCaja } from "../servicios/caja";
import estilos from "./CajaFraude.module.css";

export function AnomaliasCaja({ idSucursal }: { idSucursal: number }) {
  const [anomalias, setAnomalias] = useState<AnomaliaCaja[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [idSeleccionada, setIdSeleccionada] = useState<number | null>(null);
  const [soloAbiertas, setSoloAbiertas] = useState(true);

  const [resolucion, setResolucion] = useState("");
  const [idOperador, setIdOperador] = useState("");
  const [errorForm, setErrorForm] = useState<string | null>(null);

  function recargar() {
    setError(null);
    listarAnomalias(idSucursal, soloAbiertas ? { estado: "sin_explicacion" } : {})
      .then(setAnomalias)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar las anomalías.")
      );
  }

  useEffect(recargar, [idSucursal, soloAbiertas]);

  const seleccionada = anomalias.find((a) => a.id_anomalia_caja === idSeleccionada) ?? null;

  async function resolver(evento: FormEvent) {
    evento.preventDefault();
    if (!seleccionada) return;
    setErrorForm(null);
    try {
      await resolverAnomalia(seleccionada.id_anomalia_caja, {
        resolucion,
        id_operador: Number(idOperador),
      });
      setResolucion("");
      setIdOperador("");
      recargar();
    } catch (e) {
      setErrorForm(e instanceof ErrorApi ? e.message : "No se pudo resolver la anomalía.");
    }
  }

  return (
    <div className={estilos.dosColumnas}>
      <div className={estilos.columnaLista}>
        <label className={estilos.filtro}>
          <input
            type="checkbox"
            checked={soloAbiertas}
            onChange={(e) => setSoloAbiertas(e.target.checked)}
          />
          Solo sin explicación
        </label>
        {error && <p className={estilos.error}>{error}</p>}
        <ul className={estilos.lista}>
          {anomalias.map((a) => (
            <li key={a.id_anomalia_caja}>
              <button
                className={[
                  estilos.bloqueLista,
                  idSeleccionada === a.id_anomalia_caja ? estilos.bloqueSeleccionado : "",
                ].join(" ")}
                onClick={() => setIdSeleccionada(a.id_anomalia_caja)}
              >
                <span
                  className={
                    a.estado === "sin_explicacion" ? estilos.marcaSinExplicacion : estilos.marcaResuelta
                  }
                >
                  <span
                    className={
                      a.estado === "sin_explicacion" ? estilos.puntoHueco : estilos.puntoLleno
                    }
                    aria-hidden="true"
                  />
                  {a.estado === "sin_explicacion" ? "sin explicación" : "resuelta"}
                </span>
                <span className={estilos.resumenAnomalia}>
                  {a.origen === "efectivo"
                    ? `efectivo · ${a.monto}`
                    : `inventario · ${a.magnitud} u`}
                </span>
              </button>
            </li>
          ))}
          {anomalias.length === 0 && (
            <li className={estilos.nota}>Ninguna anomalía en esta vista.</li>
          )}
        </ul>
      </div>

      <div className={estilos.columnaDetalle}>
        {!seleccionada && (
          <p className={estilos.nota}>Elige una anomalía de la lista para revisarla.</p>
        )}
        {seleccionada && (
          <div key={seleccionada.id_anomalia_caja} className={estilos.detalleRevelado}>
            <h2 className={estilos.subtitulo}>
              Anomalía {seleccionada.id_anomalia_caja} · {seleccionada.origen}
            </h2>
            <dl className={estilos.datos}>
              <div>
                <dt>Estado</dt>
                <dd>{seleccionada.estado}</dd>
              </div>
              <div>
                <dt>Día local</dt>
                <dd>{seleccionada.dia_local}</dd>
              </div>
              {seleccionada.origen === "efectivo" && (
                <div>
                  <dt>Monto</dt>
                  <dd>{seleccionada.monto}</dd>
                </div>
              )}
              {seleccionada.origen === "inventario" && (
                <>
                  <div>
                    <dt>Magnitud</dt>
                    <dd>{seleccionada.magnitud} u</dd>
                  </div>
                  <div>
                    <dt>Valor estimado</dt>
                    <dd>{seleccionada.valor_estimado ?? "no calculable"}</dd>
                  </div>
                </>
              )}
            </dl>

            {seleccionada.indicador_snapshot && (
              <details className={estilos.snapshot}>
                <summary>Indicadores congelados al generarse</summary>
                <pre>{JSON.stringify(seleccionada.indicador_snapshot, null, 2)}</pre>
              </details>
            )}

            <h3 className={estilos.subtituloMenor}>Historial</h3>
            <ol className={estilos.historial}>
              {seleccionada.historial.map((h, i) => (
                <li key={i}>
                  {h.estado} · {new Date(h.instante).toLocaleString()}
                  {h.nota ? ` · ${h.nota}` : ""}
                </li>
              ))}
            </ol>

            {seleccionada.estado === "sin_explicacion" ? (
              <form className={estilos.formulario} onSubmit={resolver}>
                <label className={estilos.campoAncho}>
                  Resolución (texto libre)
                  <input
                    className={estilos.entrada}
                    placeholder="error operativo confirmado, escalado a fraude, ajuste aceptado…"
                    value={resolucion}
                    onChange={(e) => setResolucion(e.target.value)}
                    required
                  />
                </label>
                <label className={estilos.campo}>
                  Operador (id)
                  <input
                    className={estilos.entrada}
                    inputMode="numeric"
                    value={idOperador}
                    onChange={(e) => setIdOperador(e.target.value)}
                    required
                  />
                </label>
                <button className={estilos.boton} type="submit">
                  Resolver
                </button>
                {errorForm && <p className={estilos.error}>{errorForm}</p>}
              </form>
            ) : (
              <p className={estilos.nota}>
                Resuelta: <strong>{seleccionada.resolucion}</strong>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
