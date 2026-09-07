/**
 * Cliente de `/operadores`. Servicio dedicado, como `servicios/sucursales.ts` — ninguna
 * pantalla debe hacer `fetch` directo a la URL base para esto.
 *
 * User Story 10 (Principio VI): `Operador` lleva `rol` (`cajero`|`encargado`|`admin`) e
 * `id_sucursal` en vez del booleano de encargado anterior. El alta / edición / desactivación
 * son exclusivas del rol `admin` (el backend lo verifica con `requiere_rol`).
 *
 * User Story 11 (enmienda v2.4.0): la identidad del solicitante ya no viaja en el cuerpo; la
 * resuelve el backend del token de sesión de turno (header `Authorization`, lo añade clienteHttp).
 */

import { clienteHttp } from "./clienteHttp";
import type { Rol } from "../hooks/useRol";

export interface Operador {
  id_operador: number;
  nombre: string;
  rol: Rol;
  id_sucursal: number;
  activo?: boolean;
}

export interface OperadorNuevo {
  nombre: string;
  rol: Rol;
  id_sucursal: number;
  pin?: string;
}

export function listarOperadores(): Promise<Operador[]> {
  return clienteHttp.get<Operador[]>("/operadores");
}

export function crearOperador(datos: OperadorNuevo): Promise<Operador> {
  return clienteHttp.post<Operador>("/operadores", datos);
}

export function actualizarOperador(
  idOperador: number,
  datos: OperadorNuevo,
): Promise<Operador> {
  return clienteHttp.put<Operador>(`/operadores/${idOperador}`, datos);
}

export function fijarActivoOperador(
  idOperador: number,
  datos: { activo: boolean },
): Promise<Operador> {
  return clienteHttp.post<Operador>(`/operadores/${idOperador}/activo`, datos);
}
