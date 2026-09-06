/**
 * Modal único y reutilizable para todo formulario de creación o edición de un dato maestro
 * (La Regla del Modal Administrable, DESIGN.md v1.2.0). NUNCA se escribe un formulario ad-hoc
 * por pantalla: esta es la única forma del sistema.
 *
 * Estructura: velo en Tinta al 45% (nunca negro puro) · tarjeta centrada máx. 420px, radio 6px
 * (registro de Análisis: administrar un maestro es una decisión gerencial) · header en
 * Superficie Alta con título Source Serif 4 + cierre circular · cuerpo en Superficie Base ·
 * footer en Superficie Alta con "Cancelar" (borde, sin relleno) y la acción primaria a la
 * derecha. Sin sombra: sólo contraste de tono.
 */

import { useEffect, type ReactNode } from "react";
import estilos from "./ModalAdministrable.module.css";

interface Props {
  titulo: string;
  onCerrar: () => void;
  onGuardar: () => void;
  guardando?: boolean;
  etiquetaPrimaria?: string;
  primariaHabilitada?: boolean;
  error?: string | null;
  children: ReactNode;
}

export function ModalAdministrable({
  titulo,
  onCerrar,
  onGuardar,
  guardando = false,
  etiquetaPrimaria = "Guardar",
  primariaHabilitada = true,
  error,
  children,
}: Props) {
  useEffect(() => {
    function alPresionar(e: KeyboardEvent) {
      if (e.key === "Escape") onCerrar();
    }
    window.addEventListener("keydown", alPresionar);
    return () => window.removeEventListener("keydown", alPresionar);
  }, [onCerrar]);

  return (
    <div className={estilos.velo} onMouseDown={onCerrar} role="presentation">
      <div
        className={estilos.tarjeta}
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
      >
        <header className={estilos.header}>
          <h2 className={estilos.titulo}>{titulo}</h2>
          <button
            type="button"
            className={estilos.cerrar}
            onClick={onCerrar}
            aria-label="Cerrar"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path
                d="M2 2 L10 10 M10 2 L2 10"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </header>

        <form
          className={estilos.cuerpo}
          onSubmit={(e) => {
            e.preventDefault();
            if (!guardando && primariaHabilitada) onGuardar();
          }}
        >
          {children}
          {error && <p className={estilos.error}>{error}</p>}

          <footer className={estilos.footer}>
            <button type="button" className={estilos.cancelar} onClick={onCerrar}>
              Cancelar
            </button>
            <button
              type="submit"
              className={estilos.primaria}
              disabled={guardando || !primariaHabilitada}
            >
              {guardando ? "Guardando…" : etiquetaPrimaria}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
