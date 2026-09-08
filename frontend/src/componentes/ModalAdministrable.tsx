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

function IconoFlecha() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path
        d="M2.5 7.5h9M8 3.8l3.7 3.7L8 11.2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface Props {
  titulo: string;
  onCerrar: () => void;
  onGuardar: () => void;
  guardando?: boolean;
  etiquetaPrimaria?: string;
  primariaHabilitada?: boolean;
  error?: string | null;
  /** Guía en Tinta Suave (no error) — p. ej. qué falta para poder guardar. */
  aviso?: string | null;
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
  aviso,
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
          {!error && aviso && <p className={estilos.aviso}>{aviso}</p>}

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
              {!guardando && <IconoFlecha />}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
