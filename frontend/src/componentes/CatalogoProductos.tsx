/**
 * Catálogo de productos en grid para la pantalla de Venta (US12 de 001).
 *
 * Camino ADICIONAL para agregar un producto al ticket — convive con el buscador
 * `SelectorProducto`, no lo reemplaza. Cada tarjeta muestra la imagen del producto (vía
 * `ImagenProducto`, con fallback al ícono de familia de categoría), su nombre, su código y su
 * precio. Al hacer click en una tarjeta se llama a `onAgregar(producto)` — la MISMA función que
 * usa el buscador, sin lógica de negocio propia.
 *
 * El "+" de cada tarjeta NO usa Verde Rasero: ese color sigue exclusivo del botón Cobrar
 * (La Regla de la Sola Voz).
 */

import { useMemo, useState } from "react";
import type { Categoria, Producto } from "../servicios/productos";
import { ImagenProducto } from "./ImagenProducto";
import { EstadoVacio } from "./EstadoVacio";
import { formatearMoneda } from "../utilidades/formato";
import estilos from "./CatalogoProductos.module.css";

interface Props {
  productos: Producto[];
  categorias: Categoria[];
  onAgregar: (producto: Producto) => void;
}

export function CatalogoProductos({ productos, categorias, onAgregar }: Props) {
  const [idCategoria, setIdCategoria] = useState<number | null>(null);

  const nombreCategoria = (id: number | null) =>
    categorias.find((c) => c.id_categoria === id)?.nombre ?? null;

  // Sólo se muestran chips de categorías que tienen al menos un producto en el catálogo.
  const categoriasConProductos = useMemo(() => {
    const ids = new Set(productos.map((p) => p.id_categoria));
    return categorias.filter((c) => ids.has(c.id_categoria));
  }, [productos, categorias]);

  const visibles = useMemo(
    () =>
      idCategoria === null
        ? productos
        : productos.filter((p) => p.id_categoria === idCategoria),
    [productos, idCategoria],
  );

  return (
    <div className={estilos.catalogo}>
      <h2 className={estilos.titulo}>Productos</h2>

      <div className={estilos.chips} role="tablist" aria-label="Filtrar por categoría">
        <button
          type="button"
          role="tab"
          aria-selected={idCategoria === null}
          className={idCategoria === null ? estilos.chipActivo : estilos.chip}
          onClick={() => setIdCategoria(null)}
        >
          Todos
        </button>
        {categoriasConProductos.map((c) => (
          <button
            key={c.id_categoria}
            type="button"
            role="tab"
            aria-selected={idCategoria === c.id_categoria}
            className={idCategoria === c.id_categoria ? estilos.chipActivo : estilos.chip}
            onClick={() => setIdCategoria(c.id_categoria)}
          >
            {c.nombre}
          </button>
        ))}
      </div>

      {visibles.length === 0 ? (
        <EstadoVacio
          registro="operacion"
          glifo="lista"
          titulo="No hay productos en esta categoría"
          descripcion="Elige otra categoría o el filtro «Todos». Los productos se dan de alta desde Administración."
        />
      ) : (
        <ul className={estilos.grid}>
          {visibles.map((p) => (
            <li key={p.id_producto}>
              <button
                type="button"
                className={estilos.tarjeta}
                onClick={() => onAgregar(p)}
                aria-label={`Agregar ${p.nombre} al ticket`}
              >
                <ImagenProducto
                  bloque
                  urlImagen={p.url_imagen}
                  nombreCategoria={nombreCategoria(p.id_categoria)}
                  nombreProducto={p.nombre}
                />
                <span className={estilos.cuerpo}>
                  <span className={estilos.nombre}>{p.nombre}</span>
                  <span className={estilos.codigo}>#{p.id_producto}</span>
                  <span className={estilos.filaPrecio}>
                    <span className={estilos.precio}>
                      {formatearMoneda(p.precio_efectivo)}
                      {p.es_granel ? <span className={estilos.porKg}> / kg</span> : null}
                    </span>
                    <span className={estilos.mas} aria-hidden="true">
                      +
                    </span>
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
