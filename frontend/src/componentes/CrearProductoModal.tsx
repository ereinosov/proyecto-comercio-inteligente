/**
 * Alta rápida de un producto desde el flujo de "Agregar producto" de Venta.tsx (Parte 3,
 * "Atajo desde Venta"). Usa el MISMO componente `ModalAdministrable` que la pantalla de
 * Administración y los mismos campos del alta de producto — no un formulario distinto.
 *
 * Sólo debe montarse cuando el operador del turno tiene rol encargado o admin (hook `useRol`,
 * `esEncargadoOMas()`): si no lo tiene,
 * la opción "+ Crear producto nuevo" no se ofrece en absoluto (nunca lleva a un error de
 * permisos al guardar).
 */

import { useEffect, useState } from "react";
import { ModalAdministrable } from "./ModalAdministrable";
import { Obligatorio } from "./Obligatorio";
import { ErrorApi } from "../servicios/clienteHttp";
import { crearMaestro, type ProductoMaestro } from "../servicios/administracion";
import { listarCategorias, type Categoria } from "../servicios/productos";
import estilos from "../pantallas/Administracion.module.css";

interface Props {
  idOperador: number;
  onCerrar: () => void;
  onCreado: (producto: ProductoMaestro) => void;
}

export function CrearProductoModal({ idOperador, onCerrar, onCreado }: Props) {
  const [nombre, setNombre] = useState("");
  const [idCategoria, setIdCategoria] = useState("");
  const [precio, setPrecio] = useState("");
  const [esGranel, setEsGranel] = useState(false);
  const [llevaCaducidad, setLlevaCaducidad] = useState(false);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
  }, []);

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      const creado = (await crearMaestro("productos", {
        nombre: nombre.trim(),
        id_categoria: idCategoria === "" ? null : Number(idCategoria),
        precio_vigente: precio.trim() === "" ? null : Number(precio),
        es_granel: esGranel,
        lleva_caducidad: llevaCaducidad,
        id_operador: idOperador,
      })) as ProductoMaestro;
      onCreado(creado);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo crear el producto.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <ModalAdministrable
      titulo="Nuevo producto"
      onCerrar={onCerrar}
      onGuardar={guardar}
      guardando={guardando}
      error={error}
      primariaHabilitada={nombre.trim() !== "" && precio.trim() !== ""}
    >
      <label className={estilos.campo}>
        <span className={estilos.campoEtiqueta}>Nombre <Obligatorio /></span>
        <input
          className={estilos.entrada}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          autoFocus
        />
      </label>
      <label className={estilos.campo}>
        <span className={estilos.campoEtiqueta}>Categoría</span>
        <select
          className={estilos.entrada}
          value={idCategoria}
          onChange={(e) => setIdCategoria(e.target.value)}
        >
          <option value="">(sin categoría)</option>
          {categorias.map((c) => (
            <option key={c.id_categoria} value={c.id_categoria}>
              {c.nombre}
            </option>
          ))}
        </select>
      </label>
      <label className={estilos.campo}>
        <span className={estilos.campoEtiqueta}>Precio base de venta <Obligatorio /></span>
        <input
          className={estilos.entrada}
          inputMode="decimal"
          value={precio}
          onChange={(e) => setPrecio(e.target.value)}
        />
      </label>
      <label className={estilos.campo}>
        <span className={estilos.campoBool}>
          <input type="checkbox" checked={esGranel} onChange={(e) => setEsGranel(e.target.checked)} />
          Se vende a peso (granel)
        </span>
      </label>
      <label className={estilos.campo}>
        <span className={estilos.campoBool}>
          <input
            type="checkbox"
            checked={llevaCaducidad}
            onChange={(e) => setLlevaCaducidad(e.target.checked)}
          />
          Lleva fecha de caducidad
        </span>
      </label>
    </ModalAdministrable>
  );
}
