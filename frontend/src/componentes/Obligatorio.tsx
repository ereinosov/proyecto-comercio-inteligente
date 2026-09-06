/**
 * Indicador de campo obligatorio: un "*" en Crítico junto a la etiqueta. Patrón único del
 * sistema — se usa igual en los formularios de Cliente y de Administración (Parte 2).
 */

import estilos from "./Obligatorio.module.css";

export function Obligatorio() {
  return (
    <span className={estilos.marca} aria-hidden="true" title="Campo obligatorio">
      *
    </span>
  );
}
