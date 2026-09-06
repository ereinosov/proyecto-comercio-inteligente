/**
 * Mermas y alertas de caducidad (006-caja-mermas-fraude, US2 — T028). Registro de ANÁLISIS: una
 * decisión por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md). Sin Verde Rasero (La
 * Regla del Registro Sin Dinero).
 *
 * La clasificación de diferencias de conteo físico está BLOQUEADA por 001 User Story 5: se
 * muestra deshabilitada con el texto explícito, NO se oculta. Sí funcionan: declarar una merma
 * fuera de conteo (FR-012) y la alerta de caducidad (FR-014).
 *
 * "no calculable" y "lote caducado" se comunican con los tres portadores (color + forma + texto).
 */

import { useEffect, useState, type FormEvent } from "react";
import { SelectorProducto } from "../componentes/SelectorProducto";
import { MermasPorCausaGrafico } from "../componentes/graficos/MermasPorCausaGrafico";
import type { Producto } from "../servicios/productos";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  listarAlertasCaducidad,
  listarMermas,
  registrarMerma,
  type AlertaCaducidad,
  type CausaMerma,
  type DesgloseMermas,
} from "../servicios/caja";
import estilos from "./CajaFraude.module.css";

const CAUSAS: { valor: CausaMerma; etiqueta: string }[] = [
  { valor: "vencimiento", etiqueta: "Vencimiento" },
  { valor: "dano", etiqueta: "Daño" },
  { valor: "robo_externo", etiqueta: "Robo externo" },
  { valor: "error_conteo", etiqueta: "Error de conteo" },
  { valor: "merma_granel", etiqueta: "Merma de granel" },
  { valor: "pendiente_clasificar", etiqueta: "Pendiente de clasificar" },
];

export function Mermas({ idSucursal, idOperador }: { idSucursal: number; idOperador: number }) {
  const [desglose, setDesglose] = useState<DesgloseMermas | null>(null);
  const [alertas, setAlertas] = useState<AlertaCaducidad[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [producto, setProducto] = useState<Producto | null>(null);
  const [cantidad, setCantidad] = useState("");
  const [causa, setCausa] = useState<CausaMerma>("dano");
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState(false);

  function recargar() {
    setError(null);
    Promise.all([listarMermas(idSucursal), listarAlertasCaducidad(idSucursal)])
      .then(([d, a]) => {
        setDesglose(d);
        setAlertas(a);
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar las mermas.")
      );
  }

  useEffect(recargar, [idSucursal]);

  async function declarar(evento: FormEvent) {
    evento.preventDefault();
    setErrorForm(null);
    if (!producto) {
      setErrorForm("Elige un producto.");
      return;
    }
    try {
      await registrarMerma({
        id_producto: producto.id_producto,
        id_sucursal: idSucursal,
        cantidad_faltante: Number(cantidad),
        causa,
        id_operador_registro: idOperador,
      });
      setConfirmado(true);
      setTimeout(() => setConfirmado(false), 1600);
      setProducto(null);
      setCantidad("");
      recargar();
    } catch (e) {
      setErrorForm(e instanceof ErrorApi ? e.message : "No se pudo registrar la merma.");
    }
  }

  return (
    <div className={estilos.contenido}>
      {error && <p className={estilos.error}>{error}</p>}

      <MermasPorCausaGrafico idSucursal={idSucursal} />

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Declarar una merma fuera de conteo</h2>
        <p className={estilos.nota}>
          Una rotura o un vencimiento en estantería. Queda pendiente de conciliarse con el próximo
          conteo físico de inventario; este módulo no ajusta la existencia.
        </p>
        <form className={estilos.formulario} onSubmit={declarar}>
          <div className={estilos.campo}>
            <span>Producto</span>
            <SelectorProducto
              idSucursal={idSucursal}
              seleccionado={producto}
              onSeleccionar={setProducto}
            />
          </div>
          <label className={estilos.campo}>
            Cantidad faltante
            <input
              className={estilos.entrada}
              inputMode="numeric"
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              required
            />
          </label>
          <label className={estilos.campo}>
            Causa
            <select
              className={estilos.entrada}
              value={causa}
              onChange={(e) => setCausa(e.target.value as CausaMerma)}
            >
              {CAUSAS.map((c) => (
                <option key={c.valor} value={c.valor}>
                  {c.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <button className={estilos.boton} type="submit">
            {confirmado ? "Merma registrada" : "Registrar merma"}
          </button>
        </form>
        {errorForm && <p className={estilos.error}>{errorForm}</p>}
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Clasificar diferencias de conteo físico</h2>
        <p className={estilos.notaBloqueada}>
          <span className={estilos.puntoHueco} aria-hidden="true" />
          Requiere el conteo físico de inventario de 001, que todavía no está disponible.
        </p>
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Total de mermas del período</h2>
        {desglose && (
          <p className={estilos.nota}>
            Valorado: <strong>{desglose.total_valorado}</strong>
            {desglose.con_valor_no_calculable > 0 && (
              <span className={estilos.noCalculable}>
                {" · "}
                <span className={estilos.puntoMedio} aria-hidden="true" />
                {desglose.con_valor_no_calculable} sin costo (no calculable)
              </span>
            )}
          </p>
        )}
        <ul className={estilos.lista}>
          {(desglose?.mermas ?? []).map((m) => (
            <li key={m.id_merma} className={estilos.filaLista}>
              <span>
                Producto {m.id_producto} · {m.causa} · {m.cantidad_faltante} u
              </span>
              <span className={m.valoracion === null ? estilos.noCalculable : estilos.valor}>
                {m.valoracion === null ? "no calculable" : m.valoracion}
              </span>
            </li>
          ))}
          {desglose?.mermas.length === 0 && (
            <li className={estilos.nota}>Sin mermas registradas en el período.</li>
          )}
        </ul>
      </section>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Alertas de caducidad</h2>
        <ul className={estilos.lista}>
          {alertas.map((a) => (
            <li key={a.id_lote} className={estilos.filaLista}>
              <span className={a.ya_caducado ? estilos.caducado : estilos.porCaducar}>
                <span
                  className={a.ya_caducado ? estilos.puntoHueco : estilos.puntoMedio}
                  aria-hidden="true"
                />
                {a.nombre_producto} · vence {a.fecha_caducidad}
                {a.ya_caducado
                  ? " — ya caducado"
                  : ` — en ${a.dias_para_caducar} d`}
              </span>
              <span className={estilos.valor}>
                {a.valor_en_riesgo === null
                  ? "valor no calculable"
                  : `${a.valor_en_riesgo} en riesgo`}
              </span>
            </li>
          ))}
          {alertas.length === 0 && (
            <li className={estilos.nota}>Ningún lote próximo a caducar.</li>
          )}
        </ul>
      </section>
    </div>
  );
}
