/**
 * Resultado del experimento de reactivación (005-promociones-inteligentes, US3, T045). Registro
 * de Análisis: radio 6px, Source Serif 4.
 *
 * Distingue con TRES portadores simultáneos el DATO de la INFERENCIA (constitución, "un número
 * estimado nunca se presenta como un hecho medido"):
 *  - el % de retorno OBSERVADO de cada grupo va en tinta normal (dato);
 *  - la incrementalidad, el estadístico z, el valor p y el veredicto van en el color
 *    `--color-estimado` (#1F5673), con un indicador de forma (▲ significativa / ▬ no
 *    significativa / ◇ muestra insuficiente) y el texto explícito de la prueba — nunca sólo
 *    color, nunca un número sin su prueba.
 *
 * El único momento de animación de la pantalla ocurre al revelar el detalle de un experimento
 * cerrado (remount por `key`, ver Promociones.module.css) — sin hover por fila ni fade-in por
 * tarjeta (T046).
 */

import { useCallback, useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  cerrarExperimento,
  crearExperimento,
  obtenerExperimento,
  type Experimento,
} from "../servicios/promociones";
import estilos from "./ResultadoExperimento.module.css";

function pct(proporcion: string | null): string {
  if (proporcion === null) return "—";
  return `${(Number(proporcion) * 100).toFixed(1)} %`;
}

function puntos(incrementalidad: string | null): string {
  if (incrementalidad === null) return "—";
  const pp = Number(incrementalidad) * 100;
  return `${pp >= 0 ? "+" : ""}${pp.toFixed(1)} pp`;
}

interface LecturaInferencia {
  forma: "▲" | "▬" | "◇";
  texto: string;
}

function lecturaInferencia(e: Experimento): LecturaInferencia {
  if (e.veredicto === "muestra_insuficiente") {
    return {
      forma: "◇",
      texto: e.motivo_muestra_insuficiente ?? "Muestra insuficiente para concluir.",
    };
  }
  if (e.veredicto === "en_curso") {
    return { forma: "◇", texto: "En curso: la ventana de medición no ha cerrado." };
  }
  const partes = [
    `incrementalidad ${puntos(e.incrementalidad)}`,
    `z = ${e.estadistico_z ?? "—"}`,
    `p = ${e.valor_p ?? "—"}`,
  ];
  if (e.veredicto === "efectivo") {
    return { forma: "▲", texto: `${partes.join(" · ")} · significativa (p < ${e.parametros_muestra.alfa})` };
  }
  return { forma: "▬", texto: `${partes.join(" · ")} · no significativa` };
}

export function ResultadoExperimento() {
  const [idActual, setIdActual] = useState<number | null>(null);
  const [experimento, setExperimento] = useState<Experimento | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const refrescar = useCallback((id: number) => {
    obtenerExperimento(id)
      .then(setExperimento)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el experimento.")
      );
  }, []);

  useEffect(() => {
    if (idActual !== null) refrescar(idActual);
  }, [idActual, refrescar]);

  async function crear() {
    setOcupado(true);
    setError(null);
    try {
      const nuevo = await crearExperimento();
      setExperimento(nuevo);
      setIdActual(nuevo.id_experimento_reactivacion);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo crear el experimento.");
    } finally {
      setOcupado(false);
    }
  }

  async function cerrar() {
    if (idActual === null) return;
    setOcupado(true);
    setError(null);
    try {
      setExperimento(await cerrarExperimento(idActual));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo cerrar el experimento.");
    } finally {
      setOcupado(false);
    }
  }

  const inferencia = experimento ? lecturaInferencia(experimento) : null;

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.instruccion}>
        Reparte los clientes inactivos (señal de fuga activa) en tratamiento y control por
        aleatorización real con semilla fija. Sólo el tratamiento recibe el descuento. Al cerrar
        la ventana se mide el retorno de cada grupo y se juzga la incrementalidad con una prueba z
        de dos proporciones.
      </p>

      <div className={estilos.acciones}>
        <button className={estilos.boton} onClick={crear} disabled={ocupado}>
          {ocupado ? "Trabajando…" : "Crear experimento"}
        </button>
        {experimento && experimento.veredicto === "en_curso" && (
          <button className={estilos.botonSecundario} onClick={cerrar} disabled={ocupado}>
            Cerrar ventana y medir
          </button>
        )}
      </div>

      {error && <p className={estilos.error}>{error}</p>}

      {experimento && (
        <div key={`${experimento.id_experimento_reactivacion}-${experimento.veredicto}`} className={estilos.detalle}>
          <h3 className={estilos.subtitulo}>
            Experimento {experimento.id_experimento_reactivacion}
          </h3>

          <dl className={estilos.parametros}>
            <div>
              <dt>Elegibles</dt>
              <dd>{experimento.n_elegibles}</dd>
            </div>
            <div>
              <dt>Tratamiento / control</dt>
              <dd>
                {experimento.n_tratamiento ?? "—"} / {experimento.n_control ?? "—"}
              </dd>
            </div>
            <div>
              <dt>Muestra mínima por grupo</dt>
              <dd>{experimento.parametros_muestra.tamano_minimo_muestra}</dd>
            </div>
            <div>
              <dt>Semilla</dt>
              <dd>{experimento.semilla}</dd>
            </div>
          </dl>

          <div className={estilos.tasas}>
            <div className={estilos.tasa}>
              <span className={estilos.tasaEtiqueta}>Retorno observado · tratamiento</span>
              <span className={estilos.tasaValor}>{pct(experimento.retorno_tratamiento)}</span>
            </div>
            <div className={estilos.tasa}>
              <span className={estilos.tasaEtiqueta}>Retorno observado · control</span>
              <span className={estilos.tasaValor}>{pct(experimento.retorno_control)}</span>
            </div>
          </div>

          {inferencia && (
            <p className={estilos.inferencia}>
              <span className={estilos.forma} aria-hidden="true">
                {inferencia.forma}
              </span>
              <span className={estilos.inferenciaTexto}>{inferencia.texto}</span>
            </p>
          )}
          <p
            className={`${estilos.veredicto} ${estilos[`veredicto_${experimento.veredicto}`] ?? ""}`}
          >
            Veredicto: <strong>{experimento.veredicto.replace("_", " ")}</strong>
          </p>
        </div>
      )}
    </div>
  );
}
