/**
 * Cliente de conteo físico (T070, T071). Iniciar un conteo acotado a una sucursal y a un
 * subconjunto opcional de productos; resolverlo capturando lo contado y ver la diferencia por
 * producto y lote. 006 clasifica la causa; este módulo sólo la expone en bruto.
 */

import { clienteHttp } from "./clienteHttp";

export interface RenglonConteo {
  id_producto: number;
  id_lote: number | null;
  cantidad_esperada: number;
  cantidad_contada: number;
  diferencia: number;
}

export interface ConteoFisico {
  id_conteo_fisico: number;
  id_sucursal: number;
  estado: "abierto" | "resuelto";
  instante_inicio: string;
  instante_resolucion: string | null;
  renglones?: RenglonConteo[];
}

export function iniciarConteo(datos: {
  id_sucursal: number;
  id_productos?: number[];
}): Promise<ConteoFisico> {
  return clienteHttp.post<ConteoFisico>("/conteos-fisicos", datos);
}

export function resolverConteo(
  idConteo: number,
  renglones: { id_producto: number; id_lote?: number | null; cantidad_contada: number }[],
): Promise<ConteoFisico> {
  return clienteHttp.post<ConteoFisico>(`/conteos-fisicos/${idConteo}/resolucion`, { renglones });
}
