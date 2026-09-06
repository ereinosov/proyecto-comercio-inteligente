/**
 * Cliente de inventario (T049, US2 · US7). Registrar entradas por compra, consultar existencias
 * (incluido el saldo negativo) y el listado de capital inmovilizado.
 */

import { clienteHttp } from "./clienteHttp";

export interface Lote {
  id_lote: number;
  id_producto: number;
  id_sucursal: number;
  cantidad_restante: number;
  costo_unitario: string;
  moneda: string;
  fecha_caducidad: string | null;
  instante_entrada: string;
}

export interface Existencia {
  id_sucursal: number;
  id_producto: number;
  cantidad: number;
  es_granel: boolean;
}

export interface CapitalInmovilizado {
  id_lote: number;
  id_producto: number;
  id_sucursal: number;
  cantidad_restante: number;
  dias_sin_salida: number;
  dias_umbral_aplicado: number;
  umbral_heredado_del_global: boolean;
  valor_calculable: boolean;
  valor_inmovilizado: string | null;
}

export function registrarEntrada(datos: {
  id_sucursal: number;
  id_producto: number;
  cantidad: number;
  costo_unitario: string;
  fecha_caducidad?: string | null;
}): Promise<Lote> {
  return clienteHttp.post<Lote>("/entradas-inventario", datos);
}

export function listarExistencias(idSucursal: number, idProducto?: number): Promise<Existencia[]> {
  const q = idProducto !== undefined ? `&id_producto=${idProducto}` : "";
  return clienteHttp.get<Existencia[]>(`/existencias?id_sucursal=${idSucursal}${q}`);
}

export function listarCapitalInmovilizado(idSucursal: number): Promise<CapitalInmovilizado[]> {
  return clienteHttp.get<CapitalInmovilizado[]>(
    `/capital-inmovilizado?id_sucursal=${idSucursal}`,
  );
}
