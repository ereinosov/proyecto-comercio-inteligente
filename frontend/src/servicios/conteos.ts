/**
 * Cliente de conteo físico (T070, T071). Iniciar un conteo acotado a una sucursal y a un
 * subconjunto opcional de productos; resolverlo capturando lo contado y ver la diferencia por
 * producto y lote. 006 clasifica la causa; este módulo sólo la expone en bruto.
 */

import { clienteHttp } from "./clienteHttp";

export interface RenglonConteo {
  id_conteo_renglon?: number;
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

export function listarConteos(opciones: {
  idSucursal?: number;
  estado?: ConteoFisico["estado"];
} = {}): Promise<ConteoFisico[]> {
  const params = new URLSearchParams();
  if (opciones.idSucursal !== undefined) params.set("id_sucursal", String(opciones.idSucursal));
  if (opciones.estado) params.set("estado", opciones.estado);
  const q = params.toString();
  return clienteHttp.get<ConteoFisico[]>(`/conteos-fisicos${q ? `?${q}` : ""}`);
}

export function obtenerConteo(idConteo: number): Promise<ConteoFisico> {
  return clienteHttp.get<ConteoFisico>(`/conteos-fisicos/${idConteo}`);
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
