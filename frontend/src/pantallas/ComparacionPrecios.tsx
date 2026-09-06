/**
 * Comparación del precio propio contra las observaciones de competencia (T064, US4). Registro de
 * Análisis (DESIGN.md): 6px, Source Serif 4, un bloque por observación. Cada observación muestra
 * su precio normalizado a la misma unidad de medida y su antigüedad con los TRES portadores
 * (color, forma, texto). El sistema NO ajusta ningún precio (FR-028).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import { compararPrecios, type ComparacionPrecios as Comparacion } from "../servicios/competencia";
import { AntiguedadDato } from "../componentes/AntiguedadDato";
import estilos from "./Competencia.module.css";

interface Props {
  idSucursal: number;
}

export function ComparacionPrecios({ idSucursal }: Props) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [idProducto, setIdProducto] = useState<number | "">("");
  const [comparacion, setComparacion] = useState<Comparacion | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarProductos(idSucursal).then(setProductos).catch(() => setProductos([]));
  }, [idSucursal]);

  async function comparar(id: number) {
    setIdProducto(id);
    setCargando(true);
    setError(null);
    try {
      setComparacion(await compararPrecios(id, idSucursal));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la comparación.");
      setComparacion(null);
    } finally {
      setCargando(false);
    }
  }

  const nombreProducto = productos.find((p) => p.id_producto === idProducto)?.nombre;

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Comparación de precios</h2>
      <p className={estilos.instruccion}>
        Tu precio de esta sucursal frente a lo observado en la competencia, cada dato con su
        antigüedad a la vista. Mover el precio es tu decisión: el sistema solo muestra.
      </p>

      <div className={estilos.formulario}>
        <div className={estilos.campo}>
          <label htmlFor="cp-producto">Producto</label>
          <select
            id="cp-producto"
            className={estilos.seleccion}
            value={idProducto}
            onChange={(e) => comparar(Number(e.target.value))}
          >
            <option value="" disabled>
              Elige…
            </option>
            {productos.map((p) => (
              <option key={p.id_producto} value={p.id_producto}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className={estilos.error}>{error}</p>}
      {cargando && <p className={estilos.ok}>Cargando…</p>}

      {comparacion && !cargando && (
        <div className={estilos.comparacion}>
          <p className={estilos.precioPropio}>
            {nombreProducto}: tu precio por unidad de medida es{" "}
            <strong>${comparacion.precio_propio_por_unidad_medida}</strong>
          </p>

          {comparacion.observaciones.length === 0 ? (
            <p className={estilos.ok}>Todavía no hay observaciones de competencia para este producto.</p>
          ) : (
            comparacion.observaciones.map((o) => (
              <div className={estilos.bloqueObs} key={o.id_observacion_precio}>
                <span className={estilos.canal}>{o.canal}</span>
                <span className={estilos.cifras}>
                  Observado: ${o.precio_observado} · {o.presentacion}
                </span>
                {o.comparable ? (
                  <span className={estilos.cifras}>
                    Normalizado: <strong>${o.precio_por_unidad_medida}</strong> por unidad de medida
                  </span>
                ) : (
                  <span className={estilos.noComparable}>
                    Presentación no comparable con tu unidad de medida
                  </span>
                )}
                <AntiguedadDato texto={o.antiguedad_texto} forma={o.indicador_forma} />
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
