/**
 * Apertura de turno: selector de sucursal + operador + PIN de 4 dígitos (FR-005).
 *
 * "El Panel de Bienvenida" (DESIGN.md v3.0.0): la puerta del sistema pasa de una tarjeta única
 * centrada a dos paneles — un panel de bienvenida con la identidad del comercio (izquierda) y la
 * tarjeta del formulario (centro). Sobre ~1200px se suma una franja angosta de beneficios
 * (derecha); por debajo se oculta, nunca se aprieta. El wordmark de Rasero vive arriba del panel
 * de bienvenida, fuera de la tarjeta (La Regla de la Identidad del Comercio se mantiene: el logo
 * del comercio nunca sobre un fondo oscuro). El PIN se captura con 4 casillas individuales (La
 * Regla del PIN de Casillas) en vez de un solo input enmascarado. El botón primario usa Verde
 * Rasero — cuarto uso permitido por la enmienda v3.0.0 de La Regla de la Sola Voz, exclusivo de
 * la acción de apertura de esta puerta (fuera de los registros Operación/Análisis).
 *
 * Sólo cambia la presentación: el estado, la validación del PIN, las llamadas a la API y el
 * comportamiento al enviar no se tocan.
 */

import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { clienteHttp } from "../servicios/clienteHttp";
import { type Turno, abrirTurno } from "../servicios/turnos";
import { listarOperadores, type Operador } from "../servicios/operadores";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import { Selector } from "./Selector";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
import logoComercioPorDefecto from "../activos/marca/despensa-logo-color-800w.png";
import marcaMono from "../activos/marca/despensa-logo-mono-800w.png";
import estilos from "./AperturaTurno.module.css";

const LOGO_COMERCIO: string = import.meta.env.VITE_LOGO_COMERCIO ?? logoComercioPorDefecto;
const NOMBRE_COMERCIO: string | undefined = import.meta.env.VITE_NOMBRE_COMERCIO;
const CAJA = "caja-1";
const CASILLAS_PIN = 4;

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

function IconoPersona() {
  return (
    <svg width="18" height="18" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <circle cx="7.5" cy="4.6" r="2.6" stroke="currentColor" strokeWidth="1.3" />
      <path d="M2.2 13c0-2.9 2.4-4.6 5.3-4.6s5.3 1.7 5.3 4.6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function IconoTienda() {
  return (
    <svg width="18" height="18" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path d="M2 3.5h11L12.3 7H2.7L2 3.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M3 7v4.3c0 .4.3.7.7.7h7.6c.4 0 .7-.3.7-.7V7" stroke="currentColor" strokeWidth="1.3" />
      <path d="M6 12v-2.3c0-.4.3-.7.7-.7h1.6c.4 0 .7.3.7.7V12" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function IconoCandado() {
  return (
    <svg width="18" height="18" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <rect x="3" y="6.6" width="9" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5 6.6V4.8a2.5 2.5 0 0 1 5 0v1.8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function IconoReloj() {
  return (
    <svg width="16" height="16" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <circle cx="7" cy="7" r="5.6" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 4v3.2l2.2 1.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconoUbicacion() {
  return (
    <svg width="16" height="16" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path
        d="M7 12.6s4.2-3.7 4.2-7A4.2 4.2 0 1 0 2.8 5.6c0 3.3 4.2 7 4.2 7Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <circle cx="7" cy="5.6" r="1.5" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function IconoFlecha() {
  return (
    <svg width="20" height="20" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path d="M2.5 7.5h9M8 3.8l3.7 3.7L8 11.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconoEscudo() {
  return (
    <svg width="22" height="22" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M9 2.4 14.8 4.5v4.1c0 3.7-2.5 6.1-5.8 7-3.3-.9-5.8-3.3-5.8-7V4.5L9 2.4Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M6.4 9.1l1.8 1.8 3.4-3.7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconoGrafico() {
  return (
    <svg width="22" height="22" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M3 14.6V3.4M3 14.6h12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M5.4 12.2V9.4M9 12.2V6.4M12.6 12.2V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function IconoNegocio() {
  return (
    <svg width="22" height="22" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M3 7.5h12v6.3a.8.8 0 0 1-.8.8H3.8a.8.8 0 0 1-.8-.8V7.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M2 4.3h14l-1 3.2H3l-1-3.2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M7.4 14.6v-3c0-.4.3-.8.8-.8h1.6c.4 0 .8.4.8.8v3" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

const BENEFICIOS = [
  {
    icono: IconoEscudo,
    titulo: "Control",
    texto: "Mayor seguridad en cada operación.",
  },
  {
    icono: IconoGrafico,
    titulo: "Gestión",
    texto: "Información en tiempo real para mejores decisiones.",
  },
  {
    icono: IconoNegocio,
    titulo: "Tu negocio",
    texto: "Más eficiente, siempre.",
  },
];

interface Props {
  onTurnoAbierto: (turno: Turno) => void;
  // User Story 11: mensaje cuando se vuelve aquí porque la sesión de turno expiró o se cerró.
  avisoSesion?: string | null;
  // Superficie de demostración: abre la documentación del sistema. No es parte del flujo de un
  // operador; por eso vive aquí y no en el nav.
  onVerDocumentacion?: () => void;
}

export function AperturaTurno({ onTurnoAbierto, avisoSesion, onVerDocumentacion }: Props) {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [idOperador, setIdOperador] = useState<number | "">("");
  const [idSucursal, setIdSucursal] = useState<number | "">("");
  // El PIN se captura en 4 casillas independientes (La Regla del PIN de Casillas); `pin` sigue
  // siendo la cadena de 4 dígitos que consume `abrirTurno`, derivada de las casillas.
  const [casillas, setCasillas] = useState<string[]>(Array(CASILLAS_PIN).fill(""));
  const pin = casillas.join("");
  const refsCasillas = useRef<(HTMLInputElement | null)[]>([]);
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

  function limpiarCasillas() {
    setCasillas(Array(CASILLAS_PIN).fill(""));
    refsCasillas.current[0]?.focus();
  }

  function cambiarCasilla(indice: number, valor: string) {
    const digito = valor.replace(/\D/g, "").slice(-1);
    setCasillas((anterior) => {
      const copia = [...anterior];
      copia[indice] = digito;
      return copia;
    });
    if (digito && indice < CASILLAS_PIN - 1) refsCasillas.current[indice + 1]?.focus();
  }

  function teclaCasilla(indice: number, evento: KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "Backspace" && !casillas[indice] && indice > 0) {
      refsCasillas.current[indice - 1]?.focus();
    }
  }

  function pegarCasillas(indice: number, evento: ClipboardEvent<HTMLInputElement>) {
    const digitos = evento.clipboardData.getData("text").replace(/\D/g, "").slice(0, CASILLAS_PIN);
    if (!digitos) return;
    evento.preventDefault();
    setCasillas((anterior) => {
      const copia = [...anterior];
      for (let i = 0; i < digitos.length && indice + i < CASILLAS_PIN; i++) copia[indice + i] = digitos[i];
      return copia;
    });
    refsCasillas.current[Math.min(indice + digitos.length, CASILLAS_PIN - 1)]?.focus();
  }

  async function confirmar(evento: FormEvent) {
    evento.preventDefault();
    if (idOperador === "" || idSucursal === "" || pin.length !== CASILLAS_PIN) return;
    setEnviando(true);
    setError(null);
    try {
      const turno = await abrirTurno({ id_operador: idOperador, id_sucursal: idSucursal, caja: CAJA, pin });
      onTurnoAbierto(turno);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo abrir el turno.");
      limpiarCasillas();
    } finally {
      setEnviando(false);
    }
  }

  const pinCompleto = pin.length === CASILLAS_PIN;

  return (
    <div className={estilos.contenedor}>
      <section className={estilos.panelBienvenida}>
        {/* Detalle de fondo: las líneas de graduación de un rasero (la tablilla que nivela el
            grano al ras) y la marca de agua del logo mono — motivo propio, muy tenue, nunca
            compite con el contenido (La Regla del Hueco que Enseña, extendida). */}
        <svg className={estilos.trazoFondo} viewBox="0 0 420 420" aria-hidden="true">
          <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="0" y1="48" x2="150" y2="48" />
            <line x1="0" y1="78" x2="110" y2="78" />
            <line x1="0" y1="108" x2="190" y2="108" />
            <line x1="0" y1="138" x2="90" y2="138" />
            <line x1="0" y1="168" x2="160" y2="168" />
          </g>
        </svg>
        <img className={estilos.aguaMarca} src={marcaMono} alt="" aria-hidden="true" />
        <div className={estilos.olaFondo} aria-hidden="true" />

        <div className={estilos.marcaSistemaTop}>
          <img src={marcaSistema} alt="Rasero" width={128} height={32} />
          <span>Nivela el dato. Decide con criterio.</span>
        </div>

        <div className={estilos.contenidoBienvenida}>
          <img className={estilos.logoComercio} src={LOGO_COMERCIO} alt={NOMBRE_COMERCIO ?? "Comercio"} />

          <p className={estilos.ubicacion}>
            <IconoUbicacion />
            {sucursalElegida ? sucursalElegida.nombre : "Elige una sucursal"}
            <span className={estilos.pillCaja}>{CAJA}</span>
          </p>

          <h2 className={estilos.saludo}>¡Bienvenido!</h2>
          <p className={estilos.subSaludo}>Prepárate para iniciar tu turno en la caja.</p>
        </div>

        {ultimaApertura && (
          <p className={estilos.ultimaApertura}>
            <IconoReloj />
            Última apertura: {ultimaAperturaTexto(ultimaApertura)}
          </p>
        )}
      </section>

      <section className={estilos.panelFormulario}>
        <form className={estilos.tarjeta} onSubmit={confirmar}>
          <div className={estilos.encabezadoTarjeta}>
            <span className={estilos.acentoVertical} aria-hidden="true" />
            <div>
              <h1 className={estilos.tituloTarjeta}>Apertura de turno</h1>
              <p className={estilos.descripcionTarjeta}>
                Identifica al operador y confirma tu PIN para comenzar la jornada de caja.
              </p>
            </div>
          </div>

          <div className={estilos.divisor} />

          <div className={estilos.campos}>
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="operador">
                <IconoPersona />
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
                sucursal fija, ya mostrada en el panel de bienvenida (Principio VI). */}
            {!sucursalFija && (
              <div className={estilos.campo}>
                <label className={estilos.etiqueta} htmlFor="sucursal">
                  <IconoTienda />
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
              <label className={estilos.etiqueta} id="etiqueta-pin">
                <IconoCandado />
                PIN de acceso
              </label>
              <div className={estilos.casillasPin} role="group" aria-labelledby="etiqueta-pin">
                {casillas.map((valor, indice) => (
                  <input
                    key={indice}
                    ref={(el) => {
                      refsCasillas.current[indice] = el;
                    }}
                    className={estilos.casilla}
                    type="password"
                    inputMode="numeric"
                    maxLength={1}
                    value={valor}
                    onChange={(e) => cambiarCasilla(indice, e.target.value)}
                    onKeyDown={(e) => teclaCasilla(indice, e)}
                    onPaste={(e) => pegarCasillas(indice, e)}
                    autoFocus={indice === 0}
                    aria-label={`Dígito ${indice + 1} del PIN`}
                  />
                ))}
              </div>
            </div>
          </div>

          <button
            className={estilos.boton}
            type="submit"
            disabled={enviando || !pinCompleto || idSucursal === ""}
          >
            {enviando ? "Verificando…" : "Abrir turno"}
            {!enviando && <IconoFlecha />}
          </button>

          {/* Franja de estado: siempre color + forma + texto explícito (nunca solo el color), el
              mismo criterio que el resto del sistema para comunicar un estado sin ambigüedad. */}
          {error ? (
            <p className={estilos.estado}>
              <span className={`${estilos.punto} ${estilos.puntoCritico}`} aria-hidden="true" />
              {error}
            </p>
          ) : avisoSesion ? (
            <p className={estilos.estado}>
              <span className={`${estilos.punto} ${estilos.puntoAtencion}`} aria-hidden="true" />
              {avisoSesion}
            </p>
          ) : pinCompleto ? (
            <p className={estilos.estado}>
              <span className={`${estilos.punto} ${estilos.puntoOk}`} aria-hidden="true" />
              Caja lista para abrir
            </p>
          ) : (
            <p className={estilos.estado}>
              <span className={`${estilos.punto} ${estilos.puntoNeutro}`} aria-hidden="true" />
              Completa el PIN para continuar
            </p>
          )}
        </form>

        <div className={estilos.pie}>
          {NOMBRE_COMERCIO && <p className={estilos.pieComercio}>{NOMBRE_COMERCIO}</p>}
          {onVerDocumentacion && (
            <button type="button" className={estilos.enlaceDoc} onClick={onVerDocumentacion}>
              Documentación del sistema
            </button>
          )}
        </div>
      </section>

      <aside className={estilos.panelBeneficios} aria-label="Por qué Rasero">
        {BENEFICIOS.map(({ icono: Icono, titulo, texto }) => (
          <div className={estilos.beneficio} key={titulo}>
            <span className={estilos.iconoBeneficio}>
              <Icono />
            </span>
            <div>
              <p className={estilos.tituloBeneficio}>{titulo}</p>
              <p className={estilos.textoBeneficio}>{texto}</p>
            </div>
          </div>
        ))}
      </aside>
    </div>
  );
}
