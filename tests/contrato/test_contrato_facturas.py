"""Prueba obligatoria de contrato de 009-facturacion-electronica.

Forma del cuerpo `Factura` según `contracts/openapi.yaml`; `aviso_simulacion` siempre presente;
401 sin sesión; 404 con venta inexistente; 422 con venta de total 0.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Venta
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico, headers_sesion

cliente = TestClient(app)


def _cab(sesion, esc):
    cab = headers_sesion(sesion, esc["operador"])
    sesion.commit()
    return cab


def test_generar_factura_sin_sesion_da_401():
    r = cliente.post("/facturas", json={"id_venta": 1})
    assert r.status_code == 401


def test_generar_factura_forma_del_contrato(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta, *_ = registrar_venta(sesion, clave_idempotencia=f"c-{uuid.uuid4()}",
                                id_turno=esc["turno"].id_turno, referencia_terminal_pago=None,
                                instante_origen=datetime.now(timezone.utc),
                                renglones=[RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                          cantidad_unidades=2, cantidad_gramos=None)])
    cab = _cab(sesion, esc)

    r = cliente.post("/facturas", json={"id_venta": venta.id_venta}, headers=cab)
    assert r.status_code == 201
    c = r.json()
    for clave in ("id_factura_simulada", "id_venta", "tipo", "secuencial", "fecha_emision",
                  "emisor", "comprador", "renglones", "subtotal", "tarifa_iva", "monto_iva",
                  "total", "estado", "aviso_simulacion"):
        assert clave in c
    assert c["aviso_simulacion"]
    assert c["tipo"] == "factura"
    # Segunda llamada → 200, misma factura.
    r2 = cliente.post("/facturas", json={"id_venta": venta.id_venta}, headers=cab)
    assert r2.status_code == 200
    assert r2.json()["id_factura_simulada"] == c["id_factura_simulada"]

    # GET /facturas/venta/{id}
    rv = cliente.get(f"/facturas/venta/{venta.id_venta}", headers=cab)
    assert rv.status_code == 200
    assert rv.json()["factura"]["aviso_simulacion"]
    assert rv.json()["nota_credito"] is None


def test_generar_factura_venta_inexistente_da_404(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    cab = _cab(sesion, esc)
    r = cliente.post("/facturas", json={"id_venta": 99999999}, headers=cab)
    assert r.status_code == 404


def test_generar_factura_venta_total_cero_da_422(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    v = Venta(clave_idempotencia=f"z-{uuid.uuid4()}", id_turno=esc["turno"].id_turno,
              referencia_terminal_pago=None, instante=datetime.now(timezone.utc),
              total=Decimal("0.00"))
    sesion.add(v)
    cab = _cab(sesion, esc)
    r = cliente.post("/facturas", json={"id_venta": v.id_venta}, headers=cab)
    assert r.status_code == 422
    assert r.json()["codigo"] == "factura_no_aplicable"


def test_nota_credito_de_venta_no_anulada_da_409(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta, *_ = registrar_venta(sesion, clave_idempotencia=f"nc-{uuid.uuid4()}",
                                id_turno=esc["turno"].id_turno, referencia_terminal_pago=None,
                                instante_origen=datetime.now(timezone.utc),
                                renglones=[RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                          cantidad_unidades=1, cantidad_gramos=None)])
    cab = _cab(sesion, esc)
    r = cliente.post(f"/facturas/nota-credito/{venta.id_venta}", headers=cab)
    assert r.status_code == 409
    assert r.json()["codigo"] == "venta_no_anulada"
