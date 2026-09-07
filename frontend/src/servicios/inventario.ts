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

/** US14: un lote del desglose de existencia de un producto. `costo_unitario` sólo llega si se
 *  pidió `incluir_costo` — la pantalla de Venta nunca lo pide. */
export interface LoteExistencia {
  id_lote: number;
  cantidad: number;
  fecha_caducidad: string | null;
  instante_entrada: string;
  costo_unitario?: string | null;
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

/** US14: desglose por lote del saldo de un producto en una sucursal, en orden FEFO.
 *  `incluirCosto` sólo lo usan superficies con derecho a ver margen (traspasos), nunca Venta. */
export function existenciasPorLote(
  idSucursal: number,
  idProducto: number,
  incluirCosto = false,
): Promise<LoteExistencia[]> {
  const costo = incluirCosto ? "&incluir_costo=true" : "";
  return clienteHttp.get<LoteExistencia[]>(
    `/existencias/lotes?id_sucursal=${idSucursal}&id_producto=${idProducto}${costo}`,
  );
}

export function listarCapitalInmovilizado(idSucursal: number): Promise<CapitalInmovilizado[]> {
  return clienteHttp.get<CapitalInmovilizado[]>(
    `/capital-inmovilizado?id_sucursal=${idSucursal}`,
  );
}
