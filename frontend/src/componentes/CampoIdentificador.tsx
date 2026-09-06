/**
 * Campo "Cédula o RUC (opcional)" reutilizable, con ayuda de formato permanente y validación en
 * vivo (Parte 2). Lo usan el alta de cliente (`IdentificarCliente.tsx`) y la edición
 * (`Clientes.tsx`).
 *
 * El campo es OPCIONAL: la validación en vivo es una ayuda, no un gate — nunca deshabilita el
 * botón "Guardar" del modal. Sólo muestra un aviso inline en Crítico cuando el usuario ya
 * escribió 10 o 13 dígitos y el valor no valida (mientras sigue escribiendo, no molesta).
 */

import { validarIdentificador } from "../dominio/identidadCliente";
import estilos from "./CampoIdentificador.module.css";

interface Props {
  /** Sólo dígitos. */
  value: string;
  onChange: (digitos: string) => void;
  /** Clase del `<label>` contenedor (la del formulario que lo incrusta). */
  claseCampo: string;
}

export function CampoIdentificador({ value, onChange, claseCampo }: Props) {
  const longitudCompleta = value.length === 10 || value.length === 13;
  const mostrarError = longitudCompleta && !validarIdentificador(value);

  return (
    <label className={claseCampo}>
      <span>Cédula o RUC (opcional)</span>
      <input
        inputMode="numeric"
        maxLength={13}
        placeholder="1234567890 (cédula) o 1234567890001 (RUC)"
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, ""))}
      />
      <span className={estilos.ayuda}>10 dígitos para cédula, 13 para RUC de persona natural.</span>
      {mostrarError && <span className={estilos.error}>Verifica los dígitos.</span>}
    </label>
  );
}
