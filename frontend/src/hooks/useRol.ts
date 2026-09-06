/**
 * Hook único de rol del operador de la sesión (User Story 10, Principio VI).
 *
 * NO es una nueva fuente de verdad: recibe el `rol` que `App.tsx` ya resuelve del operador del
 * turno (el booleano de encargado anterior, ahora `rol`). Toda pantalla que necesite decidir
 * qué ofrecer según el rol consume este hook — leer el rol crudo directamente en un componente
 * está prohibido (FR-062).
 *
 * "Ocultar, no deshabilitar": los helpers devuelven un booleano que el componente usa para
 * **no renderizar** la opción, nunca para deshabilitarla.
 */

export type Rol = "cajero" | "encargado" | "admin";

const RANGO: Record<Rol, number> = { cajero: 1, encargado: 2, admin: 3 };

export interface Autorizacion {
  rol: Rol | null;
  puedeVer: (rolMinimo: Rol) => boolean;
  esAdmin: () => boolean;
  esEncargadoOMas: () => boolean;
}

export function useRol(rol: Rol | null | undefined): Autorizacion {
  const actual = rol ?? null;
  const rango = actual ? RANGO[actual] : 0;
  return {
    rol: actual,
    puedeVer: (rolMinimo: Rol) => rango >= RANGO[rolMinimo],
    esAdmin: () => rango >= RANGO.admin,
    esEncargadoOMas: () => rango >= RANGO.encargado,
  };
}
