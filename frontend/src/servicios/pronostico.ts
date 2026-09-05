/**
 * Cliente HTTP de 004-pronostico-demanda: serie de demanda observada y corregida (T017, User
 * Story 1). Las cantidades llegan como cadena decimal (contracts/openapi.yaml, esquema
 * `PuntoSerie`): la demanda observada sin decimales, la corregida con hasta 4.
 */

import { clienteHttp } from "./clienteHttp";

export type RespaldoQuiebre = "no_aplica" | "metodo_base" | "consulta_no_atendida";
export type EstadoPeriodo = "ok" | "no_estimable_censura_total";

export interface SenalSustitucion {
  id_producto_en_quiebre: number;
  id_sustitucion_producto: number;
}

export interface PuntoSerie {
  id_producto: number;
  id_sucursal: number;
  periodo: string;
  demanda_observada: string;
  demanda_corregida: string | null;
  estado: EstadoPeriodo;
  dias_en_quiebre: string;
  correccion_quiebre: string;
  respaldo_quiebre: RespaldoQuiebre;
  ajuste_cruzado_sustituto: string;
  precio_vigente_periodo: string | null;
  correccion_precio: string;
  elasticidad_usada: string | null;
  con_promocion: boolean;
  excluido_por_promocion: boolean;
  senal_sustitucion: SenalSustitucion | null;
}

export function obtenerSerieDemanda(
  idSucursal: number,
  idProducto?: number,
  desde?: string,
  hasta?: string
): Promise<PuntoSerie[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (idProducto !== undefined) params.set("id_producto", String(idProducto));
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);
  return clienteHttp.get<PuntoSerie[]>(`/demanda?${params.toString()}`);
}

// --------------------------------------------------------------------------
// User Story 2 — validación de la descensura con datos sintéticos (T029)
// --------------------------------------------------------------------------

export interface ErrorPorCamino {
  periodos: number;
  error_medio_descensura: string;
  error_medio_sin_corregir: string;
}

export interface ReporteValidacion {
  id_producto: number;
  id_sucursal: number;
  periodos_quiebre_evaluados: number;
  error_medio_descensura: string;
  error_medio_sin_corregir: string;
  descensura_mejora_sobre_no_corregir: boolean;
  detalle_por_camino: {
    con_consulta_no_atendida: ErrorPorCamino;
    solo_metodo_base: ErrorPorCamino;
  };
}

export interface CargaSintetica {
  id_producto: number;
  id_sucursal: number;
  periodos: {
    periodo: string;
    demanda_observada: string;
    dias_en_quiebre: string;
    demanda_latente_verdadera?: string;
  }[];
  consultas_no_atendidas_sinteticas: { periodo: string; conteo: number }[];
}

export function cargarSerieSintetica(carga: CargaSintetica): Promise<{ periodos_cargados: number }> {
  return clienteHttp.post<{ periodos_cargados: number }>("/demanda-sintetica", carga);
}

export function obtenerValidacionDescensura(
  idSucursal: number,
  idProducto: number
): Promise<ReporteValidacion> {
  return clienteHttp.get<ReporteValidacion>(
    `/demanda-sintetica/validacion?id_sucursal=${idSucursal}&id_producto=${idProducto}`
  );
}

/**
 * Construye una serie sintética de demostración (misma lógica que
 * `tests/utilidades/generador_sintetico.py`): nivel base plano de lunes a viernes con recargo de
 * fin de semana, dos intervalos de quiebre —uno con consultas no atendidas sintéticas, otro sin—
 * y la demanda latente verdadera conocida de cada día de quiebre. Es un artefacto de validación,
 * no un juego de datos real (FR-017).
 */
export function construirSerieSinteticaDemo(
  idProducto: number,
  idSucursal: number
): CargaSintetica {
  const INICIO = new Date(Date.UTC(2026, 0, 5)); // lunes
  const DIAS = 56;
  const quiebreA = new Set([33, 34, 35, 36, 37, 38]); // incluye sáb+dom, con consultas
  const quiebreB = new Set([45, 46, 47]); // sin consultas

  const demandaVerdadera = (d: Date): number => {
    const diasem = d.getUTCDay(); // 0 dom ... 6 sáb
    if (diasem === 6) return 15;
    if (diasem === 0) return 12;
    return 10;
  };

  const periodos: CargaSintetica["periodos"] = [];
  const consultas: CargaSintetica["consultas_no_atendidas_sinteticas"] = [];

  for (let i = 0; i < DIAS; i++) {
    const d = new Date(INICIO.getTime() + i * 86_400_000);
    const iso = d.toISOString().slice(0, 10);
    const verdadera = demandaVerdadera(d);
    if (quiebreA.has(i) || quiebreB.has(i)) {
      periodos.push({
        periodo: iso,
        demanda_observada: "0",
        dias_en_quiebre: "1",
        demanda_latente_verdadera: String(verdadera),
      });
      if (quiebreA.has(i)) consultas.push({ periodo: iso, conteo: verdadera });
    } else {
      periodos.push({ periodo: iso, demanda_observada: String(verdadera), dias_en_quiebre: "0" });
    }
  }

  return {
    id_producto: idProducto,
    id_sucursal: idSucursal,
    periodos,
    consultas_no_atendidas_sinteticas: consultas,
  };
}

// --------------------------------------------------------------------------
// User Story 3 — pronóstico (T040)
// --------------------------------------------------------------------------

export interface PuntoPronostico {
  periodo: string;
  valor: string;
}

export interface Pronostico {
  id_pronostico: number;
  id_producto: number;
  id_sucursal: number;
  horizonte: "corto" | "medio";
  dias_horizonte: number;
  serie_pronosticada: PuntoPronostico[];
  factores: {
    nivel_suavizado: string;
    alfa_usado: string;
    multiplicadores_tramo: Record<string, string> | null;
  };
  periodo_datos_desde: string;
  periodo_datos_hasta: string;
  valor_linea_base: string;
  error_retrospectivo: string | null;
  error_linea_base: string | null;
  vigente: boolean;
  motivo_no_vigente: string | null;
  instante_generacion: string;
}

export function obtenerPronostico(
  idProducto: number,
  idSucursal: number,
  horizonte: "corto" | "medio" = "corto"
): Promise<Pronostico> {
  return clienteHttp.get<Pronostico>(
    `/productos/${idProducto}/pronostico?id_sucursal=${idSucursal}&horizonte=${horizonte}`
  );
}

// --------------------------------------------------------------------------
// User Story 6 — relaciones de sustitución (T065)
// --------------------------------------------------------------------------

export interface Sustitucion {
  id_sustitucion_producto: number;
  id_producto: number;
  id_producto_sustituto: number;
  instante_declaracion: string;
}

export function listarSustituciones(idProducto?: number): Promise<Sustitucion[]> {
  const q = idProducto !== undefined ? `?id_producto=${idProducto}` : "";
  return clienteHttp.get<Sustitucion[]>(`/sustituciones${q}`);
}

export function declararSustitucion(
  idProducto: number,
  idProductoSustituto: number
): Promise<Sustitucion> {
  return clienteHttp.post<Sustitucion>("/sustituciones", {
    id_producto: idProducto,
    id_producto_sustituto: idProductoSustituto,
  });
}

export function retirarSustitucion(idSustitucionProducto: number): Promise<void> {
  return clienteHttp.del<void>(`/sustituciones/${idSustitucionProducto}`);
}
