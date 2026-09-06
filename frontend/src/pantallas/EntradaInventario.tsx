/**
 * Registro de una entrada de inventario por compra a proveedor (T048, US2). Registro de
 * Operación (DESIGN.md): producto, cantidad, costo y —si aplica— caducidad. Solo costo, nunca
 * margen (FR-014).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import { registrarEntrada } from "../servicios/inventario";
import { formatearMoneda } from "../utilidades/formato";
import estilos from "./Inventario.module.css";

interface Props {
  idSucursal: number;
}

export function EntradaInventario({ idSucursal }: Props) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [idProducto, setIdProducto] = useState<number | "">("");
  const [cantidad, setCantidad] = useState("");
  const [costo, setCosto] = useState("");
  const [caducidad, setCaducidad] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);

  useEffect(() => {
    listarProductos(idSucursal).then(setProductos).catch(() => setProductos([]));
  }, [idSucursal]);

  const producto = productos.find((p) => p.id_producto === idProducto);

  async function registrar() {
    if (idProducto === "" || !cantidad || !costo) {
      setError("Indica producto, cantidad y costo.");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      const lote = await registrarEntrada({
        id_sucursal: idSucursal,
        id_producto: idProducto,
        cantidad: Math.trunc(Number(cantidad)),
        costo_unitario: Number(costo).toFixed(4),
        fecha_caducidad: caducidad || null,
      });
      setConfirmacion(
        `Lote #${lote.id_lote}: ${lote.cantidad_restante} ${
          producto?.es_granel ? "g" : "u"
        } a ${formatearMoneda(lote.costo_unitario)} c/u`,
      );
      setCantidad("");
      setCosto("");
      setCaducidad("");
      setTimeout(() => setConfirmacion(null), 3500);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo registrar la entrada.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Entrada de mercancía</h2>
      <p className={estilos.nota}>
        Registra qué llegó, cuánto, a qué costo y —si es perecedero— con qué caducidad. Este
        módulo guarda el costo; no calcula ningún margen.
      </p>

      <div className={estilos.formulario}>
        <div className={estilos.campo}>
          <label htmlFor="ei-producto">Producto</label>
          <select
            id="ei-producto"
            className={estilos.seleccion}
            value={idProducto}
            onChange={(e) => setIdProducto(Number(e.target.value))}
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
        <div className={estilos.campo}>
          <label htmlFor="ei-cantidad">
            Cantidad {producto?.es_granel ? "(gramos)" : "(unidades)"}
          </label>
          <input
            id="ei-cantidad"
            className={`${estilos.entrada} ${estilos.numero}`}
            type="number"
            min={1}
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
        </div>
        <div className={estilos.campo}>
          <label htmlFor="ei-costo">Costo unitario</label>
          <input
            id="ei-costo"
            className={`${estilos.entrada} ${estilos.numero}`}
            type="number"
            min={0}
            step="0.0001"
            value={costo}
            onChange={(e) => setCosto(e.target.value)}
          />
        </div>
        {producto?.lleva_caducidad && (
          <div className={estilos.campo}>
            <label htmlFor="ei-caducidad">Caducidad</label>
            <input
              id="ei-caducidad"
              className={estilos.entrada}
              type="date"
              value={caducidad}
              onChange={(e) => setCaducidad(e.target.value)}
            />
          </div>
        )}
        <button className={estilos.boton} onClick={registrar} disabled={guardando}>
          {guardando ? "Registrando…" : "Registrar entrada"}
        </button>
      </div>

      {error && <p className={estilos.error}>{error}</p>}
      {confirmacion && <p className={estilos.ok}>{confirmacion}</p>}
    </div>
  );
}
