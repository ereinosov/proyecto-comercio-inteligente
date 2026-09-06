/**
 * Paginador reutilizable (La Regla del Filtro y la Página, DESIGN.md v1.2.0).
 *
 * "Página X de Y" en Tinta Suave, con flechas anterior/siguiente como chevrones SVG de línea
 * simple (sin relleno), deshabilitadas VISUALMENTE (opacidad reducida, no ocultas) en los
 * extremos. Tamaño de página por defecto: 20 (ver TAMANO_PAGINA).
 */

import estilos from "./Paginador.module.css";

export const TAMANO_PAGINA = 20;

interface Props {
  pagina: number;
  totalPaginas: number;
  onCambiar: (pagina: number) => void;
}

function Chevron({ direccion }: { direccion: "izquierda" | "derecha" }) {
  const d = direccion === "izquierda" ? "M9 2 L4 7 L9 12" : "M5 2 L10 7 L5 12";
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Paginador({ pagina, totalPaginas, onCambiar }: Props) {
  const total = Math.max(1, totalPaginas);
  const enPrimera = pagina <= 1;
  const enUltima = pagina >= total;
  return (
    <div className={estilos.paginador}>
      <button
        type="button"
        className={estilos.flecha}
        onClick={() => onCambiar(pagina - 1)}
        disabled={enPrimera}
        aria-label="Página anterior"
      >
        <Chevron direccion="izquierda" />
      </button>
      <span className={estilos.texto}>
        Página {Math.min(pagina, total)} de {total}
      </span>
      <button
        type="button"
        className={estilos.flecha}
        onClick={() => onCambiar(pagina + 1)}
        disabled={enUltima}
        aria-label="Página siguiente"
      >
        <Chevron direccion="derecha" />
      </button>
    </div>
  );
}
