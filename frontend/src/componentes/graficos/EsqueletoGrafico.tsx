/**
 * Esqueleto de carga de un gráfico: barras esquemáticas de alturas distintas que anticipan la
 * forma del gráfico real (La Regla del Pulso, No el Brillo). Sólo oscilación de opacidad.
 */

import type { Registro } from "./temaGraficos";
import estilos from "./EsqueletoGrafico.module.css";

const ALTURAS = [46, 72, 58, 88, 64, 40, 76, 52];

export function EsqueletoGrafico({
  alto,
  registro,
}: {
  alto: number;
  registro: Registro;
}) {
  const clase = registro === "analisis" ? estilos.analisis : estilos.operacion;
  return (
    <div className={estilos.marco} style={{ height: alto }} aria-hidden="true">
      {ALTURAS.map((h, i) => (
        <span key={i} className={`${estilos.barra} ${clase}`} style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}
