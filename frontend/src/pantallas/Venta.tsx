/**
 * Pantalla de Venta (T039, T042, T043). Contrato de dirección:
 * .impeccable/surfaces/frontend-src-pantallas-venta-tsx.md — tabla de fila expansible, total
 * anclado sin desplazarse. Registro de Operación (DESIGN.md).
 *
 * Verde Rasero (--color-marca) aparece EXCLUSIVAMENTE en el botón de cobro. Ningún otro
 * elemento de este archivo —ícono, borde, fondo— lo repite (La Regla de la Sola Voz).
 *
 * v1.5.0 (ronda de evolución visual): encabezado con `EncabezadoPantalla` (antes: sólo una
 * línea de contexto en Tinta Suave, sin <h1>), botones vía el componente `Boton`, total en
 * `--texto-display`, cantidad vía `Campo`, estado de ticket vacío que enseña. Sin cambios de
 * lógica de cobro, idempotencia, anulación, visita de cliente ni redención de promoción.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { listarCategorias, listarProductos, type Categoria, type Producto } from "../servicios/productos";
import { listarExistencias } from "../servicios/inventario";
import { ImagenProducto } from "../componentes/ImagenProducto";
import { SelectorProducto } from "../componentes/SelectorProducto";
import { CrearProductoModal } from "../componentes/CrearProductoModal";
import { Boton } from "../componentes/Boton";
import { Campo } from "../componentes/Campo";
import { CatalogoProductos } from "../componentes/CatalogoProductos";
import { EncabezadoPantalla } from "../componentes/EncabezadoPantalla";
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
import {
  type Factura,
  emitirNotaCredito,
  generarFactura,
} from "../servicios/facturas";
import { FacturaSimulada } from "../componentes/FacturaSimulada";
import { DocumentoImprimible } from "../componentes/DocumentoImprimible";
import { gramosDesdeKg, RenglonGranel } from "../componentes/RenglonGranel";
import { IdentificarCliente, type ClienteSeleccionado } from "../componentes/IdentificarCliente";
import {
  AplicarPromocionVenta,
  type PromocionSeleccionada,
} from "../componentes/AplicarPromocionVenta";
import { ValorClienteResumen } from "../componentes/ValorClienteResumen";
import { EstadoVacio } from "../componentes/EstadoVacio";
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
  // US14: existencia total por producto en la sucursal del turno. Una sola consulta, la comparten
  // el catálogo y el buscador; se refresca al cobrar (el stock cambió).
  const [existencias, setExistencias] = useState<Map<number, number>>(new Map());
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
  // 009: factura SIMULADA. Se genera DESPUÉS del cobro, nunca lo bloquea (Principio II). Si la
  // generación falla, la venta ya está hecha: se ofrece "Generar factura" para reintentar.
  const [factura, setFactura] = useState<Factura | null>(null);
  const [notaCredito, setNotaCredito] = useState<Factura | null>(null);
  const [facturaFallo, setFacturaFallo] = useState(false);
  const [generandoFactura, setGenerandoFactura] = useState(false);

  function pedirFactura(idVenta: number) {
    setGenerandoFactura(true);
    setFacturaFallo(false);
    generarFactura(idVenta)
      .then((f) => setFactura(f))
      .catch(() => setFacturaFallo(true))
      .finally(() => setGenerandoFactura(false));
  }

  const recargarExistencias = useCallback(() => {
    listarExistencias(turno.id_sucursal)
      .then((filas) => setExistencias(new Map(filas.map((f) => [f.id_producto, f.cantidad]))))
      .catch(() => setExistencias(new Map()));
  }, [turno.id_sucursal]);

  useEffect(() => {
    listarProductos(turno.id_sucursal).then(setProductos);
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
    recargarExistencias();
  }, [turno.id_sucursal, recargarExistencias]);

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

  // Única lógica de "agregar un renglón al ticket" del sistema. La usan los DOS caminos: el
  // formulario de fila expansible (buscador `SelectorProducto`) y el catálogo en grid (US12).
  // Un mismo producto, cantidad y cálculo de importe, no importa por dónde se agregó.
  function agregarRenglon(producto: Producto, cantidad: { unidades: number } | { gramos: number }) {
    setRenglones((prev) => {
      // Un producto por unidad que ya está en el ticket suma a la cantidad de esa fila, no
      // crea una segunda. A granel siempre es fila aparte: cada pesada es distinta.
      if ("unidades" in cantidad) {
        const i = prev.findIndex(
          (r) => r.producto.id_producto === producto.id_producto && r.cantidadUnidades !== undefined,
        );
        if (i !== -1) {
          const nueva = (prev[i].cantidadUnidades ?? 0) + cantidad.unidades;
          const copia = [...prev];
          copia[i] = {
            ...prev[i],
            cantidadUnidades: nueva,
            importeEstimado: importeEstimado(producto.precio_efectivo, nueva),
          };
          return copia;
        }
        return [
          ...prev,
          {
            idLocal: crypto.randomUUID(),
            producto,
            cantidadUnidades: cantidad.unidades,
            importeEstimado: importeEstimado(producto.precio_efectivo, cantidad.unidades),
          },
        ];
      }
      return [
        ...prev,
        {
          idLocal: crypto.randomUUID(),
          producto,
          cantidadGramos: cantidad.gramos,
          importeEstimado: importeEstimado(producto.precio_efectivo, cantidad.gramos / 1000),
        },
      ];
    });
  }

  function confirmarFila() {
    if (!productoNuevo) return;

    if (productoNuevo.es_granel) {
      const gramos = gramosDesdeKg(kg);
      if (gramos === null) return;
      agregarRenglon(productoNuevo, { gramos });
    } else {
      const cantidad = Number(unidades);
      if (!Number.isFinite(cantidad) || cantidad <= 0) return;
      agregarRenglon(productoNuevo, { unidades: cantidad });
    }
    setAgregando(false);
  }

  // US12: click en una tarjeta del catálogo. Un producto por unidad se agrega directo (cantidad
  // 1); uno a granel abre el formulario de fila con el producto ya elegido para capturar el peso
  // en la báscula — mismo flujo exacto que el buscador, no una segunda lógica.
  function agregarDesdeCatalogo(producto: Producto) {
    if (producto.es_granel) {
      setAgregando(true);
      setIdProductoNuevo(producto.id_producto);
      setUnidades("");
      setKg("");
      return;
    }
    agregarRenglon(producto, { unidades: 1 });
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
      // 009: la factura simulada se pide aquí, DESPUÉS de que la venta ya está confirmada, con el
      // mismo patrón sin bloquear que la visita y la redención de arriba.
      pedirFactura(venta.id_venta);
      setCobrando(false);
      setConfirmado(true);
      recargarExistencias(); // US14: el stock cambió con esta venta.
      setTimeout(() => {
        setVentaConfirmada(venta);
        setConfirmado(false);
      }, 450);
    } catch (e) {
      setCobrando(false);
      // Incluye `existencia_insuficiente` (409, Corrección 2026-09-07): el backend ahora
      // rechaza en vez de completar con advertencia `saldo_negativo`. El mensaje del dominio
      // ya trae la acción correctiva ("Ajusta la cantidad o haz un conteo físico…").
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
    setFactura(null);
    setNotaCredito(null);
    setFacturaFallo(false);
  }

  async function anular() {
    if (!ventaConfirmada) return;
    setAnulando(true);
    try {
      await anularVenta(ventaConfirmada.id_venta);
      setVentaConfirmada({ ...ventaConfirmada, anulada: true });
      recargarExistencias(); // US14: la anulación repone el stock, igual que cobrar lo descuenta.
      // 009: si la venta tenía factura, se emite la nota de crédito que la revierte. No bloquea
      // la anulación (Principio II): si falla, la venta ya quedó anulada en 001.
      emitirNotaCredito(ventaConfirmada.id_venta)
        .then((nc) => nc && setNotaCredito(nc))
        .catch(() => undefined);
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
          <p className={estilos.etiquetaConfirmado}>
            {ventaConfirmada.anulada ? "Venta anulada" : "Venta registrada"}
          </p>
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
            <Boton variante="primaria" onClick={nuevaVenta}>
              Nueva venta
            </Boton>
            {!ventaConfirmada.anulada && (
              <Boton variante="neutra" onClick={anular} disabled={anulando}>
                {anulando ? "Anulando…" : "Anular esta venta"}
              </Boton>
            )}
          </div>
        </div>

        <div className={estilos.bloqueFactura}>
          {factura ? (
            <>
              <FacturaSimulada factura={factura} />
              {notaCredito && <FacturaSimulada factura={notaCredito} />}
              <DocumentoImprimible factura={factura} notaCredito={notaCredito} />
            </>
          ) : generandoFactura ? (
            <p className={estilos.notaFactura}>Generando la factura simulada…</p>
          ) : facturaFallo ? (
            <div className={estilos.notaFactura}>
              <p>No se pudo generar la factura simulada. La venta sí quedó registrada.</p>
              <Boton
                variante="secundaria"
                tamano="sm"
                onClick={() => pedirFactura(ventaConfirmada.id_venta)}
              >
                Generar factura
              </Boton>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={estilos.pantalla}>
      <EncabezadoPantalla
        titulo="Venta"
        registro="operacion"
        acciones={
          <>
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
              <Boton variante="secundaria" tamano="sm" onClick={() => setConsultando(true)}>
                Consulta no atendida
              </Boton>
            )}
            <Boton variante="secundaria" tamano="sm" onClick={onCerrarTurno}>
              Cerrar turno
            </Boton>
          </>
        }
      />

      <div className={estilos.cuerpoDoble}>
        <section className={estilos.columnaCatalogo} aria-label="Catálogo de productos">
          <h2 className={estilos.tituloColumna}>Productos</h2>
          <CatalogoProductos
            productos={productos}
            categorias={categorias}
            onAgregar={agregarDesdeCatalogo}
            existencias={existencias}
            idSucursal={turno.id_sucursal}
          />
        </section>

        <section className={estilos.columnaTicket} aria-label="Ticket de venta">
          <h2 className={estilos.tituloColumna}>Ticket de venta</h2>
          <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Producto</th>
              <th className={`${estilos.num} ${estilos.thCantidad}`}>Cantidad</th>
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
                    <ImagenProducto
                      urlImagen={r.producto.url_imagen}
                      nombreCategoria={nombreCategoria(r.producto.id_categoria)}
                      nombreProducto={r.producto.nombre}
                      tamano={28}
                    />
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
                    <span className={estilos.unidad}>
                      {r.cantidadGramos !== undefined ? "kg" : "u"}
                    </span>
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
                    <div className={`${estilos.campoFila} ${estilos.campoProducto}`}>
                      <span className={estilos.etiquetaCampo}>Producto</span>
                      <span className={estilos.slotProducto}>
                        <SelectorProducto
                          idSucursal={turno.id_sucursal}
                          autoAbrir
                          seleccionado={productoNuevo ?? null}
                          onSeleccionar={(p) => setIdProductoNuevo(p?.id_producto ?? "")}
                          existencias={existencias}
                        />
                      </span>
                    </div>

                    {productoNuevo?.es_granel ? (
                      <RenglonGranel kg={kg} onCambiarKg={setKg} />
                    ) : (
                      <Campo etiqueta="Cantidad" htmlFor="cantidad-unidades" numerico>
                        <input
                          id="cantidad-unidades"
                          type="number"
                          min={1}
                          value={unidades}
                          onChange={(e) => setUnidades(e.target.value)}
                        />
                      </Campo>
                    )}

                    <Boton variante="primaria" onClick={confirmarFila}>
                      Agregar
                    </Boton>
                    <Boton variante="neutra" onClick={cancelarFila}>
                      Cancelar
                    </Boton>
                    {esEncargadoOMas() && (
                      <Boton variante="secundaria" onClick={() => setCreandoProducto(true)}>
                        + Crear producto nuevo
                      </Boton>
                    )}
                  </div>
                </td>
              </tr>
            ) : renglones.length === 0 ? (
              <tr>
                <td colSpan={5} className={estilos.celdaCarritoVacio}>
                  <button
                    type="button"
                    className={estilos.botonCarritoVacio}
                    onClick={iniciarAgregarFila}
                  >
                    <EstadoVacio
                      registro="operacion"
                      glifo="caja"
                      titulo="Todavía no hay productos en el carrito"
                      descripcion="Toca aquí para agregar el primero. Cada producto aparece como una fila con su cantidad, su precio y su importe."
                    />
                  </button>
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
        </section>
      </div>

      {creandoProducto && (
        <CrearProductoModal
          onCerrar={() => setCreandoProducto(false)}
          onCreado={(p) => tomarProductoNuevo(p.id_producto)}
        />
      )}

      <div className={estilos.pie}>
        <span className={estilos.bloqueTotal}>
          <span className={estilos.totalEtiqueta}>Total</span>
          <span className={estilos.total}>{formatearMoneda(total)}</span>
        </span>
        <Boton
          variante="cobro"
          tamano="lg"
          className={`${estilos.botonCobrar} ${confirmado ? estilos.confirmado : ""}`}
          onClick={cobrar}
          disabled={cobrando || confirmado || !hayRenglonValido}
        >
          {cobrando ? "Cobrando…" : confirmado ? "¡Cobrado!" : "Cobrar"}
        </Boton>
      </div>
    </div>
  );
}
