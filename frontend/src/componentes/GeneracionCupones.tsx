/**
 * Generación de cupones por fecha fija (005-promociones-inteligentes, US1, T018). Registro de
 * Análisis: radio 6px, Source Serif 4, una decisión por bloque.
 *
 * Dispara la generación de un rango de fechas (idempotente en el backend por
 * `UNIQUE (id_cliente, fecha_objetivo)`) y lista los cupones emitidos con su estado. No aplica
 * ningún descuento: sólo emite el cupón; la redención se registra en la caja, después de la venta.
 */

import { useCallback, useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  generarCupones,
  listarCuponesPagina,
  type Cupon,
  type ResultadoGeneracion,
} from "../servicios/promociones";
import { Paginador, TAMANO_PAGINA } from "./Paginador";
import estilos from "./GeneracionCupones.module.css";

function hoyISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function enDiasISO(dias: number): string {
  return new Date(Date.now() + dias * 86_400_000).toISOString().slice(0, 10);
}

const ETIQUETA_ESTADO: Record<Cupon["estado"], string> = {
  generado: "Generado",
  redimido: "Redimido",
  vencido: "Vencido",
};

export function GeneracionCupones() {
  const [desde, setDesde] = useState(hoyISO());
  const [hasta, setHasta] = useState(enDiasISO(21));
  const [generando, setGenerando] = useState(false);
  const [ultimoResultado, setUltimoResultado] = useState<ResultadoGeneracion | null>(null);
  const [cupones, setCupones] = useState<Cupon[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(() => {
    setCargando(true);
    listarCuponesPagina({ pagina, tamanoPagina: TAMANO_PAGINA })
      .then(({ items, total: t }) => {
        setCupones(items);
        setTotal(t ?? items.length);
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los cupones.")
      )
      .finally(() => setCargando(false));
  }, [pagina]);

  useEffect(recargar, [recargar]);

  const totalPaginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

  async function generar() {
    setGenerando(true);
    setError(null);
    try {
      const resultado = await generarCupones(desde, hasta);
      setUltimoResultado(resultado);
      setPagina(1);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo generar la campaña de cupones.");
    } finally {
      setGenerando(false);
    }
  }

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.instruccion}>
        Emite un cupón de cumpleaños para cada cliente cuya fecha entra en el rango. Ejecutarlo
        de nuevo para un rango que se solapa no duplica ningún cupón.
      </p>

      <div className={estilos.formulario}>
        <label className={estilos.campo}>
          <span>Desde</span>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className={estilos.campo}>
          <span>Hasta</span>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
        <button
          className={estilos.boton}
          onClick={generar}
          disabled={generando || !desde || !hasta}
        >
          {generando ? "Generando…" : "Generar cupones"}
        </button>
      </div>

      {error && <p className={estilos.error}>{error}</p>}

      {ultimoResultado && (
        <p className={estilos.resumen}>
          Campaña {ultimoResultado.id_campania}: {ultimoResultado.cupones_generados} cupones
          nuevos, {ultimoResultado.cupones_ya_existentes} ya existían.
        </p>
      )}

      <h3 className={estilos.subtitulo}>Cupones emitidos</h3>
      {cargando && <p className={estilos.instruccion}>Cargando…</p>}
      {!cargando && cupones.length === 0 && (
        <p className={estilos.instruccion}>Todavía no se ha emitido ningún cupón.</p>
      )}
      {!cargando && cupones.length > 0 && (
        <>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Cupón</th>
              <th>Cliente</th>
              <th>Fecha objetivo</th>
              <th>Vigencia</th>
              <th>Descuento</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {cupones.map((c) => (
              <tr key={c.id_cupon}>
                <td>{c.id_cupon}</td>
                <td>{c.id_cliente}</td>
                <td>{c.fecha_objetivo}</td>
                <td>
                  {c.valido_desde} — {c.valido_hasta}
                </td>
                <td>{c.porcentaje_descuento} %</td>
                <td>
                  <span className={estilos[`estado_${c.estado}`]}>
                    {ETIQUETA_ESTADO[c.estado]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Paginador pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />
        </>
      )}
    </div>
  );
}
