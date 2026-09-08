/**
 * Pantalla de Pronóstico de Demanda (004-pronostico-demanda). Registro de Análisis: una decisión
 * por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md). Este módulo no tiene ninguna
 * superficie en el registro de Operación — no participa de la caja.
 *
 * Por producto y sucursal, cuatro vistas: el pronóstico (User Story 3), la serie de demanda
 * observada y corregida por los cuatro ejes (User Stories 1, 4, 5, 6), la validación de la
 * descensura contra datos sintéticos (User Story 2), y la declaración de sustitutos (User Story 6).
 */

import { useEffect, useMemo, useState } from "react";
import { DeclararSustituto } from "../componentes/DeclararSustituto";
import { SerieDemanda } from "../componentes/SerieDemanda";
import { ValidacionDescensura } from "../componentes/ValidacionDescensura";
import { VistaPronostico } from "../componentes/VistaPronostico";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import { Segmentado } from "../componentes/Segmentado";
import { Buscador } from "../componentes/Buscador";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
import { EstadoVacio } from "../componentes/EstadoVacio";
import estilos from "./Pronostico.module.css";

type Vista = "pronostico" | "serie" | "validacion" | "sustitutos";

// BLOQUE 3 — "Validación de la descensura" es herramienta de QA/defensa oral (expone FR-009,
// semilla sintética, código de requisito): no corresponde a la superficie de un encargado real.
// Se deja fuera de la navegación de producto y solo se muestra si se entra por URL directa
// (#pronostico/validacion-descensura). Ver quickstart.md de 004.
const RUTA_QA_DESCENSURA = "pronostico/validacion-descensura";
const qaDescensuraActiva = () =>
  typeof window !== "undefined" &&
  window.location.hash.replace(/^#\/?/, "") === RUTA_QA_DESCENSURA;

const VISTAS: { valor: Vista; texto: string }[] = [
  { valor: "pronostico", texto: "Pronóstico" },
  { valor: "serie", texto: "Serie de demanda" },
  ...(qaDescensuraActiva()
    ? [{ valor: "validacion" as Vista, texto: "Validación de la descensura" }]
    : []),
  { valor: "sustitutos", texto: "Sustitutos" },
];

export function Pronostico({ idSucursal }: { idSucursal: number }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);
  const [vista, setVista] = useState<Vista>(
    qaDescensuraActiva() ? "validacion" : "pronostico"
  );
  // Búsqueda y paginación client-side: el catálogo completo ya llega en una sola llamada
  // (no hay endpoint paginado de productos), así que se filtra y se pagina en memoria —
  // mismo patrón de debounce de 200ms que Clientes.tsx / IdentificarCliente.tsx.
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setBusqueda(texto), 200);
    return () => clearTimeout(t);
  }, [texto]);

  useEffect(() => setPagina(1), [busqueda]);

  useEffect(() => {
    setCargando(true);
    setError(null);
    setIdSeleccionado(null);
    setVista(qaDescensuraActiva() ? "validacion" : "pronostico");
    setTexto("");
    setBusqueda("");
    setPagina(1);
    listarProductos(idSucursal)
      .then(setProductos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los productos.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal]);

  const productosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return q ? productos.filter((p) => p.nombre.toLowerCase().includes(q)) : productos;
  }, [productos, busqueda]);

  const totalPaginas = Math.max(1, Math.ceil(productosFiltrados.length / TAMANO_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const productosPagina = productosFiltrados.slice(
    (paginaActual - 1) * TAMANO_PAGINA,
    paginaActual * TAMANO_PAGINA,
  );

  const productoSeleccionado = productos.find((p) => p.id_producto === idSeleccionado) ?? null;

  return (
    <div className={estilos.pantalla}>
      <EncabezadoPantalla titulo="Pronóstico de Demanda" registro="analisis" />

      <div className={estilos.cuerpo}>
        {error && <p className={estilos.error}>{error}</p>}
        {!error && cargando && <p className={estilos.instruccion}>Cargando…</p>}
        {!error && !cargando && productos.length === 0 && (
          <p className={estilos.instruccion}>Todavía no hay productos en el catálogo.</p>
        )}
        {!error && !cargando && productos.length > 0 && (
          <>
            <div className={estilos.lista}>
              <Buscador
                valor={texto}
                onCambiar={setTexto}
                placeholder="Buscar producto por nombre…"
              />
              {productosFiltrados.length === 0 ? (
                <EstadoVacio
                  glifo="lista"
                  titulo="Ningún producto coincide con la búsqueda"
                  descripcion="Prueba con otra parte del nombre; la búsqueda ignora mayúsculas."
                  registro="analisis"
                />
              ) : (
                <>
                  <ul className={estilos.listaUl}>
                    {productosPagina.map((producto) => (
                      <li key={producto.id_producto}>
                        <button
                          className={
                            idSeleccionado === producto.id_producto
                              ? `${estilos.bloque} ${estilos.bloqueSeleccionado}`
                              : estilos.bloque
                          }
                          onClick={() => setIdSeleccionado(producto.id_producto)}
                        >
                          {producto.nombre}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <Paginador pagina={paginaActual} totalPaginas={totalPaginas} onCambiar={setPagina} />
                </>
              )}
            </div>

            <div className={estilos.panelDetalle}>
              {!productoSeleccionado && (
                <p className={estilos.instruccion}>
                  Elige un producto para ver su pronóstico y su serie de demanda corregida.
                </p>
              )}
              {productoSeleccionado && (
                <div key={productoSeleccionado.id_producto} className={estilos.detalleRevelado}>
                  <h2 className={estilos.nombreDetalle}>{productoSeleccionado.nombre}</h2>
                  <div className={estilos.selectorVista}>
                    <Segmentado
                      opciones={VISTAS}
                      activa={vista}
                      onCambiar={setVista}
                      registro="operacion"
                      etiqueta="Vista del producto"
                    />
                  </div>

                  {vista === "pronostico" && (
                    <VistaPronostico
                      idProducto={productoSeleccionado.id_producto}
                      idSucursal={idSucursal}
                    />
                  )}
                  {vista === "serie" && (
                    <SerieDemanda
                      idProducto={productoSeleccionado.id_producto}
                      idSucursal={idSucursal}
                    />
                  )}
                  {vista === "validacion" && (
                    <ValidacionDescensura
                      idProducto={productoSeleccionado.id_producto}
                      idSucursal={idSucursal}
                    />
                  )}
                  {vista === "sustitutos" && (
                    <DeclararSustituto
                      idProducto={productoSeleccionado.id_producto}
                      idSucursal={idSucursal}
                    />
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
