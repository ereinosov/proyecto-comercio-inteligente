/**
 * Campo de formulario único del sistema (DESIGN.md v1.5.0, "Campo: input y select").
 *
 * Envuelve `<label>` + control con un tratamiento único y retira las definiciones locales de
 * `.entrada` / `.campo` / `.campoFila` / `.campoModal` al migrar cada pantalla. En esta ronda
 * se aplica SÓLO en Venta.
 *
 * El control va como `children` (un `<input>`, un `<select>` restyled, el componente
 * `Selector`, …); el estilo de borde/alto/foco lo hereda del contenedor `.campo`. Un campo
 * numérico añade `data-num` para las cifras tabulares.
 */

import type { ReactNode } from "react";
import { Obligatorio } from "./Obligatorio";
import estilos from "./Campo.module.css";

interface Props {
  etiqueta: ReactNode;
  children: ReactNode;
  obligatorio?: boolean;
  /** Mensaje de error: pinta el borde en crítico y lo muestra debajo (nunca sólo el borde). */
  error?: string | null;
  /** Texto de ayuda bajo el control cuando no hay error. */
  ayuda?: ReactNode;
  /** Cifras tabulares y alineación a la derecha para campos de dinero/peso/cantidad. */
  numerico?: boolean;
  htmlFor?: string;
  className?: string;
}

export function Campo({
  etiqueta,
  children,
  obligatorio = false,
  error,
  ayuda,
  numerico = false,
  htmlFor,
  className = "",
}: Props) {
  return (
    <label
      className={[estilos.campo, error ? estilos.conError : "", className].filter(Boolean).join(" ")}
      htmlFor={htmlFor}
      data-num={numerico ? "" : undefined}
    >
      <span className={estilos.etiqueta}>
        {etiqueta}
        {obligatorio && <Obligatorio />}
      </span>
      {children}
      {error ? (
        <span className={estilos.error}>{error}</span>
      ) : ayuda ? (
        <span className={estilos.ayuda}>{ayuda}</span>
      ) : null}
    </label>
  );
}
