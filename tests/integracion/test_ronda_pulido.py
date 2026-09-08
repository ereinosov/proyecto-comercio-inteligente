"""Ronda de pulido de UX/funcionalidad — cobertura de los endpoints/servicios nuevos:

- `GET /traspasos` lista los traspasos en tránsito de una sucursal (bug del "viaje eterno").
- `generar_cupones(..., porcentaje_descuento=)` y `anular_cupon` (arrepentimiento del encargado).
- `GET /observaciones-precio` + `DELETE` (historial y corrección de competencia).
- `GET /pagos/cobros` (ventas con su medio de pago; la "bitácora" era de seguridad).
- `GET /promociones/campanias/rendimiento` (¿sirvió la promo?).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.errores import RedencionInvalida
from rasero.persistencia.modelos import Cupon
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.promociones import anular_cupon, generar_cupones
from rasero.servicios.traspasos import RenglonDespacho, despachar_traspaso
from tests.apoyo import crear_escenario_basico, headers_encargado
from tests.apoyo_promociones import crear_cliente_cumpleanos

_s_cab = SesionLocal()
_CAB = headers_encargado(_s_cab)
_s_cab.close()
cliente = TestClient(app, headers=_CAB)


def test_get_traspasos_lista_los_en_transito_de_la_sucursal(sesion):
    origen = crear_escenario_basico(sesion, existencia_inicial=0)
    destino = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = origen["producto"].id_producto
    registrar_entrada(
        sesion,
        id_sucursal=origen["sucursal"].id_sucursal,
        id_producto=id_producto,
        cantidad=10,
        costo_unitario=Decimal("2.0000"),
    )
    traspaso = despachar_traspaso(
        sesion,
        id_sucursal_origen=origen["sucursal"].id_sucursal,
        id_sucursal_destino=destino["sucursal"].id_sucursal,
        renglones=[RenglonDespacho(id_producto=id_producto, cantidad=4)],
    )
    sesion.commit()

    r = cliente.get(
        "/traspasos",
        params={
            "estado": "en_transito",
            "id_sucursal_destino": destino["sucursal"].id_sucursal,
        },
    )
    assert r.status_code == 200
    ids = [t["id_traspaso"] for t in r.json()]
    assert traspaso.id_traspaso in ids


def test_cupon_con_descuento_configurable_y_anulacion(sesion):
    hoy = date.today()
    objetivo = (hoy + timedelta(days=10)).replace(year=1991)
    crear_cliente_cumpleanos(sesion, nombre="Cumple pulido", fecha_nacimiento=objetivo)
    generar_cupones(
        sesion,
        desde=hoy,
        hasta=hoy + timedelta(days=40),
        porcentaje_descuento="25",
    )
    sesion.commit()

    cupon = (
        sesion.query(Cupon)
        .filter(Cupon.porcentaje_descuento == Decimal("25.00"))
        .order_by(Cupon.id_cupon.desc())
        .first()
    )
    assert cupon is not None

    anular_cupon(sesion, id_cupon=cupon.id_cupon)
    sesion.commit()
    sesion.refresh(cupon)
    assert cupon.estado == "anulado"

    # Un cupón que ya no está 'generado' no se vuelve a anular.
    with pytest.raises(RedencionInvalida):
        anular_cupon(sesion, id_cupon=cupon.id_cupon)


def test_observaciones_precio_historial_y_borrado(sesion):
    escenario = crear_escenario_basico(sesion)
    sesion.commit()
    id_producto = escenario["producto"].id_producto

    canal = cliente.post("/canales-competencia", json={"nombre": "Tienda Pulido"}).json()
    obs = cliente.post(
        "/observaciones-precio",
        json={
            "id_producto": id_producto,
            "id_canal_competencia": canal["id_canal_competencia"],
            "presentacion_cantidad": "1",
            "presentacion_unidad": "unidad",
            "precio_observado": "1.20",
            "fuente": "visita",
            "origen_captura": "manual",
        },
    )
    assert obs.status_code == 201
    id_obs = obs.json()["id_observacion_precio"]

    hist = cliente.get("/observaciones-precio", params={"id_producto": id_producto})
    assert hist.status_code == 200
    assert any(o["id_observacion_precio"] == id_obs for o in hist.json())

    borrar = cliente.delete(f"/observaciones-precio/{id_obs}")
    assert borrar.status_code == 204
    hist2 = cliente.get("/observaciones-precio", params={"id_producto": id_producto})
    assert all(o["id_observacion_precio"] != id_obs for o in hist2.json())


def test_pagos_cobros_devuelve_ventas_con_medio_y_totales(sesion):
    escenario = crear_escenario_basico(sesion)
    sesion.commit()
    r = cliente.get(
        "/pagos/cobros", params={"id_sucursal": escenario["sucursal"].id_sucursal}
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert "cobros" in cuerpo and "total_por_medio" in cuerpo


def test_rendimiento_campanias_shape(sesion):
    escenario = crear_escenario_basico(sesion)
    sesion.commit()
    r = cliente.get(
        "/promociones/campanias/rendimiento",
        params={
            "id_sucursal": escenario["sucursal"].id_sucursal,
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
        },
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["cupones"].keys() >= {"emitidos", "redimidos", "tasa_redencion"}
    assert "por_mecanismo" in cuerpo
