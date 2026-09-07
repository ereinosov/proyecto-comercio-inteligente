/**
 * Selector de producto con buscador por nombre. Mismo patrón de interacción que
 * IdentificarCliente.tsx (buscar mientras se escribe, elegir de una lista de resultados),
 * pero para `Producto` en vez de `Cliente`. Reutiliza servicios/productos.ts para la búsqueda:
 * el catálogo no expone endpoint de búsqueda, así que se filtra en cliente por subcadena del
 * nombre sobre `listarProductos(idSucursal)`.
 *
 * Registro de Operación (mismo que IdentificarCliente): sin Verde Rasero, sin animación.
 * Sustituye a un input de "Producto (id)" en crudo: nadie debería teclear un identificador.
 */

import { useEffect, useMemo, useState } from "react";
import { listarProductos, type Producto } from "../servicios/productos";
import estilos from "./IdentificarCliente.module.css";

interface Props {
  idSucursal: number;
  seleccionado: Producto | null;
  onSeleccionar: (producto: Producto | null) => void;
  /** Abre el buscador de entrada, sin el paso previo "+ Elegir producto". Para el flujo de
   *  caja, de mayor frecuencia: el cajero ya quiere teclear el nombre. */
  autoAbrir?: boolean;
  /** US14: existencia total por id_producto, para mostrarla junto a cada resultado. */
  existencias?: Map<number, number>;
}

export function SelectorProducto({
  idSucursal,
  seleccionado,
  onSeleccionar,
  autoAbrir = false,
  existencias,
}: Props) {
  const [abierto, setAbierto] = useState(autoAbrir);
  const [busqueda, setBusqueda] = useState("");
  const [catalogo, setCatalogo] = useState<Producto[]>([]);

  useEffect(() => {
    if (!abierto || catalogo.length > 0) return;
    listarProductos(idSucursal)
      .then(setCatalogo)
      .catch(() => setCatalogo([]));
  }, [abierto, idSucursal, catalogo.length]);

  // No se muestra el catálogo entero por defecto: los resultados aparecen a medida que se
  // escribe. Sin término no hay lista (evita el "muro" con scrollbar de todo el catálogo).
  const resultados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase();
    if (!termino) return [];
    return catalogo.filter((p) => p.nombre.toLowerCase().includes(termino)).slice(0, 8);
  }, [busqueda, catalogo]);

  function elegir(producto: Producto) {
    onSeleccionar(producto);
    setAbierto(false);
    setBusqueda("");
  }

  if (seleccionado) {
    return (
      <span className={estilos.chip}>
        {seleccionado.nombre}
        <button
          type="button"
          className={estilos.quitar}
          onClick={() => onSeleccionar(null)}
          aria-label="Quitar producto"
        >
          ✕
        </button>
      </span>
    );
  }

  if (!abierto) {
    return (
      <button type="button" className={estilos.abrir} onClick={() => setAbierto(true)}>
        + Elegir producto
      </button>
    );
  }

  // La búsqueda vive en una caja del alto de un control; los resultados FLOTAN debajo (panel
  // flotante, DESIGN.md "Identificar cliente") para no empujar la fila de "agregar producto"
  // ni desalinear el campo Cantidad.
  return (
    <div className={estilos.caja}>
      <input
        className={estilos.input}
        type="text"
        placeholder="Buscar por nombre…"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        onKeyDown={(e) => {
          // Selección rápida: Enter elige el primer resultado, para no añadir pasos frente
          // al <select> anterior cuando el cajero ya sabe el nombre exacto.
          if (e.key === "Enter" && resultados.length > 0) {
            e.preventDefault();
            elegir(resultados[0]);
          }
          if (e.key === "Escape") {
            setAbierto(false);
            setBusqueda("");
          }
        }}
        autoFocus
      />
      <div className={estilos.flotante}>
        {busqueda.trim() === "" ? (
          <p className={estilos.pista}>Escribe el nombre del producto para ver resultados.</p>
        ) : resultados.length === 0 ? (
          <p className={estilos.pista}>Ningún producto coincide con «{busqueda.trim()}».</p>
        ) : (
          <ul className={estilos.resultados}>
            {resultados.map((p) => {
              const stock = existencias?.get(p.id_producto);
              return (
                <li key={p.id_producto}>
                  <button
                    type="button"
                    className={estilos.filaResultado}
                    onClick={() => elegir(p)}
                  >
                    {p.nombre}
                    {stock !== undefined && (
                      <span className={stock <= 0 ? estilos.stockCritico : estilos.stock}>
                        Stock {stock}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        <button
          type="button"
          className={estilos.enlace}
          onClick={() => {
            setAbierto(false);
            setBusqueda("");
          }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
