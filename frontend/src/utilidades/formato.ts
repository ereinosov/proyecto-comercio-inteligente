/**
 * Capa de formato de presentación centralizada (BLOQUE 2 de la auditoría de diseño).
 *
 * Ningún componente debe imprimir un precio, un ratio o un identificador crudo directamente en
 * JSX: el backend entrega cadenas con 4 decimales ("1.5000") y fracciones ("0.0345") porque son
 * fieles a la base de datos, no porque sean legibles. Estas funciones son puras y sin estado.
 */

/** Moneda con dos decimales y símbolo $. Acepta number o la cadena que llega del backend. */
export function formatearMoneda(valor: number | string | null | undefined): string {
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `$${n.toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Porcentaje a partir de una fracción 0-1 ("0.0345" → "3.45%"). `decimales` por defecto 2.
 */
export function formatearPorcentaje(
  fraccion: number | string | null | undefined,
  decimales = 2
): string {
  const n = typeof fraccion === "string" ? Number(fraccion) : fraccion;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(decimales)}%`;
}

/** Número con `decimales` fijos (sin símbolo). Para cantidades y pesos. */
export function formatearNumero(
  valor: number | string | null | undefined,
  decimales = 2
): string {
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(decimales);
}

/** ENUM técnico de medio de pago → etiqueta legible. El ENUM del backend no cambia. */
const ETIQUETA_MEDIO_PAGO: Record<string, string> = {
  efectivo: "Efectivo",
  tarjeta_debito: "Tarjeta de débito",
  tarjeta_credito: "Tarjeta de crédito",
  transferencia: "Transferencia bancaria",
  cheque: "Cheque",
  billetera_digital: "Billetera digital",
  credito_tienda: "Crédito de la tienda",
};

export function etiquetaMedioPago(valorEnum: string | null | undefined): string {
  if (!valorEnum) return "—";
  return ETIQUETA_MEDIO_PAGO[valorEnum] ?? valorEnum.replace(/_/g, " ");
}

/** "caja-1" → "Caja 1"; "caja-1" ya humano se deja pasar. */
export function formatearCaja(caja: string | null | undefined): string {
  if (!caja) return "—";
  const m = /^caja[-_ ]?(\w+)$/i.exec(caja.trim());
  return m ? `Caja ${m[1]}` : caja;
}

/** Nombre de cliente para tablas: su nombre, o "Cliente #<id>" si es anónimo. */
export function nombreClienteODefecto(
  nombre: string | null | undefined,
  idCliente: number
): string {
  return nombre?.trim() ? nombre : `Cliente #${idCliente}`;
}
