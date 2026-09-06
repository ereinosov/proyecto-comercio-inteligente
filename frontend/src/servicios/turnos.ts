/**
 * Cliente de turnos (POST /turnos). Detalle de implementación de T036, análogo a
 * servicios/productos.ts.
 */

import { clienteHttp } from "./clienteHttp";

export interface Turno {
  id_turno: number;
  id_operador: number;
  id_sucursal: number;
  caja: string;
  instante_apertura: string;
  instante_cierre: string | null;
}

export function abrirTurno(datos: {
  id_operador: number;
  id_sucursal: number;
  caja: string;
  pin: string;
}): Promise<Turno> {
  return clienteHttp.post<Turno>("/turnos", datos);
}

export function cerrarTurno(idTurno: number): Promise<Turno> {
  return clienteHttp.post<Turno>(`/turnos/${idTurno}/cierre`, {});
}

export interface Operador {
  id_operador: number;
  nombre: string;
  es_encargado: boolean;
}

export function listarOperadores(): Promise<Operador[]> {
  return clienteHttp.get<Operador[]>("/operadores");
}
