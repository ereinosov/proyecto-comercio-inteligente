/**
 * Pantalla de Arqueo de caja (006-caja-mermas-fraude, US1 — T016). Registro de OPERACIÓN: alta
 * densidad, la tabla como elemento principal, sin tarjetas, radio 2px, IBM Plex Sans con cifras
 * tabulares, SIN animación salvo la confirmación de cerrar el arqueo (DESIGN.md; la constitución
 * lista "arqueo" literalmente en Operación).
 *
 * Sin Verde Rasero: arquear una caja registra un conteo, no compromete dinero (La Regla del
 * Registro Sin Dinero). El arqueo, por sí solo, NUNCA es señal del fraude de sub-registro
 * (FR-008): esa señal vive en la pestaña "Caja y fraude".
 *
 * Dos modos (hallazgo #2 de la auditoría — el backend exige que el turno YA esté cerrado para
 * aceptar un arqueo, y desde el nav sólo se ve el turno abierto):
 *  - **modo normal** (pestaña del nav): sólo lectura del historial. El aviso explica que el
 *    arqueo se hace al cerrar el turno.
 *  - **`modoCierre`** (paso obligatorio de "Cerrar turno", montado por `App.tsx`): el turno ya
 *    está cerrado; se registra su arqueo y recién entonces `onListo()` vuelve a la apertura de
 *    turno. Se eligió este flujo sobre "seleccionar un turno cerrado" porque es el de un POS
 *    real: no se empieza el turno siguiente sin haber arqueado el anterior.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarArqueos, registrarArqueo, type Arqueo } from "../servicios/caja";
import type { Turno } from "../servicios/turnos";
import { formatearCaja, formatearMoneda } from "../utilidades/formato";
import { Boton } from "../componentes/Boton";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
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

interface Props {
  turno: Turno;
  /** Paso obligatorio tras "Cerrar turno": el turno ya está cerrado y hay que arquearlo. */
  modoCierre?: boolean;
  /** En `modoCierre`, se llama cuando el arqueo quedó registrado (o ya existía). */
  onListo?: () => void;
}

export function Arqueo({ turno, modoCierre = false, onListo }: Props) {
  const idSucursal = turno.id_sucursal;
  const [arqueos, setArqueos] = useState<Arqueo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const [montoContado, setMontoContado] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [registrado, setRegistrado] = useState(false);

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
      setRegistrado(true);
      setMontoContado("");
      setMotivo("");
      recargar();
      if (!modoCierre) setTimeout(() => setRegistrado(false), 1600);
    } catch (e) {
      setErrorForm(e instanceof ErrorApi ? e.message : "No se pudo registrar el arqueo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={estilos.pantalla}>
      {modoCierre && (
        <div className={estilos.barraCierre}>
          <img
            className={estilos.marcaSistema}
            src={marcaSistema}
            alt="Rasero"
            width={88}
            height={22}
          />
          <span className={estilos.contextoCierre}>
            Cierre de turno · {formatearCaja(turno.caja)}
          </span>
        </div>
      )}

      <EncabezadoPantalla
        titulo={modoCierre ? "Arqueo de cierre de turno" : "Arqueo de caja"}
        registro="operacion"
        contexto={
          modoCierre ? (
            <>El turno #{turno.id_turno} está cerrado. Cuenta el efectivo para poder continuar.</>
          ) : (
            <>
              Faltante acumulado del período: <strong>{formatearMoneda(totalFaltante)}</strong>
            </>
          )
        }
      />

      {modoCierre && registrado ? (
        <div className={estilos.confirmacionCierre}>
          <p className={estilos.confirmacionTexto}>
            Arqueo del turno #{turno.id_turno} registrado.
          </p>
          <Boton variante="primaria" onClick={() => onListo?.()}>
            Continuar a la apertura de turno
          </Boton>
        </div>
      ) : modoCierre ? (
        <form className={estilos.formulario} onSubmit={registrar}>
          <span className={estilos.campo}>
            Turno cerrado
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
              autoFocus
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
            {enviando ? "Registrando…" : "Registrar arqueo"}
          </Boton>
          {errorForm && <p className={estilos.errorForm}>{errorForm}</p>}
        </form>
      ) : (
        <p className={estilos.instruccion}>
          El arqueo de cada turno se registra al cerrarlo, desde la pantalla de Venta. Aquí queda
          el historial de arqueos de esta sucursal.
        </p>
      )}

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
