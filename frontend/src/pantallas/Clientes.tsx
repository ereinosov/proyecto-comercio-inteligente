/**
 * Pantalla de Clientes (T026, T027, T038). Registro de Análisis: una decisión por bloque, aire
 * visual, líneas bajo 80 caracteres, radio 6px, Source Serif 4 (constitución, Sistema de
 * Diseño). El listado muestra solo la puntuación compuesta (FR-011a la muestra también en
 * Operación); el desglose de las tres dimensiones y el estado de fuga viven en el detalle, con
 * el único momento de animación deliberado de esta pantalla al revelarlo — la constitución cita
 * textualmente este caso ("al revelar el detalle de un cliente en riesgo de fuga") como ejemplo
 * del registro de Análisis.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  actualizarCliente,
  listarClientesPagina,
  obtenerCliente,
  type ClienteDetalle,
  type ClienteResumen,
} from "../servicios/clientes";
import { EstadoVacio } from "../componentes/EstadoVacio";
import { EsqueletoLista } from "../componentes/Esqueleto";
import { ModalAdministrable } from "../componentes/ModalAdministrable";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
import estilos from "./Clientes.module.css";

function textoValor(valor: number | null): string {
  return valor === null ? "Datos insuficientes" : String(Math.round(valor));
}

// Estado de fuga: tres portadores simultáneos, nunca solo color (constitución, redundancia de
// portadores). "hace N d" se calcula sobre el instante relevante de cada estado.
function antiguedad(iso: string | null): string {
  if (!iso) return "";
  const dias = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  return `hace ${dias} d`;
}

function InsigniaFuga({ detalle }: { detalle: ClienteDetalle }) {
  const fuga = detalle.fuga;
  if (!fuga || fuga.estado === "sin_senal") {
    return (
      <span className={estilos.fugaOk}>
        <span className={estilos.puntoLleno} aria-hidden="true" />
        Sin señal de fuga
      </span>
    );
  }
  if (fuga.estado === "datos_insuficientes") {
    return (
      <span className={estilos.fugaNeutra}>
        <span className={estilos.puntoHueco} aria-hidden="true" />
        Datos insuficientes para evaluar fuga
      </span>
    );
  }
  if (fuga.estado === "resuelta") {
    return (
      <span className={estilos.fugaOk}>
        <span className={estilos.puntoLleno} aria-hidden="true" />
        Resuelta {antiguedad(fuga.instante_resolucion)}
      </span>
    );
  }
  if (fuga.estado === "confirmada") {
    return (
      <span className={estilos.fugaCritica}>
        <span className={estilos.puntoHueco} aria-hidden="true" />
        Fuga confirmada, {antiguedad(fuga.instante_confirmacion)}
      </span>
    );
  }
  // activa
  return (
    <span className={estilos.fugaAtencion}>
      <span className={estilos.puntoMedio} aria-hidden="true" />
      En riesgo de fuga, detectada {antiguedad(fuga.instante_deteccion)}
    </span>
  );
}

export function Clientes() {
  const [orden, setOrden] = useState<"valor" | "monto_total">("valor");
  const [clientes, setClientes] = useState<ClienteResumen[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [cargandoLista, setCargandoLista] = useState(true);
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<ClienteDetalle | null>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({
    nombre: "",
    fecha_nacimiento: "",
    contacto: "",
    identificador: "",
  });
  const [guardando, setGuardando] = useState(false);
  const [errorEdicion, setErrorEdicion] = useState<string | null>(null);

  function recargarLista() {
    setCargandoLista(true);
    listarClientesPagina(orden, pagina, TAMANO_PAGINA)
      .then(({ items, total: t }) => {
        setClientes(items);
        setTotal(t ?? items.length);
      })
      .finally(() => setCargandoLista(false));
  }

  useEffect(recargarLista, [orden, pagina]);

  useEffect(() => setPagina(1), [orden]);

  const totalPaginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

  async function guardarEdicion() {
    if (!detalle) return;
    setGuardando(true);
    setErrorEdicion(null);
    try {
      await actualizarCliente(detalle.id_cliente, {
        nombre: form.nombre.trim(),
        fecha_nacimiento: form.fecha_nacimiento,
        contacto: form.contacto.trim() || null,
        identificador: form.identificador.trim() || null,
      });
      setEditando(false);
      const fresco = await obtenerCliente(detalle.id_cliente);
      setDetalle(fresco);
      recargarLista();
    } catch (e) {
      setErrorEdicion(e instanceof ErrorApi ? e.message : "No se pudo guardar el cliente.");
    } finally {
      setGuardando(false);
    }
  }

  useEffect(() => {
    if (idSeleccionado === null) {
      setDetalle(null);
      return;
    }
    setCargandoDetalle(true);
    setDetalle(null); // el detalle anterior desaparece antes: la revelación es de ESTE cliente
    obtenerCliente(idSeleccionado)
      .then(setDetalle)
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el cliente."))
      .finally(() => setCargandoDetalle(false));
  }, [idSeleccionado]);

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Clientes</h1>
        <div className={estilos.controlOrden}>
          <button
            className={orden === "valor" ? estilos.ordenActivo : estilos.ordenInactivo}
            onClick={() => setOrden("valor")}
          >
            Por valor
          </button>
          <button
            className={orden === "monto_total" ? estilos.ordenActivo : estilos.ordenInactivo}
            onClick={() => setOrden("monto_total")}
          >
            Por monto
          </button>
        </div>
      </div>

      <div className={estilos.cuerpo}>
        <div className={estilos.lista}>
          {cargandoLista ? (
            <EsqueletoLista filas={8} registro="analisis" altoFila={52} />
          ) : clientes.length === 0 ? (
            <EstadoVacio
              glifo="lista"
              titulo="Todavía no hay clientes registrados"
              descripcion="Aquí aparecerá cada cliente, ordenado por su valor o su monto. Los clientes se registran desde la caja al identificar a alguien durante una venta."
            />
          ) : (
            <>
              <ul className={estilos.listaUl}>
                {clientes.map((c) => (
                  <li key={c.id_cliente}>
                    <button
                      className={`${estilos.bloque} ${idSeleccionado === c.id_cliente ? estilos.bloqueSeleccionado : ""}`}
                      onClick={() => setIdSeleccionado(c.id_cliente)}
                    >
                      <span className={estilos.nombreCliente}>{c.nombre ?? "(sin nombre)"}</span>
                      <span className={estilos.valorResumen}>{textoValor(c.valor)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <Paginador pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />
            </>
          )}
        </div>

        <div className={estilos.panelDetalle}>
          {error && <p className={estilos.error}>{error}</p>}
          {!error && !idSeleccionado && (
            <EstadoVacio
              glifo="seleccion"
              titulo="Elige un cliente"
              descripcion="Aquí se abrirá el detalle del cliente que elijas: el desglose de su valor por frecuencia, monto y margen, y su estado de señal de fuga."
            />
          )}
          {!error && idSeleccionado && cargandoDetalle && (
            <EsqueletoLista filas={4} registro="analisis" altoFila={40} />
          )}
          {!error && detalle && (
            // key fuerza el remount al cambiar de cliente: la animación de revelación se
            // dispara una vez por cliente mostrado, nunca en cada re-render.
            <div key={detalle.id_cliente} className={estilos.detalleRevelado}>
              <div className={estilos.filaTituloDetalle}>
                <h2 className={estilos.nombreDetalle}>{detalle.nombre ?? "(sin nombre)"}</h2>
                {!detalle.anonimizado && (
                  <button
                    type="button"
                    className={estilos.editarCliente}
                    onClick={() => {
                      setForm({
                        nombre: detalle.nombre ?? "",
                        fecha_nacimiento: detalle.fecha_nacimiento ?? "",
                        contacto: detalle.contacto ?? "",
                        identificador: detalle.identificador ?? "",
                      });
                      setErrorEdicion(null);
                      setEditando(true);
                    }}
                  >
                    Editar
                  </button>
                )}
              </div>

              <InsigniaFuga detalle={detalle} />

              {/* Regla del Hueco que Enseña: sólo si el cliente tiene identificador; nunca
                  "N/A" ni un placeholder para un dato ausente. */}
              {detalle.identificador && (
                <p className={estilos.identificador}>
                  Cédula / RUC: <span>{detalle.identificador}</span>
                </p>
              )}

              {detalle.valor === null ? (
                <p className={estilos.avisoInsuficiente}>
                  Datos insuficientes: este cliente todavía no tiene el historial mínimo para
                  calcular su valor.
                </p>
              ) : (
                <dl className={estilos.desglose}>
                  <div className={estilos.bloqueDesglose}>
                    <dt>Puntuación compuesta</dt>
                    <dd className={estilos.compuesto}>{Math.round(detalle.valor.compuesto)}</dd>
                  </div>
                  <div className={estilos.bloqueDesglose}>
                    <dt>Frecuencia</dt>
                    <dd>{Math.round(detalle.valor.percentil_frecuencia)}º percentil</dd>
                  </div>
                  <div className={estilos.bloqueDesglose}>
                    <dt>Monto</dt>
                    <dd>{Math.round(detalle.valor.percentil_monto)}º percentil</dd>
                  </div>
                  <div className={estilos.bloqueDesglose}>
                    <dt>Margen</dt>
                    <dd>{Math.round(detalle.valor.percentil_margen)}º percentil</dd>
                  </div>
                </dl>
              )}
            </div>
          )}
        </div>
      </div>

      {editando && detalle && (
        <ModalAdministrable
          titulo="Editar cliente"
          onCerrar={() => setEditando(false)}
          onGuardar={guardarEdicion}
          guardando={guardando}
          error={errorEdicion}
          primariaHabilitada={form.nombre.trim() !== "" && form.fecha_nacimiento !== ""}
        >
          <label className={estilos.campoModal}>
            <span>Nombre</span>
            <input
              value={form.nombre}
              onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
              autoFocus
            />
          </label>
          <label className={estilos.campoModal}>
            <span>Fecha de nacimiento</span>
            <input
              type="date"
              value={form.fecha_nacimiento}
              onChange={(e) => setForm((f) => ({ ...f, fecha_nacimiento: e.target.value }))}
            />
          </label>
          <label className={estilos.campoModal}>
            <span>Contacto (opcional)</span>
            <input
              value={form.contacto}
              onChange={(e) => setForm((f) => ({ ...f, contacto: e.target.value }))}
            />
          </label>
          <label className={estilos.campoModal}>
            <span>Cédula o RUC (opcional)</span>
            <input
              inputMode="numeric"
              maxLength={13}
              value={form.identificador}
              onChange={(e) =>
                setForm((f) => ({ ...f, identificador: e.target.value.replace(/\D/g, "") }))
              }
            />
          </label>
        </ModalAdministrable>
      )}
    </div>
  );
}
