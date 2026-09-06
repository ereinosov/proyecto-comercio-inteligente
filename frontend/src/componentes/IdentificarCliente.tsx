/**
 * Identificación opcional de cliente en el punto de venta (FR-003). Vive en el encabezado de
 * Venta.tsx, nunca en el flujo de cobro: el cajero puede ignorarlo por completo y la venta se
 * completa exactamente igual (Principio II).
 *
 * Registro de Operación: sin Verde Rasero (reservado al botón de cobro, La Regla de la Sola
 * Voz), sin animación de revelación.
 *
 * - Colapsado: enlace de texto en Tinta Suave.
 * - Buscar: panel flotante en Superficie Alta, filo de Operación (DESIGN.md, "Identificar
 *   cliente").
 * - Registrar / editar un cliente: `ModalAdministrable` (La Regla del Modal Administrable) —
 *   el alta y la edición de un cliente son un formulario de dato maestro, mismo componente que
 *   Administración y que la edición desde Clientes.tsx. Aquí se captura además "Cédula o RUC
 *   (opcional)" (FR-017); si el backend responde 422/409, el mensaje devuelto se muestra en el
 *   propio modal, nunca como alerta genérica.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  buscarClientes,
  registrarCliente,
  type Cliente,
  type ClienteResumen,
} from "../servicios/clientes";
import { ModalAdministrable } from "./ModalAdministrable";
import { CampoIdentificador } from "./CampoIdentificador";
import { Obligatorio } from "./Obligatorio";
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
  const [form, setForm] = useState({ nombre: "", fecha_nacimiento: "", identificador: "" });
  const [guardando, setGuardando] = useState(false);
  const [errorAlta, setErrorAlta] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto || creandoNuevo) return;
    const temporizador = setTimeout(() => {
      buscarClientes(busqueda).then(setResultados);
    }, 200);
    return () => clearTimeout(temporizador);
  }, [busqueda, abierto, creandoNuevo]);

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
    setForm({ nombre: "", fecha_nacimiento: "", identificador: "" });
    setErrorAlta(null);
  }

  async function guardarNuevo() {
    if (!form.nombre.trim()) return;
    setGuardando(true);
    setErrorAlta(null);
    try {
      const cliente: Cliente = await registrarCliente({
        nombre: form.nombre.trim(),
        fecha_nacimiento: form.fecha_nacimiento || undefined,
        identificador: form.identificador.trim() || undefined,
      });
      // Cliente recién creado: cero visitas, sin historial suficiente todavía (FR-007).
      onSeleccionar({
        id_cliente: cliente.id_cliente,
        nombre: cliente.nombre ?? form.nombre,
        valor: null,
      });
      cerrar();
    } catch (e) {
      setErrorAlta(e instanceof ErrorApi ? e.message : "No se pudo registrar el cliente.");
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

  return (
    <>
      {!abierto ? (
        <button type="button" className={estilos.abrir} onClick={() => setAbierto(true)}>
          + Identificar cliente
        </button>
      ) : (
        <div className={estilos.panel}>
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
            <button
              type="button"
              className={estilos.enlace}
              onClick={() => {
                setErrorAlta(null);
                setForm((f) => ({ ...f, nombre: busqueda.trim() }));
                setCreandoNuevo(true);
              }}
            >
              + Registrar cliente nuevo
            </button>
            <button type="button" className={estilos.enlace} onClick={cerrar}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {creandoNuevo && (
        <ModalAdministrable
          titulo="Registrar cliente"
          onCerrar={() => setCreandoNuevo(false)}
          onGuardar={guardarNuevo}
          guardando={guardando}
          error={errorAlta}
          primariaHabilitada={form.nombre.trim() !== ""}
        >
          <label className={estilos.campoModal}>
            <span>
              Nombre <Obligatorio />
            </span>
            <input
              value={form.nombre}
              onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
              autoFocus
            />
          </label>
          <label className={estilos.campoModal}>
            <span>Fecha de nacimiento (opcional)</span>
            <input
              type="date"
              value={form.fecha_nacimiento}
              onChange={(e) => setForm((f) => ({ ...f, fecha_nacimiento: e.target.value }))}
            />
          </label>
          <CampoIdentificador
            value={form.identificador}
            onChange={(d) => setForm((f) => ({ ...f, identificador: d }))}
            claseCampo={estilos.campoModal}
          />
        </ModalAdministrable>
      )}
    </>
  );
}
