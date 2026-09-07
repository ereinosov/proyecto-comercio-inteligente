/**
 * Cliente HTTP base (T016). Backend en http://localhost:8000 por defecto.
 * Los errores de dominio del backend llegan como { codigo, mensaje } (ver
 * backend/rasero/errores.py) — nunca una traza técnica; se propagan tal cual.
 *
 * Sesión de turno (User Story 11, enmienda v2.4.0): el token JWT que devuelve `POST /turnos`
 * se guarda EN MEMORIA aquí (nunca en localStorage/sessionStorage — convención del proyecto) y
 * se adjunta como `Authorization: Bearer <token>` en toda petición mientras haya sesión activa.
 * Si el backend responde `401` con `codigo` de sesión (`sesion_invalida` / `sesion_expirada`),
 * se avisa por el callback registrado para que la app vuelva a la pantalla de apertura de turno.
 */

const URL_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ErrorApi extends Error {
  codigo: string;
  status: number;

  constructor(codigo: string, mensaje: string, status: number) {
    super(mensaje);
    this.codigo = codigo;
    this.status = status;
  }
}

// --- Sesión de turno: token en memoria + aviso de sesión perdida -----------

const CODIGOS_SESION_PERDIDA = new Set(["sesion_invalida", "sesion_expirada"]);

let tokenSesion: string | null = null;
let alPerderSesion: ((error: ErrorApi) => void) | null = null;

/** Guarda el token de la sesión de turno recién abierta. */
export function fijarTokenSesion(token: string): void {
  tokenSesion = token;
}

/** Borra el token (al cerrar turno, o al perder la sesión). */
export function limpiarTokenSesion(): void {
  tokenSesion = null;
}

export function hayTokenSesion(): boolean {
  return tokenSesion !== null;
}

/**
 * Registra el callback que se dispara cuando el backend rechaza una petición por sesión
 * inválida o expirada. La app lo usa para volver a la pantalla de apertura de turno.
 */
export function alPerderSesionDeTurno(callback: ((error: ErrorApi) => void) | null): void {
  alPerderSesion = callback;
}

async function peticion<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const cabeceras: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opciones.headers as Record<string, string> | undefined),
  };
  if (tokenSesion) {
    cabeceras["Authorization"] = `Bearer ${tokenSesion}`;
  }

  const respuesta = await fetch(`${URL_BASE}${ruta}`, { ...opciones, headers: cabeceras });

  if (respuesta.status === 204) {
    return undefined as T;
  }

  const cuerpo = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const codigo = cuerpo?.codigo ?? "error_desconocido";
    const mensaje = cuerpo?.mensaje ?? "Ocurrió un error. Intenta de nuevo.";
    const error = new ErrorApi(codigo, mensaje, respuesta.status);
    if (respuesta.status === 401 && CODIGOS_SESION_PERDIDA.has(codigo)) {
      limpiarTokenSesion();
      alPerderSesion?.(error);
    }
    throw error;
  }

  return cuerpo as T;
}

/**
 * Página de un listado (La Regla del Filtro y la Página, DESIGN.md v1.2.0). El backend responde
 * con un objeto `{ items, total }` (schema `RespuestaPaginada`); `total` es el número total de
 * registros que cumplen el filtro, no el de la página.
 */
export interface Pagina<T> {
  items: T[];
  total: number;
}

export const clienteHttp = {
  get: <T>(ruta: string) => peticion<T>(ruta, { method: "GET" }),
  getPagina: async <T>(ruta: string): Promise<Pagina<T>> => {
    const cuerpo = await peticion<{ items: T[]; total: number }>(ruta, { method: "GET" });
    return { items: cuerpo.items ?? [], total: cuerpo.total ?? 0 };
  },
  post: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "POST", body: JSON.stringify(cuerpo) }),
  put: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PUT", body: JSON.stringify(cuerpo) }),
  patch: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PATCH", body: JSON.stringify(cuerpo) }),
  del: <T>(ruta: string) => peticion<T>(ruta, { method: "DELETE" }),
};
