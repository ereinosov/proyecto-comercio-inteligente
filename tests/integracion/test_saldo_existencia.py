"""T020 — Prueba obligatoria (Principio III): el saldo consultado en `existencia` coincide
exactamente con la suma de `movimiento_inventario`.

Corrección 2026-09-07: una venta que excede la existencia disponible ya NO se registra en
saldo negativo — se rechaza con `ExistenciaInsuficiente` (409) y no deja ningún movimiento.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from rasero.errores import ExistenciaInsuficiente
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


def test_venta_que_excede_el_saldo_es_rechazada_sin_dejar_movimiento(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=5)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    renglones = [
        RenglonEntrada(id_producto=id_producto, cantidad_unidades=8, cantidad_gramos=None)
    ]

    with pytest.raises(ExistenciaInsuficiente):
        registrar_venta(
            sesion,
            clave_idempotencia=f"saldo-negativo-{uuid.uuid4()}",
            id_turno=escenario["turno"].id_turno,
            referencia_terminal_pago=None,
            instante_origen=None,
            renglones=renglones,
        )
    sesion.rollback()

    # El saldo queda EXACTAMENTE igual que antes del intento: ningún movimiento de salida.
    reconstruido = _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    assert reconstruido == Decimal(5)
    saldo_lote = obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=escenario["lote"].id_lote
    )
    assert saldo_lote == Decimal(5)
    salidas = sesion.execute(
        select(func.count()).select_from(MovimientoInventario).where(
            MovimientoInventario.id_producto == id_producto,
            MovimientoInventario.tipo == "salida_venta",
        )
    ).scalar_one()
    assert salidas == 0


def test_venta_con_la_existencia_exacta_tiene_exito(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=5)
    id_producto = escenario["producto"].id_producto

    _venta, creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=f"exacto-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[RenglonEntrada(id_producto=id_producto, cantidad_unidades=5, cantidad_gramos=None)],
    )
    assert creada is True
    reconstruido = _suma_movimientos(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=id_producto,
    )
    assert reconstruido == Decimal(0)


def test_venta_de_una_unidad_mas_que_la_disponible_se_rechaza(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=5)
    id_producto = escenario["producto"].id_producto

    with pytest.raises(ExistenciaInsuficiente):
        registrar_venta(
            sesion,
            clave_idempotencia=f"uno-mas-{uuid.uuid4()}",
            id_turno=escenario["turno"].id_turno,
            referencia_terminal_pago=None,
            instante_origen=None,
            renglones=[RenglonEntrada(id_producto=id_producto, cantidad_unidades=6, cantidad_gramos=None)],
        )
