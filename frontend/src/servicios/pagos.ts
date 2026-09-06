/**
 * Cliente HTTP de 007-pagos-seguridad (T014 cobertura US1; T025 terminales US2; T038 tokenización
 * US3; T044 bitácora US4). Error `{ codigo, mensaje }` unificado con 001-006.
 *
 * El número de tarjeta NUNCA llega a este cliente en una respuesta: `POST /pagos/tokens` lo recibe
 * como `numero_tarjeta` (writeOnly) y devuelve sólo el token y los últimos 4 dígitos (FR-017).
 * 007 no mueve dinero (FR-036) — ninguna pantalla de este módulo usa el Verde Rasero.
 */

import { clienteHttp } from "./clienteHttp";

export interface MedioPago {
  id_medio_pago: number;
  nombre: string;
  requiere_terminal: boolean;
  admite_tokenizacion: boolean;
  activo: boolean;
}

export interface ResumenCobertura {
  id_sucursal: number;
  periodo: string;
  medios: Array<{
    id_medio_pago: number;
    nombre: string;
    cubierto: boolean;
    intencion_no_atendida: number;
    cuota_no_atendida: string;
  }>;
  total_intencion_no_atendida: number;
}

export interface TramoCobertura {
  id_cobertura_pago: number | null;
  id_medio_pago: number;
  id_sucursal: number;
  fecha_desde: string;
  fecha_hasta: string | null;
  id_operador: number;
}

export interface TerminalPago {
  id_terminal_pago: number;
  identificador: string;
  modelo: string;
  id_sucursal: number;
  version_firmware: string;
  fecha_ultima_actualizacion_firmware: string | null;
  ultima_version_referencia: string | null;
  desactualizada: boolean;
  expuesta_a_clonacion: boolean;
  version_referencia_desconocida: boolean;
  referencias_vulnerabilidad: string[];
  historial_ubicacion: Array<{ id_sucursal: number; desde: string; hasta: string | null }>;
  historial_firmware: Array<{ version: string; fecha: string; id_operador: number }>;
  activa: boolean;
}

export interface Pago {
  token: string;
  id_venta: number;
  ultimos_digitos: string;
  marca: string;
  tipo: string;
  id_terminal_pago: number;
  id_sucursal: number;
  instante: string;
  dia_local: string;
}

export type TipoEventoBitacora =
  | "token_emitido"
  | "token_idempotencia_divergente"
  | "token_purgado"
  | "pan_rechazado"
  | "firmware_actualizado"
  | "firmware_desactualizado_detectado"
  | "terminal_expuesta_detectada"
  | "terminal_registrada"
  | "terminal_movida"
  | "medio_pago_alta"
  | "medio_pago_baja"
  | "cobertura_declarada"
  | "intencion_no_atendida"
  | "config_firmware_cambiada";

export interface EntradaBitacora {
  id_bitacora_auditoria: number;
  tipo_evento: TipoEventoBitacora;
  instante: string;
  dia_local: string;
  id_sucursal: number;
  id_terminal_pago: number | null;
  id_medio_pago: number | null;
  iniciador_tipo: "operador" | "proceso";
  id_operador: number | null;
  proceso: string | null;
  resultado: string;
  referencia_recurso_tipo: string | null;
  referencia_recurso_id: string | null;
}

// --- Cobertura de medios de pago (US1) ---------------------------------

export function listarMedios(): Promise<MedioPago[]> {
  return clienteHttp.get<MedioPago[]>("/pagos/medios");
}

export function declararCobertura(cuerpo: {
  id_sucursal: number;
  id_medio_pago: number;
  acepta: boolean;
  fecha_desde: string;
  id_operador: number;
}): Promise<TramoCobertura> {
  return clienteHttp.put<TramoCobertura>("/pagos/cobertura", cuerpo);
}

export function obtenerCobertura(
  idSucursal: number,
  opciones: { desde?: string; hasta?: string } = {}
): Promise<ResumenCobertura> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  return clienteHttp.get<ResumenCobertura>(`/pagos/cobertura?${params}`);
}

export function registrarIntencionNoAtendida(cuerpo: {
  id_sucursal: number;
  id_medio_pago_deseado: number;
  id_operador: number;
  nota?: string | null;
  clave_idempotencia: string;
}): Promise<EntradaBitacora> {
  return clienteHttp.post<EntradaBitacora>("/pagos/intencion-no-atendida", cuerpo);
}

// --- Terminales y firmware (US2) --------------------------------------

export function registrarTerminal(cuerpo: {
  identificador: string;
  modelo: string;
  id_sucursal: number;
  version_firmware: string;
  fecha_ultima_actualizacion_firmware?: string | null;
  id_operador: number;
}): Promise<TerminalPago> {
  return clienteHttp.post<TerminalPago>("/pagos/terminales", cuerpo);
}

export function listarTerminales(
  idSucursal: number,
  soloConSenal = false
): Promise<TerminalPago[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (soloConSenal) params.set("solo_con_senal", "true");
  return clienteHttp.get<TerminalPago[]>(`/pagos/terminales?${params}`);
}

export function moverTerminal(
  idTerminal: number,
  cuerpo: {
    id_sucursal_destino?: number | null;
    fecha_movimiento?: string | null;
    retirar?: boolean;
    id_operador: number;
  }
): Promise<TerminalPago> {
  return clienteHttp.patch<TerminalPago>(`/pagos/terminales/${idTerminal}`, cuerpo);
}

export function registrarActualizacionFirmware(
  idTerminal: number,
  cuerpo: { version: string; fecha: string; id_operador: number }
): Promise<TerminalPago> {
  return clienteHttp.post<TerminalPago>(`/pagos/terminales/${idTerminal}/firmware`, cuerpo);
}

// --- Tokenización (US3) — sin pantalla propia (plan.md) ---------------

export function consultarPagoDeVenta(idVenta: number): Promise<Pago> {
  return clienteHttp.get<Pago>(`/pagos/ventas/${idVenta}/pago`);
}

// --- Bitácora de auditoría (US4) -------------------------------------

export function consultarBitacora(
  idSucursal: number,
  opciones: {
    idTerminalPago?: number;
    tipoEvento?: TipoEventoBitacora;
    desde?: string;
    hasta?: string;
  } = {}
): Promise<EntradaBitacora[]> {
  const params = new URLSearchParams({ id_sucursal: String(idSucursal) });
  if (opciones.idTerminalPago) params.set("id_terminal_pago", String(opciones.idTerminalPago));
  if (opciones.tipoEvento) params.set("tipo_evento", opciones.tipoEvento);
  if (opciones.desde) params.set("desde", opciones.desde);
  if (opciones.hasta) params.set("hasta", opciones.hasta);
  return clienteHttp.get<EntradaBitacora[]>(`/pagos/bitacora?${params}`);
}
