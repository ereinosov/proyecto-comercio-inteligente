/**
 * Glifo de ayuda "?" con una explicación al pasar el cursor o al enfocar con el teclado.
 * SVG de línea (La Regla del Ícono — nunca un emoji). Sin librería, sin portal: el texto vive
 * en un `<span role="tooltip">` que se muestra en hover/focus por CSS y `aria-describedby`.
 *
 * La posición se recalcula en JS al mostrarse (`position: fixed`, anclada al disparador y
 * pinzada al viewport con 8px de margen) para que nunca quede recortada por el `overflow-y:
 * auto` de un panel o una celda de tabla angosta — el problema del posicionamiento puramente
 * relativo que tenía antes.
 */

import { useLayoutEffect, useId, useRef, useState } from "react";
import estilos from "./Ayuda.module.css";

const MARGEN_VIEWPORT = 8;

export function Ayuda({ texto, etiqueta }: { texto: string; etiqueta?: string }) {
  const id = useId();
  const disparadorRef = useRef<HTMLButtonElement>(null);
  const globoRef = useRef<HTMLSpanElement>(null);
  const [activo, setActivo] = useState(false);
  const [posicion, setPosicion] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!activo) return;
    const disparador = disparadorRef.current;
    const globo = globoRef.current;
    if (!disparador || !globo) return;
    const rectDisparador = disparador.getBoundingClientRect();
    const anchoGlobo = globo.offsetWidth;
    const left = Math.min(
      Math.max(rectDisparador.left + rectDisparador.width / 2 - anchoGlobo / 2, MARGEN_VIEWPORT),
      window.innerWidth - anchoGlobo - MARGEN_VIEWPORT,
    );
    setPosicion({ top: rectDisparador.bottom + 6, left });
  }, [activo]);

  return (
    <span className={estilos.envoltura}>
      <button
        ref={disparadorRef}
        type="button"
        className={estilos.disparador}
        aria-label={etiqueta ?? "Más información"}
        aria-describedby={id}
        onMouseEnter={() => setActivo(true)}
        onMouseLeave={() => setActivo(false)}
        onFocus={() => setActivo(true)}
        onBlur={() => setActivo(false)}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <path
            d="M5.4 5.3 A1.7 1.7 0 1 1 7.3 7.4 C7 7.6 7 7.9 7 8.4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
          />
          <circle cx="7" cy="10.4" r="0.7" fill="currentColor" />
        </svg>
      </button>
      <span
        ref={globoRef}
        role="tooltip"
        id={id}
        className={`${estilos.globo} ${activo ? estilos.globoVisible : ""}`}
        style={activo && posicion ? { position: "fixed", top: posicion.top, left: posicion.left, transform: "none" } : undefined}
      >
        {texto}
      </span>
    </span>
  );
}
