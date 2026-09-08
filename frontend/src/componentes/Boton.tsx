/**
 * Botón único del sistema (DESIGN.md v1.5.0, "Botón: spec general").
 *
 * Reemplaza la proliferación de clases equivalentes por pantalla (`botonSecundario`,
 * `botonCancelar`, `botonTexto`, `botonNuevo`, `boton`, `primaria`, `cancelar`, …). Desde
 * v1.8.0 se aplica en TODAS las pantallas: ningún `<button>` crudo de acción queda sin migrar
 * (salvo las filas de selección de listas, que no son un botón de acción).
 *
 * Variantes:
 *  - `cobro`      Verde Rasero. EXCLUSIVO del botón de cobro de Venta (La Regla de la Sola Voz).
 *  - `primaria`   Fondo Tinta. Acción principal de una pantalla que NO compromete dinero.
 *  - `secundaria` Contorno en Acento Secundario #7A6A56 (La Regla del Segundo Tono). Nunca relleno.
 *  - `neutra`     Borde gris, texto Tinta Suave. El "Cancelar" de un par.
 *  - `fantasma`   Sin borde ni fondo, subrayado en hover. Acciones de fila de baja jerarquía.
 *
 * El radio y la familia salen del registro; el foco, del token `--foco-anillo`.
 *
 * `conFlecha` (v3.0.0, del Panel de Bienvenida): añade la misma flecha SVG de línea que ya usa
 * "Abrir turno →". Reservada a la acción que **cierra** un flujo — el cobro de Venta, el guardado
 * de `ModalAdministrable` — nunca a un botón secundario ni a uno de una fila de lista.
 */

import type { ButtonHTMLAttributes } from "react";
import estilos from "./Boton.module.css";

type Variante = "cobro" | "primaria" | "secundaria" | "neutra" | "fantasma";
type Registro = "operacion" | "analisis";
type Tamano = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  registro?: Registro;
  tamano?: Tamano;
  conFlecha?: boolean;
}

function IconoFlecha() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path
        d="M2.5 7.5h9M8 3.8l3.7 3.7L8 11.2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Boton({
  variante = "neutra",
  registro = "operacion",
  tamano = "md",
  conFlecha = false,
  className = "",
  type = "button",
  children,
  ...resto
}: Props) {
  const clases = [
    estilos.boton,
    estilos[variante],
    estilos[registro],
    estilos[tamano],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type={type} className={clases} {...resto}>
      {children}
      {conFlecha && <IconoFlecha />}
    </button>
  );
}
