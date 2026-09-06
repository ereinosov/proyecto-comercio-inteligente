/**
 * Apertura de turno (T038): selector de operador + PIN de 4 dígitos (FR-005).
 * Verde Rasero no aparece aquí — reservado a la acción de cobro (DESIGN.md, Sola Voz).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { type Turno, abrirTurno } from "../servicios/turnos";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
import estilos from "./AperturaTurno.module.css";

interface Operador {
  id_operador: number;
  nombre: string;
  es_encargado: boolean;
}

const URL_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const ID_SUCURSAL = 1; // Quevedo Centro — única sucursal de esta demostración de caja
const CAJA = "caja-1";

interface Props {
  onTurnoAbierto: (turno: Turno) => void;
}

export function AperturaTurno({ onTurnoAbierto }: Props) {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [idOperador, setIdOperador] = useState<number | "">("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    fetch(`${URL_BASE}/operadores`)
      .then((r) => r.json())
      .then((lista: Operador[]) => {
        setOperadores(lista);
        if (lista.length > 0) setIdOperador(lista[0].id_operador);
      })
      .catch(() => setError("No se pudo cargar la lista de operadores."));
  }, []);

  async function confirmar(evento: React.FormEvent) {
    evento.preventDefault();
    if (idOperador === "" || pin.length !== 4) return;
    setEnviando(true);
    setError(null);
    try {
      const turno = await abrirTurno({ id_operador: idOperador, id_sucursal: ID_SUCURSAL, caja: CAJA, pin });
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
        width={220}
        height={54}
      />
      <form className={estilos.panel} onSubmit={confirmar}>
        <h1 className={estilos.titulo}>Abrir turno</h1>
        <p className={estilos.subtitulo}>Quevedo Centro · {CAJA}</p>

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

        <button className={estilos.boton} type="submit" disabled={enviando || pin.length !== 4}>
          {enviando ? "Verificando…" : "Abrir turno"}
        </button>
      </form>
    </div>
  );
}
