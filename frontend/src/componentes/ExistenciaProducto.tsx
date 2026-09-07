/**
 * Existencia de un producto: total en la sucursal + desglose por lote al expandir (US14 de 001).
 *
 * El total lo pasa el padre (una sola consulta `GET /existencias` para toda la pantalla); el
 * desglose por lote se carga perezosamente al expandir (`GET /existencias/lotes`, en orden FEFO).
 *
 * NUNCA muestra costo: es dato de margen (003), no de la caja. El servicio sólo lo devolvería
 * con `incluir_costo`, que esta vista no pide.
 *
 * Una existencia ≤ 0 (dato histórico, ya no se puede crear) se marca en el color "crítico" del
 * sistema — es la señal de que ese producto necesita un conteo.
 */

import { useState } from "react";
import { existenciasPorLote, type LoteExistencia } from "../servicios/inventario";
import estilos from "./ExistenciaProducto.module.css";

interface Props {
  idSucursal: number;
  idProducto: number;
  /** Total en la sucursal, ya resuelto por el padre. `undefined` mientras carga. */
  total: number | undefined;
  registro?: "operacion" | "analisis";
}

function antiguedad(iso: string): string {
  const dias = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  if (dias === 1) return "hace 1 día";
  return `hace ${dias} días`;
}

export function ExistenciaProducto({ idSucursal, idProducto, total, registro = "operacion" }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [lotes, setLotes] = useState<LoteExistencia[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(false);

  function alternar() {
    const siguiente = !abierto;
    setAbierto(siguiente);
    if (siguiente && lotes === null && !cargando) {
      setCargando(true);
      setError(false);
      existenciasPorLote(idSucursal, idProducto)
        .then(setLotes)
        .catch(() => setError(true))
        .finally(() => setCargando(false));
    }
  }

  const critico = total !== undefined && total <= 0;

  return (
    <div className={`${estilos.contenedor} ${estilos[registro]}`}>
      <button
        type="button"
        className={estilos.disparador}
        onClick={alternar}
        aria-expanded={abierto}
      >
        <span className={critico ? estilos.totalCritico : estilos.total}>
          Stock {total === undefined ? "…" : total}
        </span>
        <span className={estilos.caret} aria-hidden="true">
          {abierto ? "▾" : "▸"}
        </span>
      </button>

      {abierto && (
        <div className={estilos.desglose}>
          {cargando && <p className={estilos.nota}>Cargando lotes…</p>}
          {error && <p className={estilos.nota}>No se pudo cargar el desglose por lote.</p>}
          {lotes !== null && lotes.length === 0 && (
            <p className={estilos.nota}>Sin lotes con existencia.</p>
          )}
          {lotes !== null && lotes.length > 0 && (
            <ul className={estilos.lista}>
              {lotes.map((l) => (
                <li key={l.id_lote} className={l.cantidad <= 0 ? estilos.filaCritica : estilos.fila}>
                  <span className={estilos.cantidad}>{l.cantidad}</span>
                  <span className={estilos.detalle}>
                    {l.fecha_caducidad ? `vence ${l.fecha_caducidad}` : "sin caducidad"}
                    {" · "}
                    {antiguedad(l.instante_entrada)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
