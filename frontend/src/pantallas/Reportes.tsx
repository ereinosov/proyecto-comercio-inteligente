/**
 * Reportes e Inteligencia (008). Capa de SOLO LECTURA sobre 001–007, rol `encargado`.
 * Registro de Análisis (Source Serif 4, radio 6px); sin Verde Rasero.
 *
 * Cuatro vistas bajo un `Segmentado`: comparativo entre sucursales, tendencias por semana/mes,
 * tablero de KPIs y segmentos de clientes (k-means, recálculo por lote). El activo de marca mono
 * (`despensa-logo-mono-800w.png`, reservado en DESIGN.md v1.3.0 para "reportes y dashboards")
 * ancla la sección.
 */

import { useEffect, useState } from "react";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
import { Segmentado } from "../componentes/Segmentado";
import { Boton } from "../componentes/Boton";
import { EstadoVacio } from "../componentes/EstadoVacio";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  obtenerComparativo,
  obtenerTablero,
  obtenerTendencia,
  obtenerSegmentos,
  recalcularSegmentos,
  type Comparativo,
  type Tablero,
  type Tendencia,
  type Segmentos,
} from "../servicios/reportes";
import marcaMono from "../activos/marca/despensa-logo-mono-800w.png";
import estilos from "./Reportes.module.css";

type Vista = "comparativo" | "tendencias" | "tablero" | "segmentos";
const VISTAS: { valor: Vista; texto: string }[] = [
  { valor: "comparativo", texto: "Comparativo" },
  { valor: "tendencias", texto: "Tendencias" },
  { valor: "tablero", texto: "Tablero" },
  { valor: "segmentos", texto: "Segmentos" },
];

export function Reportes() {
  const [vista, setVista] = useState<Vista>("comparativo");
  // "Exportar PDF" (paridad con la factura de 009): sin PDF de servidor —el diálogo de
  // impresión del navegador ya trae "Guardar como PDF" y su propia vista previa—. Al pulsar,
  // se marca la pantalla como hoja de impresión (base.css oculta el nav, los filtros y los
  // botones vía `data-noprint`) y se lanza `window.print()`; `afterprint` limpia el estado.
  const [imprimiendo, setImprimiendo] = useState(false);
  useEffect(() => {
    if (!imprimiendo) return;
    const restaurar = () => setImprimiendo(false);
    window.addEventListener("afterprint", restaurar);
    const t = window.setTimeout(() => window.print(), 60);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("afterprint", restaurar);
    };
  }, [imprimiendo]);

  const nombreVista = VISTAS.find((v) => v.valor === vista)?.texto ?? "";

  return (
    <div className={`${estilos.pantalla} ${imprimiendo ? estilos.imprimiendo : ""}`}>
      <img className={estilos.marca} src={marcaMono} alt="" aria-hidden="true" data-noprint />
      <EncabezadoPantalla
        titulo="Reportes e Inteligencia"
        registro="analisis"
        acciones={
          <span data-noprint>
            <Boton variante="secundaria" tamano="sm" onClick={() => setImprimiendo(true)}>
              Exportar PDF
            </Boton>
          </span>
        }
      />
      <div className={estilos.selectorVista} data-noprint>
        <Segmentado
          opciones={VISTAS}
          activa={vista}
          onCambiar={setVista}
          registro="analisis"
          etiqueta="Vista de reportes"
        />
      </div>
      <div className={estilos.cuerpo}>
        <p className={estilos.tituloImpresion} data-solo-impresion>
          Rasero · Reportes e Inteligencia — {nombreVista}
          <br />
          Generado {new Date().toLocaleString("es-EC")} · comprobante de demostración, sin valor
          contractual.
        </p>
        {vista === "comparativo" && <VistaComparativo />}
        {vista === "tendencias" && <VistaTendencias />}
        {vista === "tablero" && <VistaTablero />}
        {vista === "segmentos" && <VistaSegmentos />}
      </div>
    </div>
  );
}

function useCarga<T>(cargar: () => Promise<T>, deps: unknown[]) {
  const [dato, setDato] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  function recargar(fn = cargar) {
    setCargando(true);
    setError(null);
    fn()
      .then(setDato)
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el reporte."))
      .finally(() => setCargando(false));
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => recargar(), deps);
  return { dato, error, cargando, recargar, setDato, setError, setCargando };
}

// ── Comparativo ─────────────────────────────────────────────────────────────────────────────
function VistaComparativo() {
  const { dato, error, cargando, recargar } = useCarga<Comparativo>(() => obtenerComparativo(), []);
  if (cargando) return <p className={estilos.nota}>Cargando…</p>;
  if (error) return <p className={estilos.error}>{error}</p>;
  if (!dato) return null;
  return (
    <div>
      <div className={estilos.barraAcciones}>
        <span className={estilos.nota}>
          Período {dato.periodo_inicio} – {dato.periodo_fin} · calculado{" "}
          {new Date(dato.instante_calculo).toLocaleString()}
        </span>
        <Boton variante="secundaria" tamano="sm" onClick={() => recargar(() => obtenerComparativo(true))}>
          Actualizar
        </Boton>
      </div>
      {!dato.comparable && (
        <p className={estilos.nota}>No hay otra sucursal activa con la que comparar.</p>
      )}
      <table className={estilos.tabla}>
        <thead>
          <tr>
            <th>Indicador</th>
            {dato.sucursales.map((s) => (
              <th key={s.id_sucursal}>
                {s.nombre}
                {!s.activa && " (desactivada)"}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dato.indicadores.map((fila) => (
            <tr key={fila.clave}>
              <td>{fila.etiqueta}</td>
              {fila.celdas.map((c) => (
                <td key={c.id_sucursal} className={c.atencion ? estilos.atencion : undefined}>
                  {c.sin_datos ? <span className={estilos.sinDatos}>sin datos</span> : c.valor}
                  {c.diferencia_relativa && (
                    <span className={estilos.dif}> ({c.diferencia_relativa})</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tendencias ──────────────────────────────────────────────────────────────────────────────
const INDICADORES = [
  { valor: "ventas", texto: "Ventas" },
  { valor: "unidades", texto: "Unidades" },
  { valor: "margen_ponderado", texto: "Margen" },
  { valor: "merma_valorada", texto: "Merma" },
];

function VistaTendencias() {
  const [indicador, setIndicador] = useState("ventas");
  const [granularidad, setGranularidad] = useState<"semana" | "mes">("semana");
  const { dato, error, cargando, recargar } = useCarga<Tendencia>(
    () => obtenerTendencia(indicador, granularidad),
    [indicador, granularidad],
  );
  return (
    <div>
      <div className={estilos.barraAcciones}>
        <Segmentado
          opciones={INDICADORES}
          activa={indicador}
          onCambiar={setIndicador}
          registro="analisis"
          etiqueta="Indicador"
        />
        <Segmentado
          opciones={[
            { valor: "semana", texto: "Semana" },
            { valor: "mes", texto: "Mes" },
          ]}
          activa={granularidad}
          onCambiar={(v) => setGranularidad(v as "semana" | "mes")}
          registro="analisis"
          etiqueta="Granularidad"
        />
        <Boton
          variante="secundaria"
          tamano="sm"
          onClick={() => recargar(() => obtenerTendencia(indicador, granularidad, { actualizar: true }))}
        >
          Actualizar
        </Boton>
      </div>
      {cargando && <p className={estilos.nota}>Cargando…</p>}
      {error && <p className={estilos.error}>{error}</p>}
      {dato && !dato.disponible && (
        <p className={estilos.nota}>{dato.razon ?? "Sin datos para el rango pedido."}</p>
      )}
      {dato?.disponible && (
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Período</th>
              <th className={estilos.num}>{INDICADORES.find((i) => i.valor === indicador)?.texto}</th>
            </tr>
          </thead>
          <tbody>
            {dato.puntos.map((p) => (
              <tr key={p.periodo}>
                <td>
                  {p.etiqueta}
                  {!p.completo && <span className={estilos.dif}> (incompleto)</span>}
                </td>
                <td className={estilos.num}>{p.valor ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Tablero ─────────────────────────────────────────────────────────────────────────────────
function VistaTablero() {
  const { dato, error, cargando, recargar } = useCarga<Tablero>(() => obtenerTablero(), []);
  if (cargando) return <p className={estilos.nota}>Cargando…</p>;
  if (error) return <p className={estilos.error}>{error}</p>;
  if (!dato) return null;
  return (
    <div>
      <div className={estilos.barraAcciones}>
        <span className={estilos.nota}>
          Calculado {new Date(dato.instante_calculo).toLocaleString()}
        </span>
        <Boton variante="secundaria" tamano="sm" onClick={() => recargar(() => obtenerTablero(true))}>
          Actualizar
        </Boton>
      </div>
      <div className={estilos.tarjetas}>
        {dato.tarjetas.map((t) => (
          <div key={t.modulo} className={estilos.tarjeta}>
            <h3 className={estilos.tarjetaTitulo}>{t.titulo}</h3>
            <span className={estilos.tarjetaPeriodo}>{t.periodo_referencia}</span>
            {t.sin_datos ? (
              <p className={estilos.nota}>{t.razon}</p>
            ) : (
              <ul className={estilos.cifras}>
                {t.cifras.map((c) => (
                  <li key={c.etiqueta} className={c.atencion ? estilos.atencion : undefined}>
                    <span className={estilos.cifraValor}>{c.valor}</span> {c.etiqueta}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Segmentos ───────────────────────────────────────────────────────────────────────────────
function VistaSegmentos() {
  const { dato, error, cargando, setDato, setError, setCargando } = useCarga<Segmentos>(
    () => obtenerSegmentos(),
    [],
  );
  const [recalculando, setRecalculando] = useState(false);

  function recalcular() {
    setRecalculando(true);
    setError(null);
    recalcularSegmentos()
      .then(setDato)
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "No se pudo recalcular."))
      .finally(() => {
        setRecalculando(false);
        setCargando(false);
      });
  }

  return (
    <div>
      <div className={estilos.barraAcciones}>
        {dato?.calculado && dato.corrida && (
          <span className={estilos.nota}>
            Último recálculo {new Date(dato.corrida).toLocaleString()}
          </span>
        )}
        <Boton variante="primaria" registro="analisis" onClick={recalcular} disabled={recalculando}>
          {recalculando ? "Recalculando…" : "Recalcular segmentos"}
        </Boton>
      </div>
      {cargando && <p className={estilos.nota}>Cargando…</p>}
      {error && <p className={estilos.error}>{error}</p>}
      {dato && !dato.calculado && !cargando && (
        <EstadoVacio
          glifo="grafico"
          titulo="Todavía no se han calculado los segmentos"
          descripcion="Al pulsar «Recalcular segmentos» el sistema agrupa a los clientes por parecido en frecuencia, margen y recencia, y aquí verás cada grupo con su perfil y algunos clientes de ejemplo."
        />
      )}
      {dato?.calculado && (
        <div className={estilos.grupos}>
          {dato.grupos.map((g) => (
            <div key={g.etiqueta_grupo} className={estilos.grupo}>
              <div className={estilos.grupoCabecera}>
                <span className={estilos.grupoNombre}>{g.etiqueta_grupo.replace("_", " ")}</span>
                <span className={estilos.nota}>{g.n_clientes} clientes</span>
              </div>
              <p className={estilos.grupoDescripcion}>{g.descripcion}</p>
              {g.ejemplos.length > 0 && (
                <p className={estilos.nota}>
                  Ej.: {g.ejemplos.map((e) => e.nombre ?? `#${e.id_cliente}`).join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
