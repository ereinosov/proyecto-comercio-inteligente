/**
 * Selector de rol comercial de un producto (T024, User Story 2). Registro de Análisis, integrado
 * en el panel de detalle de `Precios.tsx`. "Sin clasificar" se muestra con texto explícito, nunca
 * con un rol supuesto por defecto (FR-007).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { asignarRol, obtenerRol, type RolProducto } from "../servicios/precios";
import estilos from "./RolProductoSelector.module.css";

const ETIQUETAS: Record<RolProducto, string> = {
  gancho_trafico: "Gancho de tráfico",
  generador_margen: "Generador de margen",
};

const GLOSA: Record<RolProducto, string> = {
  gancho_trafico:
    "Se vende barato, cerca del costo, para atraer clientes a la tienda; el margen lo dejan otros productos.",
  generador_margen: "Deja margen: sostiene la rentabilidad de la sucursal.",
};

export function RolProductoSelector({ idProducto }: { idProducto: number }) {
  const [rol, setRol] = useState<RolProducto | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    obtenerRol(idProducto)
      .then((detalle) => setRol(detalle.rol))
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el rol."))
      .finally(() => setCargando(false));
  }, [idProducto]);

  async function elegir(nuevoRol: RolProducto) {
    setGuardando(true);
    setError(null);
    try {
      const detalle = await asignarRol(idProducto, nuevoRol);
      setRol(detalle.rol);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo guardar el rol.");
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) return <p className={estilos.sinClasificar}>Cargando rol…</p>;

  return (
    <div className={estilos.selector}>
      <span className={estilos.etiqueta}>
        {rol === null ? (
          <span className={estilos.sinClasificar}>Sin clasificar</span>
        ) : (
          ETIQUETAS[rol]
        )}
      </span>
      <div className={estilos.botones}>
        {(Object.keys(ETIQUETAS) as RolProducto[]).map((opcion) => (
          <button
            key={opcion}
            className={rol === opcion ? `${estilos.boton} ${estilos.botonActivo}` : estilos.boton}
            disabled={guardando || rol === opcion}
            onClick={() => elegir(opcion)}
          >
            {ETIQUETAS[opcion]}
          </button>
        ))}
      </div>
      {rol !== null && <p className={estilos.sinClasificar}>{GLOSA[rol]}</p>}
      {error && <p className={estilos.sinClasificar}>{error}</p>}
    </div>
  );
}
