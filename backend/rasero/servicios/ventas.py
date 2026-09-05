"""Registro y anulación de venta (T026, T027).

El eje: `movimiento_inventario` es la única fuente de verdad; `existencia` se actualiza por
delta en la misma transacción (persistencia/movimientos.py). La venta es idempotente por
`clave_idempotencia` — la restricción UNIQUE de base de datos es lo que hace que la unicidad
de la venta implique unicidad de sus movimientos, incluso bajo reintentos concurrentes
(research.md, decisión 2). Ninguna validación de existencias bloquea el cobro (Principio II);
el exceso se registra en saldo negativo (FR-047).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.dominio.seleccion_lote import ordenar_fefo
from rasero.dominio.totales import calcular_importe_renglon, calcular_total_venta
from rasero.errores import (
    AnulacionNoAutorizada,
    RecursoNoEncontrado,
    RenglonInvalido,
    TurnoInvalido,
    VentaYaAnulada,
)
from rasero.persistencia.modelos import (
    AnulacionVenta,
    Lote,
    MovimientoInventario,
    Operador,
    Producto,
    ProductoPrecioSucursal,
    RenglonVenta,
    Turno,
    Venta,
)
from rasero.persistencia.movimientos import obtener_existencia, registrar_movimiento


@dataclass
class RenglonEntrada:
    id_producto: int
    cantidad_unidades: int | None
    cantidad_gramos: int | None


def _resolver_precio(sesion: Session, *, id_producto: int, id_sucursal: int, precio_base: Decimal) -> Decimal:
    override = sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()
    return resolver_precio_efectivo(precio_base=precio_base, override_sucursal=override)


def _consumir_fefo(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int,
    nombre_producto: str,
    cantidad_requerida: Decimal,
    instante: datetime,
    id_venta: int,
) -> tuple[list[dict], list[dict]]:
    """Consume existencia en orden FEFO. Devuelve (lotes_consumidos, advertencias)."""
    lotes = sesion.execute(
        select(Lote)
        .where(Lote.id_producto == id_producto, Lote.id_sucursal == id_sucursal)
        .with_for_update()
    ).scalars().all()
    lotes_ordenados = ordenar_fefo(lotes)

    restante = cantidad_requerida
    lotes_consumidos: list[dict] = []

    for lote in lotes_ordenados:
        if restante <= 0:
            break
        disponible = obtener_existencia(
            sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=lote.id_lote
        )
        tomar = min(restante, disponible) if disponible > 0 else Decimal(0)
        if tomar > 0:
            registrar_movimiento(
                sesion,
                id_sucursal=id_sucursal,
                id_producto=id_producto,
                id_lote=lote.id_lote,
                tipo="salida_venta",
                cantidad=-tomar,
                instante=instante,
                id_venta=id_venta,
            )
            lotes_consumidos.append({"id_lote": lote.id_lote, "cantidad": tomar})
            restante -= tomar

    advertencias: list[dict] = []
    if restante > 0:
        # FR-047: ninguna validación de existencias bloquea el cobro. El exceso se imputa al
        # último lote seleccionado por FEFO (research.md, decisión 5); si no hay ningún lote
        # en la sucursal, el movimiento se registra con id_lote nulo.
        id_lote_destino = lotes_ordenados[-1].id_lote if lotes_ordenados else None
        registrar_movimiento(
            sesion,
            id_sucursal=id_sucursal,
            id_producto=id_producto,
            id_lote=id_lote_destino,
            tipo="salida_venta",
            cantidad=-restante,
            instante=instante,
            id_venta=id_venta,
        )
        lotes_consumidos.append({"id_lote": id_lote_destino, "cantidad": restante})
        advertencias.append(
            {
                "codigo": "saldo_negativo",
                "mensaje": (
                    f"La existencia de {nombre_producto} no alcanzaba; la venta se registró "
                    "igual y el saldo quedó negativo hasta el siguiente conteo."
                ),
                "id_producto": id_producto,
            }
        )

    return lotes_consumidos, advertencias


def registrar_venta(
    sesion: Session,
    *,
    clave_idempotencia: str,
    id_turno: int,
    referencia_terminal_pago: str | None,
    instante_origen: datetime | None,
    renglones: list[RenglonEntrada],
) -> tuple[Venta, bool, list[dict], dict[int, list[dict]]]:
    """Devuelve (venta, creada_ahora, advertencias, lotes_consumidos_por_renglon)."""

    existente = sesion.execute(
        select(Venta).where(Venta.clave_idempotencia == clave_idempotencia)
    ).scalar_one_or_none()
    if existente is not None:
        return existente, False, [], {}

    if not renglones:
        raise RenglonInvalido("La venta debe tener al menos un renglón.")

    turno = sesion.get(Turno, id_turno)
    if turno is None:
        raise TurnoInvalido("El turno indicado no existe.")

    instante = instante_origen or datetime.now(timezone.utc)

    venta = Venta(
        clave_idempotencia=clave_idempotencia,
        id_turno=id_turno,
        referencia_terminal_pago=referencia_terminal_pago,
        instante=instante,
        total=Decimal("0.00"),
    )
    sesion.add(venta)
    sesion.flush()

    importes: list[Decimal] = []
    advertencias: list[dict] = []
    lotes_consumidos_por_renglon: dict[int, list[dict]] = {}

    for entrada in renglones:
        producto = sesion.get(Producto, entrada.id_producto)
        if producto is None:
            raise RecursoNoEncontrado(f"El producto {entrada.id_producto} no existe.")

        if producto.es_granel:
            if entrada.cantidad_gramos is None or entrada.cantidad_unidades is not None:
                raise RenglonInvalido(
                    f"El producto {producto.nombre} se vende a peso: envía cantidad_gramos."
                )
            if entrada.cantidad_gramos <= 0:
                raise RenglonInvalido("El peso leído en báscula debe ser mayor que cero.")
            cantidad_base = Decimal(entrada.cantidad_gramos)
        else:
            if entrada.cantidad_unidades is None or entrada.cantidad_gramos is not None:
                raise RenglonInvalido(
                    f"El producto {producto.nombre} se vende por unidad: envía cantidad_unidades."
                )
            if entrada.cantidad_unidades <= 0:
                raise RenglonInvalido("La cantidad debe ser mayor que cero.")
            cantidad_base = Decimal(entrada.cantidad_unidades)

        precio = _resolver_precio(
            sesion,
            id_producto=producto.id_producto,
            id_sucursal=turno.id_sucursal,
            precio_base=producto.precio_vigente,
        )
        importe = calcular_importe_renglon(
            cantidad_unidades=entrada.cantidad_unidades,
            cantidad_gramos=entrada.cantidad_gramos,
            precio_por_unidad_o_kg=precio,
        )

        renglon = RenglonVenta(
            id_venta=venta.id_venta,
            id_producto=producto.id_producto,
            cantidad_unidades=entrada.cantidad_unidades,
            cantidad_gramos=entrada.cantidad_gramos,
            precio_aplicado=precio,
            importe=importe,
            moneda=producto.moneda,
        )
        sesion.add(renglon)
        sesion.flush()
        importes.append(importe)

        lotes_consumidos, advertencias_renglon = _consumir_fefo(
            sesion,
            id_sucursal=turno.id_sucursal,
            id_producto=producto.id_producto,
            nombre_producto=producto.nombre,
            cantidad_requerida=cantidad_base,
            instante=instante,
            id_venta=venta.id_venta,
        )
        lotes_consumidos_por_renglon[renglon.id_renglon_venta] = lotes_consumidos
        advertencias.extend(advertencias_renglon)

    venta.total = calcular_total_venta(importes)
    sesion.flush()

    try:
        sesion.commit()
    except IntegrityError:
        # Reintento concurrente con la misma clave: gana quien insertó primero.
        sesion.rollback()
        existente = sesion.execute(
            select(Venta).where(Venta.clave_idempotencia == clave_idempotencia)
        ).scalar_one()
        return existente, False, [], {}

    return venta, True, advertencias, lotes_consumidos_por_renglon


def anular_venta(
    sesion: Session, *, id_venta: int, id_operador_ejecuta: int, motivo: str | None
) -> AnulacionVenta:
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")

    ya_anulada = sesion.execute(
        select(AnulacionVenta).where(AnulacionVenta.id_venta == id_venta)
    ).scalar_one_or_none()
    if ya_anulada is not None:
        raise VentaYaAnulada()

    operador = sesion.get(Operador, id_operador_ejecuta)
    if operador is None or not operador.activo:
        raise RecursoNoEncontrado("El operador que anula no existe o está inactivo.")

    turno_venta = sesion.get(Turno, venta.id_turno)
    turno_en_curso = turno_venta.instante_cierre is None
    es_su_propio_turno = turno_venta.id_operador == id_operador_ejecuta

    autorizado = (turno_en_curso and es_su_propio_turno) or operador.es_encargado
    if not autorizado:
        raise AnulacionNoAutorizada()

    instante = datetime.now(timezone.utc)
    anulacion = AnulacionVenta(
        id_venta=id_venta, id_operador=id_operador_ejecuta, instante=instante, motivo=motivo
    )
    sesion.add(anulacion)
    sesion.flush()

    movimientos_originales = sesion.execute(
        select(MovimientoInventario).where(
            MovimientoInventario.id_venta == id_venta,
            MovimientoInventario.tipo == "salida_venta",
        )
    ).scalars().all()

    for mov in movimientos_originales:
        registrar_movimiento(
            sesion,
            id_sucursal=mov.id_sucursal,
            id_producto=mov.id_producto,
            id_lote=mov.id_lote,
            tipo="entrada_anulacion",
            cantidad=-mov.cantidad,
            instante=instante,
            id_anulacion_venta=anulacion.id_anulacion_venta,
        )

    sesion.commit()
    return anulacion
