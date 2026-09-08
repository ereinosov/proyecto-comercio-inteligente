/**
 * Ofertas de recompra con reserva de precio (005-promociones-inteligentes, US2, T031). Registro
 * de Análisis: radio 6px, Source Serif 4.
 *
 * Dispara la detección para la sucursal del turno y lista las ofertas propuestas con su producto,
 * su `precio_garantizado` (RESERVA DE PRECIO, no de inventario) y su justificación: qué compras
 * del propio cliente sustentan la elección del producto (FR-009, Principio V "explicable").
 */

import { useCallback, useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  cancelarOfertaRecompra,
  detectarOfertasRecompra,
  listarOfertasRecompra,
  type OfertaRecompra,
  type ResultadoDeteccion,
} from "../servicios/promociones";
import { Boton } from "./Boton";
import estilos from "./OfertasRecompra.module.css";

const ETIQUETA_DESENLACE: Record<OfertaRecompra["desenlace"], string> = {
  pendiente: "Pendiente",
  comprado: "Comprada",
  no_comprado: "No comprada",
  reserva_vencida: "Reserva vencida",
};

export function OfertasRecompra({ idSucursal }: { idSucursal: number }) {
  const [ofertas, setOfertas] = useState<OfertaRecompra[]>([]);
  const [detectando, setDetectando] = useState(false);
  const [ultimaDeteccion, setUltimaDeteccion] = useState<ResultadoDeteccion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(() => {
    setCargando(true);
    listarOfertasRecompra()
      .then(setOfertas)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar las ofertas.")
      )
      .finally(() => setCargando(false));
  }, []);

  useEffect(recargar, [recargar]);

  async function detectar() {
    setDetectando(true);
    setError(null);
    try {
      setUltimaDeteccion(await detectarOfertasRecompra(idSucursal));
      recargar();
    } catch (e) {
      setError(
        e instanceof ErrorApi ? e.message : "No se pudo ejecutar la detección de recompras."
      );
    } finally {
      setDetectando(false);
    }
  }

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.instruccion}>
        Propone, a un cliente que se acerca a su intervalo de compra habitual, una oferta de un
        producto que suele recomprar, garantizando el precio dentro de una ventana. No aparta
        inventario: si al volver no hay stock, el cliente recibe el trato normal.
      </p>

      <button className={estilos.boton} onClick={detectar} disabled={detectando}>
        {detectando ? "Detectando…" : "Detectar recompras de esta sucursal"}
      </button>

      {error && <p className={estilos.error}>{error}</p>}

      {ultimaDeteccion && (
        <p className={estilos.resumen}>
          {ultimaDeteccion.ofertas_propuestas} ofertas nuevas,{" "}
          {ultimaDeteccion.ofertas_ya_activas} clientes ya tenían una oferta activa del mismo
          producto.
        </p>
      )}

      {cargando && <p className={estilos.instruccion}>Cargando…</p>}
      {!cargando && ofertas.length === 0 && (
        <p className={estilos.instruccion}>Todavía no hay ofertas de recompra propuestas.</p>
      )}
      {!cargando && ofertas.length > 0 && (
        <ul className={estilos.lista}>
          {ofertas.map((o) => (
            <li key={o.id_oferta_recompra} className={estilos.tarjeta}>
              <div className={estilos.encabezadoTarjeta}>
                <span className={estilos.cliente}>Cliente {o.id_cliente}</span>
                <span className={estilos[`desenlace_${o.desenlace}`]}>
                  {ETIQUETA_DESENLACE[o.desenlace]}
                </span>
              </div>
              <p className={estilos.detalle}>
                Producto {o.id_producto} · precio garantizado{" "}
                <strong>{o.precio_garantizado}</strong> hasta {o.reserva_hasta}
              </p>
              <p className={estilos.justificacion}>
                {o.justificacion.compras_del_producto} compras de este producto en los últimos{" "}
                {o.justificacion.ventana_dias} días (ventas{" "}
                {o.justificacion.ventas_consideradas.join(", ")}).
              </p>
              {o.desenlace === "pendiente" && (
                <Boton
                  variante="neutra"
                  registro="analisis"
                  tamano="sm"
                  onClick={async () => {
                    if (!window.confirm("¿Cancelar esta oferta de recompra?")) return;
                    try {
                      await cancelarOfertaRecompra(o.id_oferta_recompra);
                      recargar();
                    } catch (e) {
                      setError(
                        e instanceof ErrorApi ? e.message : "No se pudo cancelar la oferta."
                      );
                    }
                  }}
                >
                  Cancelar oferta
                </Boton>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
