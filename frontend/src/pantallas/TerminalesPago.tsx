/**
 * Pantalla de Terminales de pago (007-pagos-seguridad, US2 — T026). Registro de OPERACIÓN: alta
 * densidad, la tabla como elemento principal, sin tarjetas, radio 2px, IBM Plex Sans con cifras
 * tabulares, SIN animación salvo la confirmación de registrar una terminal o una actualización
 * (DESIGN.md; un registro de dispositivos es de la familia "inventario").
 *
 * Sin Verde Rasero: 007 no mueve dinero (La Regla del Registro Sin Dinero). Ninguna señal de
 * firmware deshabilita una terminal (FR-012): son consultivas. Tres portadores para cada señal
 * (color semántico + forma + texto).
 */

import { useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  listarTerminales,
  registrarActualizacionFirmware,
  registrarTerminal,
  type TerminalPago,
} from "../servicios/pagos";
import estilos from "./TerminalesPago.module.css";

function EstadoFirmware({ t }: { t: TerminalPago }) {
  if (t.expuesta_a_clonacion) {
    return (
      <span className={estilos.senalExpuesta}>
        <span className={estilos.puntoLleno} aria-hidden="true" />
        expuesta a clonación
        <span className={estilos.referencias}>({t.referencias_vulnerabilidad.join(", ")})</span>
      </span>
    );
  }
  if (t.desactualizada) {
    return (
      <span className={estilos.senalDesactualizada}>
        <span className={estilos.puntoMedio} aria-hidden="true" />
        desactualizada (última {t.ultima_version_referencia})
      </span>
    );
  }
  if (t.version_referencia_desconocida) {
    return (
      <span className={estilos.senalDesconocida}>
        <span className={estilos.puntoHueco} aria-hidden="true" />
        versión de referencia desconocida
      </span>
    );
  }
  return <span className={estilos.aldia}>al día</span>;
}

export function TerminalesPago({ idSucursal, idOperador }: { idSucursal: number; idOperador: number }) {
  const [terminales, setTerminales] = useState<TerminalPago[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const [identificador, setIdentificador] = useState("");
  const [modelo, setModelo] = useState("");
  const [version, setVersion] = useState("");
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState<string | null>(null);

  function recargar() {
    setCargando(true);
    setError(null);
    listarTerminales(idSucursal)
      .then(setTerminales)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar las terminales.")
      )
      .finally(() => setCargando(false));
  }

  useEffect(recargar, [idSucursal]);

  async function registrar(evento: FormEvent) {
    evento.preventDefault();
    setErrorForm(null);
    try {
      await registrarTerminal({
        identificador: identificador.trim(),
        modelo: modelo.trim(),
        id_sucursal: idSucursal,
        version_firmware: version.trim(),
        id_operador: idOperador,
      });
      setConfirmado("Terminal registrada.");
      setTimeout(() => setConfirmado(null), 1600);
      setIdentificador("");
      setModelo("");
      setVersion("");
      recargar();
    } catch (e) {
      setErrorForm(e instanceof ErrorApi ? e.message : "No se pudo registrar la terminal.");
    }
  }

  async function actualizarFirmware(t: TerminalPago) {
    const version = window.prompt(
      `Nueva versión de firmware para ${t.identificador} (actual ${t.version_firmware}):`
    );
    if (!version) return;
    try {
      await registrarActualizacionFirmware(t.id_terminal_pago, {
        version: version.trim(),
        fecha: new Date().toISOString().slice(0, 10),
        id_operador: idOperador,
      });
      setConfirmado("Firmware actualizado.");
      setTimeout(() => setConfirmado(null), 1600);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo actualizar el firmware.");
    }
  }

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h2 className={estilos.titulo}>Terminales de pago</h2>
        <span className={estilos.resumen}>
          {terminales.length} terminal{terminales.length === 1 ? "" : "es"} · sucursal {idSucursal}
        </span>
      </div>

      <form className={estilos.formulario} onSubmit={registrar}>
        <label className={estilos.campo}>
          Identificador
          <input
            className={estilos.entrada}
            value={identificador}
            onChange={(e) => setIdentificador(e.target.value)}
            required
          />
        </label>
        <label className={estilos.campo}>
          Modelo
          <input
            className={estilos.entrada}
            value={modelo}
            onChange={(e) => setModelo(e.target.value)}
            required
          />
        </label>
        <label className={estilos.campo}>
          Versión de firmware
          <input
            className={estilos.entrada}
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="3.2.0"
            required
          />
        </label>
        <button className={estilos.boton} type="submit">
          Registrar terminal
        </button>
        {confirmado && <span className={estilos.confirmado}>{confirmado}</span>}
      </form>
      {errorForm && <p className={estilos.errorForm}>{errorForm}</p>}
      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.tablaContenedor}>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Identificador</th>
              <th>Modelo</th>
              <th>Firmware</th>
              <th>Última actualización</th>
              <th>Estado</th>
              <th>Activa</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cargando ? (
              <tr>
                <td colSpan={7}>Cargando…</td>
              </tr>
            ) : terminales.length === 0 ? (
              <tr>
                <td colSpan={7}>Aún no hay terminales registradas en esta sucursal.</td>
              </tr>
            ) : (
              terminales.map((t) => (
                <tr key={t.id_terminal_pago}>
                  <td>{t.identificador}</td>
                  <td>{t.modelo}</td>
                  <td>{t.version_firmware}</td>
                  <td>{t.fecha_ultima_actualizacion_firmware ?? "—"}</td>
                  <td>
                    <EstadoFirmware t={t} />
                  </td>
                  <td>{t.activa ? "sí" : "retirada"}</td>
                  <td>
                    <button
                      className={estilos.boton}
                      type="button"
                      onClick={() => actualizarFirmware(t)}
                    >
                      Actualizar firmware
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
