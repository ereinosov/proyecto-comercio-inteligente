/**
 * Declarar relaciones de sustitución de un producto (T066, User Story 6 de
 * 004-pronostico-demanda). Registro de Análisis.
 *
 * Declaración MANUAL y dirigida (FR-032): "si ESTE producto se agota, la demanda puede irse a…".
 * El sistema no infiere sustitutos; sólo registra los que el encargado declara. La señal y el
 * ajuste cruzado de la descensura (User Story 6) usan estas relaciones.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  declararSustitucion,
  listarSustituciones,
  retirarSustitucion,
  type Sustitucion,
} from "../servicios/pronostico";
import { listarProductos, type Producto } from "../servicios/productos";
import estilos from "./DeclararSustituto.module.css";

export function DeclararSustituto({
  idProducto,
  idSucursal,
}: {
  idProducto: number;
  idSucursal: number;
}) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [relaciones, setRelaciones] = useState<Sustitucion[]>([]);
  const [elegido, setElegido] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  function recargar() {
    setError(null);
    Promise.all([listarProductos(idSucursal), listarSustituciones(idProducto)])
      .then(([ps, rs]) => {
        setProductos(ps);
        setRelaciones(rs);
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los sustitutos.")
      );
  }

  useEffect(recargar, [idProducto, idSucursal]);

  const nombre = (id: number) =>
    productos.find((p) => p.id_producto === id)?.nombre ?? `producto #${id}`;
  const candidatos = productos.filter(
    (p) =>
      p.id_producto !== idProducto &&
      !relaciones.some((r) => r.id_producto_sustituto === p.id_producto)
  );

  async function agregar() {
    if (!elegido) return;
    setError(null);
    try {
      await declararSustitucion(idProducto, Number(elegido));
      setElegido("");
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo declarar el sustituto.");
    }
  }

  async function quitar(id: number) {
    setError(null);
    try {
      await retirarSustitucion(id);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo retirar la relación.");
    }
  }

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.explicacion}>
        Si este producto se agota, ¿a qué producto se puede ir su demanda? Se declara a mano; el
        sistema no lo infiere. Estas relaciones alimentan el ajuste de la descensura y la señal de
        demanda inflada por sustitución.
      </p>

      {relaciones.length === 0 ? (
        <p className={estilos.vacio}>Sin sustitutos declarados.</p>
      ) : (
        <ul className={estilos.lista}>
          {relaciones.map((r) => (
            <li key={r.id_sustitucion_producto} className={estilos.item}>
              <span>→ {nombre(r.id_producto_sustituto)}</span>
              <button
                className={estilos.botonQuitar}
                onClick={() => quitar(r.id_sustitucion_producto)}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className={estilos.formulario}>
        <select
          className={estilos.selector}
          value={elegido}
          onChange={(e) => setElegido(e.target.value)}
        >
          <option value="">Elegir un sustituto…</option>
          {candidatos.map((p) => (
            <option key={p.id_producto} value={p.id_producto}>
              {p.nombre}
            </option>
          ))}
        </select>
        <button className={estilos.boton} onClick={agregar} disabled={!elegido}>
          Declarar sustituto
        </button>
      </div>

      {error && <p className={estilos.error}>{error}</p>}
    </div>
  );
}
