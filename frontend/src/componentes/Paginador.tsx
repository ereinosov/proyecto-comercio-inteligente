/**
 * Paginador reutilizable (La Regla del Filtro y la Página, DESIGN.md v1.2.0).
 *
 * Por defecto: "Página X de Y" en Tinta Suave, con flechas anterior/siguiente como chevrones
 * SVG de línea simple, deshabilitadas VISUALMENTE (opacidad reducida, no ocultas) en los
 * extremos. Tamaño de página por defecto: 20 (ver TAMANO_PAGINA).
 *
 * Con `numerado`: además de las flechas, botones cuadrados con el número de cada página
 * (1, 2, 3…), con elipsis cuando hay muchas. La página actual va marcada. Para grillas cortas
 * donde ver "en qué página estoy y cuántas hay" de un vistazo importa más que el texto.
 */

import estilos from "./Paginador.module.css";

export const TAMANO_PAGINA = 20;

interface Props {
  pagina: number;
  totalPaginas: number;
  onCambiar: (pagina: number) => void;
  numerado?: boolean;
}

function Chevron({ direccion }: { direccion: "izquierda" | "derecha" }) {
  const d = direccion === "izquierda" ? "M9 2 L4 7 L9 12" : "M5 2 L10 7 L5 12";
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Números de página a mostrar, con `"..."` como hueco. Ventana de ±1 alrededor de la actual,
 *  siempre con la primera y la última. */
function numerosVisibles(pagina: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set<number>([1, total, pagina, pagina - 1, pagina + 1]);
  const orden = [...set].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
  const salida: (number | "...")[] = [];
  for (let i = 0; i < orden.length; i++) {
    if (i > 0 && orden[i] - orden[i - 1] > 1) salida.push("...");
    salida.push(orden[i]);
  }
  return salida;
}

export function Paginador({ pagina, totalPaginas, onCambiar, numerado = false }: Props) {
  const total = Math.max(1, totalPaginas);
  const actual = Math.min(pagina, total);
  const enPrimera = actual <= 1;
  const enUltima = actual >= total;
  return (
    <div className={estilos.paginador}>
      <button
        type="button"
        className={estilos.flecha}
        onClick={() => onCambiar(actual - 1)}
        disabled={enPrimera}
        aria-label="Página anterior"
      >
        <Chevron direccion="izquierda" />
      </button>

      {numerado ? (
        <span className={estilos.numeros}>
          {numerosVisibles(actual, total).map((n, i) =>
            n === "..." ? (
              <span key={`e${i}`} className={estilos.elipsis} aria-hidden="true">
                …
              </span>
            ) : (
              <button
                key={n}
                type="button"
                className={n === actual ? estilos.numeroActivo : estilos.numero}
                onClick={() => onCambiar(n)}
                aria-label={`Página ${n}`}
                aria-current={n === actual ? "page" : undefined}
              >
                {n}
              </button>
            ),
          )}
        </span>
      ) : (
        <span className={estilos.texto}>
          Página {actual} de {total}
        </span>
      )}

      <button
        type="button"
        className={estilos.flecha}
        onClick={() => onCambiar(actual + 1)}
        disabled={enUltima}
        aria-label="Página siguiente"
      >
        <Chevron direccion="derecha" />
      </button>
    </div>
  );
}
