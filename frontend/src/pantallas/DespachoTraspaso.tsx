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
import { type Traspaso, despacharTraspaso, listarTraspasos } from "../servicios/traspasos";
import { listarExistencias } from "../servicios/inventario";
import { RecepcionTraspaso } from "./RecepcionTraspaso";
import { Boton } from "../componentes/Boton";
import { ExistenciaProducto } from "../componentes/ExistenciaProducto";
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
  // Traspaso cuya recepción se está confirmando ahora (recién despachado o retomado de la lista).
  const [recibiendo, setRecibiendo] = useState<Traspaso | null>(null);
  // Traspasos en tránsito que tocan esta sucursal y siguen sin confirmar recepción.
  const [pendientes, setPendientes] = useState<Traspaso[]>([]);
  const [despachando, setDespachando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // US14: existencia total por producto en la sucursal de ORIGEN.
  const [existencias, setExistencias] = useState<Map<number, number>>(new Map());

  function recargarExistencias() {
    listarExistencias(idSucursal)
      .then((filas) => setExistencias(new Map(filas.map((f) => [f.id_producto, f.cantidad]))))
      .catch(() => setExistencias(new Map()));
  }

  function recargarPendientes() {
    listarTraspasos({
      estado: "en_transito",
      idSucursalOrigen: idSucursal,
      idSucursalDestino: idSucursal,
    })
      .then(setPendientes)
      .catch(() => setPendientes([]));
  }

  useEffect(() => {
    listarProductos(idSucursal).then(setProductos).catch(() => setProductos([]));
    listarSucursales().then(setSucursales).catch(() => setSucursales([]));
    recargarExistencias();
    recargarPendientes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setRecibiendo(traspaso);
      recargarPendientes();
    } catch (e) {
      // Incluye `existencia_insuficiente` (409, Corrección 2026-09-07): traspasar más de lo
      // disponible en origen ahora se rechaza. El mensaje del dominio ya trae la acción.
      setError(e instanceof ErrorApi ? e.message : "No se pudo despachar el traspaso.");
    } finally {
      setDespachando(false);
    }
  }

  if (recibiendo && recibiendo.estado === "en_transito") {
    return (
      <div className={estilos.pantalla}>
        <h2 className={estilos.titulo}>
          Traspaso #{recibiendo.id_traspaso} en tránsito · sucursal {recibiendo.id_sucursal_origen} →{" "}
          {recibiendo.id_sucursal_destino}
        </h2>
        <RecepcionTraspaso
          traspaso={recibiendo}
          productos={productos}
          onConfirmado={() => {
            setRecibiendo(null);
            setLineas([{ id_producto: 0, cantidad: "" }]);
            setIdDestino("");
            recargarExistencias();
            recargarPendientes();
          }}
        />
        <div className={estilos.acciones}>
          <Boton variante="neutra" onClick={() => setRecibiendo(null)}>
            Volver sin confirmar
          </Boton>
        </div>
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

      {pendientes.length > 0 && (
        <div className={estilos.formulario}>
          <h3 className={estilos.titulo}>Traspasos en tránsito</h3>
          <p className={estilos.nota}>
            Sin confirmar recepción. Mientras sigan aquí, esa mercancía no está disponible en
            ninguna sucursal.
          </p>
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Traspaso</th>
                <th>Ruta</th>
                <th>Despachado</th>
                <th className={estilos.num}>Productos</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {pendientes.map((t) => (
                <tr key={t.id_traspaso}>
                  <td>#{t.id_traspaso}</td>
                  <td>
                    Sucursal {t.id_sucursal_origen} → {t.id_sucursal_destino}
                  </td>
                  <td>{new Date(t.instante_despacho).toLocaleString()}</td>
                  <td className={estilos.num}>{t.renglones.length}</td>
                  <td>
                    <Boton variante="secundaria" tamano="sm" onClick={() => setRecibiendo(t)}>
                      Confirmar recepción
                    </Boton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
            <th>En origen</th>
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
              <td>
                {l.id_producto > 0 && (
                  <ExistenciaProducto
                    idSucursal={idSucursal}
                    idProducto={l.id_producto}
                    total={existencias.get(l.id_producto)}
                  />
                )}
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
