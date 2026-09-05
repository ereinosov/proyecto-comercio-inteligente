/**
 * Pantalla de Precios y Márgenes (T017 User Story 1; T024 rol de producto, User Story 2; T035,
 * T046 sugerencias de precio y colocación, User Story 3 y 4). Registro de Análisis: una decisión
 * por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md) — este módulo no tiene ninguna
 * superficie en el registro de Operación (plan.md, "Sistema de diseño en el frontend").
 *
 * Lista con margen real (columna izquierda) + panel de detalle del producto elegido (rol,
 * sugerencia de precio, sugerencia de colocación) — mismo patrón lista/detalle que ya usa
 * `Clientes.tsx` para el registro de Análisis.
 *
 * `GET /margenes` no incluye el nombre del producto (contracts/openapi.yaml, `MargenProducto`):
 * se cruza aquí con `GET /productos`, que ya existe desde 001, en vez de ampliar ese contrato
 * solo para un dato de presentación.
 */

import { useEffect, useState } from "react";
import { RolProductoSelector } from "../componentes/RolProductoSelector";
import { SugerenciaPrecioColocacion } from "../componentes/SugerenciaPrecioColocacion";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarMargenes, type MargenProducto } from "../servicios/precios";
import { listarProductos, type Producto } from "../servicios/productos";
import estilos from "./Precios.module.css";

function IndicadorMargen({ margen }: { margen: MargenProducto | undefined }) {
  if (!margen || margen.margen === null) {
    return <span className={estilos.margenNoCalculable}>Margen no calculable</span>;
  }

  const porcentaje = Math.round(margen.margen * 100);

  if (!margen.confiable) {
    // FR-004: el costo vigente es cero o negativo. Tres portadores (color, forma, texto) —
    // nunca solo el número — porque es una señal de dato sospechoso, no solo un valor calculado.
    return (
      <span className={estilos.margenNoConfiable}>
        <span className={estilos.puntoMedio} aria-hidden="true" />
        {porcentaje}% — costo no confiable
      </span>
    );
  }

  return <span className={estilos.margenValor}>{porcentaje}%</span>;
}

export function Precios({ idSucursal }: { idSucursal: number }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [margenes, setMargenes] = useState<Map<number, MargenProducto>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    setIdSeleccionado(null);
    Promise.all([listarProductos(idSucursal), listarMargenes(idSucursal)])
      .then(([listaProductos, listaMargenes]) => {
        setProductos(listaProductos);
        setMargenes(new Map(listaMargenes.map((m) => [m.id_producto, m])));
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los márgenes.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal]);

  const productoSeleccionado = productos.find((p) => p.id_producto === idSeleccionado) ?? null;

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Precios y Márgenes</h1>
      </div>

      <div className={estilos.cuerpo}>
        {error && <p className={estilos.error}>{error}</p>}
        {!error && cargando && <p className={estilos.instruccion}>Cargando…</p>}
        {!error && !cargando && productos.length === 0 && (
          <p className={estilos.instruccion}>Todavía no hay productos en el catálogo.</p>
        )}
        {!error && !cargando && productos.length > 0 && (
          <>
            <ul className={estilos.lista}>
              {productos.map((producto) => (
                <li key={producto.id_producto}>
                  <button
                    className={
                      idSeleccionado === producto.id_producto
                        ? `${estilos.bloque} ${estilos.bloqueSeleccionado}`
                        : estilos.bloque
                    }
                    onClick={() => setIdSeleccionado(producto.id_producto)}
                  >
                    <span className={estilos.nombreProducto}>{producto.nombre}</span>
                    <IndicadorMargen margen={margenes.get(producto.id_producto)} />
                  </button>
                </li>
              ))}
            </ul>

            <div className={estilos.panelDetalle}>
              {!productoSeleccionado && (
                <p className={estilos.instruccion}>
                  Elige un producto de la lista para clasificarlo y ver sus sugerencias.
                </p>
              )}
              {productoSeleccionado && (
                <div key={productoSeleccionado.id_producto} className={estilos.detalleRevelado}>
                  <h2 className={estilos.nombreDetalle}>{productoSeleccionado.nombre}</h2>
                  <RolProductoSelector idProducto={productoSeleccionado.id_producto} />
                  <SugerenciaPrecioColocacion
                    idProducto={productoSeleccionado.id_producto}
                    idSucursal={idSucursal}
                  />
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
