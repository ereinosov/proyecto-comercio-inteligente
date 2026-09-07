/**
 * Pantalla de Arqueo de caja (006-caja-mermas-fraude, US1 — T016). Registro de OPERACIÓN: alta
 * densidad, la tabla como elemento principal, sin tarjetas, radio 2px, IBM Plex Sans con cifras
 * tabulares, SIN animación salvo la confirmación de cerrar el arqueo (DESIGN.md; la constitución
 * lista "arqueo" literalmente en Operación).
 *
 * Sin Verde Rasero: arquear una caja registra un conteo, no compromete dinero (La Regla del
 * Registro Sin Dinero). El arqueo, por sí solo, NUNCA es señal del fraude de sub-registro
 * (FR-008): esa señal vive en la pestaña "Caja y fraude".
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarArqueos, registrarArqueo, type Arqueo } from "../servicios/caja";
import type { Turno } from "../servicios/turnos";
import { formatearCaja, formatearMoneda } from "../utilidades/formato";
import { Boton } from "../componentes/Boton";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import estilos from "./Arqueo.module.css";

function Diferencia({ valor, motivo }: { valor: string; motivo: string | null }) {
  const numero = Number(valor);
  if (numero === 0) {
    return <span className={estilos.cuadrado}>{formatearMoneda(0)} — cuadrado</span>;
  }
  const signo = numero > 0 ? "+" : "";
  // Diferencia con motivo conocido anotado: atención (dato en seguimiento, no crítico).
  // Sin motivo: la genera una anomalía sin explicación — se marca en "Caja y fraude".
  const clase = motivo ? estilos.difConMotivo : estilos.difSinMotivo;
  const texto = motivo ? "con motivo" : "sin motivo — anomalía";
  return (
    <span className={clase}>
      <span className={motivo ? estilos.puntoMedio : estilos.puntoHueco} aria-hidden="true" />
      {signo}
      {formatearMoneda(valor)} — {texto}
    </span>
  );
}

export function Arqueo({ turno }: { turno: Turno }) {
  const idSucursal = turno.id_sucursal;
  const [arqueos, setArqueos] = useState<Arqueo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const [montoContado, setMontoContado] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState(false);

  function recargar() {
    setCargando(true);
    setError(null);
    listarArqueos(idSucursal)
      .then(setArqueos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los arqueos.")
      )
      .finally(() => setCargando(false));
  }

  useEffect(recargar, [idSucursal]);

  const totalFaltante = useMemo(
    () =>
      arqueos
        .reduce((suma, a) => suma + Math.min(0, Number(a.diferencia)), 0),
    [arqueos]
  );

  async function registrar(evento: FormEvent) {
    evento.preventDefault();
    setErrorForm(null);
    setEnviando(true);
    try {
      await registrarArqueo({
        id_turno: turno.id_turno,
        monto_contado: montoContado,
        motivo_conocido: motivo.trim() || null,
        marca_tiempo_origen: new Date().toISOString(),
      });
      setConfirmado(true);
      setTimeout(() => setConfirmado(false), 1600);
      setMontoContado("");
      setMotivo("");
      recargar();
    } catch (e) {
      setErrorForm(e instanceof ErrorApi ? e.message : "No se pudo registrar el arqueo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={estilos.pantalla}>
      <EncabezadoPantalla
        titulo="Arqueo de caja"
        registro="operacion"
        contexto={
          <>
            Faltante acumulado del período: <strong>{formatearMoneda(totalFaltante)}</strong>
          </>
        }
      />

      <form className={estilos.formulario} onSubmit={registrar}>
        <span className={estilos.campo}>
          Turno abierto
          <strong className={estilos.entrada}>
            Turno #{turno.id_turno} · {formatearCaja(turno.caja)}
          </strong>
        </span>
        <label className={estilos.campo}>
          Efectivo + comprobantes contados
          <input
            className={estilos.entrada}
            inputMode="decimal"
            placeholder="0.00"
            value={montoContado}
            onChange={(e) => setMontoContado(e.target.value)}
            required
          />
        </label>
        <label className={estilos.campoAncho}>
          Motivo conocido de una diferencia (opcional)
          <input
            className={estilos.entrada}
            placeholder="mal dado el cambio, pago no registrado…"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        </label>
        <Boton variante="primaria" type="submit" disabled={enviando}>
          {confirmado ? "Arqueo registrado" : enviando ? "Registrando…" : "Registrar arqueo"}
        </Boton>
        {errorForm && <p className={estilos.errorForm}>{errorForm}</p>}
      </form>

      {error && <p className={estilos.error}>{error}</p>}
      {!error && cargando && <p className={estilos.instruccion}>Cargando arqueos…</p>}
      {!error && !cargando && arqueos.length === 0 && (
        <p className={estilos.instruccion}>Todavía no hay arqueos en esta sucursal.</p>
      )}
      {!error && !cargando && arqueos.length > 0 && (
        <div className={estilos.tablaContenedor}>
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Turno</th>
                <th>Día local</th>
                <th className={estilos.der}>Esperado</th>
                <th className={estilos.der}>Contado</th>
                <th>Diferencia</th>
                <th>Ajustes</th>
              </tr>
            </thead>
            <tbody>
              {arqueos.map((a) => (
                <tr key={a.id_arqueo}>
                  <td>{a.id_turno}</td>
                  <td>{a.dia_local}</td>
                  <td className={estilos.der}>{formatearMoneda(a.monto_esperado)}</td>
                  <td className={estilos.der}>{formatearMoneda(a.monto_contado)}</td>
                  <td>
                    <Diferencia valor={a.diferencia} motivo={a.motivo_conocido} />
                  </td>
                  <td>{a.ajustes.length > 0 ? `${a.ajustes.length}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
