/**
 * Aplicar una promoción del cliente identificado en el punto de venta (005, US2, T032).
 * Registro de Operación: radio 2px, IBM Plex Sans con cifras tabulares, sin Verde Rasero
 * (reservado al botón de cobro) y sin animación salvo la confirmación de la acción.
 *
 * Vive en el encabezado de Venta.tsx junto a `IdentificarCliente` y NUNCA en el flujo de cobro:
 * el cajero marca aquí qué cupón u oferta vigente del cliente se aplica, y `Venta.tsx` registra
 * la redención DESPUÉS de que la venta se confirmó — igual que `registrarVisita` (Principio II,
 * mismo patrón que `IdentificarCliente.tsx` de 002). Si 005 no responde, el cobro sigue.
 */

import { useEffect, useState } from "react";
import {
  listarCupones,
  listarOfertasRecompra,
  type Cupon,
  type OfertaRecompra,
} from "../servicios/promociones";
import estilos from "./AplicarPromocionVenta.module.css";

export interface PromocionSeleccionada {
  tipo_origen: "cupon" | "oferta_recompra";
  id_cupon?: number;
  id_oferta_recompra?: number;
  id_producto?: number;
  etiqueta: string;
}

interface Props {
  idCliente: number;
  seleccion: PromocionSeleccionada | null;
  onSeleccionar: (promocion: PromocionSeleccionada | null) => void;
}

export function AplicarPromocionVenta({ idCliente, seleccion, onSeleccionar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [cupones, setCupones] = useState<Cupon[]>([]);
  const [ofertas, setOfertas] = useState<OfertaRecompra[]>([]);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    setCargando(true);
    Promise.all([
      listarCupones({ idCliente, vigentes: true }),
      listarOfertasRecompra({ idCliente, desenlace: "pendiente" }),
    ])
      .then(([c, o]) => {
        setCupones(c);
        setOfertas(o);
      })
      .catch(() => {
        // No bloqueante: si 005 no responde, el cajero simplemente no ve promociones.
        setCupones([]);
        setOfertas([]);
      })
      .finally(() => setCargando(false));
  }, [abierto, idCliente]);

  function elegirCupon(c: Cupon) {
    onSeleccionar({
      tipo_origen: "cupon",
      id_cupon: c.id_cupon,
      etiqueta: `Cupón ${c.id_cupon} · ${c.porcentaje_descuento} %`,
    });
    setAbierto(false);
  }

  function elegirOferta(o: OfertaRecompra) {
    onSeleccionar({
      tipo_origen: "oferta_recompra",
      id_oferta_recompra: o.id_oferta_recompra,
      id_producto: o.id_producto,
      etiqueta: `Oferta ${o.id_oferta_recompra} · producto ${o.id_producto} a ${o.precio_garantizado}`,
    });
    setAbierto(false);
  }

  if (seleccion) {
    return (
      <span className={estilos.chip}>
        Promoción: {seleccion.etiqueta}
        <button
          type="button"
          className={estilos.quitar}
          onClick={() => onSeleccionar(null)}
          aria-label="Quitar promoción"
        >
          ✕
        </button>
      </span>
    );
  }

  if (!abierto) {
    return (
      <button type="button" className={estilos.abrir} onClick={() => setAbierto(true)}>
        + Aplicar promoción
      </button>
    );
  }

  const sinPromociones = !cargando && cupones.length === 0 && ofertas.length === 0;

  return (
    <div className={estilos.panel}>
      {cargando && <p className={estilos.vacio}>Cargando…</p>}
      {sinPromociones && <p className={estilos.vacio}>Este cliente no tiene promociones vigentes.</p>}
      {cupones.map((c) => (
        <button key={`c${c.id_cupon}`} type="button" className={estilos.fila} onClick={() => elegirCupon(c)}>
          Cupón {c.id_cupon} · {c.porcentaje_descuento} % · vence {c.valido_hasta}
        </button>
      ))}
      {ofertas.map((o) => (
        <button
          key={`o${o.id_oferta_recompra}`}
          type="button"
          className={estilos.fila}
          onClick={() => elegirOferta(o)}
        >
          Oferta {o.id_oferta_recompra} · producto {o.id_producto} · {o.precio_garantizado}
        </button>
      ))}
      <button type="button" className={estilos.cancelar} onClick={() => setAbierto(false)}>
        Cancelar
      </button>
    </div>
  );
}
