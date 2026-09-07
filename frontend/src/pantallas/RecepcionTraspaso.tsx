/**
 * Confirmación de la recepción de un traspaso (T079, US6). Muestra la discrepancia por producto
 * cuando lo recibido difiere de lo despachado, con tres portadores (texto + forma + color) y
 * sin clasificarla ni absorberla (FR-019).
 */

import { useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { type Producto } from "../servicios/productos";
import { type Traspaso, recibirTraspaso } from "../servicios/traspasos";
import estilos from "./Inventario.module.css";

interface Props {
  traspaso: Traspaso;
  productos: Producto[];
  onConfirmado: (traspaso: Traspaso) => void;
}

function Discrepancia({ valor }: { valor: number | null }) {
  if (valor === null || valor === 0) {
    return (
      <span className={`${estilos.discrepancia} ${estilos.discrepanciaCuadra}`}>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <line x1="1" y1="5" x2="9" y2="5" stroke="currentColor" strokeWidth="2" />
        </svg>
        cuadra
      </span>
    );
  }
  const falta = valor < 0;
  return (
    <span
      className={`${estilos.discrepancia} ${
        falta ? estilos.discrepanciaFalta : estilos.discrepanciaSobra
      }`}
    >
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
        {falta ? (
          <polygon points="5,9 1,2 9,2" fill="currentColor" />
        ) : (
          <polygon points="5,1 9,8 1,8" fill="currentColor" />
        )}
      </svg>
      {valor > 0 ? `+${valor}` : valor} {falta ? "faltan" : "sobran"}
    </span>
  );
}

export function RecepcionTraspaso({ traspaso, productos, onConfirmado }: Props) {
  const [recibidas, setRecibidas] = useState<Record<number, string>>(() =>
    Object.fromEntries(
      traspaso.renglones.map((r) => [r.id_producto, String(r.cantidad_despachada)]),
    ),
  );
  const [resultado, setResultado] = useState<Traspaso | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nombre = (id: number) =>
    productos.find((p) => p.id_producto === id)?.nombre ?? `Producto ${id}`;

  async function confirmar() {
    setGuardando(true);
    setError(null);
    try {
      const recibido = await recibirTraspaso(
        traspaso.id_traspaso,
        traspaso.renglones.map((r) => ({
          id_producto: r.id_producto,
          cantidad_recibida: Math.max(0, Math.trunc(Number(recibidas[r.id_producto] ?? "0"))),
        })),
      );
      setResultado(recibido);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo confirmar la recepción.");
    } finally {
      setGuardando(false);
    }
  }

  if (resultado) {
    return (
      <div>
        <p className={estilos.nota}>Traspaso #{resultado.id_traspaso} recibido.</p>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Producto</th>
              <th className={estilos.num}>Despachado</th>
              <th className={estilos.num}>Recibido</th>
              <th className={estilos.num}>Discrepancia</th>
            </tr>
          </thead>
          <tbody>
            {resultado.renglones.map((r) => (
              <tr key={r.id_producto}>
                <td>{nombre(r.id_producto)}</td>
                <td className={estilos.num}>{r.cantidad_despachada}</td>
                <td className={estilos.num}>{r.cantidad_recibida}</td>
                <td className={estilos.num}>
                  <Discrepancia valor={r.discrepancia} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className={estilos.acciones}>
          <button className={estilos.botonSecundario} onClick={() => onConfirmado(resultado)}>
            Listo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <p className={estilos.nota}>
        Confirma cuánto llegó de cada producto del traspaso #{traspaso.id_traspaso}.
      </p>
      <table className={`${estilos.tabla} ${estilos.tablaEditable}`}>
        <thead>
          <tr>
            <th>Producto</th>
            <th className={estilos.num}>Despachado</th>
            <th className={estilos.num}>Recibido</th>
          </tr>
        </thead>
        <tbody>
          {traspaso.renglones.map((r) => (
            <tr key={r.id_producto}>
              <td>{nombre(r.id_producto)}</td>
              <td className={estilos.num}>{r.cantidad_despachada}</td>
              <td className={estilos.num}>
                <input
                  className={`${estilos.entrada} ${estilos.numero}`}
                  type="number"
                  min={0}
                  aria-label={`Cantidad recibida de ${nombre(r.id_producto)}`}
                  value={recibidas[r.id_producto] ?? ""}
                  onChange={(e) =>
                    setRecibidas((prev) => ({ ...prev, [r.id_producto]: e.target.value }))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className={estilos.error}>{error}</p>}
      <div className={estilos.acciones}>
        <button className={estilos.boton} onClick={confirmar} disabled={guardando}>
          {guardando ? "Confirmando…" : "Confirmar recepción"}
        </button>
      </div>
    </div>
  );
}
