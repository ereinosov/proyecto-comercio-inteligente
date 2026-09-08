"""Facturación electrónica SIMULADA (009-facturacion-electronica).

Genera un documento con la FORMA de una factura ecuatoriana DESPUÉS de una `venta` confirmada de
001. **Solo lectura sobre 001/002**: consulta `venta`, `renglon_venta`, `producto` y la `visita`
identificada; escribe únicamente en `factura_simulada` (entidad propia de 009, constitución
v2.7.0). NUNCA es camino crítico del cobro (Principio II) — el frontend la llama tras
`POST /ventas`, sin bloquear su resultado.

SIMULADA: sin SRI, sin firma, sin XML regulatorio. `aviso_simulacion` viaja en toda respuesta.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rasero.configuracion import (
    DIRECCION_COMERCIO,
    ESTABLECIMIENTO_SRI,
    PUNTO_EMISION_SRI,
    RAZON_SOCIAL_COMERCIO,
    RUC_COMERCIO,
    TARIFA_IVA,
)
from rasero.dominio.factura import descomponer_iva, formatear_secuencial
from rasero.errores import FacturaNoAplicable, RecursoNoEncontrado, VentaNoAnulada
from rasero.persistencia.modelos import (
    AnulacionVenta,
    Cliente,
    FacturaSimulada,
    Producto,
    RenglonVenta,
    Turno,
    Venta,
    Visita,
)

AVISO_SIMULACION = (
    "Comprobante de DEMOSTRACIÓN. No tiene validez tributaria: no está autorizado por el SRI, "
    "no lleva firma electrónica y su secuencial no corresponde a un rango autorizado."
)


def _emisor() -> dict:
    d = {"razon_social": RAZON_SOCIAL_COMERCIO, "ruc": RUC_COMERCIO}
    if DIRECCION_COMERCIO:
        d["direccion"] = DIRECCION_COMERCIO
    return d


def _comprador(sesion: Session, id_venta: int) -> dict:
    cliente = sesion.execute(
        select(Cliente)
        .join(Visita, Visita.id_cliente == Cliente.id_cliente)
        .where(Visita.id_venta == id_venta)
    ).scalar_one_or_none()
    if cliente is None or cliente.anonimizado:
        return {"tipo": "consumidor_final"}
    d = {"tipo": "identificado", "nombre": cliente.nombre}
    if cliente.identificador:
        d["identificador"] = cliente.identificador
    return d


def _renglones(sesion: Session, id_venta: int) -> list[dict]:
    filas = sesion.execute(
        select(RenglonVenta, Producto.nombre)
        .join(Producto, Producto.id_producto == RenglonVenta.id_producto)
        .where(RenglonVenta.id_venta == id_venta)
        .order_by(RenglonVenta.id_renglon_venta)
    ).all()
    salida = []
    for r, nombre in filas:
        cantidad = r.cantidad_unidades if r.cantidad_unidades is not None else (
            f"{Decimal(r.cantidad_gramos) / 1000}" if r.cantidad_gramos else "0"
        )
        salida.append(
            {
                "descripcion": nombre,
                "cantidad": str(cantidad),
                "precio_unitario": f"{Decimal(r.precio_aplicado):.4f}",
                "importe": f"{Decimal(r.importe):.2f}",
            }
        )
    return salida


def _fecha_emision(sesion: Session, venta: Venta) -> date:
    turno = sesion.get(Turno, venta.id_turno)
    sucursal_zona = "America/Guayaquil"
    if turno is not None:
        from rasero.persistencia.modelos import Sucursal

        s = sesion.get(Sucursal, turno.id_sucursal)
        if s is not None:
            sucursal_zona = s.zona_horaria
    return datetime.now(ZoneInfo(sucursal_zona)).date()


def _siguiente_numero(sesion: Session, est: str, pto: str, tipo: str) -> int:
    """Correlativo `MAX(numero)+1` para `(est, pto, tipo)`. PostgreSQL no permite `FOR UPDATE`
    con agregación, así que la garantía de "sin huecos ni repeticiones" (SC-003) la da el
    `UNIQUE (establecimiento, punto_emision, tipo, numero)` + el reintento del llamador ante un
    `IntegrityError`.
    """
    actual = sesion.execute(
        select(func.coalesce(func.max(FacturaSimulada.numero), 0)).where(
            FacturaSimulada.establecimiento == est,
            FacturaSimulada.punto_emision == pto,
            FacturaSimulada.tipo == tipo,
        )
    ).scalar_one()
    return int(actual) + 1


def _insertar_con_reintento(sesion: Session, construir, est: str, pto: str, tipo: str):
    """Inserta la factura que devuelve `construir(numero)`; ante colisión del `UNIQUE` del
    secuencial, vuelve a leer el máximo y reintenta (hasta 5 veces).
    """
    for _ in range(5):
        numero = _siguiente_numero(sesion, est, pto, tipo)
        fila = construir(numero)
        sesion.add(fila)
        try:
            sesion.flush()
            return fila
        except IntegrityError as e:
            sesion.rollback()
            if "uq_factura_simulada_secuencial" not in str(e):
                raise
    raise RuntimeError("no se pudo asignar un secuencial de factura tras varios intentos")


def _medio_pago(venta: Venta) -> str:
    # Heurística (research §5): sin referencia de terminal → efectivo; con referencia → tarjeta.
    # NUNCA un dato de instrumento de pago, sólo la categoría (FR-020).
    return "tarjeta" if venta.referencia_terminal_pago else "efectivo"


def factura_a_respuesta(f: FacturaSimulada) -> dict:
    return {
        "id_factura_simulada": f.id_factura_simulada,
        "id_venta": f.id_venta,
        "tipo": f.tipo,
        "id_factura_referida": f.id_factura_referida,
        "secuencial": f.secuencial,
        "fecha_emision": f.fecha_emision.isoformat(),
        "emisor": f.emisor,
        "comprador": f.comprador,
        "renglones": f.renglones,
        "subtotal": f"{Decimal(f.subtotal):.2f}",
        "tarifa_iva": f"{Decimal(f.tarifa_iva):.2f}",
        "monto_iva": f"{Decimal(f.monto_iva):.2f}",
        "total": f"{Decimal(f.total):.2f}",
        "medio_pago": f.medio_pago,
        "estado": f.estado,
        "instante_generacion": f.instante_generacion.isoformat(),
        "aviso_simulacion": AVISO_SIMULACION,
    }


def obtener_factura_de_venta(sesion: Session, *, id_venta: int, tipo: str = "factura") -> FacturaSimulada | None:
    return sesion.execute(
        select(FacturaSimulada).where(
            FacturaSimulada.id_venta == id_venta, FacturaSimulada.tipo == tipo
        )
    ).scalar_one_or_none()


def obtener_factura(sesion: Session, *, id_factura: int) -> FacturaSimulada:
    f = sesion.get(FacturaSimulada, id_factura)
    if f is None:
        raise RecursoNoEncontrado(f"La factura {id_factura} no existe.")
    return f


def generar_factura(sesion: Session, *, id_venta: int) -> tuple[FacturaSimulada, bool]:
    """Devuelve (factura, creada_ahora). Idempotente por `id_venta` (FR-007/FR-012)."""
    existente = obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="factura")
    if existente is not None:
        return existente, False

    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")
    if Decimal(venta.total) == 0:
        raise FacturaNoAplicable()

    tarifa = Decimal(TARIFA_IVA)
    subtotal, monto_iva = descomponer_iva(Decimal(venta.total), tarifa)
    est, pto = ESTABLECIMIENTO_SRI, PUNTO_EMISION_SRI
    emisor, comprador, renglones = _emisor(), _comprador(sesion, id_venta), _renglones(sesion, id_venta)
    fecha = _fecha_emision(sesion, venta)
    medio = _medio_pago(venta)

    factura = _insertar_con_reintento(
        sesion,
        lambda numero: FacturaSimulada(
            id_venta=id_venta,
            tipo="factura",
            establecimiento=est,
            punto_emision=pto,
            numero=numero,
            secuencial=formatear_secuencial(est, pto, numero),
            fecha_emision=fecha,
            emisor=emisor,
            comprador=comprador,
            renglones=renglones,
            subtotal=subtotal,
            tarifa_iva=tarifa,
            monto_iva=monto_iva,
            total=Decimal(venta.total),
            medio_pago=medio,
            estado="emitida",
            instante_generacion=datetime.now(timezone.utc),
        ),
        est, pto, "factura",
    )
    sesion.commit()
    return factura, True


def obtener_facturas_de_venta(sesion: Session, *, id_venta: int) -> dict:
    return {
        "id_venta": id_venta,
        "factura": obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="factura"),
        "nota_credito": obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="nota_credito"),
    }


def emitir_nota_credito(sesion: Session, *, id_venta: int) -> tuple[FacturaSimulada | None, bool]:
    """Devuelve (nota, creada_ahora). `None` si la venta no tenía factura (FR-016, → 204).
    Idempotente (FR-017). `409` si la venta no está anulada en 001.
    """
    anulada = sesion.execute(
        select(AnulacionVenta.id_anulacion_venta).where(AnulacionVenta.id_venta == id_venta)
    ).scalar_one_or_none()
    if anulada is None:
        raise VentaNoAnulada()

    existente = obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="nota_credito")
    if existente is not None:
        return existente, False

    factura = obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="factura")
    if factura is None:
        return None, False

    est, pto = factura.establecimiento, factura.punto_emision
    ref = factura.id_factura_simulada
    snap = dict(emisor=factura.emisor, comprador=factura.comprador, renglones=factura.renglones,
                subtotal=-Decimal(factura.subtotal), tarifa_iva=Decimal(factura.tarifa_iva),
                monto_iva=-Decimal(factura.monto_iva), total=-Decimal(factura.total),
                medio_pago=factura.medio_pago)
    fecha = _fecha_emision(sesion, sesion.get(Venta, id_venta))

    nota = _insertar_con_reintento(
        sesion,
        lambda numero: FacturaSimulada(
            id_venta=id_venta,
            tipo="nota_credito",
            id_factura_referida=ref,
            establecimiento=est,
            punto_emision=pto,
            numero=numero,
            secuencial=formatear_secuencial(est, pto, numero),
            fecha_emision=fecha,
            estado="emitida",
            instante_generacion=datetime.now(timezone.utc),
            **snap,
        ),
        est, pto, "nota_credito",
    )
    # La factura queda anulada SÓLO tras insertar la nota (si el insert falla y se hace rollback,
    # no se pierde el cambio de estado).
    factura = obtener_factura_de_venta(sesion, id_venta=id_venta, tipo="factura")
    factura.estado = "anulada"
    sesion.commit()
    return nota, True
