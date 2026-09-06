/**
 * Cliente HTTP base (T016). Backend en http://localhost:8000 por defecto.
 * Los errores de dominio del backend llegan como { codigo, mensaje } (ver
 * backend/rasero/errores.py) — nunca una traza técnica; se propagan tal cual.
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

async function peticionCompleta<T>(
  ruta: string,
  opciones: RequestInit = {},
): Promise<{ datos: T; total: number | null }> {
  const respuesta = await fetch(`${URL_BASE}${ruta}`, {
    ...opciones,
    headers: {
      "Content-Type": "application/json",
      ...opciones.headers,
    },
  });

  if (respuesta.status === 204) {
    return { datos: undefined as T, total: null };
  }

  const cuerpo = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const codigo = cuerpo?.codigo ?? "error_desconocido";
    const mensaje = cuerpo?.mensaje ?? "Ocurrió un error. Intenta de nuevo.";
    throw new ErrorApi(codigo, mensaje, respuesta.status);
  }

  const cabecera = respuesta.headers.get("X-Total-Count");
  return { datos: cuerpo as T, total: cabecera === null ? null : Number(cabecera) };
}

async function peticion<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  return (await peticionCompleta<T>(ruta, opciones)).datos;
}

/** Página de un listado: los elementos más el total de registros de la cabecera `X-Total-Count`
 * (La Regla del Filtro y la Página, DESIGN.md v1.2.0). `total` es `null` si el backend no la
 * envió. */
export interface Pagina<T> {
  items: T[];
  total: number | null;
}

export const clienteHttp = {
  get: <T>(ruta: string) => peticion<T>(ruta, { method: "GET" }),
  getPagina: async <T>(ruta: string): Promise<Pagina<T>> => {
    const { datos, total } = await peticionCompleta<T[]>(ruta, { method: "GET" });
    return { items: datos, total };
  },
  post: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "POST", body: JSON.stringify(cuerpo) }),
  put: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PUT", body: JSON.stringify(cuerpo) }),
  patch: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PATCH", body: JSON.stringify(cuerpo) }),
  del: <T>(ruta: string) => peticion<T>(ruta, { method: "DELETE" }),
};
