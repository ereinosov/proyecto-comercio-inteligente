/**
 * Cliente HTTP de 002-clientes-fidelizacion (T013, T020, T021, T036). El desglose de valor y
 * el estado de fuga solo llegan en `obtenerCliente` (detalle), nunca en los listados/búsqueda
 * — esos solo llevan la puntuación compuesta (FR-011).
 */

import { clienteHttp } from "./clienteHttp";

export interface ClienteResumen {
  id_cliente: number;
  nombre: string | null;
  valor: number | null;
  monto_total: string;
}

export interface Cliente {
  id_cliente: number;
  nombre: string | null;
  fecha_nacimiento: string | null;
  contacto: string | null;
  /** Cédula (10 díg.) o RUC de persona natural (13). Opcional — sólo para no duplicar al
   * cliente entre visitas (FR-017). `null` si el cajero no lo registró. */
  identificador: string | null;
  fecha_alta: string;
  anonimizado: boolean;
}

export interface DesgloseValor {
  compuesto: number;
  percentil_frecuencia: number;
  percentil_monto: number;
  percentil_margen: number;
}

export type EstadoFuga = "sin_senal" | "datos_insuficientes" | "activa" | "confirmada" | "resuelta";

export interface Fuga {
  estado: EstadoFuga;
  intervalo_esperado_dias: number | null;
  instante_deteccion: string | null;
  instante_confirmacion: string | null;
  instante_resolucion: string | null;
}

export interface ClienteDetalle extends Cliente {
  valor: DesgloseValor | null;
  fuga: Fuga | null;
}

export interface Visita {
  id_visita: number;
  id_cliente: number;
  id_venta: number;
  instante: string;
  monto_total: string;
  margen_relativo: number;
}

export function buscarClientes(q: string): Promise<ClienteResumen[]> {
  if (q.trim().length === 0) return Promise.resolve([]);
  return clienteHttp.get<ClienteResumen[]>(`/clientes/busqueda?q=${encodeURIComponent(q)}`);
}

export function registrarCliente(datos: {
  nombre?: string;
  fecha_nacimiento?: string;
  contacto?: string;
  identificador?: string;
}): Promise<Cliente> {
  return clienteHttp.post<Cliente>("/clientes", datos);
}

export function actualizarCliente(
  idCliente: number,
  datos: {
    nombre: string;
    fecha_nacimiento: string;
    contacto?: string | null;
    identificador?: string | null;
  },
): Promise<Cliente> {
  return clienteHttp.put<Cliente>(`/clientes/${idCliente}`, datos);
}

export function registrarVisita(idCliente: number, idVenta: number): Promise<Visita> {
  return clienteHttp.post<Visita>(`/clientes/${idCliente}/visitas`, { id_venta: idVenta });
}

export function listarClientes(orden: "valor" | "monto_total" = "valor"): Promise<ClienteResumen[]> {
  // `GET /clientes` responde `{ items, total }` (schema RespuestaPaginada); sin `pagina`,
  // `items` trae todos los clientes.
  return clienteHttp.getPagina<ClienteResumen>(`/clientes?orden=${orden}`).then((p) => p.items);
}

export function listarClientesPagina(
  orden: "valor" | "monto_total",
  pagina: number,
  tamanoPagina: number,
) {
  return clienteHttp.getPagina<ClienteResumen>(
    `/clientes?orden=${orden}&pagina=${pagina}&tamano_pagina=${tamanoPagina}`,
  );
}

export function obtenerCliente(idCliente: number): Promise<ClienteDetalle> {
  return clienteHttp.get<ClienteDetalle>(`/clientes/${idCliente}`);
}
