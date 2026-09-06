/**
 * Réplica ligera en TypeScript de la validación de cédula / RUC de persona natural, para dar
 * feedback EN VIVO en el formulario antes de enviar (Parte 2).
 *
 * FUENTE DE VERDAD DEL ALGORITMO: `backend/rasero/dominio/identidad_cliente.py`. El backend
 * sigue siendo el que decide (422 `identificador_invalido`); esto es solo una ayuda de UI y
 * debe mantenerse igual a esa función. Cualquier cambio del algoritmo se hace allí primero.
 *
 * - Cédula: 10 dígitos. Provincia (2 primeros) en 01–24 o 30. Tercer dígito 0–5 (persona
 *   natural). Décimo dígito verificador por módulo 10 (coef. 2,1,2,1,2,1,2,1,2; producto > 9
 *   se reduce restándole 9; verificador = complemento a la decena de la suma módulo 10).
 * - RUC de persona natural: 13 dígitos = cédula válida + sufijo "001".
 * - RUC de sociedad (módulo 11): fuera de alcance.
 */

const PROVINCIAS_VALIDAS = new Set<number>([...Array.from({ length: 24 }, (_, i) => i + 1), 30]);
const COEFICIENTES = [2, 1, 2, 1, 2, 1, 2, 1, 2];

export function validarCedulaEcuatoriana(numero: string): boolean {
  if (!/^\d{10}$/.test(numero)) return false;

  const provincia = Number(numero.slice(0, 2));
  if (!PROVINCIAS_VALIDAS.has(provincia)) return false;

  if (Number(numero[2]) > 5) return false;

  let suma = 0;
  for (let i = 0; i < 9; i++) {
    const producto = Number(numero[i]) * COEFICIENTES[i];
    suma += producto > 9 ? producto - 9 : producto;
  }
  const verificador = (10 - (suma % 10)) % 10;
  return verificador === Number(numero[9]);
}

export function validarIdentificador(numero: string): boolean {
  if (!/^\d+$/.test(numero)) return false;
  if (numero.length === 10) return validarCedulaEcuatoriana(numero);
  if (numero.length === 13) return numero.slice(10) === "001" && validarCedulaEcuatoriana(numero.slice(0, 10));
  return false;
}
