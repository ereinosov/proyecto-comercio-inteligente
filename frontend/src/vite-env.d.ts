/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Nombre del comercio de demostración (pie de la pantalla de apertura). */
  readonly VITE_NOMBRE_COMERCIO?: string;
  /** URL/import del logo del comercio para la cabecera de apertura; si falta, el asset por defecto. */
  readonly VITE_LOGO_COMERCIO?: string;
  /** URL/import del ícono del comercio para el nav global (La Regla de la Marca Persistente). */
  readonly VITE_ICONO_COMERCIO?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
