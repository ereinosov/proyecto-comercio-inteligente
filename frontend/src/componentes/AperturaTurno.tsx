/**
 * Apertura de turno: selector de sucursal + operador + PIN de 4 dígitos (FR-005).
 *
 * La Regla de la Identidad del Comercio (DESIGN.md v1.3.0): cabecera de marca del comercio con
 * fondo blanco y el logo a color centrado como elemento principal; debajo, con aire, el nombre
 * de la sucursal elegida y la caja en Tinta Suave, y "Última apertura: …" si existe un turno
 * previo en esa sucursal (si no, la línea se omite — nunca un placeholder falso). El wordmark de
 * Rasero es marca de sistema pequeña ARRIBA de la tarjeta, fuera de ella. El logo del comercio
 * de demostración se puede sobreescribir por `VITE_LOGO_COMERCIO` en un despliegue real.
 *
 * Sólo cambia la presentación: el estado, la validación del PIN, las llamadas a la API y el
 * comportamiento al enviar no se tocan.
 *
 * Verde Rasero no aparece aquí — reservado a la acción de cobro (La Regla de la Sola Voz).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { clienteHttp } from "../servicios/clienteHttp";
import { type Turno, abrirTurno } from "../servicios/turnos";
import { listarOperadores, type Operador } from "../servicios/operadores";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import { Selector } from "./Selector";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
import logoComercioPorDefecto from "../activos/marca/despensa-logo-color-800w.png";
import estilos from "./AperturaTurno.module.css";

const LOGO_COMERCIO: string = import.meta.env.VITE_LOGO_COMERCIO ?? logoComercioPorDefecto;
const NOMBRE_COMERCIO: string | undefined = import.meta.env.VITE_NOMBRE_COMERCIO;
const CAJA = "caja-1";

function ultimaAperturaTexto(iso: string): string {
  const fecha = new Date(iso);
  const hhmm = fecha.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const hoy = new Date();
  const ayer = new Date(hoy);
  ayer.setDate(hoy.getDate() - 1);
  const mismoDia = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
  if (mismoDia(fecha, hoy)) return `hoy, ${hhmm}`;
  if (mismoDia(fecha, ayer)) return `ayer, ${hhmm}`;
  return `${fecha.toLocaleDateString()}, ${hhmm}`;
}

interface Props {
  onTurnoAbierto: (turno: Turno) => void;
}

export function AperturaTurno({ onTurnoAbierto }: Props) {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [idOperador, setIdOperador] = useState<number | "">("");
  const [idSucursal, setIdSucursal] = useState<number | "">("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [ultimaApertura, setUltimaApertura] = useState<string | null>(null);

  useEffect(() => {
    listarOperadores()
      .then((lista) => {
        setOperadores(lista);
        if (lista.length > 0) setIdOperador(lista[0].id_operador);
      })
      .catch(() => setError("No se pudo cargar la lista de operadores."));
    listarSucursales()
      .then((lista) => {
        setSucursales(lista);
        if (lista.length > 0) setIdSucursal(lista[0].id_sucursal);
      })
      .catch(() => setError("No se pudo cargar la lista de sucursales."));
  }, []);

  const sucursalElegida = sucursales.find((s) => s.id_sucursal === idSucursal);
  const operadorElegido = operadores.find((o) => o.id_operador === idOperador);
  // User Story 10 (Principio VI): un cajero/encargado abre turno SIEMPRE en su sucursal fija —
  // el selector no se le ofrece. Sólo el admin elige (su `id_sucursal` es dato de registro).
  const sucursalFija = operadorElegido && operadorElegido.rol !== "admin";

  useEffect(() => {
    if (sucursalFija && operadorElegido) setIdSucursal(operadorElegido.id_sucursal);
  }, [sucursalFija, operadorElegido]);

  useEffect(() => {
    setUltimaApertura(null);
    if (idSucursal === "") return;
    clienteHttp
      .get<{ instante_apertura: string } | null>(`/turnos/ultimo?id_sucursal=${idSucursal}`)
      .then((t) => setUltimaApertura(t?.instante_apertura ?? null))
      .catch(() => setUltimaApertura(null));
  }, [idSucursal]);

  async function confirmar(evento: React.FormEvent) {
    evento.preventDefault();
    if (idOperador === "" || idSucursal === "" || pin.length !== 4) return;
    setEnviando(true);
    setError(null);
    try {
      const turno = await abrirTurno({ id_operador: idOperador, id_sucursal: idSucursal, caja: CAJA, pin });
      onTurnoAbierto(turno);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo abrir el turno.");
      setPin("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={estilos.contenedor}>
      <img
        className={estilos.marca}
        src={marcaSistema}
        alt="Rasero"
        width={84}
        height={21}
      />
      <form className={estilos.panel} onSubmit={confirmar}>
        <header className={estilos.cabecera}>
          <img className={estilos.logoComercio} src={LOGO_COMERCIO} alt={NOMBRE_COMERCIO ?? "Comercio"} />
          <p className={estilos.contexto}>
            {sucursalElegida ? sucursalElegida.nombre : "Elige una sucursal"}
            {" · "}
            {CAJA}
          </p>
          {ultimaApertura && (
            <p className={estilos.ultimaApertura}>
              Última apertura: {ultimaAperturaTexto(ultimaApertura)}
            </p>
          )}
        </header>

        <div className={estilos.campos}>
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="operador">
              Operador
            </label>
            <Selector
              id="operador"
              value={idOperador}
              onChange={(e) => setIdOperador(Number(e.target.value))}
            >
              {operadores.map((op) => (
                <option key={op.id_operador} value={op.id_operador}>
                  {op.nombre}
                </option>
              ))}
            </Selector>
          </div>

          {/* Selector de sucursal SÓLO para el admin; cajero/encargado abren turno en su
              sucursal fija, ya mostrada en la cabecera de contexto (Principio VI). */}
          {!sucursalFija && (
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="sucursal">
                Sucursal
              </label>
              <Selector
                id="sucursal"
                value={idSucursal}
                onChange={(e) => setIdSucursal(Number(e.target.value))}
              >
                {sucursales.map((s) => (
                  <option key={s.id_sucursal} value={s.id_sucursal}>
                    {s.nombre}
                  </option>
                ))}
              </Selector>
            </div>
          )}

          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="pin">
              PIN (4 dígitos)
            </label>
            <input
              id="pin"
              className={estilos.input}
              type="password"
              inputMode="numeric"
              maxLength={4}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
              autoFocus
            />
          </div>
        </div>

        {error && <p className={estilos.error}>{error}</p>}

        <button
          className={estilos.boton}
          type="submit"
          disabled={enviando || pin.length !== 4 || idSucursal === ""}
        >
          {enviando ? "Verificando…" : "Abrir turno"}
        </button>
      </form>
      {NOMBRE_COMERCIO && <p className={estilos.pieComercio}>{NOMBRE_COMERCIO}</p>}
    </div>
  );
}
