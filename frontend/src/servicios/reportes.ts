/**
 * Cliente de 008-reportes-inteligencia. Capa de solo lectura sobre 001–007; rol `encargado`.
 */

import { clienteHttp } from "./clienteHttp";

export interface CeldaComparativo {
  id_sucursal: number;
  valor: string | null;
  sin_datos: boolean;
  diferencia_relativa: string | null;
  atencion: boolean;
}
export interface FilaComparativo {
  clave: string;
  etiqueta: string;
  celdas: CeldaComparativo[];
}
export interface Comparativo {
  periodo_inicio: string;
  periodo_fin: string;
  comparable: boolean;
  sucursales: { id_sucursal: number; nombre: string; activa: boolean }[];
  indicadores: FilaComparativo[];
  instante_calculo: string;
}

export interface PuntoTendencia {
  periodo: string;
  etiqueta: string;
  valor: string | null;
  completo: boolean;
}
export interface Tendencia {
  indicador: string;
  granularidad: string;
  ambito: string;
  disponible: boolean;
  razon: string | null;
  puntos: PuntoTendencia[];
  instante_calculo: string | null;
}

export interface TarjetaKpi {
  modulo: string;
  titulo: string;
  periodo_referencia: string;
  sin_datos: boolean;
  razon: string | null;
  cifras: { etiqueta: string; valor: string; atencion: boolean }[];
}
export interface Tablero {
  tarjetas: TarjetaKpi[];
  instante_calculo: string;
}

export interface GrupoSegmento {
  etiqueta_grupo: string;
  descripcion: string;
  n_clientes: number;
  centroide: { frecuencia: string; margen: string; recencia_dias: string };
  ejemplos: { id_cliente: number; nombre: string | null }[];
}
export interface Segmentos {
  calculado: boolean;
  corrida: string | null;
  semilla: number | null;
  grupos: GrupoSegmento[];
}
export interface EtiquetaSegmentoCliente {
  id_cliente: number;
  etiqueta_grupo: string | null;
  descripcion: string | null;
  corrida: string | null;
}

const q = (params: Record<string, string | number | boolean | undefined>) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");

export const obtenerComparativo = (actualizar = false) =>
  clienteHttp.get<Comparativo>(`/reportes/comparativo?${q({ actualizar })}`);

export const obtenerTendencia = (
  indicador: string,
  granularidad: "semana" | "mes",
  opciones: { idSucursal?: number; idProducto?: number; periodos?: number; actualizar?: boolean } = {},
) =>
  clienteHttp.get<Tendencia>(
    `/reportes/tendencia?${q({
      indicador,
      granularidad,
      id_sucursal: opciones.idSucursal,
      id_producto: opciones.idProducto,
      periodos: opciones.periodos,
      actualizar: opciones.actualizar,
    })}`,
  );

export const obtenerTablero = (actualizar = false) =>
  clienteHttp.get<Tablero>(`/reportes/tablero?${q({ actualizar })}`);

export const obtenerSegmentos = () => clienteHttp.get<Segmentos>("/reportes/segmentos");
export const recalcularSegmentos = () => clienteHttp.post<Segmentos>("/reportes/segmentos/recalculo", {});
export const obtenerSegmentoDeCliente = (idCliente: number) =>
  clienteHttp.get<EtiquetaSegmentoCliente>(`/reportes/segmentos/cliente/${idCliente}`);
