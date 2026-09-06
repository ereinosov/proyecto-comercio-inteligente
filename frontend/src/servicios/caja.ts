/**
 * Cliente HTTP de 006-caja-mermas-fraude (T015 arqueos US1; T027 mermas US2; T039 indicadores US3;
 * T048 anomalías US4). Montos y valoraciones llegan como cadena decimal; cantidades como número
 * entero (gramos para granel) — ver contracts/openapi.yaml.
 *
 * Las rutas bloqueadas (`ejecutarCruceOperador`, y `registrarMerma` con `id_conteo_renglon`) devuelven
 * `409 caja_bloqueado_por_001` mientras 001 no implemente su User Story 5 — comportamiento
 * controlado y esperado, no un fallo.
 */

import { clienteHttp } from "./clienteHttp";

export interface Arqueo {
  id_arqueo: number;
  id_turno: number;
  id_operador: number;
  id_sucursal: number;
  dia_local: string;
  monto_esperado: string;
  monto_contado: string;
  diferencia: string;
  motivo_conocido: string | null;
  genero_anomalia: boolean;
  id_anomalia_caja: number | null;
  ajustes: Array<{
    instante: string;
    id_operador: number;
    monto_contado_anterior: string;
    monto_contado_nuevo: string;
    nota: string;
  }>;
  instante_cierre_arqueo: string;
}

export type CausaMerma =
  | "vencimiento"
  | "dano"
  | "robo_externo"
  | "error_conteo"
  | "merma_granel"
  | "pendiente_clasificar";

export interface Merma {
  id_merma: number;
  id_conteo_renglon: number | null;
  id_producto: number;
  id_lote: number | null;
  id_sucursal: number;
  cantidad_faltante: number;
  causa: CausaMerma;
  valoracion: string | null;
  moneda: string;
  periodo_desde: string;
  periodo_hasta: string;
  estado: "pendiente_clasificar" | "clasificada";
  conciliar_con_conteo: boolean;
  id_operador_registro: number;
  instante_registro: string;
  nota: string | null;
}

export interface DesgloseMermas {
  total_valorado: string;
  con_valor_no_calculable: number;
  mermas: Merma[];
}

export interface AlertaCaducidad {
  id_lote: number;
  id_producto: number;
  nombre_producto: string;
  id_sucursal: number;
  fecha_caducidad: string;
  dias_para_caducar: number;
  ya_caducado: boolean;
  existencia_restante: number;
  valor_en_riesgo: string | null;
}

export interface IndicadorOperador {
  id_operador: number;
  nombre: string;
  ventas_periodo: number;
  comparable: boolean;
  tasa_anulaciones: string;
  concentracion_bajo_lista: string;
  se_desvia: boolean;
  detalle_desviacion: string[] | null;
}

export interface IndicadoresRespuesta {
  periodo: string;
  mediana_pares_tasa_anulaciones: string | null;
  mediana_pares_concentracion_bajo_lista: string | null;
  factor_desviacion_anulaciones: string;
  factor_desviacion_precio_bajo_lista: string;
  operadores: IndicadorOperador[];
}

export interface AnomaliaCaja {
  id_anomalia_caja: number;
  origen: "efectivo" | "inventario";
  estado: "sin_explicacion" | "resuelta";
  id_sucursal: number;
  id_arqueo: number | null;
  id_turno: number | null;
  id_operador: number | null;
  id_producto: number | null;
  id_conteo_fisico: number | null;
  monto: string | null;
  magnitud: number | null;
  valor_estimado: string | null;
  periodo_desde: string | null;
  periodo_hasta: string | null;
  dia_local: string;
  indicador_snapshot: Record<string, unknown> | null;
  historial: Array<{
    estado: string;
    instante: string;
    id_operador: number | null;
    nota: string | null;
    estado_anterior?: string;
  }>;
  resolucion: string | null;
  id_operador_resolucion: number | null;
  instante_resolucion: string | null;
  instante_deteccion: string;
}

// --- Arqueos (US1) ---------------------------------------------------------

export function registrarArqueo(cuerpo: {
  id_turno: number;
  monto_contado: string;
  motivo_conocido?: string | null;
  marca_tiempo_origen: string;
}): Promise<Arqueo> {
  return clienteHttp.post<Arqueo>("/caja/arqueos", cuerpo);
}

export function listarArqueos(
  idSucursal: number,
  opciones: { desde?: string; hasta?: string; soloDescuadrados?: boolean } = {}
): Promise<Arqueo[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  if (opciones.soloDescuadrados) params.set("solo_descuadrados", "true");
  return clienteHttp.get<Arqueo[]>(`/caja/arqueos?${params}`);
}

export function obtenerArqueo(idArqueo: number): Promise<Arqueo> {
  return clienteHttp.get<Arqueo>(`/caja/arqueos/${idArqueo}`);
}

export function ajustarArqueo(
  idArqueo: number,
  cuerpo: { monto_contado_nuevo: string; id_operador: number; nota: string }
): Promise<Arqueo> {
  return clienteHttp.patch<Arqueo>(`/caja/arqueos/${idArqueo}`, cuerpo);
}

// --- Mermas y alertas de caducidad (US2) ---------------------------------

export function registrarMerma(cuerpo: {
  id_producto: number;
  id_sucursal: number;
  cantidad_faltante: number;
  causa: CausaMerma;
  id_operador_registro: number;
  id_conteo_renglon?: number | null;
  id_lote?: number | null;
  nota?: string | null;
}): Promise<Merma> {
  return clienteHttp.post<Merma>("/caja/mermas", cuerpo);
}

export function listarMermas(
  idSucursal: number,
  opciones: { causa?: CausaMerma; idProducto?: number; desde?: string; hasta?: string } = {}
): Promise<DesgloseMermas> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.causa) params.set("causa", opciones.causa);
  if (opciones.idProducto) params.set("id_producto", String(opciones.idProducto));
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  return clienteHttp.get<DesgloseMermas>(`/caja/mermas?${params}`);
}

/** US5: valoración de merma agregada por semana y por causa (para el gráfico). */
export interface ResumenMermaSemana {
  periodo: string;
  vencimiento: number;
  dano: number;
  robo_externo: number;
  error_conteo: number;
  merma_granel: number;
  sin_valor: number;
}

export function obtenerResumenMermas(
  idSucursal: number,
  opciones: { desde?: string; hasta?: string } = {}
): Promise<ResumenMermaSemana[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  return clienteHttp.get<ResumenMermaSemana[]>(`/caja/mermas/resumen?${params}`);
}

export function listarAlertasCaducidad(
  idSucursal: number,
  dentroDeDias?: number
): Promise<AlertaCaducidad[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (dentroDeDias !== undefined) params.set("dentro_de_dias", String(dentroDeDias));
  return clienteHttp.get<AlertaCaducidad[]>(`/caja/alertas-caducidad?${params}`);
}

// --- Indicadores por operador y cruce (US3) -----------------------------

export function obtenerIndicadoresOperador(
  idSucursal: number,
  desde: string,
  hasta: string
): Promise<IndicadoresRespuesta> {
  const params = new URLSearchParams({
    id_sucursal: String(idSucursal),
    desde,
    hasta,
  });
  return clienteHttp.get<IndicadoresRespuesta>(`/caja/indicadores-operador?${params}`);
}

export function ejecutarCruceOperador(cuerpo: {
  id_sucursal: number;
  desde: string;
  hasta: string;
  id_conteo_fisico?: number | null;
}): Promise<unknown> {
  return clienteHttp.post<unknown>("/caja/cruce-operador", cuerpo);
}

// --- Anomalías (US4) -----------------------------------------------------

export function listarAnomalias(
  idSucursal: number,
  opciones: {
    estado?: "sin_explicacion" | "resuelta";
    origen?: "efectivo" | "inventario";
    desde?: string;
    hasta?: string;
  } = {}
): Promise<AnomaliaCaja[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.estado) params.set("estado", opciones.estado);
  if (opciones.origen) params.set("origen", opciones.origen);
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  return clienteHttp.get<AnomaliaCaja[]>(`/caja/anomalias?${params}`);
}

export function obtenerAnomalia(idAnomalia: number): Promise<AnomaliaCaja> {
  return clienteHttp.get<AnomaliaCaja>(`/caja/anomalias/${idAnomalia}`);
}

export function resolverAnomalia(
  idAnomalia: number,
  cuerpo: { resolucion: string; id_operador: number; nota?: string | null }
): Promise<AnomaliaCaja> {
  return clienteHttp.post<AnomaliaCaja>(`/caja/anomalias/${idAnomalia}/resolucion`, cuerpo);
}
