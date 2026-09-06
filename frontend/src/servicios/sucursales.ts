/**
 * Cliente de `GET /sucursales`. La lista de sucursales es la fuente para cualquier selector;
 * codificar que son dos está prohibido (FR-046).
 */

import { clienteHttp } from "./clienteHttp";

export interface Sucursal {
  id_sucursal: number;
  nombre: string;
  zona_horaria: string;
}

export function listarSucursales(): Promise<Sucursal[]> {
  return clienteHttp.get<Sucursal[]>("/sucursales");
}
