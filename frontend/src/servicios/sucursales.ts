/**
 * Cliente de `GET /sucursales`. La lista de sucursales es la fuente para cualquier selector;
 * codificar que son dos está prohibido (FR-046).
 */

import { clienteHttp } from "./clienteHttp";

export interface Sucursal {
  id_sucursal: number;
  nombre: string;
  zona_horaria: string;
  activo: boolean;
}

/**
 * Por defecto `GET /sucursales` excluye las sucursales desactivadas (`activo = false`): esta
 * lista alimenta los selectores de "elegir sucursal para una acción nueva" (abrir turno,
 * crear registros), donde una sucursal desactivada no debe poder elegirse.
 *
 * `incluirInactivas = true` es para pantallas de reporte / historial, que siguen viendo todas
 * sus sucursales (un turno cerrado contra una sucursal luego desactivada no se rompe).
 */
export function listarSucursales(incluirInactivas = false): Promise<Sucursal[]> {
  return clienteHttp.get<Sucursal[]>(
    `/sucursales${incluirInactivas ? "?incluir_inactivas=true" : ""}`,
  );
}
