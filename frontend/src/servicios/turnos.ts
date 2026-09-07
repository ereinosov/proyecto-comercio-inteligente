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
  // Token de sesión de turno (User Story 11, enmienda v2.4.0). Sólo lo puebla la respuesta de
  // `POST /turnos`; `null` en el cierre. Se guarda en memoria (clienteHttp), nunca en storage.
  token?: string | null;
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

// `listarOperadores` vive en `servicios/operadores.ts`; se re-exporta aquí por compatibilidad
// con quien ya lo importaba desde este módulo.
export { listarOperadores, type Operador } from "./operadores";
