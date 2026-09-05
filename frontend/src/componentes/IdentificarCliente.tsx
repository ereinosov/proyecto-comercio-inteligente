/**
 * Identificación opcional de cliente en el punto de venta (T014, FR-003). Vive en el
 * encabezado de Venta.tsx, nunca en el flujo de cobro: el cajero puede ignorarlo por completo
 * y la venta se completa exactamente igual (Principio II — ver spec.md, Clarifications).
 *
 * Registro de Operación: sin Verde Rasero (reservado al botón de cobro, DESIGN.md, La Regla
 * de la Sola Voz), sin animación de revelación — esta pantalla no muestra ningún valor de
 * cliente todavía, eso lo añade User Story 2.
 */

import { useEffect, useState } from "react";
import {
  buscarClientes,
  registrarCliente,
  type Cliente,
  type ClienteResumen,
} from "../servicios/clientes";
import estilos from "./IdentificarCliente.module.css";

export interface ClienteSeleccionado {
  id_cliente: number;
  nombre: string;
  /** Puntuación compuesta (User Story 2). `null` = datos insuficientes, nunca un valor por
   * defecto (FR-007). Viene ya incluida en la respuesta de búsqueda/alta; no se pide aparte. */
  valor: number | null;
}

interface Props {
  seleccionado: ClienteSeleccionado | null;
  onSeleccionar: (cliente: ClienteSeleccionado | null) => void;
}

export function IdentificarCliente({ seleccionado, onSeleccionar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<ClienteResumen[]>([]);
  const [creandoNuevo, setCreandoNuevo] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [fechaNacimientoNueva, setFechaNacimientoNueva] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    const temporizador = setTimeout(() => {
      buscarClientes(busqueda).then(setResultados);
    }, 200);
    return () => clearTimeout(temporizador);
  }, [busqueda, abierto]);

  function elegir(cliente: ClienteResumen) {
    if (cliente.nombre === null) return; // cliente anonimizado; no debería aparecer en la búsqueda
    onSeleccionar({ id_cliente: cliente.id_cliente, nombre: cliente.nombre, valor: cliente.valor });
    cerrar();
  }

  function cerrar() {
    setAbierto(false);
    setBusqueda("");
    setResultados([]);
    setCreandoNuevo(false);
    setNombreNuevo("");
    setFechaNacimientoNueva("");
  }

  async function guardarNuevo() {
    if (!nombreNuevo.trim() || !fechaNacimientoNueva) return;
    setGuardando(true);
    try {
      const cliente: Cliente = await registrarCliente({
        nombre: nombreNuevo.trim(),
        fecha_nacimiento: fechaNacimientoNueva,
      });
      // Cliente recién creado: cero visitas, sin historial suficiente todavía (FR-007).
      onSeleccionar({ id_cliente: cliente.id_cliente, nombre: cliente.nombre ?? nombreNuevo, valor: null });
      cerrar();
    } finally {
      setGuardando(false);
    }
  }

  if (seleccionado) {
    return (
      <span className={estilos.chip}>
        Cliente: {seleccionado.nombre}
        <button
          type="button"
          className={estilos.quitar}
          onClick={() => onSeleccionar(null)}
          aria-label="Quitar cliente identificado"
        >
          ✕
        </button>
      </span>
    );
  }

  if (!abierto) {
    return (
      <button type="button" className={estilos.abrir} onClick={() => setAbierto(true)}>
        + Identificar cliente
      </button>
    );
  }

  return (
    <div className={estilos.panel}>
      {!creandoNuevo ? (
        <>
          <input
            className={estilos.input}
            type="text"
            placeholder="Buscar por nombre…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            autoFocus
          />
          <ul className={estilos.resultados}>
            {resultados.map((r) => (
              <li key={r.id_cliente}>
                <button type="button" className={estilos.filaResultado} onClick={() => elegir(r)}>
                  {r.nombre}
                </button>
              </li>
            ))}
          </ul>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.enlace} onClick={() => setCreandoNuevo(true)}>
              + Registrar cliente nuevo
            </button>
            <button type="button" className={estilos.enlace} onClick={cerrar}>
              Cancelar
            </button>
          </div>
        </>
      ) : (
        <>
          <input
            className={estilos.input}
            type="text"
            placeholder="Nombre"
            value={nombreNuevo}
            onChange={(e) => setNombreNuevo(e.target.value)}
            autoFocus
          />
          <input
            className={estilos.input}
            type="date"
            value={fechaNacimientoNueva}
            onChange={(e) => setFechaNacimientoNueva(e.target.value)}
          />
          <div className={estilos.acciones}>
            <button
              type="button"
              className={estilos.enlace}
              onClick={guardarNuevo}
              disabled={guardando || !nombreNuevo.trim() || !fechaNacimientoNueva}
            >
              {guardando ? "Guardando…" : "Guardar"}
            </button>
            <button type="button" className={estilos.enlace} onClick={cerrar}>
              Cancelar
            </button>
          </div>
        </>
      )}
    </div>
  );
}
