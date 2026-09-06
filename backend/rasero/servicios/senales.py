"""Registro de señales del punto de venta (T051, FR-020, FR-021).

Hoy sólo `consulta_no_atendida`: un producto que un cliente pidió y no se le pudo vender.
Se registra en dos toques desde la pantalla de venta, **sin ningún dato del cliente**, y
congela el saldo que el sistema tenía de ese producto en ese instante — es lo que permite a
`004-pronostico-demanda` distinguir un agotamiento real de un producto que estaba pero no se
localizó (FR-021, `data-model.md`).

La consulta no atendida NO mueve dinero ni existencias: no genera `movimiento_inventario`.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.errores import RecursoNoEncontrado, TurnoInvalido
from rasero.persistencia.modelos import ConsultaNoAtendida, Existencia, Producto, Turno


def _saldo_actual(sesion: Session, *, id_sucursal: int, id_producto: int) -> Decimal:
    """Saldo del producto en la sucursal, sumando la existencia derivada de todos sus lotes
    (incluido el saldo sin lote). Coherente con `persistencia/movimientos.py`: `existencia` es
    la agregación de `movimiento_inventario`, y aquí se congela tal cual estaba.
    """
    total = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
            Existencia.id_sucursal == id_sucursal,
            Existencia.id_producto == id_producto,
        )
    ).scalar_one()
    return Decimal(total)


def registrar_consulta_no_atendida(
    sesion: Session,
    *,
    id_producto: int,
    id_turno: int,
    instante_origen: datetime | None = None,
) -> ConsultaNoAtendida:
    """Registra una consulta no atendida. `instante_origen` sólo llega si la operación se
    registró sin conectividad (reconciliación offline, User Story 8); si no, se usa el instante
    del servidor. La sucursal se deriva del turno, nunca se pide aparte (FR-020).
    """
    turno = sesion.get(Turno, id_turno)
    if turno is None:
        raise TurnoInvalido("El turno indicado no existe.")

    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    instante = instante_origen or datetime.now(timezone.utc)
    saldo = _saldo_actual(sesion, id_sucursal=turno.id_sucursal, id_producto=id_producto)

    consulta = ConsultaNoAtendida(
        id_producto=id_producto,
        id_sucursal=turno.id_sucursal,
        id_turno=id_turno,
        instante=instante,
        saldo_en_el_instante=saldo,
    )
    sesion.add(consulta)
    sesion.commit()
    return consulta
