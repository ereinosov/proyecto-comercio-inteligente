/**
 * Conteo físico de inventario (T070). Inicia un conteo programado acotado a la sucursal del
 * turno y, opcionalmente, a un subconjunto de productos (FR-029). Una vez abierto, entrega el
 * flujo de captura y resolución a `ResolucionConteo` (T071).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import { type ConteoFisico as Conteo, iniciarConteo } from "../servicios/conteos";
import { ResolucionConteo } from "./ResolucionConteo";
import { Boton } from "../componentes/Boton";
import { Buscador } from "../componentes/Buscador";
import estilos from "./ConteoFisico.module.css";

interface Props {
  idSucursal: number;
}

export function ConteoFisico({ idSucursal }: Props) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [acotar, setAcotar] = useState(false);
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());
  const [filtro, setFiltro] = useState("");
  const [conteo, setConteo] = useState<Conteo | null>(null);
  const [iniciando, setIniciando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarProductos(idSucursal).then(setProductos).catch(() => setProductos([]));
  }, [idSucursal]);

  function alternar(idProducto: number) {
    setSeleccion((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(idProducto)) siguiente.delete(idProducto);
      else siguiente.add(idProducto);
      return siguiente;
    });
  }

  async function iniciar() {
    setIniciando(true);
    setError(null);
    try {
      const idProductos = acotar && seleccion.size > 0 ? [...seleccion] : undefined;
      const abierto = await iniciarConteo({ id_sucursal: idSucursal, id_productos: idProductos });
      setConteo(abierto);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo iniciar el conteo.");
    } finally {
      setIniciando(false);
    }
  }

  if (conteo && conteo.estado === "abierto") {
    return (
      <ResolucionConteo
        conteo={{
          ...conteo,
          renglones:
            acotar && seleccion.size > 0
              ? [...seleccion].map((id_producto) => ({
                  id_producto,
                  id_lote: null,
                  cantidad_esperada: 0,
                  cantidad_contada: 0,
                  diferencia: 0,
                }))
              : undefined,
        }}
        productos={productos}
        onResuelto={setConteo}
        onCancelar={() => setConteo(null)}
      />
    );
  }

  if (conteo && conteo.estado === "resuelto") {
    return (
      <div className={estilos.pantalla}>
        <h2 className={estilos.titulo}>Conteo #{conteo.id_conteo_fisico} resuelto</h2>
        <p className={estilos.subtitulo}>
          El ajuste quedó registrado como movimiento trazable a este conteo.
        </p>
        <div className={estilos.fila}>
          <Boton
            variante="primaria"
            onClick={() => {
              setConteo(null);
              setSeleccion(new Set());
              setAcotar(false);
            }}
          >
            Nuevo conteo
          </Boton>
        </div>
      </div>
    );
  }

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Iniciar conteo físico</h2>
      <p className={estilos.subtitulo}>
        El conteo compara lo que hay en estantería y bodega contra el saldo que el sistema
        calculó de sus movimientos. Clasificar la causa de una diferencia no es tarea de este
        módulo.
      </p>

      <label>
        <input type="checkbox" checked={acotar} onChange={(e) => setAcotar(e.target.checked)} />{" "}
        Acotar a un subconjunto de productos
      </label>

      {acotar &&
        (() => {
          const norm = filtro.trim().toLowerCase();
          const visibles = norm
            ? productos.filter((p) => p.nombre.toLowerCase().includes(norm))
            : productos;
          return (
            <>
              <div className={estilos.fila}>
                <div className={estilos.campo} style={{ flex: 1, minWidth: 200 }}>
                  <Buscador
                    valor={filtro}
                    onCambiar={setFiltro}
                    placeholder="Buscar producto por nombre…"
                  />
                </div>
                <Boton
                  variante="secundaria"
                  onClick={() =>
                    setSeleccion((prev) => {
                      const s = new Set(prev);
                      visibles.forEach((p) => s.add(p.id_producto));
                      return s;
                    })
                  }
                >
                  Seleccionar los visibles
                </Boton>
              </div>
              <p className={estilos.subtitulo}>{seleccion.size} seleccionados</p>
              <div className={estilos.seleccionAlcance}>
                {visibles.map((p) => (
                  <label key={p.id_producto}>
                    <input
                      type="checkbox"
                      checked={seleccion.has(p.id_producto)}
                      onChange={() => alternar(p.id_producto)}
                    />
                    {p.nombre}
                  </label>
                ))}
              </div>
            </>
          );
        })()}

      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.fila}>
        <Boton variante="primaria" onClick={iniciar} disabled={iniciando}>
          {iniciando ? "Iniciando…" : "Iniciar conteo"}
        </Boton>
      </div>
    </div>
  );
}
