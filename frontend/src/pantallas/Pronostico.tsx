/**
 * Pantalla de Pronóstico de Demanda (004-pronostico-demanda). Registro de Análisis: una decisión
 * por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md). Este módulo no tiene ninguna
 * superficie en el registro de Operación — no participa de la caja.
 *
 * Por producto y sucursal, cuatro vistas: el pronóstico (User Story 3), la serie de demanda
 * observada y corregida por los cuatro ejes (User Stories 1, 4, 5, 6), la validación de la
 * descensura contra datos sintéticos (User Story 2), y la declaración de sustitutos (User Story 6).
 */

import { useEffect, useState } from "react";
import { DeclararSustituto } from "../componentes/DeclararSustituto";
import { SerieDemanda } from "../componentes/SerieDemanda";
import { ValidacionDescensura } from "../componentes/ValidacionDescensura";
import { VistaPronostico } from "../componentes/VistaPronostico";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import estilos from "./Pronostico.module.css";

type Vista = "pronostico" | "serie" | "validacion" | "sustitutos";

const VISTAS: { clave: Vista; texto: string }[] = [
  { clave: "pronostico", texto: "Pronóstico" },
  { clave: "serie", texto: "Serie de demanda" },
  { clave: "validacion", texto: "Validación de la descensura" },
  { clave: "sustitutos", texto: "Sustitutos" },
];

export function Pronostico({ idSucursal }: { idSucursal: number }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);
  const [vista, setVista] = useState<Vista>("pronostico");

  useEffect(() => {
    setCargando(true);
    setError(null);
    setIdSeleccionado(null);
    setVista("pronostico");
    listarProductos(idSucursal)
      .then(setProductos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los productos.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal]);

  const productoSeleccionado = productos.find((p) => p.id_producto === idSeleccionado) ?? null;

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Pronóstico de Demanda</h1>
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
                    {producto.nombre}
                  </button>
                </li>
              ))}
            </ul>

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
                    {VISTAS.map((v) => (
                      <button
                        key={v.clave}
                        className={
                          vista === v.clave ? estilos.vistaActiva : estilos.vistaInactiva
                        }
                        onClick={() => setVista(v.clave)}
                      >
                        {v.texto}
                      </button>
                    ))}
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
