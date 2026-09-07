/**
 * Resolución de un conteo físico (T071). Se capturan las cantidades contadas y se muestra la
 * diferencia por producto (y lote, cuando 001 la calcula por lote) contra el saldo que el
 * sistema calculó de sus movimientos. La causa NO se clasifica aquí: eso es de
 * 006-caja-mermas-fraude (FR-031). La diferencia se comunica con tres portadores simultáneos
 * —texto, forma e color— nunca solo por color (DESIGN.md).
 */

import { useMemo, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { type Producto } from "../servicios/productos";
import { type ConteoFisico, resolverConteo } from "../servicios/conteos";
import estilos from "./ConteoFisico.module.css";

interface Props {
  conteo: ConteoFisico;
  productos: Producto[];
  onResuelto: (conteo: ConteoFisico) => void;
  onCancelar: () => void;
}

function IndicadorDiferencia({ valor }: { valor: number }) {
  if (valor === 0) {
    return (
      <span className={`${estilos.diferencia} ${estilos.cuadra}`}>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <line x1="1" y1="5" x2="9" y2="5" stroke="currentColor" strokeWidth="2" />
        </svg>
        cuadra
      </span>
    );
  }
  const faltante = valor < 0;
  return (
    <span
      className={`${estilos.diferencia} ${faltante ? estilos.faltante : estilos.sobrante}`}
    >
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
        {faltante ? (
          <polygon points="5,9 1,2 9,2" fill="currentColor" />
        ) : (
          <polygon points="5,1 9,8 1,8" fill="currentColor" />
        )}
      </svg>
      {valor > 0 ? `+${valor}` : valor} {faltante ? "faltante" : "sobrante"}
    </span>
  );
}

export function ResolucionConteo({ conteo, productos, onResuelto, onCancelar }: Props) {
  const alcance = useMemo<Producto[]>(() => {
    const ids = conteo.renglones?.map((r) => r.id_producto);
    if (ids && ids.length > 0) {
      return productos.filter((p) => ids.includes(p.id_producto));
    }
    return productos;
  }, [conteo, productos]);

  const [contadas, setContadas] = useState<Record<number, string>>({});
  const [resultado, setResultado] = useState<ConteoFisico | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resolver() {
    const renglones = alcance
      .filter((p) => contadas[p.id_producto] !== undefined && contadas[p.id_producto] !== "")
      .map((p) => ({
        id_producto: p.id_producto,
        cantidad_contada: Math.trunc(Number(contadas[p.id_producto])),
      }));
    if (renglones.length === 0) {
      setError("Captura al menos una cantidad contada antes de resolver.");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      const resuelto = await resolverConteo(conteo.id_conteo_fisico, renglones);
      setResultado(resuelto);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo resolver el conteo.");
    } finally {
      setGuardando(false);
    }
  }

  if (resultado) {
    return (
      <div className={estilos.pantalla}>
        <h2 className={estilos.titulo}>Conteo #{resultado.id_conteo_fisico} resuelto</h2>
        <p className={estilos.subtitulo}>
          Diferencia por producto y lote frente al saldo calculado. La causa la clasifica el
          módulo de caja, mermas y fraude.
        </p>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Lote</th>
              <th className={estilos.num}>Esperado</th>
              <th className={estilos.num}>Contado</th>
              <th className={estilos.num}>Diferencia</th>
            </tr>
          </thead>
          <tbody>
            {(resultado.renglones ?? []).map((r, i) => {
              const nombre = productos.find((p) => p.id_producto === r.id_producto)?.nombre;
              return (
                <tr key={`${r.id_producto}-${r.id_lote ?? "sin-lote"}-${i}`}>
                  <td>{nombre ?? `Producto ${r.id_producto}`}</td>
                  <td>{r.id_lote ?? "—"}</td>
                  <td className={estilos.num}>{r.cantidad_esperada}</td>
                  <td className={estilos.num}>{r.cantidad_contada}</td>
                  <td className={estilos.num}>
                    <IndicadorDiferencia valor={r.diferencia} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className={estilos.fila}>
          <button className={estilos.boton} onClick={() => onResuelto(resultado)}>
            Listo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Capturar conteo #{conteo.id_conteo_fisico}</h2>
      <p className={estilos.subtitulo}>
        Escribe lo que contaste en estantería y bodega. Deja en blanco lo que no cuentes en esta
        sesión.
      </p>
      <table className={`${estilos.tabla} ${estilos.tablaEditable}`}>
        <thead>
          <tr>
            <th>Producto</th>
            <th className={estilos.num}>Contado</th>
          </tr>
        </thead>
        <tbody>
          {alcance.map((p) => (
            <tr key={p.id_producto}>
              <td>{p.nombre}</td>
              <td className={estilos.num}>
                <input
                  className={estilos.inputCantidad}
                  type="number"
                  min={0}
                  inputMode="numeric"
                  aria-label={`Cantidad contada de ${p.nombre}`}
                  value={contadas[p.id_producto] ?? ""}
                  onChange={(e) =>
                    setContadas((prev) => ({ ...prev, [p.id_producto]: e.target.value }))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className={estilos.error}>{error}</p>}
      <div className={estilos.fila}>
        <button className={estilos.boton} onClick={resolver} disabled={guardando}>
          {guardando ? "Resolviendo…" : "Resolver conteo"}
        </button>
        <button className={estilos.botonSecundario} onClick={onCancelar} disabled={guardando}>
          Volver
        </button>
      </div>
    </div>
  );
}
