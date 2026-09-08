/**
 * Cliente HTTP de 002-clientes-fidelizacion (T013, T020, T021, T036). El desglose de valor solo
 * llega en `obtenerCliente` (detalle). `estado_fuga` llega en `obtenerCliente` y en el LISTADO
 * (`GET /clientes`, rol `encargado`, para el tint de fuga por fila), pero NO en
 * `GET /clientes/busqueda` (nivel base): la señal de fuga es dato de `encargado` (constitución
 * v2.5.0) y el flujo de cajero de Venta solo necesita `valor` (FR-011a).
 */

import { clienteHttp } from "./clienteHttp";

export type EstadoFuga = "sin_senal" | "datos_insuficientes" | "activa" | "confirmada" | "resuelta";

export interface ClienteResumen {
  id_cliente: number;
  nombre: string | null;
  valor: number | null;
  monto_total: string;
  /** Sólo en el listado `GET /clientes` (rol `encargado`), para el tint de fuga por fila sin
   * pedir el detalle de cada cliente. Ausente en `GET /clientes/busqueda` (nivel base): dato de
   * `encargado` (constitución v2.5.0). */
  estado_fuga?: EstadoFuga;
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
  busqueda?: string,
) {
  const params = new URLSearchParams({
    orden,
    pagina: String(pagina),
    tamano_pagina: String(tamanoPagina),
  });
  if (busqueda && busqueda.trim()) params.set("busqueda", busqueda.trim());
  return clienteHttp.getPagina<ClienteResumen>(`/clientes?${params.toString()}`);
}

export function obtenerCliente(idCliente: number): Promise<ClienteDetalle> {
  return clienteHttp.get<ClienteDetalle>(`/clientes/${idCliente}`);
}

/** US6: distribución instantánea de clientes por segmento de fuga (snapshot, no serie temporal). */
export type ResumenFuga = Record<
  "sin_senal" | "datos_insuficientes" | "activa" | "confirmada" | "resuelta",
  number
>;

export function obtenerResumenFuga(): Promise<ResumenFuga> {
  return clienteHttp.get<ResumenFuga>("/clientes/fuga/resumen");
}
