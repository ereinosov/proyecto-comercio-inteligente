"""T033 — Prueba obligatoria (Principio III): POST /ventas conforme al esquema `Venta` de
contracts/openapi.yaml: 201 en la primera llamada, 200 con la venta original en el reintento,
y las claves de la respuesta según el contrato.
"""

import uuid

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.sesion import SesionLocal
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def test_post_ventas_devuelve_201_y_luego_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=20)
    sesion.close()

    cuerpo = {
        "clave_idempotencia": f"contrato-{uuid.uuid4()}",
        "id_turno": escenario["turno"].id_turno,
        "referencia_terminal_pago": "datafono-1",
        "renglones": [{"id_producto": escenario["producto"].id_producto, "cantidad_unidades": 2}],
    }

    primera = cliente.post("/ventas", json=cuerpo)
    assert primera.status_code == 201
    cuerpo_respuesta = primera.json()

    for clave in (
        "id_venta",
        "clave_idempotencia",
        "id_turno",
        "id_operador",
        "id_sucursal",
        "referencia_terminal_pago",
        "instante",
        "total",
        "moneda",
        "anulada",
        "renglones",
        "advertencias",
    ):
        assert clave in cuerpo_respuesta, f"falta '{clave}' en la respuesta de POST /ventas"

    assert cuerpo_respuesta["clave_idempotencia"] == cuerpo["clave_idempotencia"]
    assert cuerpo_respuesta["total"] == "5.00"  # 2 * 2.50
    assert cuerpo_respuesta["moneda"] == "USD"
    assert cuerpo_respuesta["anulada"] is False
    assert len(cuerpo_respuesta["renglones"]) == 1
    assert cuerpo_respuesta["renglones"][0]["precio_aplicado"] == "2.5000"

    segunda = cliente.post("/ventas", json=cuerpo)
    assert segunda.status_code == 200
    assert segunda.json()["id_venta"] == cuerpo_respuesta["id_venta"]


def test_post_ventas_con_renglon_invalido_devuelve_422():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=20)
    sesion.close()

    cuerpo = {
        "clave_idempotencia": f"contrato-invalido-{uuid.uuid4()}",
        "id_turno": escenario["turno"].id_turno,
        "renglones": [
            {"id_producto": escenario["producto"].id_producto}  # sin ninguna cantidad
        ],
    }
    respuesta = cliente.post("/ventas", json=cuerpo)
    assert respuesta.status_code == 422
    assert "codigo" in respuesta.json()
    assert "mensaje" in respuesta.json()
