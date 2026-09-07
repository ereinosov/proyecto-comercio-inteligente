/**
 * Catálogo de productos en grid para la pantalla de Venta (US12 de 001).
 *
 * Camino ADICIONAL para agregar un producto al ticket — convive con el buscador
 * `SelectorProducto`, no lo reemplaza. Cada tarjeta muestra la imagen del producto (vía
 * `ImagenProducto`, con fallback al ícono de familia de categoría), su nombre, su código y su
 * precio, y un botón "+" que suma el producto al ticket con `onAgregar(producto)` — la MISMA
 * función que usa el buscador, sin lógica de negocio propia.
 *
 * El producto se agrega SÓLO al pulsar "+", no al hacer click en el resto de la tarjeta. El
 * "+" NO usa Verde Rasero: ese color sigue exclusivo del botón Cobrar (La Regla de la Sola
 * Voz).
 *
 * El grid es apoyo, no el protagonista: buscador + chips de categoría arriba, ~6 tarjetas por
 * página, y el paginador (numerado, La Regla del Filtro y la Página) anclado abajo.
 */

import { useEffect, useMemo, useState } from "react";
import type { Categoria, Producto } from "../servicios/productos";
import { ImagenProducto } from "./ImagenProducto";
import { ExistenciaProducto } from "./ExistenciaProducto";
import { EstadoVacio } from "./EstadoVacio";
import { Paginador } from "./Paginador";
import { Buscador } from "./Buscador";
import { formatearMoneda } from "../utilidades/formato";
import estilos from "./CatalogoProductos.module.css";

const POR_PAGINA = 9;

interface Props {
  productos: Producto[];
  categorias: Categoria[];
  onAgregar: (producto: Producto) => void;
  /** US14: existencia total por id_producto en la sucursal del turno (una sola consulta en Venta). */
  existencias: Map<number, number>;
  idSucursal: number;
}

export function CatalogoProductos({
  productos,
  categorias,
  onAgregar,
  existencias,
  idSucursal,
}: Props) {
  const [idCategoria, setIdCategoria] = useState<number | null>(null);
  const [texto, setTexto] = useState("");
  const [pagina, setPagina] = useState(1);

  const nombreCategoria = (id: number | null) =>
    categorias.find((c) => c.id_categoria === id)?.nombre ?? null;

  const categoriasConProductos = useMemo(() => {
    const ids = new Set(productos.map((p) => p.id_categoria));
    return categorias.filter((c) => ids.has(c.id_categoria));
  }, [productos, categorias]);

  const filtrados = useMemo(() => {
    const q = texto.trim().toLowerCase();
    return productos.filter(
      (p) =>
        (idCategoria === null || p.id_categoria === idCategoria) &&
        (q === "" || p.nombre.toLowerCase().includes(q)),
    );
  }, [productos, idCategoria, texto]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));

  useEffect(() => {
    setPagina((p) => Math.min(p, totalPaginas));
  }, [totalPaginas]);
  useEffect(() => setPagina(1), [idCategoria, texto]);

  const visibles = filtrados.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA);

  return (
    <div className={estilos.catalogo}>
      <div className={estilos.filtros}>
        <Buscador valor={texto} onCambiar={setTexto} placeholder="Buscar producto por nombre…" />
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
      </div>

      {filtrados.length === 0 ? (
        <EstadoVacio
          registro="operacion"
          glifo="lista"
          titulo={texto.trim() ? "Ningún producto coincide" : "No hay productos en esta categoría"}
          descripcion={
            texto.trim()
              ? "Prueba con otra parte del nombre, o cambia de categoría."
              : "Elige otra categoría o el filtro «Todos». Los productos se dan de alta desde Administración."
          }
        />
      ) : (
        <>
          <ul className={estilos.grid}>
            {visibles.map((p) => (
              <li key={p.id_producto} className={estilos.tarjeta}>
                <ImagenProducto
                  bloque
                  urlImagen={p.url_imagen}
                  nombreCategoria={nombreCategoria(p.id_categoria)}
                  nombreProducto={p.nombre}
                />
                <div className={estilos.cuerpo}>
                  <span className={estilos.nombre} title={`${p.nombre} · #${p.id_producto}`}>
                    {p.nombre}
                  </span>
                  <div className={estilos.filaPrecio}>
                    <span className={estilos.precio}>
                      {formatearMoneda(p.precio_efectivo)}
                      {p.es_granel ? <span className={estilos.porKg}> /kg</span> : null}
                    </span>
                    <button
                      type="button"
                      className={estilos.mas}
                      onClick={() => onAgregar(p)}
                      aria-label={`Agregar ${p.nombre} al ticket`}
                    >
                      +
                    </button>
                  </div>
                  <ExistenciaProducto
                    idSucursal={idSucursal}
                    idProducto={p.id_producto}
                    total={existencias.get(p.id_producto)}
                  />
                </div>
              </li>
            ))}
          </ul>

          <div className={estilos.pie}>
            <Paginador
              pagina={pagina}
              totalPaginas={totalPaginas}
              onCambiar={setPagina}
              numerado
            />
          </div>
        </>
      )}
    </div>
  );
}
