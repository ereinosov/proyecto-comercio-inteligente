"""US14 de 001 — desglose de existencia por lote para Venta y Traspasos.

- devuelve los lotes con saldo != 0 en orden FEFO (caducidad, luego entrada, luego id_lote);
- `costo_unitario` NO aparece salvo `incluir_costo=true`;
- un saldo negativo histórico se muestra tal cual;
- sucursal/producto inexistente -> 404.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Lote
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.inventario import registrar_entrada
from tests.apoyo import crear_escenario_basico, venta_de_prueba

cliente = TestClient(app)


def test_desglose_por_lote_en_orden_fefo_sin_costo_por_defecto(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    # Lote sin caducidad (entró primero) y lote con caducidad próxima (entró después).
    registrar_entrada(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto,
        cantidad=10, costo_unitario=Decimal("1.0000"),
    )
    registrar_entrada(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto,
        cantidad=4, costo_unitario=Decimal("1.5000"),
        fecha_caducidad=date.today() + timedelta(days=5),
    )
    sesion.close()

    r = cliente.get(f"/existencias/lotes?id_sucursal={id_sucursal}&id_producto={id_producto}")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) == 2
    # FEFO: primero el que caduca (aunque entró después), luego el sin caducidad.
    assert filas[0]["cantidad"] == 4
    assert filas[0]["fecha_caducidad"] is not None
    assert filas[1]["cantidad"] == 10
    assert filas[1]["fecha_caducidad"] is None
    assert all("costo_unitario" not in f for f in filas), "sin costo en la vista de caja"


def test_incluir_costo_expone_costo_unitario(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    registrar_entrada(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto,
        cantidad=7, costo_unitario=Decimal("2.2500"),
    )
    sesion.close()

    r = cliente.get(
        f"/existencias/lotes?id_sucursal={id_sucursal}&id_producto={id_producto}&incluir_costo=true"
    )
    assert r.status_code == 200
    assert r.json()[0]["costo_unitario"] == "2.2500"


def test_saldo_negativo_historico_se_muestra(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=3)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    lote_id = sesion.execute(
        select(Lote.id_lote).where(Lote.id_producto == id_producto)
    ).scalar_one()
    id_venta = venta_de_prueba(
        sesion, id_turno=escenario["turno"].id_turno, instante=datetime.now(timezone.utc)
    )
    registrar_movimiento(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=lote_id,
        tipo="salida_venta", cantidad=Decimal(-5), instante=datetime.now(timezone.utc),
        id_venta=id_venta,
    )
    sesion.commit()
    sesion.close()

    r = cliente.get(f"/existencias/lotes?id_sucursal={id_sucursal}&id_producto={id_producto}")
    assert r.status_code == 200
    assert r.json()[0]["cantidad"] == -2


def test_sucursal_inexistente_da_404(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    sesion.close()
    r = cliente.get(f"/existencias/lotes?id_sucursal=999999&id_producto={id_producto}")
    assert r.status_code == 404
