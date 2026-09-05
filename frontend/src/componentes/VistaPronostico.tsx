/**
 * Vista de pronóstico de demanda (T041, T042, User Story 3 de 004-pronostico-demanda). Registro
 * de Análisis.
 *
 * El pronóstico se deriva de la serie CORREGIDA (FR-018) por suavizado exponencial simple
 * (FR-020). Se muestra SIEMPRE junto a su línea base determinista (FR-022): si el pronóstico no
 * supera esa línea base en la validación retrospectiva, se dice explícitamente y se recomienda la
 * línea base (SC-004). Un producto sin histórico suficiente se marca "datos insuficientes"
 * (FR-023), nunca un número. La proyección es un valor estimado: color `estimado`, no la tinta
 * del dato.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { obtenerPronostico, type Pronostico } from "../servicios/pronostico";
import estilos from "./VistaPronostico.module.css";

type Horizonte = "corto" | "medio";

export function VistaPronostico({
  idProducto,
  idSucursal,
}: {
  idProducto: number;
  idSucursal: number;
}) {
  const [horizonte, setHorizonte] = useState<Horizonte>("corto");
  const [pronostico, setPronostico] = useState<Pronostico | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    setCargando(true);
    setError(null);
    setPronostico(null);
    obtenerPronostico(idProducto, idSucursal, horizonte)
      .then(setPronostico)
      .catch((e) => {
        if (e instanceof ErrorApi && e.status === 409) {
          setError(e.message);
        } else {
          setError(e instanceof ErrorApi ? e.message : "No se pudo generar el pronóstico.");
        }
      })
      .finally(() => setCargando(false));
  }, [idProducto, idSucursal, horizonte]);

  const datosInsuficientes = pronostico?.motivo_no_vigente === "datos insuficientes";

  return (
    <div className={estilos.contenedor}>
      <div className={estilos.controles}>
        {(["corto", "medio"] as const).map((h) => (
          <button
            key={h}
            className={horizonte === h ? estilos.horizonteActivo : estilos.horizonteInactivo}
            onClick={() => setHorizonte(h)}
          >
            {h === "corto" ? "Corto (14 días)" : "Medio (30 días)"}
          </button>
        ))}
      </div>

      {cargando && <p className={estilos.instruccion}>Generando pronóstico…</p>}
      {error && <p className={estilos.error}>{error}</p>}

      {pronostico && datosInsuficientes && (
        <p className={estilos.instruccion}>
          Datos insuficientes: este producto todavía no tiene suficiente historial de demanda para
          arriesgar un pronóstico. No se muestra ningún número.
        </p>
      )}

      {pronostico && !datosInsuficientes && (
        <div key={`${idProducto}-${horizonte}`} className={estilos.revelar}>
          {pronostico.vigente ? (
            <p className={`${estilos.veredicto} ${estilos.veredictoVigente}`}>
              <span className={estilos.puntoHueco} aria-hidden="true" />
              Pronóstico vigente: supera a la línea base en la validación retrospectiva.
            </p>
          ) : (
            <p className={`${estilos.veredicto} ${estilos.veredictoLineaBase}`}>
              <span className={estilos.puntoMedio} aria-hidden="true" />
              El pronóstico no supera su línea base — se recomienda la línea base
              ({pronostico.valor_linea_base} /día).
            </p>
          )}

          <p className={estilos.factores}>
            Suavizado exponencial simple (α {pronostico.factores.alfa_usado}), nivel{" "}
            {pronostico.factores.nivel_suavizado}. Datos de {pronostico.periodo_datos_desde} a{" "}
            {pronostico.periodo_datos_hasta}. Línea base {pronostico.valor_linea_base}.
            {pronostico.error_retrospectivo &&
              ` Error retrospectivo: ${pronostico.error_retrospectivo} vs ${pronostico.error_linea_base} de la línea base.`}
            {pronostico.factores.multiplicadores_tramo &&
              " Con multiplicadores de estacionalidad intramensual por tramo del mes."}
          </p>

          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Día</th>
                <th>Demanda pronosticada</th>
              </tr>
            </thead>
            <tbody>
              {pronostico.serie_pronosticada.map((p) => (
                <tr key={p.periodo}>
                  <td>{p.periodo}</td>
                  <td className={estilos.proyeccion}>{Number(p.valor).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
