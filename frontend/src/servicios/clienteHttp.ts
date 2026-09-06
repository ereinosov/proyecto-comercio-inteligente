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

async function peticion<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const respuesta = await fetch(`${URL_BASE}${ruta}`, {
    ...opciones,
    headers: {
      "Content-Type": "application/json",
      ...opciones.headers,
    },
  });

  if (respuesta.status === 204) {
    return undefined as T;
  }

  const cuerpo = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const codigo = cuerpo?.codigo ?? "error_desconocido";
    const mensaje = cuerpo?.mensaje ?? "Ocurrió un error. Intenta de nuevo.";
    throw new ErrorApi(codigo, mensaje, respuesta.status);
  }

  return cuerpo as T;
}

export const clienteHttp = {
  get: <T>(ruta: string) => peticion<T>(ruta, { method: "GET" }),
  post: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "POST", body: JSON.stringify(cuerpo) }),
  put: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PUT", body: JSON.stringify(cuerpo) }),
  patch: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PATCH", body: JSON.stringify(cuerpo) }),
  del: <T>(ruta: string) => peticion<T>(ruta, { method: "DELETE" }),
};
