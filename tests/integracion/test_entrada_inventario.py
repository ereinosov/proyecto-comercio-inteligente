"""T044 [US2] — Prueba de integración de la entrada de inventario (FR-012, FR-013, FR-014).

- una entrada crea el lote con su costo y su caducidad y sube la existencia;
- el movimiento de entrada es trazable al lote (tipo `entrada_compra`);
- un producto granel perecedero guarda la cantidad en gramos enteros y su caducidad;
- el módulo NO presenta ningún margen (solo costo);
- `GET /existencias` expone el saldo, incluido el negativo, sin limitarlo a cero.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Lote, MovimientoInventario
from rasero.persistencia.movimientos import obtener_existencia
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def test_entrada_no_perecedera_crea_lote_con_costo_y_sube_existencia(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    lote = registrar_entrada(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        cantidad=24,
        costo_unitario=Decimal("1.2500"),
    )
    assert lote.costo_unitario == Decimal("1.2500")
    assert lote.fecha_caducidad is None
    assert obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=lote.id_lote
    ) == Decimal(24)

    mov = sesion.execute(
        select(MovimientoInventario).where(
            MovimientoInventario.id_lote == lote.id_lote,
            MovimientoInventario.tipo == "entrada_compra",
        )
    ).scalar_one()
    assert mov.cantidad == Decimal(24)
    assert mov.id_venta is None and mov.id_traspaso is None and mov.id_conteo_fisico is None


def test_entrada_granel_perecedera_guarda_gramos_y_caducidad(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0, es_granel=True)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    caducidad = date.today() + timedelta(days=20)

    lote = registrar_entrada(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        cantidad=12500,  # 12,5 kg en gramos enteros
        costo_unitario=Decimal("6.0000"),
        fecha_caducidad=caducidad,
    )
    assert lote.fecha_caducidad == caducidad
    assert obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=lote.id_lote
    ) == Decimal(12500)


def test_endpoint_entrada_y_existencias_expone_saldo_negativo(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sesion.close()
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    entrada = cliente.post(
        "/entradas-inventario",
        json={
            "id_sucursal": id_sucursal,
            "id_producto": id_producto,
            "cantidad": 5,
            "costo_unitario": "2.0000",
        },
    )
    assert entrada.status_code == 201
    cuerpo = entrada.json()
    assert cuerpo["cantidad_restante"] == 5
    assert cuerpo["costo_unitario"] == "2.0000"
    assert "margen" not in entrada.text.lower()  # FR-014

    # Vende 8 de 5 -> saldo -3, y GET /existencias lo muestra tal cual.
    sesion2 = SesionLocal()
    registrar_venta(
        sesion2,
        clave_idempotencia=f"ent-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[RenglonEntrada(id_producto=id_producto, cantidad_unidades=8, cantidad_gramos=None)],
    )
    sesion2.close()

    existencias = cliente.get(f"/existencias?id_sucursal={id_sucursal}&id_producto={id_producto}")
    assert existencias.status_code == 200
    fila = existencias.json()[0]
    assert fila["cantidad"] == -3
    assert fila["es_granel"] is False


def test_entrada_del_mismo_costo_y_caducidad_alimenta_el_lote(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    a = registrar_entrada(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, cantidad=10,
        costo_unitario=Decimal("3.0000"),
    )
    b = registrar_entrada(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, cantidad=6,
        costo_unitario=Decimal("3.0000"),
    )
    assert a.id_lote == b.id_lote
    assert obtener_existencia(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=a.id_lote
    ) == Decimal(16)

    lotes_de_ese_costo = len(
        sesion.execute(
            select(Lote).where(
                Lote.id_producto == id_producto,
                Lote.id_sucursal == id_sucursal,
                Lote.costo_unitario == Decimal("3.0000"),
            )
        ).scalars().all()
    )
    assert lotes_de_ese_costo == 1
