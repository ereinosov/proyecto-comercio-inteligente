/**
 * Captura de una observación de precio de competencia (T062, US4). Carga MANUAL o por archivo;
 * la obtención automática desde sitios de terceros está prohibida (FR-026). El canal se elige
 * del catálogo abierto o se nombra al vuelo, sin duplicar por nombre normalizado (FR-025).
 * Registro de Análisis (DESIGN.md).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarProductos, type Producto } from "../servicios/productos";
import {
  agregarCanal,
  capturarObservacion,
  listarCanales,
  type CanalCompetencia,
  type PresentacionUnidad,
} from "../servicios/competencia";
import { Boton } from "../componentes/Boton";
import estilos from "./Competencia.module.css";

interface Props {
  idTurno?: number;
}

export function ObservacionPrecio({ idTurno }: Props) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [canales, setCanales] = useState<CanalCompetencia[]>([]);
  const [idProducto, setIdProducto] = useState<number | "">("");
  const [canalNombre, setCanalNombre] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [unidad, setUnidad] = useState<PresentacionUnidad>("unidad");
  const [precio, setPrecio] = useState("");
  const [fuente, setFuente] = useState("");
  const [origen, setOrigen] = useState<"manual" | "archivo">("manual");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    listarProductos().then(setProductos).catch(() => setProductos([]));
    listarCanales().then(setCanales).catch(() => setCanales([]));
  }, []);

  async function capturar() {
    if (idProducto === "" || !canalNombre.trim() || !cantidad || !precio || !fuente.trim()) {
      setError("Completa producto, canal, presentación, precio y fuente.");
      return;
    }
    setGuardando(true);
    setError(null);
    setOk(null);
    try {
      const canal = await agregarCanal(canalNombre.trim());
      const res = await capturarObservacion({
        id_producto: idProducto,
        id_canal_competencia: canal.id_canal_competencia,
        presentacion_cantidad: cantidad,
        presentacion_unidad: unidad,
        precio_observado: Number(precio).toFixed(2),
        fuente: fuente.trim(),
        origen_captura: origen,
        id_turno: idTurno ?? null,
      });
      setCanales(await listarCanales());
      setOk(
        res.comparable
          ? "Observación registrada y comparable."
          : "Observación registrada; su presentación no admite normalización, se marca no comparable.",
      );
      setCantidad("");
      setPrecio("");
      setFuente("");
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo registrar la observación.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className={estilos.pantalla}>
      <h2 className={estilos.titulo}>Capturar precio de competencia</h2>
      <p className={estilos.instruccion}>
        Anota lo que observaste en otro comercio: el producto, en qué presentación lo vende, a qué
        precio y de dónde salió el dato. La comparación normaliza después; aquí se guarda tal cual.
      </p>

      <div className={estilos.formulario}>
        <div className={estilos.campo}>
          <label htmlFor="op-producto">Producto propio</label>
          <select
            id="op-producto"
            className={estilos.seleccion}
            value={idProducto}
            onChange={(e) => setIdProducto(Number(e.target.value))}
          >
            <option value="" disabled>
              Elige…
            </option>
            {productos.map((p) => (
              <option key={p.id_producto} value={p.id_producto}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="op-canal">Canal (comercio observado)</label>
          <input
            id="op-canal"
            className={estilos.entrada}
            list="op-canales"
            value={canalNombre}
            onChange={(e) => setCanalNombre(e.target.value)}
            placeholder="Nómbralo si es nuevo"
          />
          <datalist id="op-canales">
            {canales.map((c) => (
              <option key={c.id_canal_competencia} value={c.nombre} />
            ))}
          </datalist>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="op-cantidad">Presentación</label>
          <input
            id="op-cantidad"
            className={estilos.entrada}
            type="number"
            min={0}
            step="0.001"
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
        </div>
        <div className={estilos.campo}>
          <label htmlFor="op-unidad">Unidad</label>
          <select
            id="op-unidad"
            className={estilos.seleccion}
            value={unidad}
            onChange={(e) => setUnidad(e.target.value as PresentacionUnidad)}
          >
            <option value="unidad">unidad</option>
            <option value="gramo">gramo</option>
            <option value="mililitro">mililitro</option>
          </select>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="op-precio">Precio observado</label>
          <input
            id="op-precio"
            className={estilos.entrada}
            type="number"
            min={0}
            step="0.01"
            value={precio}
            onChange={(e) => setPrecio(e.target.value)}
          />
        </div>

        <div className={estilos.campo}>
          <label htmlFor="op-fuente">Fuente</label>
          <input
            id="op-fuente"
            className={estilos.entrada}
            value={fuente}
            onChange={(e) => setFuente(e.target.value)}
            placeholder="visita, folleto, foto…"
          />
        </div>

        <div className={estilos.campo}>
          <label htmlFor="op-origen">Origen de la captura</label>
          <select
            id="op-origen"
            className={estilos.seleccion}
            value={origen}
            onChange={(e) => setOrigen(e.target.value as "manual" | "archivo")}
          >
            <option value="manual">manual</option>
            <option value="archivo">archivo</option>
          </select>
        </div>

        <Boton variante="primaria" registro="analisis" onClick={capturar} disabled={guardando}>
          {guardando ? "Guardando…" : "Registrar observación"}
        </Boton>
      </div>

      {error && <p className={estilos.error}>{error}</p>}
      {ok && <p className={estilos.ok}>{ok}</p>}
    </div>
  );
}
