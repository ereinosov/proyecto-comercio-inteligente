/**
 * Antigüedad de un dato (T063, US4). Tres portadores simultáneos, nunca solo color:
 *   - color semántico (reciente / atención / crítico),
 *   - forma (punto lleno / medio / hueco),
 *   - texto explícito ("hace 3 d").
 * La antigüedad se calcula en el servidor en el momento de la lectura y NO se almacena (FR-024).
 */

import estilos from "./AntiguedadDato.module.css";

type Forma = "lleno" | "medio" | "hueco";

interface Props {
  texto: string;
  forma: Forma;
}

const CLASE_COLOR: Record<Forma, string> = {
  lleno: estilos.reciente,
  medio: estilos.media,
  hueco: estilos.vieja,
};

export function AntiguedadDato({ texto, forma }: Props) {
  return (
    <span className={`${estilos.antiguedad} ${CLASE_COLOR[forma]}`}>
      <span className={`${estilos.punto} ${estilos[forma]}`} aria-hidden="true" />
      {texto}
    </span>
  );
}
