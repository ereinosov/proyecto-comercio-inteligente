"""T073 [US6] — Prueba de integración: una recepción distinta de lo despachado expone la
discrepancia por producto, sin clasificarla ni absorberla (FR-019).
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Existencia
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.traspasos import RenglonDespacho, despachar_traspaso
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def test_recepcion_parcial_expone_la_discrepancia_sin_clasificarla(sesion):
    origen = crear_escenario_basico(sesion, existencia_inicial=0)
    destino = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = origen["producto"].id_producto
    registrar_entrada(
        sesion,
        id_sucursal=origen["sucursal"].id_sucursal,
        id_producto=id_producto,
        cantidad=20,
        costo_unitario=Decimal("2.0000"),
    )
    traspaso = despachar_traspaso(
        sesion,
        id_sucursal_origen=origen["sucursal"].id_sucursal,
        id_sucursal_destino=destino["sucursal"].id_sucursal,
        renglones=[RenglonDespacho(id_producto=id_producto, cantidad=8)],
    )
    sesion.commit()

    # El destino confirma 7 de las 8 despachadas.
    respuesta = cliente.post(
        f"/traspasos/{traspaso.id_traspaso}/recepcion",
        json={"renglones": [{"id_producto": id_producto, "cantidad_recibida": 7}]},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "recibido"
    renglon = cuerpo["renglones"][0]
    assert renglon["cantidad_despachada"] == 8
    assert renglon["cantidad_recibida"] == 7
    assert renglon["discrepancia"] == -1  # sin clasificar; solo expuesta

    # En destino entran exactamente las 7 confirmadas.
    saldo_destino = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
            Existencia.id_sucursal == destino["sucursal"].id_sucursal,
            Existencia.id_producto == id_producto,
        )
    ).scalar_one()
    assert Decimal(saldo_destino) == Decimal(7)


def test_no_se_puede_recibir_dos_veces(sesion):
    origen = crear_escenario_basico(sesion, existencia_inicial=0)
    destino = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = origen["producto"].id_producto
    registrar_entrada(
        sesion, id_sucursal=origen["sucursal"].id_sucursal, id_producto=id_producto,
        cantidad=10, costo_unitario=Decimal("2.0000"),
    )
    traspaso = despachar_traspaso(
        sesion,
        id_sucursal_origen=origen["sucursal"].id_sucursal,
        id_sucursal_destino=destino["sucursal"].id_sucursal,
        renglones=[RenglonDespacho(id_producto=id_producto, cantidad=5)],
    )
    sesion.commit()
    cuerpo = {"renglones": [{"id_producto": id_producto, "cantidad_recibida": 5}]}
    assert cliente.post(f"/traspasos/{traspaso.id_traspaso}/recepcion", json=cuerpo).status_code == 200
    segunda = cliente.post(f"/traspasos/{traspaso.id_traspaso}/recepcion", json=cuerpo)
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "traspaso_invalido"
