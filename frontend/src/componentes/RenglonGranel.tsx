/**
 * Captura de peso para un renglón a granel (T040). El operador lee el peso en la báscula en
 * kilogramos; el valor se convierte a gramos enteros antes de enviarse (FR-002, FR-003) — el
 * backend nunca recibe ni almacena kilogramos.
 */

import estilos from "../pantallas/Venta.module.css";

interface Props {
  kg: string;
  onCambiarKg: (kg: string) => void;
}

export function gramosDesdeKg(kg: string): number | null {
  const valor = Number(kg.replace(",", "."));
  if (!Number.isFinite(valor) || valor <= 0) return null;
  return Math.round(valor * 1000);
}

export function RenglonGranel({ kg, onCambiarKg }: Props) {
  return (
    <div className={estilos.campoFila}>
      <label htmlFor="peso-kg">Peso (kg)</label>
      <input
        id="peso-kg"
        className={estilos.inputCantidad}
        type="text"
        inputMode="decimal"
        placeholder="0,700"
        value={kg}
        onChange={(e) => onCambiarKg(e.target.value)}
        autoFocus
      />
    </div>
  );
}
