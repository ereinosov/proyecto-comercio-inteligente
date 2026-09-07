/**
 * Segmentado: pestañas internas de una pantalla (DESIGN.md v1.8.0).
 *
 * Consolida las cuatro implementaciones duplicadas que había —`.segmentado`/`.segActivo`/
 * `.segInactivo` (Administracion, CajaFraude, GestionOperadores, Pagos), `.subnav`/`.subtab`/
 * `.subtabActiva` (Competencia) y `.selectorVista`/`.vistaActiva`/`.vistaInactiva`
 * (Promociones, Pronostico)— en una sola pieza. Todas hacían lo mismo: un grupo de pestañas
 * de estado controlado por el padre, subrayado en la activa, sin fondo relleno. La única
 * variación real era tipografía/densidad, que aquí es la prop `registro` (mismo patrón y
 * mismo default que `Boton` y `EncabezadoPantalla`).
 *
 * No lleva iconos ni badges: ninguna de las implementaciones consolidadas los usaba.
 */

import estilos from "./Segmentado.module.css";

interface Props<T extends string> {
  opciones: { valor: T; texto: string }[];
  activa: T;
  onCambiar: (valor: T) => void;
  registro?: "operacion" | "analisis";
  /** Etiqueta accesible del grupo de pestañas. */
  etiqueta?: string;
}

export function Segmentado<T extends string>({
  opciones,
  activa,
  onCambiar,
  registro = "operacion",
  etiqueta,
}: Props<T>) {
  return (
    <div
      role="tablist"
      aria-label={etiqueta}
      className={`${estilos.segmentado} ${estilos[registro]}`}
    >
      {opciones.map((opcion) => {
        const seleccionada = opcion.valor === activa;
        return (
          <button
            key={opcion.valor}
            type="button"
            role="tab"
            aria-selected={seleccionada}
            className={seleccionada ? estilos.activa : estilos.inactiva}
            onClick={() => onCambiar(opcion.valor)}
          >
            {opcion.texto}
          </button>
        );
      })}
    </div>
  );
}
