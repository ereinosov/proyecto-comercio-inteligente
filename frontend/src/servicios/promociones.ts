/**
 * Cliente HTTP de 005-promociones-inteligentes (T017 cupones + redención; T030 ofertas de
 * recompra; T044 experimento de reactivación). Formas conforme a
 * `specs/005-promociones-inteligentes/contracts/openapi.yaml`.
 *
 * Todos los importes, porcentajes, proporciones y el valor p llegan como cadena decimal — nunca
 * coma flotante (constitución, Restricciones Técnicas). Este módulo no participa del cobro: la
 * redención se registra DESPUÉS de la venta (Principio II).
 */

import { clienteHttp } from "./clienteHttp";

// --------------------------------------------------------------------------
// User Story 1 — cupón por fecha fija + redención transversal (T017)
// --------------------------------------------------------------------------

export type EstadoCupon = "generado" | "redimido" | "vencido";

export interface Cupon {
  id_cupon: number;
  id_campania: number;
  id_cliente: number;
  motivo: string;
  fecha_objetivo: string;
  valido_desde: string;
  valido_hasta: string;
  porcentaje_descuento: string;
  estado: EstadoCupon;
  instante_generacion: string;
}

export interface ResultadoGeneracion {
  id_campania: number;
  cupones_generados: number;
  cupones_ya_existentes: number;
}

export type TipoOrigenRedencion = "cupon" | "oferta_recompra" | "reactivacion";

export interface Redencion {
  id_redencion_promocion: number;
  tipo_origen: TipoOrigenRedencion;
  id_cupon: number | null;
  id_oferta_recompra: number | null;
  id_asignacion_experimento: number | null;
  id_venta: number;
  id_producto: number | null;
  id_sucursal: number;
  periodo: string;
  descuento_aplicado: string | null;
  instante_redencion: string;
}

export function generarCupones(
  desde: string,
  hasta: string,
  nombreCampania?: string
): Promise<ResultadoGeneracion> {
  return clienteHttp.post<ResultadoGeneracion>("/promociones/cupones/generacion", {
    desde,
    hasta,
    nombre_campania: nombreCampania,
  });
}

export function listarCupones(opciones?: {
  idCliente?: number;
  estado?: EstadoCupon;
  vigentes?: boolean;
}): Promise<Cupon[]> {
  const params = new URLSearchParams();
  if (opciones?.idCliente !== undefined) params.set("id_cliente", String(opciones.idCliente));
  if (opciones?.estado) params.set("estado", opciones.estado);
  if (opciones?.vigentes) params.set("vigentes", "true");
  const q = params.toString();
  return clienteHttp.get<Cupon[]>(`/promociones/cupones${q ? `?${q}` : ""}`);
}

export interface RedencionNueva {
  id_venta: number;
  tipo_origen: TipoOrigenRedencion;
  id_cupon?: number;
  id_oferta_recompra?: number;
  id_asignacion_experimento?: number;
  id_producto?: number;
}

export function registrarRedencion(cuerpo: RedencionNueva): Promise<Redencion> {
  return clienteHttp.post<Redencion>("/promociones/redenciones", cuerpo);
}

// --------------------------------------------------------------------------
// User Story 2 — empuje por recompra con reserva de precio (T030)
// --------------------------------------------------------------------------

export type DesenlaceOferta = "pendiente" | "comprado" | "no_comprado" | "reserva_vencida";

export interface OfertaRecompra {
  id_oferta_recompra: number;
  id_campania: number;
  id_cliente: number;
  id_producto: number;
  id_sucursal: number;
  intervalo_esperado_dias_disparo: string;
  justificacion: {
    ventas_consideradas: number[];
    compras_del_producto: number;
    ventana_dias: number;
  };
  precio_garantizado: string;
  reserva_desde: string;
  reserva_hasta: string;
  estado_reserva: "vigente" | "vencida";
  desenlace: DesenlaceOferta;
  instante_generacion: string;
}

export interface ResultadoDeteccion {
  id_campania: number;
  ofertas_propuestas: number;
  ofertas_ya_activas: number;
}

export function detectarOfertasRecompra(idSucursal: number): Promise<ResultadoDeteccion> {
  return clienteHttp.post<ResultadoDeteccion>("/promociones/ofertas-recompra/deteccion", {
    id_sucursal: idSucursal,
  });
}

export function listarOfertasRecompra(opciones?: {
  idCliente?: number;
  desenlace?: DesenlaceOferta;
}): Promise<OfertaRecompra[]> {
  const params = new URLSearchParams();
  if (opciones?.idCliente !== undefined) params.set("id_cliente", String(opciones.idCliente));
  if (opciones?.desenlace) params.set("desenlace", opciones.desenlace);
  const q = params.toString();
  return clienteHttp.get<OfertaRecompra[]>(`/promociones/ofertas-recompra${q ? `?${q}` : ""}`);
}

// --------------------------------------------------------------------------
// User Story 3 — reactivación con experimento de control (T044)
// --------------------------------------------------------------------------

export type VeredictoExperimento =
  | "en_curso"
  | "efectivo"
  | "no_efectivo"
  | "muestra_insuficiente";

export interface Experimento {
  id_experimento_reactivacion: number;
  id_campania: number;
  id_sucursal: number | null;
  semilla: number;
  algoritmo: string;
  proporcion_tratamiento: string;
  ventana_medicion_dias: number;
  porcentaje_descuento: string;
  parametros_muestra: {
    tasa_retorno_base_esperada: string;
    mde_puntos_porcentuales: string;
    alfa: string;
    poder: string;
    tamano_minimo_muestra: number;
  };
  n_elegibles: number;
  n_tratamiento: number | null;
  n_control: number | null;
  retorno_tratamiento: string | null;
  retorno_control: string | null;
  incrementalidad: string | null;
  estadistico_z: string | null;
  valor_p: string | null;
  veredicto: VeredictoExperimento;
  motivo_muestra_insuficiente: string | null;
  instante_asignacion: string;
  instante_cierre: string | null;
}

export interface Asignacion {
  id_asignacion_experimento: number;
  id_experimento_reactivacion: number;
  id_cliente: number;
  id_senal_fuga: number;
  grupo: "tratamiento" | "control";
  retorno: boolean;
  id_venta_retorno: number | null;
  instante_retorno: string | null;
}

export interface ExperimentoNuevo {
  id_sucursal?: number;
  semilla?: number;
  ventana_medicion_dias?: number;
  porcentaje_descuento?: string;
  mde_puntos_porcentuales?: string;
  nombre_campania?: string;
}

export function crearExperimento(cuerpo: ExperimentoNuevo = {}): Promise<Experimento> {
  return clienteHttp.post<Experimento>("/promociones/experimentos", cuerpo);
}

export function obtenerExperimento(id: number): Promise<Experimento> {
  return clienteHttp.get<Experimento>(`/promociones/experimentos/${id}`);
}

export function obtenerAsignaciones(
  id: number,
  grupo?: "tratamiento" | "control"
): Promise<Asignacion[]> {
  const q = grupo ? `?grupo=${grupo}` : "";
  return clienteHttp.get<Asignacion[]>(`/promociones/experimentos/${id}/asignaciones${q}`);
}

export function cerrarExperimento(id: number): Promise<Experimento> {
  return clienteHttp.post<Experimento>(`/promociones/experimentos/${id}/cierre`, {});
}
