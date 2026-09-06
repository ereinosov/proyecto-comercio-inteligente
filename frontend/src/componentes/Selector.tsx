/**
 * `<select>` con el estilo del sistema: sin apariencia nativa del navegador, borde 1px Borde,
 * radio de Operación (2px) y un chevron SVG de línea simple propio superpuesto — el mismo
 * chevron del nav agrupado (App.tsx). Reutilizable; hoy lo usan Sucursal y Operador en
 * `AperturaTurno.tsx`.
 */

import type { SelectHTMLAttributes } from "react";
import estilos from "./Selector.module.css";

export function Selector(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className={estilos.contenedor}>
      <select {...props} className={estilos.select} />
      <span className={estilos.chevron} aria-hidden="true">
        <svg width="10" height="10" viewBox="0 0 10 10">
          <path
            d="M2 3.5 L5 6.5 L8 3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </span>
  );
}
