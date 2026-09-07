/**
 * Encabezado de pantalla único (DESIGN.md v1.5.0, "Encabezado de pantalla").
 *
 * Toda pantalla abre con el mismo bloque: un `<h1>` en `--texto-xl`, el contexto de sesión
 * debajo (no en su lugar) y una zona de acciones a la derecha en la misma línea del título.
 * En esta ronda se aplica en Venta; el resto migra después.
 *
 * `SeccionPantalla` da el mismo padding lateral al resto del cuerpo.
 */

import type { ReactNode } from "react";
import estilos from "./EncabezadoPantalla.module.css";

interface Props {
  titulo: ReactNode;
  registro?: "operacion" | "analisis";
  /** Contexto de sesión: sucursal · caja · operador. Va debajo del <h1>, en Tinta Suave. */
  contexto?: ReactNode;
  /** Acciones alineadas a la derecha, en la línea del título. */
  acciones?: ReactNode;
}

export function EncabezadoPantalla({ titulo, registro = "operacion", contexto, acciones }: Props) {
  return (
    <header className={`${estilos.encabezado} ${estilos[registro]}`}>
      <div className={estilos.fila}>
        <h1 className={estilos.titulo}>{titulo}</h1>
        {acciones && <div className={estilos.acciones}>{acciones}</div>}
      </div>
      {contexto && <p className={estilos.contexto}>{contexto}</p>}
    </header>
  );
}

interface SeccionProps {
  children: ReactNode;
  registro?: "operacion" | "analisis";
  className?: string;
}

export function SeccionPantalla({ children, registro = "operacion", className = "" }: SeccionProps) {
  return (
    <div className={`${estilos.seccion} ${estilos[registro]} ${className}`.trim()}>{children}</div>
  );
}
