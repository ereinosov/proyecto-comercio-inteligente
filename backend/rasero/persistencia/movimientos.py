"""Registro de movimientos de inventario y actualización de `existencia` por delta.

`movimiento_inventario` es la única fuente de verdad (data-model.md); `existencia` es una
agregación derivada que se actualiza SIEMPRE sumando el delta del movimiento en la misma
transacción — nunca por asignación de un valor absoluto — para que no exista forma de
sobrescribir un saldo sin movimiento que lo origine (Principio IV).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Existencia, MovimientoInventario


def registrar_movimiento(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int,
    id_lote: int | None,
    tipo: str,
    cantidad: Decimal,
    instante: datetime,
    id_venta: int | None = None,
    id_traspaso: int | None = None,
    id_conteo_fisico: int | None = None,
    id_anulacion_venta: int | None = None,
) -> MovimientoInventario:
    movimiento = MovimientoInventario(
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=id_lote,
        tipo=tipo,
        cantidad=cantidad,
        instante=instante,
        id_venta=id_venta,
        id_traspaso=id_traspaso,
        id_conteo_fisico=id_conteo_fisico,
        id_anulacion_venta=id_anulacion_venta,
    )
    sesion.add(movimiento)
    sesion.flush()

    stmt = pg_insert(Existencia).values(
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=id_lote,
        cantidad=cantidad,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_existencia_identidad",
        set_={"cantidad": Existencia.cantidad + stmt.excluded.cantidad},
    )
    sesion.execute(stmt)

    return movimiento


def obtener_existencia(
    sesion: Session, *, id_sucursal: int, id_producto: int, id_lote: int | None
) -> Decimal:
    """Saldo actual de un (sucursal, producto, lote). Cero si no hay fila."""
    condiciones = [
        Existencia.id_sucursal == id_sucursal,
        Existencia.id_producto == id_producto,
    ]
    if id_lote is None:
        condiciones.append(Existencia.id_lote.is_(None))
    else:
        condiciones.append(Existencia.id_lote == id_lote)
    fila = sesion.execute(select(Existencia.cantidad).where(*condiciones)).scalar_one_or_none()
    return fila if fila is not None else Decimal(0)


def obtener_existencia_total(
    sesion: Session, *, id_sucursal: int, id_producto: int
) -> Decimal:
    """Existencia disponible de un producto en una sucursal: suma de todos sus lotes (más la
    fila sin lote, si la hubiera). Cero si no hay ninguna fila.
    """
    total = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
            Existencia.id_sucursal == id_sucursal,
            Existencia.id_producto == id_producto,
        )
    ).scalar_one()
    return Decimal(total)
