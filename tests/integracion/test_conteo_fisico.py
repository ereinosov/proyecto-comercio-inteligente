"""T065 [US5] — Prueba de integración del conteo físico (FR-029, FR-030, FR-032).

- al resolver, cada diferencia distinta de cero genera un `ajuste_conteo` trazable al conteo;
- el saldo anterior sigue siendo reconstruible (el ajuste es un movimiento más, no una
  reescritura): suma de movimientos SIN el ajuste == saldo previo;
- una diferencia cero no genera movimiento;
- la diferencia se expone por producto y lote sin clasificar la causa;
- un conteo ya resuelto no se puede volver a resolver.
"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import MovimientoInventario
from rasero.persistencia.movimientos import obtener_existencia
from rasero.servicios.conteos import RenglonContado, iniciar_conteo, resolver_conteo
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def _suma_movimientos(sesion, *, id_sucursal, id_producto, tipo=None) -> Decimal:
    consulta = select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
        MovimientoInventario.id_sucursal == id_sucursal,
        MovimientoInventario.id_producto == id_producto,
    )
    if tipo is not None:
        consulta = consulta.where(MovimientoInventario.tipo == tipo)
    return Decimal(sesion.execute(consulta).scalar_one())


def test_resolver_conteo_genera_ajuste_trazable_y_deja_reconstruible_el_saldo_anterior(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=40)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    id_lote = escenario["lote"].id_lote

    conteo = iniciar_conteo(sesion, id_sucursal=id_sucursal, id_productos=[id_producto])
    assert conteo.estado == "abierto"

    _resuelto, renglones = resolver_conteo(
        sesion,
        id_conteo_fisico=conteo.id_conteo_fisico,
        renglones=[RenglonContado(id_producto=id_producto, id_lote=id_lote, cantidad_contada=37)],
    )

    (renglon,) = renglones
    assert renglon.cantidad_esperada == Decimal(40)
    assert renglon.cantidad_contada == Decimal(37)
    assert renglon.diferencia == Decimal(-3)

    ajuste = sesion.execute(
        select(MovimientoInventario).where(
            MovimientoInventario.tipo == "ajuste_conteo",
            MovimientoInventario.id_conteo_fisico == conteo.id_conteo_fisico,
        )
    ).scalar_one()
    assert ajuste.cantidad == Decimal(-3)
    assert ajuste.id_lote == id_lote

    # Existencia ahora coincide con lo contado.
    assert obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=id_lote
    ) == Decimal(37)
    # Saldo total reconstruible desde movimientos.
    assert _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto) == Decimal(37)
    # Y el saldo ANTERIOR sigue siendo reconstruible sin el ajuste.
    sin_ajuste = _suma_movimientos(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto
    ) - _suma_movimientos(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, tipo="ajuste_conteo"
    )
    assert sin_ajuste == Decimal(40)


def test_diferencia_cero_no_genera_movimiento(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=12)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    id_lote = escenario["lote"].id_lote
    movs_antes = _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto, tipo="ajuste_conteo")

    conteo = iniciar_conteo(sesion, id_sucursal=id_sucursal)
    resolver_conteo(
        sesion,
        id_conteo_fisico=conteo.id_conteo_fisico,
        renglones=[RenglonContado(id_producto=id_producto, id_lote=id_lote, cantidad_contada=12)],
    )
    assert (
        _suma_movimientos(sesion, id_sucursal=id_sucursal, id_producto=id_producto, tipo="ajuste_conteo")
        == movs_antes
    )


def test_conteo_granel_registra_la_diferencia_en_gramos(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=5000, es_granel=True)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    id_lote = escenario["lote"].id_lote

    conteo = iniciar_conteo(sesion, id_sucursal=id_sucursal)
    _c, renglones = resolver_conteo(
        sesion,
        id_conteo_fisico=conteo.id_conteo_fisico,
        renglones=[RenglonContado(id_producto=id_producto, id_lote=id_lote, cantidad_contada=4850)],
    )
    assert renglones[0].diferencia == Decimal(-150)


def test_endpoint_resuelve_una_sola_vez(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=20)
    sesion.close()
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    abierto = cliente.post("/conteos-fisicos", json={"id_sucursal": id_sucursal})
    assert abierto.status_code == 201
    id_conteo = abierto.json()["id_conteo_fisico"]

    cuerpo = {"renglones": [{"id_producto": id_producto, "cantidad_contada": 18}]}
    primera = cliente.post(f"/conteos-fisicos/{id_conteo}/resolucion", json=cuerpo)
    assert primera.status_code == 200
    datos = primera.json()
    assert datos["estado"] == "resuelto"
    assert datos["renglones"][0]["diferencia"] == -2

    segunda = cliente.post(f"/conteos-fisicos/{id_conteo}/resolucion", json=cuerpo)
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "conteo_invalido"
