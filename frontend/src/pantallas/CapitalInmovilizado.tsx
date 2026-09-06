/**
 * Listado de capital inmovilizado (T083, US7). SOLO LECTURA: hace visible el dato y nada más —
 * ninguna acción de descuento, traspaso o baja (FR-036). Un lote sin costo registrado aparece
 * como "no calculable", nunca como cero (FR-035).
 */

import { useEffect, useState } from "react";
import { listarProductos, type Producto } from "../servicios/productos";
import { listarCapitalInmovilizado, type CapitalInmovilizado as Fila } from "../servicios/inventario";
import estilos from "./Inventario.module.css";

interface Props {
  idSucursal: number;
}

export function CapitalInmovilizado({ idSucursal }: Props) {
  const [filas, setFilas] = useState<Fila[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    setCargando(true);
    Promise.all([listarCapitalInmovilizado(idSucursal), listarProductos(idSucursal)])
      .then(([f, p]) => {
        setFilas(f);
        setProductos(p);
      })
      .finally(() => setCargando(false));
  }, [idSucursal]);

  const nombre = (id: number) =>
    productos.find((p) => p.id_producto === id)?.nombre ?? `Producto ${id}`;

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Capital inmovilizado</h2>
      <p className={estilos.nota}>
        Lotes que llevan más días sin salida que el umbral de su categoría, con cuánto dinero
        representa cada uno. Qué hacer con esa mercancía es una decisión suya; el sistema no
        propone nada.
      </p>

      {cargando ? (
        <p className={estilos.nota}>Cargando…</p>
      ) : filas.length === 0 ? (
        <p className={estilos.ok}>Ningún lote supera hoy el umbral de su categoría.</p>
      ) : (
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Lote</th>
              <th className={estilos.num}>Restante</th>
              <th className={estilos.num}>Días sin salida</th>
              <th className={estilos.num}>Umbral</th>
              <th className={estilos.num}>Valor inmovilizado</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.id_lote}>
                <td>{nombre(f.id_producto)}</td>
                <td>#{f.id_lote}</td>
                <td className={estilos.num}>{f.cantidad_restante}</td>
                <td className={estilos.num}>{f.dias_sin_salida}</td>
                <td className={estilos.num}>
                  {f.dias_umbral_aplicado}
                  {f.umbral_heredado_del_global ? " (global)" : ""}
                </td>
                <td className={estilos.num}>
                  {f.valor_calculable ? (
                    `$${f.valor_inmovilizado}`
                  ) : (
                    <span className={estilos.noCalculable}>no calculable</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
