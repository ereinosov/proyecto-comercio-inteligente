/**
 * Cobros por venta (007-pagos-seguridad, apoyo a US1). Registro de OPERACIÓN: tabla como
 * elemento principal, radio 2px, IBM Plex Sans con cifras tabulares, sin animación. SÓLO
 * LECTURA. Sin Verde Rasero (La Regla del Registro Sin Dinero).
 *
 * Responde "las compras con su forma de pago": cada venta de la sucursal con el medio que el
 * cliente eligió en el POS, y el total cobrado por medio en el período.
 */

import { useEffect, useMemo, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarCobros, type CobrosResumen } from "../servicios/pagos";
import { etiquetaMedioPago, formatearMoneda } from "../utilidades/formato";
import { Buscador } from "../componentes/Buscador";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
import estilos from "./BitacoraPagos.module.css";

function haceDias(dias: number): string {
  return new Date(Date.now() - dias * 86_400_000).toISOString().slice(0, 10);
}

export function CobrosPorVenta({ idSucursal }: { idSucursal: number }) {
  const [desde, setDesde] = useState(haceDias(30));
  const [hasta, setHasta] = useState(new Date().toISOString().slice(0, 10));
  const [datos, setDatos] = useState<CobrosResumen | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  // Búsqueda y paginación client-side: `GET /pagos/cobros` ya llega completo para el rango de
  // fechas elegido (sin parámetros de paginación en el backend); se filtra y se pagina en
  // memoria, mismo patrón que Pronostico.tsx.
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setBusqueda(texto), 200);
    return () => clearTimeout(t);
  }, [texto]);

  useEffect(() => setPagina(1), [busqueda, desde, hasta]);

  useEffect(() => {
    setCargando(true);
    setError(null);
    listarCobros(idSucursal, { desde, hasta })
      .then(setDatos)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los cobros.")
      )
      .finally(() => setCargando(false));
  }, [idSucursal, desde, hasta]);

  const cobrosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const cobros = datos?.cobros ?? [];
    return q ? cobros.filter((c) => c.operador.toLowerCase().includes(q)) : cobros;
  }, [datos, busqueda]);

  const totalPaginas = Math.max(1, Math.ceil(cobrosFiltrados.length / TAMANO_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const cobrosPagina = cobrosFiltrados.slice(
    (paginaActual - 1) * TAMANO_PAGINA,
    paginaActual * TAMANO_PAGINA,
  );

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h2 className={estilos.titulo}>Cobros por venta</h2>
        <span className={estilos.resumen}>
          {cobrosFiltrados.length} venta(s) · sólo lectura
        </span>
      </div>

      <div className={estilos.filtros}>
        <label>
          Desde{" "}
          <input
            className={estilos.select}
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
          />
        </label>
        <label>
          Hasta{" "}
          <input
            className={estilos.select}
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
          />
        </label>
        <span className={estilos.buscadorFiltro}>
          <Buscador
            valor={texto}
            onCambiar={setTexto}
            placeholder="Buscar por operador…"
          />
        </span>
        {datos && datos.total_por_medio.length > 0 && (
          <span className={estilos.resumen}>
            Cobrado por medio:{" "}
            {datos.total_por_medio
              .map(
                (t) =>
                  `${t.medio_pago === "sin_declarar" ? "Sin declarar" : etiquetaMedioPago(t.medio_pago)} ${formatearMoneda(t.total)}`
              )
              .join(" · ")}
          </span>
        )}
      </div>
      {error && <p className={estilos.error}>{error}</p>}

      <div className={estilos.tablaContenedor}>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Venta</th>
              <th>Medio de pago</th>
              <th>Operador</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {cargando ? (
              <tr>
                <td colSpan={5}>Cargando…</td>
              </tr>
            ) : cobrosFiltrados.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  {busqueda.trim()
                    ? "Ningún cobro coincide con la búsqueda."
                    : "Sin ventas en el período."}
                </td>
              </tr>
            ) : (
              cobrosPagina.map((c) => (
                <tr key={c.id_venta}>
                  <td>{new Date(c.instante).toLocaleString()}</td>
                  <td>
                    #{c.id_venta}
                    {c.anulada && <span className={estilos.critico}> · anulada</span>}
                  </td>
                  <td>{c.medio_pago ? etiquetaMedioPago(c.medio_pago) : "sin declarar"}</td>
                  <td>{c.operador}</td>
                  <td>{formatearMoneda(c.total)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!cargando && cobrosFiltrados.length > 0 && (
        <div className={estilos.paginadorZona}>
          <Paginador pagina={paginaActual} totalPaginas={totalPaginas} onCambiar={setPagina} numerado />
        </div>
      )}
    </div>
  );
}
