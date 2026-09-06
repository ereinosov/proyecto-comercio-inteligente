/**
 * Pantalla de Administración de datos maestros (Parte 3). Registro de ANÁLISIS (radio 6px,
 * Source Serif 4): crear o desactivar un maestro es una decisión gerencial, nunca una
 * operación de caja.
 *
 * Segmentado de texto (mismo patrón que Pronostico.tsx / Promociones.tsx) para elegir entre
 * Sucursales, Productos, Categorías, Zonas de exhibición y Medios de pago. Cada vista es una
 * lista paginada (Paginador.tsx) con "+ Nuevo …" que abre el ModalAdministrable único, y cada
 * fila con editar (mismo modal precargado) y desactivar.
 *
 * Permisos: crear / editar / desactivar cualquiera de estas cinco entidades requiere que el
 * operador del turno sea encargado (`es_encargado`). Si no lo es, la pantalla es de sólo
 * lectura y esas acciones no se ofrecen.
 *
 * Listas vacías -> La Regla del Hueco que Enseña. Mientras cargan -> La Regla del Pulso.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { EstadoVacio } from "../componentes/EstadoVacio";
import { EsqueletoLista } from "../componentes/Esqueleto";
import { IconoCategoria } from "../componentes/IconoCategoria";
import { ModalAdministrable } from "../componentes/ModalAdministrable";
import { Obligatorio } from "../componentes/Obligatorio";
import { Buscador } from "../componentes/Buscador";
import { Paginador, TAMANO_PAGINA } from "../componentes/Paginador";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  crearMaestro,
  dependenciasMaestro,
  editarMaestro,
  fijarActivoMaestro,
  idDeFila,
  listarMaestros,
  type Dependencia,
  type EntidadMaestra,
  type FilaMaestra,
} from "../servicios/administracion";
import { listarCategorias, type Categoria } from "../servicios/productos";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import { etiquetaMedioPago, formatearMoneda } from "../utilidades/formato";
import estilos from "./Administracion.module.css";

interface Props {
  idOperador: number;
  esEncargado: boolean;
}

type TipoCampo = "texto" | "numero" | "bool" | "categoria" | "sucursal";

interface Campo {
  clave: string;
  etiqueta: string;
  tipo: TipoCampo;
  opcional?: boolean;
}

// Buscador por nombre sólo en las vistas que pueden crecer sin techo. Se EXCLUYE
// deliberadamente "zonas" (una tienda tiene un puñado de zonas de exhibición) y "medios"
// (los medios de pago son una lista corta y estable) — ahí un buscador sería ruido.
const ENTIDADES_CON_BUSCADOR: ReadonlySet<EntidadMaestra> = new Set([
  "sucursales",
  "productos",
  "categorias",
]);

// `nuevo`: la frase completa del botón de creación, con la concordancia de género correcta
// ("Nueva sucursal", "Nuevo producto"). No se deriva de `singular` para no arrastrar el bug
// de "+ Nuevo sucursal".
const VISTAS: {
  valor: EntidadMaestra;
  etiqueta: string;
  singular: string;
  nuevo: string;
  campos: Campo[];
}[] = [
  {
    valor: "sucursales",
    etiqueta: "Sucursales",
    singular: "sucursal",
    nuevo: "Nueva sucursal",
    campos: [
      { clave: "nombre", etiqueta: "Nombre", tipo: "texto" },
      { clave: "zona_horaria", etiqueta: "Zona horaria (IANA, p. ej. America/Guayaquil)", tipo: "texto" },
    ],
  },
  {
    valor: "productos",
    etiqueta: "Productos",
    singular: "producto",
    nuevo: "Nuevo producto",
    campos: [
      { clave: "nombre", etiqueta: "Nombre", tipo: "texto" },
      { clave: "id_categoria", etiqueta: "Categoría", tipo: "categoria", opcional: true },
      { clave: "precio_vigente", etiqueta: "Precio base de venta", tipo: "numero" },
      { clave: "es_granel", etiqueta: "Se vende a peso (granel)", tipo: "bool" },
      { clave: "lleva_caducidad", etiqueta: "Lleva fecha de caducidad", tipo: "bool" },
    ],
  },
  {
    valor: "categorias",
    etiqueta: "Categorías",
    singular: "categoría",
    nuevo: "Nueva categoría",
    campos: [
      { clave: "nombre", etiqueta: "Nombre", tipo: "texto" },
      {
        clave: "dias_umbral_inmovilizado",
        etiqueta: "Umbral de días de capital inmovilizado (vacío = umbral global)",
        tipo: "numero",
        opcional: true,
      },
    ],
  },
  {
    valor: "zonas",
    etiqueta: "Zonas de exhibición",
    singular: "zona de exhibición",
    nuevo: "Nueva zona de exhibición",
    campos: [
      { clave: "id_sucursal", etiqueta: "Sucursal", tipo: "sucursal" },
      { clave: "nombre", etiqueta: "Nombre", tipo: "texto" },
      { clave: "grado_privilegio", etiqueta: "Grado de privilegio (mayor = mejor ubicación)", tipo: "numero" },
    ],
  },
  {
    valor: "medios",
    etiqueta: "Medios de pago",
    singular: "medio de pago",
    nuevo: "Nuevo medio de pago",
    campos: [
      { clave: "nombre", etiqueta: "Nombre", tipo: "texto" },
      { clave: "requiere_terminal", etiqueta: "Requiere terminal de pago", tipo: "bool" },
      { clave: "admite_tokenizacion", etiqueta: "Admite tokenización de tarjeta", tipo: "bool" },
    ],
  },
];

type ValoresForm = Record<string, string | boolean>;

function valoresIniciales(campos: Campo[], fila?: FilaMaestra): ValoresForm {
  const v: ValoresForm = {};
  for (const c of campos) {
    const actual = fila ? (fila as unknown as Record<string, unknown>)[c.clave] : undefined;
    if (c.tipo === "bool") v[c.clave] = Boolean(actual);
    else v[c.clave] = actual === null || actual === undefined ? "" : String(actual);
  }
  return v;
}

function payload(campos: Campo[], valores: ValoresForm, idOperador: number): Record<string, unknown> {
  const cuerpo: Record<string, unknown> = { id_operador: idOperador };
  for (const c of campos) {
    const bruto = valores[c.clave];
    if (c.tipo === "bool") {
      cuerpo[c.clave] = Boolean(bruto);
    } else if (c.tipo === "numero" || c.tipo === "categoria" || c.tipo === "sucursal") {
      const s = String(bruto).trim();
      cuerpo[c.clave] = s === "" ? null : Number(s);
    } else {
      cuerpo[c.clave] = String(bruto).trim();
    }
  }
  return cuerpo;
}

export function Administracion({ idOperador, esEncargado }: Props) {
  const [entidad, setEntidad] = useState<EntidadMaestra>("sucursales");
  const vista = VISTAS.find((v) => v.valor === entidad)!;

  const [filas, setFilas] = useState<FilaMaestra[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const conBuscador = ENTIDADES_CON_BUSCADOR.has(entidad);
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setBusqueda(texto), 200);
    return () => clearTimeout(t);
  }, [texto]);

  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);

  const [modal, setModal] = useState<{ fila?: FilaMaestra } | null>(null);
  const [valores, setValores] = useState<ValoresForm>({});
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState<string | null>(null);

  const [aDesactivar, setADesactivar] = useState<{
    fila: FilaMaestra;
    deps: Dependencia[] | null;
  } | null>(null);
  const [desactivando, setDesactivando] = useState(false);

  const nombreCategoria = useCallback(
    (id: number | null | undefined) =>
      categorias.find((c) => c.id_categoria === id)?.nombre ?? null,
    [categorias],
  );
  const nombreSucursal = useCallback(
    (id: number) => sucursales.find((s) => s.id_sucursal === id)?.nombre ?? `Sucursal ${id}`,
    [sucursales],
  );

  const recargar = useCallback(() => {
    setCargando(true);
    setError(null);
    listarMaestros(entidad, {
      pagina,
      tamanoPagina: TAMANO_PAGINA,
      incluirInactivos,
      busqueda: conBuscador ? busqueda : undefined,
    })
      .then(({ items, total: t }) => {
        setFilas(items);
        setTotal(t ?? items.length);
      })
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el listado."),
      )
      .finally(() => setCargando(false));
  }, [entidad, pagina, incluirInactivos, conBuscador, busqueda]);

  useEffect(recargar, [recargar]);

  useEffect(() => {
    listarSucursales().then(setSucursales).catch(() => setSucursales([]));
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
  }, []);

  useEffect(() => {
    setPagina(1);
  }, [entidad, incluirInactivos, busqueda]);

  // Al cambiar de vista, la búsqueda de la vista anterior no aplica.
  useEffect(() => {
    setTexto("");
    setBusqueda("");
  }, [entidad]);

  const totalPaginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

  function abrirModal(fila?: FilaMaestra) {
    setValores(valoresIniciales(vista.campos, fila));
    setErrorModal(null);
    setModal({ fila });
  }

  async function guardar() {
    if (!modal) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      const cuerpo = payload(vista.campos, valores, idOperador);
      if (modal.fila) {
        await editarMaestro(entidad, idDeFila(entidad, modal.fila), cuerpo);
      } else {
        await crearMaestro(entidad, cuerpo);
      }
      setModal(null);
      recargar();
    } catch (e) {
      setErrorModal(e instanceof ErrorApi ? e.message : "No se pudo guardar.");
    } finally {
      setGuardando(false);
    }
  }

  async function pedirDesactivar(fila: FilaMaestra) {
    setADesactivar({ fila, deps: null });
    try {
      const r = await dependenciasMaestro(entidad, idDeFila(entidad, fila));
      setADesactivar({ fila, deps: r.dependencias });
    } catch {
      setADesactivar({ fila, deps: [] });
    }
  }

  async function confirmarDesactivar() {
    if (!aDesactivar) return;
    setDesactivando(true);
    try {
      await fijarActivoMaestro(entidad, idDeFila(entidad, aDesactivar.fila), {
        activo: false,
        id_operador: idOperador,
      });
      setADesactivar(null);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo desactivar.");
      setADesactivar(null);
    } finally {
      setDesactivando(false);
    }
  }

  async function reactivar(fila: FilaMaestra) {
    try {
      await fijarActivoMaestro(entidad, idDeFila(entidad, fila), {
        activo: true,
        id_operador: idOperador,
      });
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo reactivar.");
    }
  }

  const columnas = useMemo(() => descripcionFila(entidad), [entidad]);

  // Un campo obligatorio (no `opcional`, no booleano —los booleanos siempre tienen valor—)
  // vacío deshabilita la acción primaria del modal. Mismo patrón que Cliente
  // (`primariaHabilitada={form.nombre.trim() !== ""}`), extendido a los cinco maestros.
  const obligatoriosLlenos = vista.campos.every(
    (c) => c.opcional || c.tipo === "bool" || String(valores[c.clave] ?? "").trim() !== "",
  );

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h1 className={estilos.titulo}>Administración</h1>
        <nav className={estilos.segmentado}>
          {VISTAS.map((v) => (
            <button
              key={v.valor}
              className={entidad === v.valor ? estilos.segActivo : estilos.segInactivo}
              onClick={() => setEntidad(v.valor)}
            >
              {v.etiqueta}
            </button>
          ))}
        </nav>
      </div>

      {conBuscador && (
        <div className={estilos.barraBuscador}>
          <Buscador
            valor={texto}
            onCambiar={setTexto}
            placeholder={`Buscar ${vista.singular} por nombre…`}
          />
        </div>
      )}

      <div className={estilos.barra}>
        <label className={estilos.filtroInactivos}>
          <input
            type="checkbox"
            checked={incluirInactivos}
            onChange={(e) => setIncluirInactivos(e.target.checked)}
          />
          Mostrar desactivados
        </label>
        {esEncargado ? (
          <button className={estilos.botonNuevo} onClick={() => abrirModal()}>
            + {vista.nuevo}
          </button>
        ) : (
          <span className={estilos.soloLectura}>
            Sólo un encargado puede crear o modificar estos datos.
          </span>
        )}
      </div>

      {error && <p className={estilos.error}>{error}</p>}

      {cargando ? (
        <EsqueletoLista filas={6} registro="analisis" altoFila={48} />
      ) : filas.length === 0 ? (
        <EstadoVacio
          glifo="lista"
          titulo={
            conBuscador && busqueda.trim()
              ? `Sin resultados para «${busqueda.trim()}»`
              : `Todavía no hay ${vista.etiqueta.toLowerCase()}`
          }
          descripcion={
            conBuscador && busqueda.trim()
              ? "Prueba con otra parte del nombre; la búsqueda ignora mayúsculas."
              : `Aquí aparecerá cada ${vista.singular} del sistema, con su estado y las acciones para editarlo o desactivarlo. Usa «+ ${vista.nuevo}» para crear el primero.`
          }
        />
      ) : (
        <div className={estilos.tablaContenedor}>
          <table className={estilos.tabla}>
            <thead>
              <tr>
                {columnas.map((c, i) => (
                  <th key={`${entidad}-col-${i}`}>{c}</th>
                ))}
                <th>Estado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {filas.map((fila) => (
                <tr key={idDeFila(entidad, fila)} className={fila.activo ? "" : estilos.filaInactiva}>
                  {celdasFila(entidad, fila, { nombreCategoria, nombreSucursal }).map((celda, i) => (
                    <td key={i}>{celda}</td>
                  ))}
                  <td>{fila.activo ? "Activo" : "Desactivado"}</td>
                  <td className={estilos.acciones}>
                    {esEncargado && fila.activo && (
                      <>
                        <button className={estilos.accion} onClick={() => abrirModal(fila)}>
                          Editar
                        </button>
                        <button className={estilos.accion} onClick={() => pedirDesactivar(fila)}>
                          Desactivar
                        </button>
                      </>
                    )}
                    {esEncargado && !fila.activo && (
                      <button className={estilos.accion} onClick={() => reactivar(fila)}>
                        Reactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!cargando && filas.length > 0 && (
        <Paginador pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />
      )}

      {modal && (
        <ModalAdministrable
          titulo={`${modal.fila ? "Editar" : "Nuevo"} ${vista.singular}`}
          onCerrar={() => setModal(null)}
          onGuardar={guardar}
          guardando={guardando}
          error={errorModal}
          primariaHabilitada={obligatoriosLlenos}
        >
          {vista.campos.map((c) => (
            <label key={c.clave} className={estilos.campo}>
              {c.tipo === "bool" ? (
                <span className={estilos.campoBool}>
                  <input
                    type="checkbox"
                    checked={Boolean(valores[c.clave])}
                    onChange={(e) => setValores((v) => ({ ...v, [c.clave]: e.target.checked }))}
                  />
                  {c.etiqueta}
                </span>
              ) : (
                <>
                  <span className={estilos.campoEtiqueta}>
                    {c.etiqueta} {!c.opcional && <Obligatorio />}
                  </span>
                  {c.tipo === "categoria" ? (
                    <select
                      className={estilos.entrada}
                      value={String(valores[c.clave] ?? "")}
                      onChange={(e) => setValores((v) => ({ ...v, [c.clave]: e.target.value }))}
                    >
                      <option value="">(sin categoría)</option>
                      {categorias.map((cat) => (
                        <option key={cat.id_categoria} value={cat.id_categoria}>
                          {cat.nombre}
                        </option>
                      ))}
                    </select>
                  ) : c.tipo === "sucursal" ? (
                    <select
                      className={estilos.entrada}
                      value={String(valores[c.clave] ?? "")}
                      onChange={(e) => setValores((v) => ({ ...v, [c.clave]: e.target.value }))}
                    >
                      <option value="" disabled>
                        Elige una sucursal
                      </option>
                      {sucursales.map((s) => (
                        <option key={s.id_sucursal} value={s.id_sucursal}>
                          {s.nombre}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className={estilos.entrada}
                      inputMode={c.tipo === "numero" ? "decimal" : "text"}
                      value={String(valores[c.clave] ?? "")}
                      onChange={(e) => setValores((v) => ({ ...v, [c.clave]: e.target.value }))}
                    />
                  )}
                </>
              )}
            </label>
          ))}
        </ModalAdministrable>
      )}

      {aDesactivar && (
        <ModalAdministrable
          titulo={`Desactivar ${vista.singular}`}
          onCerrar={() => setADesactivar(null)}
          onGuardar={confirmarDesactivar}
          guardando={desactivando}
          etiquetaPrimaria="Desactivar de todas formas"
          primariaHabilitada={aDesactivar.deps !== null}
        >
          {aDesactivar.deps === null ? (
            <p className={estilos.textoModal}>Comprobando dependencias…</p>
          ) : aDesactivar.deps.length === 0 ? (
            <p className={estilos.textoModal}>
              Nada más en el sistema depende de este {vista.singular}. Desactivarlo lo oculta de
              los selectores; su historial se conserva.
            </p>
          ) : (
            <>
              <p className={estilos.textoModal}>
                Desactivar este {vista.singular} lo oculta del catálogo y de los selectores, pero{" "}
                <strong>conserva todo su historial</strong>. Hoy tiene:
              </p>
              <ul className={estilos.listaDeps}>
                {aDesactivar.deps.map((d, i) => (
                  <li key={`dep-${i}`}>
                    <strong>{d.conteo}</strong> {d.descripcion}
                  </li>
                ))}
              </ul>
            </>
          )}
        </ModalAdministrable>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------

function descripcionFila(entidad: EntidadMaestra): string[] {
  switch (entidad) {
    case "sucursales":
      return ["Nombre", "Zona horaria"];
    case "categorias":
      return ["Nombre", "Umbral inmovilizado (días)"];
    case "productos":
      return ["Producto", "Categoría", "Precio base", "Granel"];
    case "zonas":
      return ["Sucursal", "Nombre", "Privilegio"];
    case "medios":
      return ["Nombre", "Requiere terminal", "Tokenización"];
  }
}

function celdasFila(
  entidad: EntidadMaestra,
  fila: FilaMaestra,
  ayuda: { nombreCategoria: (id: number | null | undefined) => string | null; nombreSucursal: (id: number) => string },
): ReactNode[] {
  const f = fila as unknown as Record<string, unknown>;
  switch (entidad) {
    case "sucursales":
      return [String(f.nombre), String(f.zona_horaria)];
    case "categorias":
      return [String(f.nombre), f.dias_umbral_inmovilizado == null ? "— (global)" : String(f.dias_umbral_inmovilizado)];
    case "productos": {
      const nombreCat = ayuda.nombreCategoria(f.id_categoria as number | null);
      return [
        <span key="p" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <IconoCategoria nombreCategoria={nombreCat} />
          {String(f.nombre)}
        </span>,
        nombreCat ?? "(sin categoría)",
        formatearMoneda(f.precio_vigente as string | number),
        f.es_granel ? "Sí" : "No",
      ];
    }
    case "zonas":
      return [ayuda.nombreSucursal(f.id_sucursal as number), String(f.nombre), String(f.grado_privilegio)];
    case "medios":
      return [
        etiquetaMedioPago(String(f.nombre)),
        f.requiere_terminal ? "Sí" : "No",
        f.admite_tokenizacion ? "Sí" : "No",
      ];
  }
}
