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
import { CrearProductoModal } from "../componentes/CrearProductoModal";
import { type Turno } from "../servicios/turnos";
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

interface Props {
  turno: Turno;
  onCerrarTurno: () => void;
  esEncargado: boolean;
}

export function Venta({ turno, onCerrarTurno, esEncargado }: Props) {
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
    setIdProductoNuevo(productos[0]?.id_producto ?? "");
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

  async function cobrar() {
    if (renglones.length === 0) return;
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
                  {r.cantidadGramos !== undefined
                    ? `${(r.cantidadGramos / 1000).toFixed(3)} kg`
                    : `${r.cantidadUnidades} u`}
                </td>
                <td className={estilos.num}>{formatearMoneda(r.producto.precio_efectivo)}</td>
                <td className={estilos.num}>{formatearMoneda(r.importeEstimado)}</td>
              </tr>
            ))}

            {agregando ? (
              <tr className={estilos.filaExpandida}>
                <td colSpan={4}>
                  <div className={estilos.formularioFila}>
                    <div className={estilos.campoFila}>
                      <label htmlFor="producto-nuevo">Producto</label>
                      <select
                        id="producto-nuevo"
                        className={estilos.selectProducto}
                        value={idProductoNuevo}
                        onChange={(e) => setIdProductoNuevo(Number(e.target.value))}
                        autoFocus
                      >
                        {productos.map((p) => (
                          <option key={p.id_producto} value={p.id_producto}>
                            {p.nombre}
                          </option>
                        ))}
                      </select>
                      {esEncargado && (
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
                <td colSpan={4}>+ Agregar producto</td>
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
          disabled={cobrando || confirmado || renglones.length === 0}
        >
          {cobrando ? "Cobrando…" : confirmado ? "¡Cobrado!" : "Cobrar"}
        </button>
      </div>
    </div>
  );
}
