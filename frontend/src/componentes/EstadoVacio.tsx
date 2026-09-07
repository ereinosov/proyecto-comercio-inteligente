/**
 * Estado vacío que enseña (La Regla del Hueco que Enseña, DESIGN.md v1.2.0).
 *
 * Tres partes, nunca una sola línea de texto plano: ícono propio en SVG de línea simple
 * (stroke, sin relleno, color Borde/Tinta Suave) · título corto en el registro de la pantalla ·
 * una frase que explica QUÉ aparecerá ahí cuando haya datos — nunca "no hay nada".
 *
 * Detrás de las tres partes va una marca de agua del logo mono del comercio al 8 % (DESIGN.md
 * v1.4.0): refuerzo visual, `pointer-events: none`, nunca reemplaza ninguna de las tres partes.
 */

import marcaAgua from "../activos/marca/despensa-logo-mono-800w.png";
import estilos from "./EstadoVacio.module.css";

type Glifo = "lista" | "seleccion" | "caja" | "grafico";

function IconoVacio({ glifo }: { glifo: Glifo }) {
  return (
    <svg
      width="40"
      height="40"
      viewBox="0 0 40 40"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {glifo === "lista" && (
        <>
          <rect x="7" y="9" width="26" height="22" rx="2" />
          <path d="M12 16 H28 M12 21 H28 M12 26 H22" />
        </>
      )}
      {glifo === "seleccion" && (
        <>
          <path d="M8 10 H20 M8 16 H18 M8 22 H21" />
          <rect x="24" y="8" width="9" height="24" rx="1.5" />
        </>
      )}
      {glifo === "caja" && (
        <>
          <path d="M6 13 L20 7 L34 13 L20 19 Z" />
          <path d="M6 13 V27 L20 33 M34 13 V27 L20 33 M20 19 V33" />
        </>
      )}
      {glifo === "grafico" && (
        <>
          <path d="M8 8 V32 H33" />
          <path d="M13 26 L19 19 L24 23 L31 13" />
        </>
      )}
    </svg>
  );
}

interface Props {
  glifo?: Glifo;
  titulo: string;
  /** Qué se mostrará aquí cuando haya datos. */
  descripcion: string;
  /** Registro tipográfico de la pantalla que lo aloja. */
  registro?: "operacion" | "analisis";
}

export function EstadoVacio({ glifo = "lista", titulo, descripcion, registro = "analisis" }: Props) {
  return (
    <div className={`${estilos.hueco} ${registro === "operacion" ? estilos.operacion : estilos.analisis}`}>
      <img className={estilos.marcaAgua} src={marcaAgua} alt="" aria-hidden="true" />
      <span className={estilos.icono}>
        <IconoVacio glifo={glifo} />
      </span>
      <p className={estilos.titulo}>{titulo}</p>
      <p className={estilos.descripcion}>{descripcion}</p>
    </div>
  );
}
