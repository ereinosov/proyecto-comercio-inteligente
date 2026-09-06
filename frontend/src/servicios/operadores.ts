/**
 * Cliente de `GET /operadores`. Servicio dedicado, como `servicios/sucursales.ts` — ninguna
 * pantalla debe hacer `fetch` directo a la URL base para esto.
 */

import { clienteHttp } from "./clienteHttp";

export interface Operador {
  id_operador: number;
  nombre: string;
  es_encargado: boolean;
}

export function listarOperadores(): Promise<Operador[]> {
  return clienteHttp.get<Operador[]>("/operadores");
}
