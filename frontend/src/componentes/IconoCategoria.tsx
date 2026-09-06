/**
 * Ícono de familia de categoría (La Regla del Ícono por Categoría, DESIGN.md v1.2.0).
 *
 * En toda superficie donde se liste `Producto` (catálogo de Venta, lista de Precios, lista de
 * Administración de productos), cada fila lleva un ícono SVG de línea simple (stroke, sin
 * relleno) asociado a su `id_categoria` — NUNCA una foto de producto.
 *
 * Set corto de 6 glifos genéricos por familia, derivado de las categorías reales sembradas en
 * `backend/rasero/semilla_catalogo.py` (Abarrotes, Bebidas, Frescos, Limpieza) más "enlatados"
 * y un "otros" de respaldo para cualquier categoría futura sin familia asignada.
 *
 * El mapeo vive PURAMENTE en el frontend: no hay ningún campo nuevo en `producto` ni en
 * `categoria`. Se resuelve por `id_categoria` -> nombre de categoría -> familia -> glifo; una
 * categoría sin familia cae a "otros" en lugar de romper la fila.
 */

import estilos from "./IconoCategoria.module.css";

export type Familia = "abarrotes" | "enlatados" | "frescos" | "bebidas" | "limpieza" | "otros";

/** Palabras del nombre de categoría -> familia. Substring, sin acentos, en minúsculas. */
const REGLAS: Array<[RegExp, Familia]> = [
  [/enlat|lata|conserva/, "enlatados"],
  [/fresco|refriger|carn|verdur|fruta|deli|lácteo|lacteo/, "frescos"],
  [/bebida|gaseosa|jugo|agua|licor|lácteos líquidos/, "bebidas"],
  [/limpiez|aseo|hogar/, "limpieza"],
  [/abarrote|grano|seco|cereal/, "abarrotes"],
];

export function familiaDeCategoria(nombre: string | null | undefined): Familia {
  if (!nombre) return "otros";
  const n = nombre
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
  for (const [patron, familia] of REGLAS) {
    if (patron.test(n)) return familia;
  }
  return "otros";
}

function Glifo({ familia }: { familia: Familia }) {
  const comun = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.4,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (familia) {
    case "abarrotes":
      // saco de grano
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <path d="M5 6 C5 3 13 3 13 6 L14 14 C14 16 4 16 4 14 Z" />
          <path d="M6 6 L12 6 M9 9 L9 12" />
        </svg>
      );
    case "enlatados":
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <ellipse cx="9" cy="4" rx="5" ry="2" />
          <path d="M4 4 V14 C4 15.1 14 15.1 14 14 V4" />
          <path d="M4 9 C4 10.1 14 10.1 14 9" />
        </svg>
      );
    case "frescos":
      // hoja + copo (refrigerado)
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <path d="M4 14 C4 7 11 4 14 4 C14 11 11 14 4 14 Z" />
          <path d="M6 12 C8 10 10 8 13 5" />
        </svg>
      );
    case "bebidas":
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <path d="M7 2 H11 V5 L12 7 V15 C12 15.6 6 15.6 6 15 V7 L7 5 Z" />
          <path d="M6 10 H12" />
        </svg>
      );
    case "limpieza":
      // botella con atomizador
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <path d="M7 6 H11 V15 C11 15.6 7 15.6 7 15 Z" />
          <path d="M8 6 V4 H11 L14 3" />
          <path d="M8 4 L5 3 M8 5 L5 5" />
        </svg>
      );
    default:
      // etiqueta (otros)
      return (
        <svg width="18" height="18" viewBox="0 0 18 18" {...comun}>
          <path d="M3 8 L9 2 L16 2 L16 9 L10 15 Z" />
          <circle cx="12.5" cy="5.5" r="1.1" />
        </svg>
      );
  }
}

interface Props {
  /** Nombre de la categoría del producto (resuelto desde `id_categoria`). */
  nombreCategoria: string | null | undefined;
}

export function IconoCategoria({ nombreCategoria }: Props) {
  const familia = familiaDeCategoria(nombreCategoria);
  return (
    <span className={estilos.icono} title={nombreCategoria ?? "Sin categoría"} aria-hidden="true">
      <Glifo familia={familia} />
    </span>
  );
}
