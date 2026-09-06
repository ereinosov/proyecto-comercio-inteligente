/**
 * Cola local de operaciones ejecutadas sin conectividad (US8 — T087, T088).
 *
 * Cada operación se guarda en IndexedDB con su `marca_tiempo_origen` generada EN EL DISPOSITIVO
 * en el momento en que ocurrió (FR-037), para que el servidor pueda ordenarlas y desempatar los
 * conflictos por esa marca (FR-038, FR-039). Al recuperar la conectividad (`window` evento
 * `online`) se envía todo el lote a `POST /operaciones-pendientes/sincronizacion` (T086); las que
 * el servidor confirma (`sincronizada` o `conflicto_resuelto`) se retiran de la cola local — la
 * operación desplazada por conflicto sigue visible en el servidor (FR-040), no en la caja.
 *
 * La caja nunca se bloquea por esto (Principio II): encolar es local e inmediato; la
 * sincronización ocurre en segundo plano.
 */

const BD = "rasero-offline";
const ALMACEN = "operaciones";
const URL_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type TipoOperacionOffline =
  | "venta"
  | "consulta_no_atendida"
  | "anulacion_venta"
  | "recepcion_traspaso"
  | "resolucion_conteo";

export interface OperacionOffline {
  id_operacion_pendiente: string;
  tipo_operacion: TipoOperacionOffline;
  carga: Record<string, unknown>;
  recurso_afectado: string;
  marca_tiempo_origen: string;
}

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolver, rechazar) => {
    const solicitud = indexedDB.open(BD, 1);
    solicitud.onupgradeneeded = () => {
      solicitud.result.createObjectStore(ALMACEN, { keyPath: "id_operacion_pendiente" });
    };
    solicitud.onsuccess = () => resolver(solicitud.result);
    solicitud.onerror = () => rechazar(solicitud.error);
  });
}

function conTransaccion<T>(
  modo: IDBTransactionMode,
  fn: (almacen: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return abrir().then(
    (bd) =>
      new Promise<T>((resolver, rechazar) => {
        const tx = bd.transaction(ALMACEN, modo);
        const req = fn(tx.objectStore(ALMACEN));
        req.onsuccess = () => resolver(req.result);
        req.onerror = () => rechazar(req.error);
      }),
  );
}

/** Encola una operación ejecutada sin conectividad. La marca de origen la pone el dispositivo. */
export async function encolar(
  tipo: TipoOperacionOffline,
  carga: Record<string, unknown>,
  recursoAfectado: string,
): Promise<OperacionOffline> {
  const operacion: OperacionOffline = {
    id_operacion_pendiente: crypto.randomUUID(),
    tipo_operacion: tipo,
    carga,
    recurso_afectado: recursoAfectado,
    marca_tiempo_origen: new Date().toISOString(),
  };
  await conTransaccion("readwrite", (a) => a.put(operacion));
  return operacion;
}

export async function pendientes(): Promise<OperacionOffline[]> {
  const todo = await conTransaccion<OperacionOffline[]>("readonly", (a) => a.getAll());
  return [...todo].sort((x, y) =>
    x.marca_tiempo_origen < y.marca_tiempo_origen ? -1 : 1,
  );
}

async function retirar(ids: string[]): Promise<void> {
  await Promise.all(ids.map((id) => conTransaccion("readwrite", (a) => a.delete(id))));
}

/**
 * Envía todas las operaciones pendientes al servidor, en orden de marca de origen. Devuelve el
 * número sincronizado. No lanza si no hay conectividad: se reintentará en el siguiente evento
 * `online`.
 */
export async function sincronizarPendientes(): Promise<number> {
  const lote = await pendientes();
  if (lote.length === 0) return 0;
  try {
    const respuesta = await fetch(`${URL_BASE}/operaciones-pendientes/sincronizacion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operaciones: lote }),
    });
    if (!respuesta.ok) return 0;
    const resueltas: { id_operacion_pendiente: string; estado: string }[] = await respuesta.json();
    const confirmadas = resueltas
      .filter((o) => o.estado === "sincronizada" || o.estado === "conflicto_resuelto")
      .map((o) => o.id_operacion_pendiente);
    await retirar(confirmadas);
    return confirmadas.length;
  } catch {
    return 0; // sin red: se reintenta al volver la conectividad
  }
}

let iniciada = false;

/** Registra el disparador de sincronización al recuperar la conectividad (T088). */
export function iniciarColaOffline(): void {
  if (iniciada || typeof window === "undefined") return;
  iniciada = true;
  window.addEventListener("online", () => {
    void sincronizarPendientes();
  });
  if (navigator.onLine) void sincronizarPendientes();
}
