/**
 * Cliente de 009-facturacion-electronica. Factura SIMULADA (sin SRI/firma/XML). Rol `cajero`.
 * La generación se llama DESPUÉS del cobro, sin bloquear su resultado (Principio II).
 */

import { clienteHttp } from "./clienteHttp";

export interface Factura {
  id_factura_simulada: number;
  id_venta: number;
  tipo: "factura" | "nota_credito";
  id_factura_referida: number | null;
  secuencial: string;
  fecha_emision: string;
  emisor: { razon_social: string; ruc: string; direccion?: string };
  comprador:
    | { tipo: "consumidor_final" }
    | { tipo: "identificado"; nombre: string | null; identificador?: string };
  renglones: { descripcion: string; cantidad: string; precio_unitario: string; importe: string }[];
  subtotal: string;
  tarifa_iva: string;
  monto_iva: string;
  total: string;
  medio_pago: string | null;
  estado: "emitida" | "anulada";
  instante_generacion: string;
  aviso_simulacion: string;
}

export interface FacturasDeVenta {
  id_venta: number;
  factura: Factura | null;
  nota_credito: Factura | null;
}

export const generarFactura = (idVenta: number) =>
  clienteHttp.post<Factura>("/facturas", { id_venta: idVenta });

export const obtenerFacturasDeVenta = (idVenta: number) =>
  clienteHttp.get<FacturasDeVenta>(`/facturas/venta/${idVenta}`);

export const emitirNotaCredito = (idVenta: number) =>
  clienteHttp.post<Factura | undefined>(`/facturas/nota-credito/${idVenta}`, {});
