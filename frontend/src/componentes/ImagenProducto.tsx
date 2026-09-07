/**
 * Imagen de un producto con fallback robusto al ícono de familia de categoría
 * (La Regla del Ícono por Categoría, DESIGN.md v1.2.0; US12 de 001).
 *
 * - Si `urlImagen` tiene valor: renderiza `<img>` desde esa URL externa.
 * - Si `urlImagen` es null/vacía, O si el `<img>` dispara `onError` (URL movida, sin conexión,
 *   403, …): renderiza el ícono SVG de familia de categoría — nunca un hueco ni una imagen rota.
 *
 * Las imágenes se alojan fuera del repositorio (URL externa en vivo): decisión consciente de
 * US12, con el riesgo de disponibilidad aceptado y cubierto por este fallback.
 *
 * Se usa en toda superficie que muestra la identidad visual de un producto: el catálogo en grid
 * de Venta y la celda de producto del ticket.
 */

import { useEffect, useState } from "react";
import { IconoCategoria } from "./IconoCategoria";
import estilos from "./ImagenProducto.module.css";

interface Props {
  urlImagen: string | null | undefined;
  /** Nombre de la categoría del producto (resuelto desde `id_categoria`) para elegir el glifo. */
  nombreCategoria: string | null | undefined;
  /** Nombre del producto, para el `alt` de la imagen. */
  nombreProducto: string;
  /** Lado del recuadro cuadrado en px. Ignorado si `bloque`. */
  tamano?: number;
  /** Ocupa el ancho de su contenedor con relación de aspecto 16/10 (tarjeta del catálogo). */
  bloque?: boolean;
}

export function ImagenProducto({
  urlImagen,
  nombreCategoria,
  nombreProducto,
  tamano = 44,
  bloque = false,
}: Props) {
  const [fallo, setFallo] = useState(false);

  // Una URL nueva merece un intento nuevo: si el producto se editó y ahora tiene otra imagen,
  // no arrastrar el `onError` de la anterior.
  useEffect(() => {
    setFallo(false);
  }, [urlImagen]);

  const mostrarIcono = !urlImagen || fallo;
  const ladoGlifo = bloque ? 30 : Math.round(tamano * 0.55);

  return (
    <span
      className={`${estilos.marco} ${bloque ? estilos.bloque : ""}`.trim()}
      style={bloque ? undefined : { width: tamano, height: tamano }}
      data-icono={mostrarIcono ? "" : undefined}
    >
      {mostrarIcono ? (
        <IconoCategoria nombreCategoria={nombreCategoria} tamano={ladoGlifo} />
      ) : (
        <img
          className={estilos.imagen}
          src={urlImagen ?? undefined}
          alt={nombreProducto}
          loading="lazy"
          onError={() => setFallo(true)}
        />
      )}
    </span>
  );
}
