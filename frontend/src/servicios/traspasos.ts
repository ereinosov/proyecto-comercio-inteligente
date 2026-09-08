/**
 * Cliente de traspasos entre sucursales (US6). Despachar deja la mercancía en tránsito;
 * confirmar la recepción expone la discrepancia por producto, sin clasificarla.
 */

import { clienteHttp } from "./clienteHttp";

export interface RenglonTraspaso {
  id_producto: number;
  cantidad_despachada: number;
  cantidad_recibida: number | null;
  discrepancia: number | null;
}

export interface Traspaso {
  id_traspaso: number;
  id_sucursal_origen: number;
  id_sucursal_destino: number;
  estado: "en_transito" | "recibido";
  instante_despacho: string;
  instante_recepcion: string | null;
  renglones: RenglonTraspaso[];
}

export function despacharTraspaso(datos: {
  id_sucursal_origen: number;
  id_sucursal_destino: number;
  renglones: { id_producto: number; cantidad: number }[];
}): Promise<Traspaso> {
  return clienteHttp.post<Traspaso>("/traspasos", datos);
}

export function listarTraspasos(opciones: {
  estado?: Traspaso["estado"];
  idSucursalOrigen?: number;
  idSucursalDestino?: number;
} = {}): Promise<Traspaso[]> {
  const params = new URLSearchParams();
  if (opciones.estado) params.set("estado", opciones.estado);
  if (opciones.idSucursalOrigen !== undefined)
    params.set("id_sucursal_origen", String(opciones.idSucursalOrigen));
  if (opciones.idSucursalDestino !== undefined)
    params.set("id_sucursal_destino", String(opciones.idSucursalDestino));
  const q = params.toString();
  return clienteHttp.get<Traspaso[]>(`/traspasos${q ? `?${q}` : ""}`);
}

export function recibirTraspaso(
  idTraspaso: number,
  renglones: { id_producto: number; cantidad_recibida: number }[],
): Promise<Traspaso> {
  return clienteHttp.post<Traspaso>(`/traspasos/${idTraspaso}/recepcion`, { renglones });
}
