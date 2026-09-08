/**
 * Pantalla de Bitácora de auditoría de pagos (007-pagos-seguridad, US4 — T045). Registro de
 * OPERACIÓN: alta densidad, tabla como elemento principal, radio 2px, IBM Plex Sans con cifras
 * tabulares, sin animación (DESIGN.md). SÓLO LECTURA — no hay acción de edición ni de borrado
 * (FR-025). Las entradas `token_emitido` muestran el token y los últimos 4 dígitos, nunca más;
 * `pan_rechazado` y `terminal_expuesta_detectada` en crítico. Sin Verde Rasero.
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  consultarBitacoraPagina,
  type EntradaBitacora,
  type TipoEventoBitacora,
} from "../servicios/pagos";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
import estilos from "./BitacoraPagos.module.css";

const TIPOS: TipoEventoBitacora[] = [
  "token_emitido",
  "token_idempotencia_divergente",
  "token_purgado",
  "pan_rechazado",
  "firmware_actualizado",
  "firmware_desactualizado_detectado",
  "terminal_expuesta_detectada",
  "terminal_registrada",
  "terminal_movida",
  "medio_pago_alta",
  "medio_pago_baja",
  "cobertura_declarada",
  "intencion_no_atendida",
  "config_firmware_cambiada",
];

const CRITICOS = new Set<TipoEventoBitacora>(["pan_rechazado", "terminal_expuesta_detectada"]);

export function BitacoraPagos({ idSucursal }: { idSucursal: number }) {
  const [entradas, setEntradas] = useState<EntradaBitacora[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [tipo, setTipo] = useState<TipoEventoBitacora | "">("");

  useEffect(() => {
    setCargando(true);
    setError(null);
    consultarBitacoraPagina(idSucursal, {
      ...(tipo ? { tipoEvento: tipo } : {}),
      pagina,
      tamanoPagina: TAMANO_PAGINA,
    })
      .then(({ items, total: t }) => {
        setEntradas(items);
        setTotal(t ?? items.length);
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la bitácora.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal, tipo, pagina]);

  useEffect(() => setPagina(1), [idSucursal, tipo]);

  const totalPaginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h2 className={estilos.titulo}>Registro de seguridad</h2>
        <span className={estilos.resumen}>
          {total} evento{total === 1 ? "" : "s"} · sólo lectura
        </span>
      </div>

      <p className={estilos.resumen} style={{ padding: "0 24px" }}>
        Rastro inmutable de los hechos de seguridad de pagos: tokens emitidos, PAN rechazado,
        firmware y terminales. Para las ventas y su medio de pago, usa «Cobros por venta».
      </p>

      <div className={estilos.filtros}>
        <select
          className={estilos.select}
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoEventoBitacora | "")}
        >
          <option value="">Todos los tipos de evento</option>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {t.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>
      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.tablaContenedor}>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Día local</th>
              <th>Evento</th>
              <th>Iniciado por</th>
              <th>Terminal</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {cargando ? (
              <tr>
                <td colSpan={5}>Cargando…</td>
              </tr>
            ) : entradas.length === 0 ? (
              <tr>
                <td colSpan={5}>Sin hechos de pago registrados con este filtro.</td>
              </tr>
            ) : (
              entradas.map((e) => (
                <tr key={e.id_bitacora_auditoria}>
                  <td>{e.dia_local}</td>
                  <td>
                    {CRITICOS.has(e.tipo_evento) ? (
                      <span className={estilos.critico}>
                        <span className={estilos.puntoLleno} aria-hidden="true" />
                        {e.tipo_evento.replaceAll("_", " ")}
                      </span>
                    ) : (
                      e.tipo_evento.replaceAll("_", " ")
                    )}
                  </td>
                  <td>
                    {e.iniciador_tipo === "operador" ? `operador ${e.id_operador}` : e.proceso}
                  </td>
                  <td>{e.id_terminal_pago ?? "—"}</td>
                  <td>{e.resultado}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!cargando && entradas.length > 0 && (
        <div className={estilos.paginadorZona}>
          <Paginador pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} numerado />
        </div>
      )}
    </div>
  );
}
