"""T020 — Prueba obligatoria (Principio III): el saldo consultado en `existencia` coincide
exactamente con la suma de `movimiento_inventario`, incluido el caso de saldo negativo por
venta que excede lo disponible (mitigación de la tabla derivada, ver plan.md Complexity
Tracking).
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import MovimientoInventario
from rasero.persistencia.movimientos import obtener_existencia
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _suma_movimientos(sesion, *, id_sucursal, id_producto) -> Decimal:
    total = sesion.execute(
        select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
            MovimientoInventario.id_sucursal == id_sucursal,
            MovimientoInventario.id_producto == id_producto,
        )
    ).scalar_one()
    return Decimal(total)


def test_saldo_reconstruido_coincide_con_saldo_consultado_caso_normal(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    renglones = [
        RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=3, cantidad_gramos=None)
    ]
    registrar_venta(
        sesion,
        clave_idempotencia=f"saldo-normal-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=renglones,
    )

    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    reconstruido = _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    assert reconstruido == Decimal(7)  # 10 - 3


def test_venta_que_excede_el_saldo_deja_existencia_negativa_y_reconstruible(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=5)
    renglones = [
        RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=8, cantidad_gramos=None)
    ]
    venta, _creada, advertencias, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=f"saldo-negativo-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=renglones,
    )

    assert venta.id_venta is not None, "La venta se registra aunque exceda el saldo (FR-047)"
    assert any(a["codigo"] == "saldo_negativo" for a in advertencias)

    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    reconstruido = _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    assert reconstruido == Decimal(-3)  # 5 - 8

    saldo_lote = obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=escenario["lote"].id_lote
    )
    assert saldo_lote == Decimal(-3)
    assert saldo_lote == reconstruido, "Saldo consultado == suma de movimientos, incluido negativo"
