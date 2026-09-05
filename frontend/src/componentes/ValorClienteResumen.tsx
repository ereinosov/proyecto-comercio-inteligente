/**
 * Resumen de valor de cliente para el registro de Operación (T024, FR-011a). Únicamente la
 * puntuación compuesta — el desglose de las tres dimensiones vive en el registro de Análisis
 * (Clientes.tsx, T027). Sin animación de revelación: aquí es información de contexto durante
 * el cobro, no la confirmación de una acción del cajero (constitución, Sistema de Diseño).
 *
 * Un cliente con historial insuficiente (`valor === null`) se distingue explícitamente
 * (FR-007, SC-004): nunca se muestra 0 ni se omite en silencio.
 */

import estilos from "./ValorClienteResumen.module.css";

interface Props {
  valor: number | null;
}

export function ValorClienteResumen({ valor }: Props) {
  if (valor === null) {
    return <span className={estilos.insuficiente}>· datos insuficientes</span>;
  }

  return (
    <span className={estilos.resumen}>
      · Valor <span className={estilos.puntuacion}>{Math.round(valor)}</span>
    </span>
  );
}
