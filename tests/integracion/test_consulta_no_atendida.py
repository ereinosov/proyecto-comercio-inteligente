"""T050 [US3] — Prueba de integración de `consulta_no_atendida` (FR-020, FR-021).

Verifica que:
- la consulta se registra con producto, sucursal (derivada del turno), instante y el saldo
  CONGELADO del producto en ese instante;
- el saldo congelado no cambia aunque la existencia cambie después (FR-021);
- el endpoint rechaza cualquier campo de cliente (FR-020: "sin solicitar ningún dato del
  cliente");
- una consulta sobre un producto con saldo positivo también se admite (Edge Case de spec.md).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import ConsultaNoAtendida, Lote
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.senales import registrar_consulta_no_atendida
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico, venta_de_prueba

cliente = TestClient(app)


def test_consulta_congela_el_saldo_del_instante_y_deriva_la_sucursal_del_turno(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=8)
    id_producto = escenario["producto"].id_producto
    id_turno = escenario["turno"].id_turno

    consulta = registrar_consulta_no_atendida(
        sesion, id_producto=id_producto, id_turno=id_turno
    )

    assert consulta.id_sucursal == escenario["sucursal"].id_sucursal
    assert consulta.saldo_en_el_instante == Decimal(8)
    assert consulta.instante is not None

    # El saldo baja después; la consulta ya registrada NO se recalcula (FR-021).
    registrar_venta(
        sesion,
        clave_idempotencia=f"cna-{uuid.uuid4()}",
        id_turno=id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[RenglonEntrada(id_producto=id_producto, cantidad_unidades=5, cantidad_gramos=None)],
    )
    sesion.refresh(consulta)
    assert consulta.saldo_en_el_instante == Decimal(8)


def test_consulta_sobre_producto_agotado_registra_saldo_cero_o_negativo(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=2)
    id_producto = escenario["producto"].id_producto
    id_turno = escenario["turno"].id_turno
    id_sucursal = escenario["sucursal"].id_sucursal
    lote_id = sesion.execute(
        select(Lote.id_lote).where(Lote.id_producto == id_producto)
    ).scalar_one()

    # Saldo negativo HISTÓRICO: desde la Corrección 2026-09-07 una venta ya no puede dejarlo
    # negativo, pero un negativo previo sigue siendo un dato válido que la consulta debe congelar
    # tal cual. Se siembra directo con un movimiento de salida de 5 sobre 2 -> -3.
    id_venta = venta_de_prueba(sesion, id_turno=id_turno, instante=datetime.now(timezone.utc))
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote_id,
        tipo="salida_venta",
        cantidad=Decimal(-5),
        instante=datetime.now(timezone.utc),
        id_venta=id_venta,
    )
    sesion.flush()

    consulta = registrar_consulta_no_atendida(sesion, id_producto=id_producto, id_turno=id_turno)
    assert consulta.saldo_en_el_instante == Decimal(-3)


def test_endpoint_registra_en_dos_datos_y_rechaza_cualquier_campo_de_cliente(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=4)
    sesion.close()
    id_producto = escenario["producto"].id_producto
    id_turno = escenario["turno"].id_turno

    ok = cliente.post(
        "/consultas-no-atendidas", json={"id_producto": id_producto, "id_turno": id_turno}
    )
    assert ok.status_code == 201
    cuerpo = ok.json()
    for clave in ("id_consulta_no_atendida", "id_producto", "id_sucursal", "instante", "saldo_en_el_instante"):
        assert clave in cuerpo
    assert cuerpo["saldo_en_el_instante"] == 4

    con_dato_de_cliente = cliente.post(
        "/consultas-no-atendidas",
        json={
            "id_producto": id_producto,
            "id_turno": id_turno,
            "cedula_cliente": "0912345678",
        },
    )
    assert con_dato_de_cliente.status_code == 422


def test_producto_o_turno_inexistente_da_error_de_dominio(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=1)
    sesion.close()

    sin_producto = cliente.post(
        "/consultas-no-atendidas",
        json={"id_producto": 999_999, "id_turno": escenario["turno"].id_turno},
    )
    assert sin_producto.status_code == 404

    sin_turno = cliente.post(
        "/consultas-no-atendidas",
        json={"id_producto": escenario["producto"].id_producto, "id_turno": 999_999},
    )
    assert sin_turno.status_code == 422
    assert sin_turno.json()["codigo"] == "turno_invalido"
