/**
 * Cliente HTTP de la administración de datos maestros (Parte 3): alta, edición y desactivación
 * de sucursal, producto, categoría, zona de exhibición y medio de pago.
 *
 * Escritura reservada a rol encargado o admin (backend: mecanismo central `requiere_rol`,
 * Principio VI). El `id_operador` viaja en el cuerpo, igual que en `POST /pagos/terminales`.
 *
 * Listados paginados: el backend responde `{ items, total }` (schema RespuestaPaginada); ver
 * clienteHttp.getPagina.
 */

import { clienteHttp, type Pagina } from "./clienteHttp";

export type EntidadMaestra = "sucursales" | "categorias" | "productos" | "zonas" | "medios";

export interface SucursalMaestra {
  id_sucursal: number;
  nombre: string;
  zona_horaria: string;
  activo: boolean;
}

export interface CategoriaMaestra {
  id_categoria: number;
  nombre: string;
  dias_umbral_inmovilizado: number | null;
  activo: boolean;
}

export interface ProductoMaestro {
  id_producto: number;
  nombre: string;
  id_categoria: number | null;
  es_granel: boolean;
  precio_vigente: string;
  lleva_caducidad: boolean;
  moneda: string;
  activo: boolean;
}

export interface ZonaMaestra {
  id_zona_exhibicion: number;
  id_sucursal: number;
  nombre: string;
  grado_privilegio: number;
  activo: boolean;
}

export interface MedioMaestro {
  id_medio_pago: number;
  nombre: string;
  requiere_terminal: boolean;
  admite_tokenizacion: boolean;
  activo: boolean;
}

export type FilaMaestra =
  | SucursalMaestra
  | CategoriaMaestra
  | ProductoMaestro
  | ZonaMaestra
  | MedioMaestro;

export interface Dependencia {
  descripcion: string;
  conteo: number;
}

export function idDeFila(entidad: EntidadMaestra, fila: FilaMaestra): number {
  switch (entidad) {
    case "sucursales":
      return (fila as SucursalMaestra).id_sucursal;
    case "categorias":
      return (fila as CategoriaMaestra).id_categoria;
    case "productos":
      return (fila as ProductoMaestro).id_producto;
    case "zonas":
      return (fila as ZonaMaestra).id_zona_exhibicion;
    case "medios":
      return (fila as MedioMaestro).id_medio_pago;
  }
}

export function listarMaestros(
  entidad: EntidadMaestra,
  opciones: {
    pagina?: number;
    tamanoPagina?: number;
    incluirInactivos?: boolean;
    busqueda?: string;
  } = {},
): Promise<Pagina<FilaMaestra>> {
  const params = new URLSearchParams();
  if (opciones.pagina !== undefined) params.set("pagina", String(opciones.pagina));
  if (opciones.tamanoPagina !== undefined) params.set("tamano_pagina", String(opciones.tamanoPagina));
  if (opciones.incluirInactivos) params.set("incluir_inactivos", "true");
  if (opciones.busqueda && opciones.busqueda.trim()) params.set("busqueda", opciones.busqueda.trim());
  const cadena = params.toString();
  return clienteHttp.getPagina<FilaMaestra>(`/administracion/${entidad}${cadena ? `?${cadena}` : ""}`);
}

export function dependenciasMaestro(
  entidad: EntidadMaestra,
  id: number,
): Promise<{ dependencias: Dependencia[]; tiene_dependencias: boolean }> {
  return clienteHttp.get(`/administracion/${entidad}/${id}/dependencias`);
}

export function fijarActivoMaestro(
  entidad: EntidadMaestra,
  id: number,
  cuerpo: { activo: boolean; id_operador: number },
): Promise<FilaMaestra> {
  return clienteHttp.post(`/administracion/${entidad}/${id}/desactivacion`, cuerpo);
}

export function crearMaestro(
  entidad: EntidadMaestra,
  cuerpo: Record<string, unknown>,
): Promise<FilaMaestra> {
  return clienteHttp.post(`/administracion/${entidad}`, cuerpo);
}

export function editarMaestro(
  entidad: EntidadMaestra,
  id: number,
  cuerpo: Record<string, unknown>,
): Promise<FilaMaestra> {
  return clienteHttp.put(`/administracion/${entidad}/${id}`, cuerpo);
}
