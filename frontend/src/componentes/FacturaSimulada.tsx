/**
 * Documento con la forma de una factura ecuatoriana — SIMULADO (009). El `aviso_simulacion` va
 * DESTACADO en la misma superficie (FR-019), no como nota al pie. Registro de Operación (es
 * parte del flujo de caja). Sin Verde Rasero.
 *
 * DESIGN.md v1.9.0 — "Presentación de documento formal".
 */

import { etiquetaMedioPago, formatearMoneda } from "../utilidades/formato";
import type { Factura } from "../servicios/facturas";
import estilos from "./FacturaSimulada.module.css";

export function FacturaSimulada({ factura }: { factura: Factura }) {
  const c = factura.comprador;
  const esNota = factura.tipo === "nota_credito";
  return (
    <div className={estilos.documento}>
      <p className={estilos.aviso}>{factura.aviso_simulacion}</p>

      <header className={estilos.encabezado}>
        <div>
          <strong className={estilos.emisor}>{factura.emisor.razon_social}</strong>
          <div className={estilos.dato}>RUC: {factura.emisor.ruc}</div>
          {factura.emisor.direccion && <div className={estilos.dato}>{factura.emisor.direccion}</div>}
        </div>
        <div className={estilos.tipoDoc}>
          <span className={estilos.tipoEtiqueta}>
            {esNota ? "Nota de crédito (simulada)" : "Factura (simulada)"}
          </span>
          <div className={estilos.dato}>N.º {factura.secuencial}</div>
          <div className={estilos.dato}>Fecha: {factura.fecha_emision}</div>
          {factura.estado === "anulada" && <div className={estilos.anulada}>ANULADA</div>}
        </div>
      </header>

      <p className={estilos.comprador}>
        {c.tipo === "consumidor_final"
          ? "Consumidor Final"
          : `${c.nombre ?? "(sin nombre)"}${c.identificador ? ` · ${c.identificador}` : ""}`}
      </p>

      <table className={estilos.tabla}>
        <thead>
          <tr>
            <th>Descripción</th>
            <th className={estilos.num}>Cant.</th>
            <th className={estilos.num}>P. unit.</th>
            <th className={estilos.num}>Importe</th>
          </tr>
        </thead>
        <tbody>
          {factura.renglones.map((r, i) => (
            <tr key={i}>
              <td>{r.descripcion}</td>
              <td className={estilos.num}>{r.cantidad}</td>
              <td className={estilos.num}>{formatearMoneda(r.precio_unitario)}</td>
              <td className={estilos.num}>{formatearMoneda(r.importe)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <dl className={estilos.totales}>
        <div>
          <dt>Subtotal</dt>
          <dd>{formatearMoneda(factura.subtotal)}</dd>
        </div>
        <div>
          <dt>IVA ({(Number(factura.tarifa_iva) * 100).toFixed(0)} %, incluido)</dt>
          <dd>{formatearMoneda(factura.monto_iva)}</dd>
        </div>
        <div className={estilos.total}>
          <dt>Total</dt>
          <dd>{formatearMoneda(factura.total)}</dd>
        </div>
        {factura.medio_pago && (
          <div>
            <dt>Medio de pago</dt>
            <dd>{etiquetaMedioPago(factura.medio_pago)}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
