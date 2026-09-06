/**
 * Campo de búsqueda por nombre para listados que crecen sin techo conocido (Clientes, Precios,
 * las vistas grandes de Administración). Controlado y presentacional: el debounce (~200ms, el
 * mismo patrón de temporizador que `IdentificarCliente.tsx`) vive en la pantalla que lo usa,
 * junto a su paginación.
 */

import estilos from "./Buscador.module.css";

interface Props {
  valor: string;
  onCambiar: (texto: string) => void;
  placeholder?: string;
}

export function Buscador({ valor, onCambiar, placeholder = "Buscar por nombre…" }: Props) {
  return (
    <input
      type="search"
      className={estilos.buscador}
      placeholder={placeholder}
      value={valor}
      onChange={(e) => onCambiar(e.target.value)}
    />
  );
}
