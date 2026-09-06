/**
 * Cliente de catálogo (GET /productos). Necesario para que la pantalla de venta pueda listar
 * productos; no es una tarea propia de tasks.md, es un detalle de implementación de T037,
 * igual que persistencia/movimientos.py lo fue de T026 en el backend.
 */

import { clienteHttp } from "./clienteHttp";

export interface Producto {
  id_producto: number;
  nombre: string;
  es_granel: boolean;
  lleva_caducidad: boolean;
  precio_efectivo: string;
  moneda: string;
  id_categoria: number | null;
}

export interface Categoria {
  id_categoria: number;
  nombre: string;
  dias_umbral_inmovilizado: number | null;
  activo: boolean;
}

export function listarProductos(idSucursal?: number): Promise<Producto[]> {
  const query = idSucursal !== undefined ? `?id_sucursal=${idSucursal}` : "";
  return clienteHttp.get<Producto[]>(`/productos${query}`);
}

export function listarCategorias(): Promise<Categoria[]> {
  return clienteHttp.get<Categoria[]>("/categorias");
}
