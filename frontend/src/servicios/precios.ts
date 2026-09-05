/**
 * Cliente HTTP de 003-precios-margenes: margen real (T016, User Story 1), rol de producto
 * (T023, User Story 2) y sugerencias de precio/colocación (T034, T045, User Story 3 y 4).
 * `margen`/`margen_usado` llegan como número (ratio 0-1, no porcentaje);
 * `costo_vigente`/`precio_vigente`/`precio_sugerido` como cadena decimal
 * (contracts/openapi.yaml).
 */

import { clienteHttp } from "./clienteHttp";

export type RolProducto = "gancho_trafico" | "generador_margen";

export interface MargenProducto {
  id_producto: number;
  id_sucursal: number;
  costo_vigente: string | null;
  precio_vigente: string;
  margen: number | null;
  confiable: boolean;
  instante_calculo: string;
}

export interface RolProductoDetalle {
  id_producto: number;
  rol: RolProducto | null;
  instante_asignacion: string | null;
}

export interface ObservacionCompetenciaUsada {
  id_observacion_precio: number;
  canal: string;
  precio_por_unidad_medida: string;
  dias_de_antiguedad: number;
}

export interface SugerenciaPrecio {
  id_sugerencia_precio: number;
  id_producto: number;
  id_sucursal: number;
  precio_sugerido: string;
  margen_usado: number | null;
  rol_usado: RolProducto | null;
  observacion_competencia_usada: ObservacionCompetenciaUsada | null;
  instante_generacion: string;
  aplicada: boolean;
  instante_aplicacion: string | null;
}

export interface SugerenciaColocacion {
  id_sugerencia_colocacion: number;
  id_producto: number;
  id_sucursal: number;
  id_zona_exhibicion: number;
  zona_nombre: string;
  margen_usado: number | null;
  rol_usado: RolProducto | null;
  instante_generacion: string;
  aplicada: boolean;
  instante_aplicacion: string | null;
}

export function listarMargenes(idSucursal: number): Promise<MargenProducto[]> {
  return clienteHttp.get<MargenProducto[]>(`/margenes?id_sucursal=${idSucursal}`);
}

export function obtenerMargen(idProducto: number, idSucursal: number): Promise<MargenProducto> {
  return clienteHttp.get<MargenProducto>(
    `/productos/${idProducto}/margen?id_sucursal=${idSucursal}`
  );
}

export function obtenerRol(idProducto: number): Promise<RolProductoDetalle> {
  return clienteHttp.get<RolProductoDetalle>(`/productos/${idProducto}/rol`);
}

export function asignarRol(idProducto: number, rol: RolProducto): Promise<RolProductoDetalle> {
  return clienteHttp.put<RolProductoDetalle>(`/productos/${idProducto}/rol`, { rol });
}

export function obtenerSugerenciaPrecio(
  idProducto: number,
  idSucursal: number
): Promise<SugerenciaPrecio> {
  return clienteHttp.get<SugerenciaPrecio>(
    `/productos/${idProducto}/sugerencia-precio?id_sucursal=${idSucursal}`
  );
}

export function aplicarSugerenciaPrecio(
  idProducto: number,
  idSugerenciaPrecio: number
): Promise<SugerenciaPrecio> {
  return clienteHttp.post<SugerenciaPrecio>(`/productos/${idProducto}/sugerencia-precio/aplicar`, {
    id_sugerencia_precio: idSugerenciaPrecio,
  });
}

export function obtenerSugerenciaColocacion(
  idProducto: number,
  idSucursal: number
): Promise<SugerenciaColocacion> {
  return clienteHttp.get<SugerenciaColocacion>(
    `/productos/${idProducto}/sugerencia-colocacion?id_sucursal=${idSucursal}`
  );
}

export function aplicarSugerenciaColocacion(
  idProducto: number,
  idSugerenciaColocacion: number
): Promise<SugerenciaColocacion> {
  return clienteHttp.post<SugerenciaColocacion>(
    `/productos/${idProducto}/sugerencia-colocacion/aplicar`,
    { id_sugerencia_colocacion: idSugerenciaColocacion }
  );
}
