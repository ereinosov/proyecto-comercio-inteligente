/**
 * Etiqueta de segmento de un cliente en el detalle de Clientes (002). DATO DE LECTURA: se sirve
 * desde 008 (`GET /reportes/segmentos/cliente/{id}`), 002 no gana ningún campo (constitución
 * v2.6.0). Si nunca se recalcularon los segmentos, no se muestra nada.
 */

import { useEffect, useState } from "react";
import { obtenerSegmentoDeCliente, type EtiquetaSegmentoCliente } from "../servicios/reportes";
import estilos from "./EtiquetaSegmento.module.css";

export function EtiquetaSegmento({ idCliente }: { idCliente: number }) {
  const [dato, setDato] = useState<EtiquetaSegmentoCliente | null>(null);

  useEffect(() => {
    let vivo = true;
    obtenerSegmentoDeCliente(idCliente)
      .then((d) => vivo && setDato(d))
      .catch(() => vivo && setDato(null));
    return () => {
      vivo = false;
    };
  }, [idCliente]);

  if (!dato || dato.etiqueta_grupo === null) return null;

  return (
    <p className={estilos.etiqueta}>
      <span className={estilos.grupo}>{dato.etiqueta_grupo.replace("_", " ")}</span>
      {dato.descripcion && <span className={estilos.descripcion}> — {dato.descripcion}</span>}
      {dato.corrida && (
        <span className={estilos.fecha}> · segmentos del {new Date(dato.corrida).toLocaleDateString()}</span>
      )}
    </p>
  );
}
