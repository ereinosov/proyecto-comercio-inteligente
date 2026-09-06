/**
 * Cliente de precios de competencia (US4). Catálogo abierto de canales, captura manual o por
 * archivo de observaciones, y la vista de comparación con la antigüedad calculada al leer.
 */

import { clienteHttp } from "./clienteHttp";

export interface CanalCompetencia {
  id_canal_competencia: number;
  nombre: string;
  nombre_normalizado: string;
}

export type PresentacionUnidad = "unidad" | "gramo" | "mililitro";

export interface ObservacionComparada {
  id_observacion_precio: number;
  canal: string;
  presentacion: string;
  precio_observado: string;
  precio_por_unidad_medida: string | null;
  comparable: boolean;
  dias_de_antiguedad: number;
  antiguedad_texto: string;
  indicador_forma: "lleno" | "medio" | "hueco";
}

export interface ComparacionPrecios {
  id_producto: number;
  id_sucursal: number;
  precio_propio_por_unidad_medida: string;
  observaciones: ObservacionComparada[];
}

export function listarCanales(): Promise<CanalCompetencia[]> {
  return clienteHttp.get<CanalCompetencia[]>("/canales-competencia");
}

export function agregarCanal(nombre: string): Promise<CanalCompetencia> {
  return clienteHttp.post<CanalCompetencia>("/canales-competencia", { nombre });
}

export function capturarObservacion(datos: {
  id_producto: number;
  id_canal_competencia: number;
  presentacion_cantidad: string;
  presentacion_unidad: PresentacionUnidad;
  precio_observado: string;
  fuente: string;
  origen_captura: "manual" | "archivo";
  id_turno?: number | null;
}): Promise<{ id_observacion_precio: number; comparable: boolean }> {
  return clienteHttp.post("/observaciones-precio", datos);
}

export function compararPrecios(
  idProducto: number,
  idSucursal: number,
): Promise<ComparacionPrecios> {
  return clienteHttp.get<ComparacionPrecios>(
    `/productos/${idProducto}/comparacion-precios?id_sucursal=${idSucursal}`,
  );
}
