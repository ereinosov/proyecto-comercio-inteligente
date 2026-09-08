/**
 * Mermas y alertas de caducidad (006-caja-mermas-fraude, US2 — T028). Registro de ANÁLISIS: una
 * decisión por bloque, aire visual, radio 6px, Source Serif 4 (DESIGN.md). Sin Verde Rasero (La
 * Regla del Registro Sin Dinero).
 *
 * La clasificación de diferencias de conteo físico YA funciona (001 User Story 5 implementada):
 * se elige un conteo resuelto y se clasifica cada faltante bruto con su causa.
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
import { listarConteos, obtenerConteo, type ConteoFisico } from "../servicios/conteos";
import { Boton } from "../componentes/Boton";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
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
  // Paginación client-side: `GET /caja/mermas` no acepta parámetros de paginación en el backend
  // y trae todo el período; se pagina en memoria.
  const [paginaMermas, setPaginaMermas] = useState(1);

  const [producto, setProducto] = useState<Producto | null>(null);
  const [cantidad, setCantidad] = useState("");
  const [causa, setCausa] = useState<CausaMerma>("dano");
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState(false);

  // Clasificar diferencias de un conteo físico resuelto.
  const [conteos, setConteos] = useState<ConteoFisico[]>([]);
  const [idConteo, setIdConteo] = useState<number | "">("");
  const [detalleConteo, setDetalleConteo] = useState<ConteoFisico | null>(null);
  const [clasif, setClasif] = useState<Record<number, { causa: CausaMerma; cantidad: string }>>({});
  const [errorClasif, setErrorClasif] = useState<string | null>(null);
  const [okClasif, setOkClasif] = useState<string | null>(null);

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
  useEffect(() => setPaginaMermas(1), [idSucursal]);

  const totalPaginasMermas = Math.max(1, Math.ceil((desglose?.mermas.length ?? 0) / TAMANO_PAGINA));
  const paginaMermasActual = Math.min(paginaMermas, totalPaginasMermas);
  const mermasPagina = (desglose?.mermas ?? []).slice(
    (paginaMermasActual - 1) * TAMANO_PAGINA,
    paginaMermasActual * TAMANO_PAGINA,
  );

  useEffect(() => {
    setIdConteo("");
    setDetalleConteo(null);
    listarConteos({ idSucursal, estado: "resuelto" })
      .then(setConteos)
      .catch(() => setConteos([]));
  }, [idSucursal]);

  useEffect(() => {
    setDetalleConteo(null);
    setClasif({});
    setErrorClasif(null);
    setOkClasif(null);
    if (idConteo === "") return;
    obtenerConteo(idConteo)
      .then(setDetalleConteo)
      .catch(() => setDetalleConteo(null));
  }, [idConteo]);

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

  const faltantes = (detalleConteo?.renglones ?? []).filter((r) => r.diferencia < 0);

  async function clasificarRenglon(idRenglon: number, faltanteBruto: number) {
    const entrada = clasif[idRenglon];
    setErrorClasif(null);
    setOkClasif(null);
    const cant = entrada?.cantidad ? Number(entrada.cantidad) : faltanteBruto;
    if (!Number.isFinite(cant) || cant <= 0 || cant > faltanteBruto) {
      setErrorClasif(`La cantidad debe estar entre 1 y ${faltanteBruto}.`);
      return;
    }
    try {
      await registrarMerma({
        id_producto: faltantes.find((r) => r.id_conteo_renglon === idRenglon)!.id_producto,
        id_sucursal: idSucursal,
        cantidad_faltante: cant,
        causa: entrada?.causa ?? "dano",
        id_operador_registro: idOperador,
        id_conteo_renglon: idRenglon,
      });
      setOkClasif(`Diferencia clasificada como ${entrada?.causa ?? "dano"}.`);
      recargar();
      obtenerConteo(idConteo as number).then(setDetalleConteo).catch(() => {});
    } catch (e) {
      setErrorClasif(
        e instanceof ErrorApi ? e.message : "No se pudo clasificar la diferencia."
      );
    }
  }

  return (
    <div className={estilos.contenido}>
      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.filaGrafico}>
        <section className={estilos.bloque}>
          <h2 className={estilos.subtitulo}>Declarar una merma fuera de conteo</h2>
          <p className={estilos.nota}>
            Una rotura o un vencimiento en estantería. Queda pendiente de conciliarse con el
            próximo conteo físico de inventario; este módulo no ajusta la existencia.
          </p>
          <form className={estilos.formulario} onSubmit={declarar}>
            <div className={estilos.campoAncho}>
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
            <Boton variante="primaria" registro="analisis" type="submit">
              {confirmado ? "Merma registrada" : "Registrar merma"}
            </Boton>
          </form>
          {errorForm && <p className={estilos.error}>{errorForm}</p>}
        </section>

        <div className={estilos.graficoCaja}>
          <MermasPorCausaGrafico idSucursal={idSucursal} />
        </div>
      </div>

      <section className={estilos.bloque}>
        <h2 className={estilos.subtitulo}>Clasificar diferencias de conteo físico</h2>
        <p className={estilos.nota}>
          Elige un conteo resuelto: sus faltantes brutos se pueden clasificar con una causa. El
          ajuste de existencia ya lo hizo el conteo; aquí sólo se le pone nombre a la diferencia.
        </p>
        <div className={estilos.filaCampos}>
          <label className={estilos.campo} style={{ width: "auto" }}>
            Conteo resuelto
            <select
              className={estilos.entrada}
              value={idConteo}
              onChange={(e) => setIdConteo(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">Elige…</option>
              {conteos.map((c) => (
                <option key={c.id_conteo_fisico} value={c.id_conteo_fisico}>
                  #{c.id_conteo_fisico} ·{" "}
                  {c.instante_resolucion
                    ? new Date(c.instante_resolucion).toLocaleDateString()
                    : ""}
                </option>
              ))}
            </select>
          </label>
        </div>
        {conteos.length === 0 && (
          <p className={estilos.nota}>Esta sucursal todavía no tiene ningún conteo resuelto.</p>
        )}
        {detalleConteo && faltantes.length === 0 && (
          <p className={estilos.nota}>Ese conteo no dejó ningún faltante para clasificar.</p>
        )}
        {errorClasif && <p className={estilos.error}>{errorClasif}</p>}
        {okClasif && <p className={estilos.nota}>{okClasif}</p>}
        {faltantes.length > 0 && (
          <ul className={estilos.lista}>
            {faltantes.map((r) => {
              const idR = r.id_conteo_renglon!;
              const faltanteBruto = -r.diferencia;
              const entrada = clasif[idR] ?? { causa: "dano" as CausaMerma, cantidad: "" };
              return (
                <li key={idR} className={estilos.bloqueOperador}>
                  <span className={estilos.nombreOperador}>
                    Producto {r.id_producto} · faltante {faltanteBruto}
                  </span>
                  <div className={estilos.filaCampos}>
                    <label className={estilos.campo}>
                      Causa
                      <select
                        className={estilos.entrada}
                        value={entrada.causa}
                        onChange={(e) =>
                          setClasif((p) => ({
                            ...p,
                            [idR]: { ...entrada, causa: e.target.value as CausaMerma },
                          }))
                        }
                      >
                        {CAUSAS.map((c) => (
                          <option key={c.valor} value={c.valor}>
                            {c.etiqueta}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className={estilos.campo}>
                      Cantidad (máx {faltanteBruto})
                      <input
                        className={estilos.entrada}
                        inputMode="numeric"
                        placeholder={String(faltanteBruto)}
                        value={entrada.cantidad}
                        onChange={(e) =>
                          setClasif((p) => ({
                            ...p,
                            [idR]: { ...entrada, cantidad: e.target.value },
                          }))
                        }
                      />
                    </label>
                    <Boton
                      variante="secundaria"
                      registro="analisis"
                      onClick={() => clasificarRenglon(idR, faltanteBruto)}
                    >
                      Clasificar
                    </Boton>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <div className={estilos.filaDoble}>
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
            {mermasPagina.map((m) => (
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
          {(desglose?.mermas.length ?? 0) > 0 && (
            <Paginador
              pagina={paginaMermasActual}
              totalPaginas={totalPaginasMermas}
              onCambiar={setPaginaMermas}
            />
          )}
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
                  {a.ya_caducado ? " — ya caducado" : ` — en ${a.dias_para_caducar} d`}
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
    </div>
  );
}
