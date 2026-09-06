/**
 * Pantalla de Venta (T039, T042, T043). Contrato de dirección:
 * .impeccable/surfaces/frontend-src-pantallas-venta-tsx.md — tabla de fila expansible, total
 * anclado sin desplazarse. Registro de Operación (DESIGN.md).
 *
 * Verde Rasero (--color-marca) aparece EXCLUSIVAMENTE en el botón de cobro. Ningún otro
 * elemento de este archivo —ícono, borde, fondo— lo repite (La Regla de la Sola Voz).
 */

import { useEffect, useMemo, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarCategorias, listarProductos, type Categoria, type Producto } from "../servicios/productos";
import { listarSucursales } from "../servicios/sucursales";
import { IconoCategoria } from "../componentes/IconoCategoria";
import { SelectorProducto } from "../componentes/SelectorProducto";
import { CrearProductoModal } from "../componentes/CrearProductoModal";
import { type Turno } from "../servicios/turnos";
import { useRol, type Rol } from "../hooks/useRol";
import {
  type RenglonVentaNuevo,
  type Venta as VentaConfirmada,
  anularVenta,
  generarClaveIdempotencia,
  registrarVenta,
} from "../servicios/ventas";
import { registrarVisita } from "../servicios/clientes";
import { registrarRedencion } from "../servicios/promociones";
import { registrarConsultaNoAtendida } from "../servicios/senales";
import { gramosDesdeKg, RenglonGranel } from "../componentes/RenglonGranel";
import { IdentificarCliente, type ClienteSeleccionado } from "../componentes/IdentificarCliente";
import {
  AplicarPromocionVenta,
  type PromocionSeleccionada,
} from "../componentes/AplicarPromocionVenta";
import { ValorClienteResumen } from "../componentes/ValorClienteResumen";
import { formatearMoneda } from "../utilidades/formato";
import estilos from "./Venta.module.css";

interface RenglonTicket {
  idLocal: string;
  producto: Producto;
  cantidadUnidades?: number;
  cantidadGramos?: number;
  importeEstimado: string;
}

function importeEstimado(precioEfectivo: string, cantidad: number): string {
  const precio = Number(precioEfectivo);
  return (precio * cantidad).toFixed(2);
}

// Papelera: SVG de línea propio (La Regla del Ícono: SVG siempre, nunca emoji), outline sin
// relleno. Quita un renglón del carrito (US9).
function IconoPapelera() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.6 8.2a1 1 0 0 0 1 .8h3.8a1 1 0 0 0 1-.8l.6-8.2M7 7v4M9 7v4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface Props {
  turno: Turno;
  onCerrarTurno: () => void;
  rol: Rol | null;
}

export function Venta({ turno, onCerrarTurno, rol }: Props) {
  // "Ocultar, no deshabilitar" (Principio VI): el atajo "+ Crear producto nuevo" sólo se
  // ofrece a encargado o admin — el mismo patrón se generaliza a todo el sistema.
  const { esEncargadoOMas } = useRol(rol);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [creandoProducto, setCreandoProducto] = useState(false);
  const [renglones, setRenglones] = useState<RenglonTicket[]>([]);
  const [agregando, setAgregando] = useState(false);
  const [idProductoNuevo, setIdProductoNuevo] = useState<number | "">("");
  const [unidades, setUnidades] = useState("");
  const [kg, setKg] = useState("");
  const [claveIdempotencia, setClaveIdempotencia] = useState(generarClaveIdempotencia());
  const [cobrando, setCobrando] = useState(false);
  const [confirmado, setConfirmado] = useState(false);
  const [ventaConfirmada, setVentaConfirmada] = useState<VentaConfirmada | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anulando, setAnulando] = useState(false);
  const [clienteIdentificado, setClienteIdentificado] = useState<ClienteSeleccionado | null>(null);
  const [promocionAplicada, setPromocionAplicada] = useState<PromocionSeleccionada | null>(null);
  const [consultando, setConsultando] = useState(false);
  const [enviandoConsulta, setEnviandoConsulta] = useState(false);
  const [consultaAnotada, setConsultaAnotada] = useState<string | null>(null);
  const [nombreSucursal, setNombreSucursal] = useState<string>("");

  useEffect(() => {
    listarProductos(turno.id_sucursal).then(setProductos);
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
    listarSucursales()
      .then((lista) => {
        const suc = lista.find((s) => s.id_sucursal === turno.id_sucursal);
        setNombreSucursal(suc?.nombre ?? `Sucursal ${turno.id_sucursal}`);
      })
      .catch(() => setNombreSucursal(`Sucursal ${turno.id_sucursal}`));
  }, [turno.id_sucursal]);

  const productoNuevo = productos.find((p) => p.id_producto === idProductoNuevo);

  const nombreCategoria = (id: number | null) =>
    categorias.find((c) => c.id_categoria === id)?.nombre ?? null;

  async function tomarProductoNuevo(idProducto: number) {
    setCreandoProducto(false);
    const lista = await listarProductos(turno.id_sucursal);
    setProductos(lista);
    setIdProductoNuevo(idProducto);
  }

  const total = useMemo(
    () => renglones.reduce((acumulado, r) => acumulado + Number(r.importeEstimado), 0).toFixed(2),
    [renglones],
  );

  function iniciarAgregarFila() {
    setAgregando(true);
    setIdProductoNuevo("");
    setUnidades("");
    setKg("");
  }

  function cancelarFila() {
    setAgregando(false);
  }

  function confirmarFila() {
    if (!productoNuevo) return;

    if (productoNuevo.es_granel) {
      const gramos = gramosDesdeKg(kg);
      if (gramos === null) return;
      setRenglones((prev) => [
        ...prev,
        {
          idLocal: crypto.randomUUID(),
          producto: productoNuevo,
          cantidadGramos: gramos,
          importeEstimado: importeEstimado(productoNuevo.precio_efectivo, gramos / 1000),
        },
      ]);
    } else {
      const cantidad = Number(unidades);
      if (!Number.isFinite(cantidad) || cantidad <= 0) return;
      setRenglones((prev) => [
        ...prev,
        {
          idLocal: crypto.randomUUID(),
          producto: productoNuevo,
          cantidadUnidades: cantidad,
          importeEstimado: importeEstimado(productoNuevo.precio_efectivo, cantidad),
        },
      ]);
    }
    setAgregando(false);
  }

  // US9 (FR-051): quitar un renglón del carrito. Acción de bajo riesgo, sin confirmación —
  // distinta de anular una venta ya cobrada, que conserva su flujo de confirmación.
  function eliminarRenglon(idLocal: string) {
    setRenglones((prev) => prev.filter((r) => r.idLocal !== idLocal));
  }

  // US9 (FR-052): editar la cantidad/peso de un renglón sin re-agregar el producto. El importe
  // del renglón y el total se recalculan al vuelo. Un valor no válido deja el renglón en 0
  // (no lo elimina: eso lo decide el cajero) — igual que US1 trata una cantidad no válida.
  function editarCantidadRenglon(idLocal: string, valorCrudo: string) {
    setRenglones((prev) =>
      prev.map((r) => {
        if (r.idLocal !== idLocal) return r;
        if (r.cantidadGramos !== undefined) {
          const gramos = gramosDesdeKg(valorCrudo) ?? 0;
          return {
            ...r,
            cantidadGramos: gramos,
            importeEstimado: importeEstimado(r.producto.precio_efectivo, gramos / 1000),
          };
        }
        const n = Number(valorCrudo);
        const cantidad = Number.isFinite(n) && n > 0 ? Math.trunc(n) : 0;
        return {
          ...r,
          cantidadUnidades: cantidad,
          importeEstimado: importeEstimado(r.producto.precio_efectivo, cantidad),
        };
      }),
    );
  }

  const hayRenglonValido = renglones.some(
    (r) => (r.cantidadGramos ?? 0) > 0 || (r.cantidadUnidades ?? 0) > 0,
  );

  async function cobrar() {
    if (!hayRenglonValido) return;
    setCobrando(true);
    setError(null);
    try {
      const cuerpo: { clave_idempotencia: string; id_turno: number; renglones: RenglonVentaNuevo[] } = {
        clave_idempotencia: claveIdempotencia,
        id_turno: turno.id_turno,
        renglones: renglones.map((r) => ({
          id_producto: r.producto.id_producto,
          cantidad_unidades: r.cantidadUnidades,
          cantidad_gramos: r.cantidadGramos,
        })),
      };
      const venta = await registrarVenta(cuerpo);
      if (clienteIdentificado) {
        // Identificar cliente NUNCA es parte del cobro (Principio II, FR-003): la venta ya
        // está confirmada: si esta llamada falla, la venta se queda igual, solo se pierde la
        // visita de este módulo (research.md #5 de 002-clientes-fidelizacion).
        registrarVisita(clienteIdentificado.id_cliente, venta.id_venta).catch(() => {
          console.warn("No se pudo registrar la visita del cliente; la venta sí quedó registrada.");
        });
      }
      if (promocionAplicada) {
        // Igual que la visita: la redención de la promoción se registra DESPUÉS de la venta y
        // NUNCA la bloquea (Principio II, 005 FR-005). Si 005 no responde, el cobro ya está hecho.
        registrarRedencion({
          id_venta: venta.id_venta,
          tipo_origen: promocionAplicada.tipo_origen,
          id_cupon: promocionAplicada.id_cupon,
          id_oferta_recompra: promocionAplicada.id_oferta_recompra,
          id_producto: promocionAplicada.id_producto,
        }).catch(() => {
          console.warn("No se pudo registrar la redención; la venta sí quedó registrada.");
        });
      }
      // La confirmación se muestra EN el botón antes de cambiar de pantalla — si
      // ventaConfirmada se fija ya, la pantalla cambia en el mismo render y la animación
      // nunca llega a verse (defecto detectado al verificar visualmente).
      setCobrando(false);
      setConfirmado(true);
      setTimeout(() => {
        setVentaConfirmada(venta);
        setConfirmado(false);
      }, 450);
    } catch (e) {
      setCobrando(false);
      setError(e instanceof ErrorApi ? e.message : "No se pudo registrar la venta.");
    }
  }

  async function marcarConsultaNoAtendida(idProducto: number, nombre: string) {
    // Dos toques, sin salir del flujo de cobro y sin pedir dato alguno del cliente (FR-020).
    // No bloquea la caja: si falla, sólo se pierde la señal, la venta en curso sigue intacta.
    setEnviandoConsulta(true);
    setError(null);
    try {
      await registrarConsultaNoAtendida({ id_producto: idProducto, id_turno: turno.id_turno });
      setConsultando(false);
      setConsultaAnotada(nombre);
      setTimeout(() => setConsultaAnotada(null), 2500);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo anotar la consulta.");
    } finally {
      setEnviandoConsulta(false);
    }
  }

  function nuevaVenta() {
    setVentaConfirmada(null);
    setRenglones([]);
    setClaveIdempotencia(generarClaveIdempotencia());
    setClienteIdentificado(null);
    setPromocionAplicada(null);
  }

  async function anular() {
    if (!ventaConfirmada) return;
    setAnulando(true);
    try {
      await anularVenta(ventaConfirmada.id_venta, { id_operador: turno.id_operador });
      setVentaConfirmada({ ...ventaConfirmada, anulada: true });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo anular la venta.");
    } finally {
      setAnulando(false);
    }
  }

  if (ventaConfirmada) {
    return (
      <div className={estilos.pantallaConfirmada}>
        <div className={estilos.resumenConfirmado}>
          <p>{ventaConfirmada.anulada ? "Venta anulada" : "Venta registrada"}</p>
          <span className={estilos.total}>{formatearMoneda(ventaConfirmada.total)}</span>
          {ventaConfirmada.advertencias.length > 0 && (
            <p className={estilos.advertencia}>
              <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
                <circle cx="5" cy="5" r="4" fill="none" stroke="currentColor" strokeWidth="2" />
              </svg>
              {ventaConfirmada.advertencias[0].mensaje}
            </p>
          )}
          <div className={estilos.accionesConfirmado}>
            <button className={estilos.botonSecundario} onClick={nuevaVenta}>
              Nueva venta
            </button>
            {!ventaConfirmada.anulada && (
              <button className={estilos.botonTexto} onClick={anular} disabled={anulando}>
                {anulando ? "Anulando…" : "Anular esta venta"}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <span>
          {nombreSucursal ? `${nombreSucursal} · ${turno.caja}` : turno.caja}
        </span>
        <div className={estilos.accionesEncabezado}>
          <IdentificarCliente
            seleccionado={clienteIdentificado}
            onSeleccionar={(cliente) => {
              setClienteIdentificado(cliente);
              if (!cliente) setPromocionAplicada(null);
            }}
          />
          {clienteIdentificado && <ValorClienteResumen valor={clienteIdentificado.valor} />}
          {clienteIdentificado && (
            <AplicarPromocionVenta
              idCliente={clienteIdentificado.id_cliente}
              seleccion={promocionAplicada}
              onSeleccionar={setPromocionAplicada}
            />
          )}
          {consultaAnotada ? (
            <span className={estilos.senalAnotada}>Consulta anotada: {consultaAnotada}</span>
          ) : consultando ? (
            <select
              className={estilos.selectProducto}
              aria-label="Producto consultado y no atendido"
              defaultValue=""
              autoFocus
              disabled={enviandoConsulta}
              onChange={(e) => {
                const id = Number(e.target.value);
                const p = productos.find((x) => x.id_producto === id);
                if (p) marcarConsultaNoAtendida(p.id_producto, p.nombre);
              }}
              onBlur={() => setConsultando(false)}
            >
              <option value="" disabled>
                ¿Qué producto pidió?
              </option>
              {productos.map((p) => (
                <option key={p.id_producto} value={p.id_producto}>
                  {p.nombre}
                </option>
              ))}
            </select>
          ) : (
            <button className={estilos.botonTexto} onClick={() => setConsultando(true)}>
              Consulta no atendida
            </button>
          )}
          <button className={estilos.botonTexto} onClick={onCerrarTurno}>
            Cerrar turno
          </button>
        </div>
      </div>

      <div className={estilos.cuerpo}>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Producto</th>
              <th className={estilos.num}>Cantidad</th>
              <th className={estilos.num}>Precio</th>
              <th className={estilos.num}>Importe</th>
              <th aria-label="Quitar" />
            </tr>
          </thead>
          <tbody>
            {renglones.map((r) => (
              <tr key={r.idLocal}>
                <td>
                  <span className={estilos.celdaProducto}>
                    <IconoCategoria nombreCategoria={nombreCategoria(r.producto.id_categoria)} />
                    {r.producto.nombre}
                  </span>
                </td>
                <td className={estilos.num}>
                  <span className={estilos.cantidadEditable}>
                    <input
                      className={estilos.inputCantidadLinea}
                      type="number"
                      min={0}
                      step={r.cantidadGramos !== undefined ? 0.001 : 1}
                      value={
                        r.cantidadGramos !== undefined
                          ? r.cantidadGramos / 1000
                          : r.cantidadUnidades ?? 0
                      }
                      onChange={(e) => editarCantidadRenglon(r.idLocal, e.target.value)}
                      aria-label={`Cantidad de ${r.producto.nombre}`}
                    />
                    {r.cantidadGramos !== undefined ? "kg" : "u"}
                  </span>
                </td>
                <td className={estilos.num}>{formatearMoneda(r.producto.precio_efectivo)}</td>
                <td className={estilos.num}>{formatearMoneda(r.importeEstimado)}</td>
                <td className={estilos.num}>
                  <button
                    type="button"
                    className={estilos.quitarRenglon}
                    onClick={() => eliminarRenglon(r.idLocal)}
                    aria-label={`Quitar ${r.producto.nombre} del carrito`}
                  >
                    <IconoPapelera />
                  </button>
                </td>
              </tr>
            ))}

            {agregando ? (
              <tr className={estilos.filaExpandida}>
                <td colSpan={5}>
                  <div className={estilos.formularioFila}>
                    <div className={estilos.campoFila}>
                      <label>Producto</label>
                      <SelectorProducto
                        idSucursal={turno.id_sucursal}
                        autoAbrir
                        seleccionado={productoNuevo ?? null}
                        onSeleccionar={(p) => setIdProductoNuevo(p?.id_producto ?? "")}
                      />
                      {esEncargadoOMas() && (
                        <button
                          type="button"
                          className={estilos.botonTexto}
                          onClick={() => setCreandoProducto(true)}
                        >
                          + Crear producto nuevo
                        </button>
                      )}
                    </div>

                    {productoNuevo?.es_granel ? (
                      <RenglonGranel kg={kg} onCambiarKg={setKg} />
                    ) : (
                      <div className={estilos.campoFila}>
                        <label htmlFor="cantidad-unidades">Cantidad</label>
                        <input
                          id="cantidad-unidades"
                          className={estilos.inputCantidad}
                          type="number"
                          min={1}
                          value={unidades}
                          onChange={(e) => setUnidades(e.target.value)}
                        />
                      </div>
                    )}

                    <button className={estilos.botonSecundario} type="button" onClick={confirmarFila}>
                      Agregar
                    </button>
                    <button className={estilos.botonTexto} type="button" onClick={cancelarFila}>
                      Cancelar
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr className={estilos.filaAgregar} onClick={iniciarAgregarFila}>
                <td colSpan={5}>+ Agregar producto</td>
              </tr>
            )}
          </tbody>
        </table>

        {error && <p className={estilos.advertencia}>{error}</p>}
      </div>

      {creandoProducto && (
        <CrearProductoModal
          idOperador={turno.id_operador}
          onCerrar={() => setCreandoProducto(false)}
          onCreado={(p) => tomarProductoNuevo(p.id_producto)}
        />
      )}

      <div className={estilos.pie}>
        <span>
          <span className={estilos.totalEtiqueta}>Total</span>
          <span className={estilos.total}>{formatearMoneda(total)}</span>
        </span>
        <button
          className={`${estilos.botonCobrar} ${confirmado ? estilos.confirmado : ""}`}
          onClick={cobrar}
          disabled={cobrando || confirmado || !hayRenglonValido}
        >
          {cobrando ? "Cobrando…" : confirmado ? "¡Cobrado!" : "Cobrar"}
        </button>
      </div>
    </div>
  );
}
