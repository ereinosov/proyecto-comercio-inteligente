/**
 * Esqueleto de carga (La Regla del Pulso, No el Brillo, DESIGN.md v1.2.0).
 *
 * Reemplaza el contenido real mientras el backend responde, con el MISMO radio y un layout
 * aproximado del contenido que va a llegar — nunca un layout genérico. La única animación es
 * la oscilación de opacidad definida en el CSS; sin shimmer ni gradiente.
 */

import estilos from "./Esqueleto.module.css";

interface Props {
  /** Cuántas filas aproximadas se van a cargar. */
  filas?: number;
  registro?: "operacion" | "analisis";
  /** Altura de cada fila del esqueleto, para acercarlo al contenido real. */
  altoFila?: number;
}

export function EsqueletoLista({ filas = 6, registro = "analisis", altoFila = 44 }: Props) {
  const claseRadio = registro === "operacion" ? estilos.operacion : estilos.analisis;
  return (
    <div aria-hidden="true" aria-busy="true">
      {Array.from({ length: filas }).map((_, i) => (
        <div
          key={i}
          className={`${estilos.bloque} ${claseRadio} ${estilos.fila}`}
          style={{ height: altoFila }}
        />
      ))}
    </div>
  );
}
