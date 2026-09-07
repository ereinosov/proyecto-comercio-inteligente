/**
 * Despacho de un traspaso entre sucursales (T078, US6). La mercancía despachada queda en
 * tránsito: no disponible en ninguna sucursal, pero sigue en el inventario total (FR-018). Tras
 * despachar, se puede confirmar la recepción en destino (RecepcionTraspaso, T079).
 * Registro de Operación (DESIGN.md).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import { type Traspaso, despacharTraspaso } from "../servicios/traspasos";
import { RecepcionTraspaso } from "./RecepcionTraspaso";
import { Boton } from "../componentes/Boton";
import estilos from "./Inventario.module.css";

interface Props {
  idSucursal: number;
}

interface Linea {
  id_producto: number;
  cantidad: string;
}

export function DespachoTraspaso({ idSucursal }: Props) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [idDestino, setIdDestino] = useState<number | "">("");
  const [lineas, setLineas] = useState<Linea[]>([{ id_producto: 0, cantidad: "" }]);
  const [enTransito, setEnTransito] = useState<Traspaso | null>(null);
  const [despachando, setDespachando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarProductos(idSucursal).then(setProductos).catch(() => setProductos([]));
    listarSucursales().then(setSucursales).catch(() => setSucursales([]));
  }, [idSucursal]);

  const destinos = sucursales.filter((s) => s.id_sucursal !== idSucursal);

  function cambiarLinea(i: number, campo: keyof Linea, valor: string) {
    setLineas((prev) =>
      prev.map((l, j) =>
        j === i ? { ...l, [campo]: campo === "id_producto" ? Number(valor) : valor } : l,
      ),
    );
  }

  async function despachar() {
    const renglones = lineas
      .filter((l) => l.id_producto > 0 && Number(l.cantidad) > 0)
      .map((l) => ({ id_producto: l.id_producto, cantidad: Math.trunc(Number(l.cantidad)) }));
    if (idDestino === "" || renglones.length === 0) {
      setError("Elige la sucursal de destino y al menos un producto con cantidad.");
      return;
    }
    setDespachando(true);
    setError(null);
    try {
      const traspaso = await despacharTraspaso({
        id_sucursal_origen: idSucursal,
        id_sucursal_destino: idDestino,
        renglones,
      });
      setEnTransito(traspaso);
    } catch (e) {
      // Incluye `existencia_insuficiente` (409, Corrección 2026-09-07): traspasar más de lo
      // disponible en origen ahora se rechaza. El mensaje del dominio ya trae la acción.
      setError(e instanceof ErrorApi ? e.message : "No se pudo despachar el traspaso.");
    } finally {
      setDespachando(false);
    }
  }

  if (enTransito && enTransito.estado === "en_transito") {
    return (
      <div className={estilos.pantalla}>
        <h2 className={estilos.titulo}>Traspaso #{enTransito.id_traspaso} en tránsito</h2>
        <RecepcionTraspaso
          traspaso={enTransito}
          productos={productos}
          onConfirmado={() => {
            setEnTransito(null);
            setLineas([{ id_producto: 0, cantidad: "" }]);
            setIdDestino("");
          }}
        />
      </div>
    );
  }

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Despachar traspaso</h2>
      <p className={estilos.nota}>
        Lo despachado deja de estar disponible aquí y en destino mientras viaja, pero sigue
        contando en el inventario total del sistema.
      </p>

      <div className={estilos.formulario}>
        <div className={estilos.campo}>
          <label htmlFor="dt-destino">Sucursal de destino</label>
          <select
            id="dt-destino"
            className={estilos.seleccion}
            value={idDestino}
            onChange={(e) => setIdDestino(Number(e.target.value))}
          >
            <option value="" disabled>
              Elige…
            </option>
            {destinos.map((s) => (
              <option key={s.id_sucursal} value={s.id_sucursal}>
                {s.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      <table className={`${estilos.tabla} ${estilos.tablaEditable}`}>
        <thead>
          <tr>
            <th>Producto</th>
            <th className={estilos.num}>Cantidad</th>
          </tr>
        </thead>
        <tbody>
          {lineas.map((l, i) => (
            <tr key={i}>
              <td>
                <select
                  className={estilos.seleccion}
                  aria-label="Producto a traspasar"
                  value={l.id_producto || ""}
                  onChange={(e) => cambiarLinea(i, "id_producto", e.target.value)}
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
              </td>
              <td className={estilos.num}>
                <input
                  className={`${estilos.entrada} ${estilos.numero}`}
                  type="number"
                  min={1}
                  aria-label="Cantidad a traspasar"
                  value={l.cantidad}
                  onChange={(e) => cambiarLinea(i, "cantidad", e.target.value)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.acciones}>
        <Boton
          variante="secundaria"
          onClick={() => setLineas((p) => [...p, { id_producto: 0, cantidad: "" }])}
        >
          + Otro producto
        </Boton>
        <Boton variante="primaria" onClick={despachar} disabled={despachando}>
          {despachando ? "Despachando…" : "Despachar"}
        </Boton>
      </div>
    </div>
  );
}
