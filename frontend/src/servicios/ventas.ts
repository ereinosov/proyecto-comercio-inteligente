/**
 * Cliente de venta (T039). Genera la clave_idempotencia ANTES del primer intento y la
 * conserva para cualquier reintento — nunca una clave nueva por reintento, o la idempotencia
 * del backend no protege nada (research.md, decisión 2).
 */

import { clienteHttp } from "./clienteHttp";

export interface RenglonVentaNuevo {
  id_producto: number;
  cantidad_unidades?: number;
  cantidad_gramos?: number;
}

export interface RenglonVentaRespuesta {
  id_renglon_venta: number;
  id_producto: number;
  cantidad_unidades: number | null;
  cantidad_gramos: number | null;
  precio_aplicado: string;
  importe: string;
  moneda: string;
  lotes_consumidos: { id_lote: number | null; cantidad: number }[];
}

export interface Advertencia {
  codigo: string;
  mensaje: string;
  id_producto: number;
}

export interface Venta {
  id_venta: number;
  clave_idempotencia: string;
  id_turno: number;
  id_operador: number;
  id_sucursal: number;
  referencia_terminal_pago: string | null;
  instante: string;
  total: string;
  moneda: string;
  anulada: boolean;
  renglones: RenglonVentaRespuesta[];
  advertencias: Advertencia[];
}

export function generarClaveIdempotencia(): string {
  return `venta-${crypto.randomUUID()}`;
}

export function registrarVenta(datos: {
  clave_idempotencia: string;
  id_turno: number;
  referencia_terminal_pago?: string | null;
  renglones: RenglonVentaNuevo[];
}): Promise<Venta> {
  return clienteHttp.post<Venta>("/ventas", datos);
}

export function anularVenta(
  idVenta: number,
  datos: { motivo?: string } = {},
): Promise<{ id_anulacion_venta: number; id_venta: number; id_operador: number; instante: string; motivo: string | null }> {
  // User Story 11: el operador que anula lo resuelve el backend del token de sesión de turno.
  return clienteHttp.post(`/ventas/${idVenta}/anulacion`, datos);
}
