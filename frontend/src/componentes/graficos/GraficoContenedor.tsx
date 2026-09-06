/**
 * Tarjeta contenedora de un gráfico (Bloque A). Borde 2px (La Regla del Filo), sin sombra.
 * Maneja los tres estados con los patrones ya establecidos del sistema:
 *  - cargando  -> esqueleto con la forma del gráfico (La Regla del Pulso).
 *  - sin datos -> `EstadoVacio` (La Regla del Hueco que Enseña), el MISMO componente que las
 *    listas, no un estado nuevo.
 *  - con datos -> el gráfico.
 */

import type { ReactNode } from "react";
import { EstadoVacio } from "../EstadoVacio";
import { EsqueletoGrafico } from "./EsqueletoGrafico";
import type { Registro } from "./temaGraficos";
import estilos from "./GraficoContenedor.module.css";

interface Props {
  titulo: string;
  subtitulo?: string;
  registro: Registro;
  cargando?: boolean;
  /** Cuando es true, muestra el `EstadoVacio` en vez del gráfico. */
  vacio?: boolean;
  vacioTitulo?: string;
  vacioDescripcion?: string;
  /** Alto del área de dibujo (y del esqueleto). */
  alto?: number;
  children: ReactNode;
}

export function GraficoContenedor({
  titulo,
  subtitulo,
  registro,
  cargando = false,
  vacio = false,
  vacioTitulo = "Sin datos para graficar todavía",
  vacioDescripcion = "Aquí aparecerá el resumen visual en cuanto haya registros suficientes; la tabla de abajo sigue siendo el detalle.",
  alto = 260,
  children,
}: Props) {
  const claseRadio = registro === "analisis" ? estilos.analisis : estilos.operacion;
  const claseTitulo =
    registro === "analisis" ? estilos.tituloAnalisis : estilos.tituloOperacion;

  return (
    <section className={`${estilos.tarjeta} ${claseRadio}`}>
      <h3 className={`${estilos.titulo} ${claseTitulo}`}>{titulo}</h3>
      {subtitulo && <p className={estilos.subtitulo}>{subtitulo}</p>}
      <div className={estilos.cuerpo} style={{ height: alto }}>
        {cargando ? (
          <EsqueletoGrafico alto={alto} registro={registro} />
        ) : vacio ? (
          <EstadoVacio glifo="grafico" titulo={vacioTitulo} descripcion={vacioDescripcion} />
        ) : (
          children
        )}
      </div>
    </section>
  );
}
