/**
 * Apertura de turno (T038): selector de operador + PIN de 4 dígitos (FR-005).
 *
 * La Regla de la Identidad del Comercio (DESIGN.md v1.2.0): esta pantalla invierte la jerarquía
 * de un login. El nombre de la sucursal elegida (dato real de `sucursal.nombre`, nunca un
 * literal) preside la tarjeta en un bloque de cabecera con fondo Tinta y Source Serif 4. El
 * wordmark de Rasero baja a marca de sistema pequeña ARRIBA de la tarjeta. Debajo del nombre:
 * la caja y la zona horaria reales, y "Última apertura: …" si existe un turno anterior en esa
 * sucursal — si no hay ninguno, esa línea se OMITE (nunca un placeholder falso). Cualquier
 * nombre de comercio de demostración viene de una variable de entorno del frontend, nunca de
 * un literal en JSX ni de una tabla.
 *
 * Verde Rasero no aparece aquí — reservado a la acción de cobro (DESIGN.md, Sola Voz).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { clienteHttp } from "../servicios/clienteHttp";
import { type Turno, abrirTurno } from "../servicios/turnos";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
import estilos from "./AperturaTurno.module.css";

const NOMBRE_COMERCIO: string | undefined = import.meta.env.VITE_NOMBRE_COMERCIO;

function tiempoRelativo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.round(ms / 60000);
  if (min < 1) return "hace un momento";
  if (min < 60) return `hace ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.round(h / 24);
  return `hace ${d} d`;
}

interface Operador {
  id_operador: number;
  nombre: string;
  es_encargado: boolean;
}

const URL_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const CAJA = "caja-1";

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
    fetch(`${URL_BASE}/operadores`)
      .then((r) => r.json())
      .then((lista: Operador[]) => {
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
        width={96}
        height={24}
      />
      <form className={estilos.panel} onSubmit={confirmar}>
        <header className={estilos.cabecera}>
          <p className={estilos.nombreSucursal}>
            {sucursalElegida ? sucursalElegida.nombre : "Elige una sucursal"}
          </p>
          <p className={estilos.contexto}>
            {CAJA}
            {sucursalElegida ? ` · ${sucursalElegida.zona_horaria}` : ""}
          </p>
          {ultimaApertura && (
            <p className={estilos.ultimaApertura}>
              Última apertura: {tiempoRelativo(ultimaApertura)}
            </p>
          )}
        </header>

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor="sucursal">
            Sucursal
          </label>
          <select
            id="sucursal"
            className={estilos.select}
            value={idSucursal}
            onChange={(e) => setIdSucursal(Number(e.target.value))}
          >
            {sucursales.map((s) => (
              <option key={s.id_sucursal} value={s.id_sucursal}>
                {s.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor="operador">
            Operador
          </label>
          <select
            id="operador"
            className={estilos.select}
            value={idOperador}
            onChange={(e) => setIdOperador(Number(e.target.value))}
          >
            {operadores.map((op) => (
              <option key={op.id_operador} value={op.id_operador}>
                {op.nombre}
              </option>
            ))}
          </select>
        </div>

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
