/**
 * Cliente de señales del punto de venta (T053). Hoy sólo `consulta_no_atendida`: se registra
 * en dos toques desde la pantalla de venta y NUNCA pide un dato del cliente (FR-020).
 */

import { clienteHttp } from "./clienteHttp";

export interface ConsultaNoAtendida {
  id_consulta_no_atendida: number;
  id_producto: number;
  id_sucursal: number;
  instante: string;
  saldo_en_el_instante: number;
}

export function registrarConsultaNoAtendida(datos: {
  id_producto: number;
  id_turno: number;
}): Promise<ConsultaNoAtendida> {
  return clienteHttp.post<ConsultaNoAtendida>("/consultas-no-atendidas", datos);
}
