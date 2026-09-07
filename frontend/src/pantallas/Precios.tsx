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
import { listarCategorias, listarProductos, type Categoria, type Producto } from "../servicios/productos";
import { IconoCategoria } from "../componentes/IconoCategoria";
import { EstadoVacio } from "../componentes/EstadoVacio";
import { EsqueletoLista } from "../componentes/Esqueleto";
import { Buscador } from "../componentes/Buscador";
import { MargenPorProductoGrafico } from "../componentes/graficos/MargenPorProductoGrafico";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import estilos from "./Precios.module.css";

// Umbral de margen saludable (fracción). Por debajo, el margen pide atención (ámbar); por
// debajo de cero es una pérdida (crítico). Un margen sano NO se marca en Verde Rasero: ese
// color queda reservado a la caja (DESIGN.md, Regla de la Sola Voz / Registro Sin Dinero).
const MARGEN_SALUDABLE = 0.15;

function IndicadorMargen({ margen }: { margen: MargenProducto | undefined }) {
  if (!margen || margen.margen === null) {
    // Dato faltante, no un juicio de valor: gris/neutral, nunca un semántico (DESIGN.md).
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

  if (margen.margen < 0) {
    return (
      <span className={estilos.margenNegativo}>
        <span className={estilos.puntoHueco} aria-hidden="true" />
        {porcentaje}% — pérdida
      </span>
    );
  }

  if (margen.margen < MARGEN_SALUDABLE) {
    return (
      <span className={estilos.margenBajo}>
        <span className={estilos.puntoMedio} aria-hidden="true" />
        {porcentaje}% — margen bajo
      </span>
    );
  }

  return <span className={estilos.margenValor}>{porcentaje}%</span>;
}

// Borde izquierdo del bloque de lista según el semántico del margen — hace la lista escaneable
// de un vistazo sin abrir cada producto (tinte de apoyo, no fondo completo). Neutro cuando el
// margen no es calculable o es sano: el color aparece solo cuando significa algo.
function claseBordeMargen(margen: MargenProducto | undefined): string {
  if (!margen || margen.margen === null || !margen.confiable) return "";
  if (margen.margen < 0) return estilos.bordeNegativo;
  if (margen.margen < MARGEN_SALUDABLE) return estilos.bordeBajo;
  return "";
}

export function Precios({ idSucursal }: { idSucursal: number }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [margenes, setMargenes] = useState<Map<number, MargenProducto>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);
  // Filtro por nombre en el cliente, sin debounce ni paginación: `GET /productos` y
  // `GET /margenes` de esta pantalla se cargan juntos y se cruzan en memoria en un Map para
  // toda la sucursal; paginar partiría ese cruce y la lista está acotada por el catálogo de un
  // minimarket de una sola tienda (decenas, no miles). Si crece, se revisa entonces.
  const [filtro, setFiltro] = useState("");

  useEffect(() => {
    setCargando(true);
    setError(null);
    setIdSeleccionado(null);
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
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
  const filtroNorm = filtro.trim().toLowerCase();
  const productosVisibles = filtroNorm
    ? productos.filter((p) => p.nombre.toLowerCase().includes(filtroNorm))
    : productos;
  const nombreCategoria = (id: number | null) =>
    categorias.find((c) => c.id_categoria === id)?.nombre ?? null;

  return (
    <div className={estilos.pantalla}>
      <EncabezadoPantalla titulo="Precios y Márgenes" registro="analisis" />

      {!error && (
        <div className={estilos.zonaGrafico}>
          <MargenPorProductoGrafico
            productos={productos}
            margenes={margenes}
            cargando={cargando}
          />
        </div>
      )}

      <div className={estilos.cuerpo}>
        {error && <p className={estilos.error}>{error}</p>}
        {!error && cargando && <EsqueletoLista filas={8} registro="analisis" altoFila={54} />}
        {!error && !cargando && productos.length === 0 && (
          <EstadoVacio
            glifo="lista"
            titulo="Todavía no hay productos en el catálogo"
            descripcion="Aquí aparecerá cada producto con su margen real, un ícono por familia de categoría y, al elegirlo, su rol y las sugerencias de precio y colocación."
          />
        )}
        {!error && !cargando && productos.length > 0 && (
          <>
            <div className={estilos.columnaLista}>
              <Buscador
                valor={filtro}
                onCambiar={setFiltro}
                placeholder="Buscar producto por nombre…"
              />
              {productosVisibles.length === 0 ? (
                <p className={estilos.instruccion}>
                  Ningún producto coincide con «{filtro.trim()}».
                </p>
              ) : (
                <ul className={estilos.lista}>
                  {productosVisibles.map((producto) => (
                    <li key={producto.id_producto}>
                      <button
                        className={[
                          estilos.bloque,
                          claseBordeMargen(margenes.get(producto.id_producto)),
                          idSeleccionado === producto.id_producto ? estilos.bloqueSeleccionado : "",
                        ].join(" ")}
                        onClick={() => setIdSeleccionado(producto.id_producto)}
                      >
                        <span className={estilos.nombreProducto}>
                          <IconoCategoria nombreCategoria={nombreCategoria(producto.id_categoria)} />
                          {producto.nombre}
                        </span>
                        <IndicadorMargen margen={margenes.get(producto.id_producto)} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

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
