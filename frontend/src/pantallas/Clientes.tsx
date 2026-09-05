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
  listarClientes,
  obtenerCliente,
  type ClienteDetalle,
  type ClienteResumen,
} from "../servicios/clientes";
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
  const [idSeleccionado, setIdSeleccionado] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<ClienteDetalle | null>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarClientes(orden).then(setClientes);
  }, [orden]);

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
        <ul className={estilos.lista}>
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
          {clientes.length === 0 && <li className={estilos.vacio}>Todavía no hay clientes registrados.</li>}
        </ul>

        <div className={estilos.panelDetalle}>
          {error && <p className={estilos.error}>{error}</p>}
          {!error && !idSeleccionado && (
            <p className={estilos.instruccion}>Elige un cliente de la lista para ver su detalle.</p>
          )}
          {!error && idSeleccionado && cargandoDetalle && (
            <p className={estilos.instruccion}>Cargando…</p>
          )}
          {!error && detalle && (
            // key fuerza el remount al cambiar de cliente: la animación de revelación se
            // dispara una vez por cliente mostrado, nunca en cada re-render.
            <div key={detalle.id_cliente} className={estilos.detalleRevelado}>
              <h2 className={estilos.nombreDetalle}>{detalle.nombre ?? "(sin nombre)"}</h2>

              <InsigniaFuga detalle={detalle} />

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
    </div>
  );
}
