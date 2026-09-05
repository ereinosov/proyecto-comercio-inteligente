"""T007 — Prueba obligatoria: `listar_margenes_sucursal` resuelve toda una sucursal con una
única consulta de conjunto y un único upsert masivo — nunca un bucle de N consultas individuales
por producto (research.md #4, patrón N+1 explícitamente rechazado). Se verifica contando las
sentencias SQL ejecutadas: si el número de productos crece pero el número de consultas no, no hay
iteración.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import event

from rasero.persistencia.modelos import Lote, Producto
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import engine
from rasero.servicios.margenes import listar_margenes_sucursal
from tests.apoyo import crear_escenario_basico


def _agregar_producto_con_lote(sesion, *, id_sucursal: int, costo: Decimal, precio: Decimal) -> int:
    producto = Producto(nombre="Producto extra", es_granel=False, precio_vigente=precio, lleva_caducidad=False)
    sesion.add(producto)
    sesion.flush()
    lote = Lote(
        id_producto=producto.id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=costo,
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=producto.id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(10),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    return producto.id_producto


def _contar_consultas(func, *args, **kwargs):
    contador = {"n": 0}

    def _contar(*_args, **_kwargs):
        contador["n"] += 1

    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resultado = func(*args, **kwargs)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    return resultado, contador["n"]


def test_listar_margenes_resuelve_varios_productos_correctamente(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio 2.50
    id_sucursal = escenario["sucursal"].id_sucursal

    id_producto_2 = _agregar_producto_con_lote(
        sesion, id_sucursal=id_sucursal, costo=Decimal("4.0000"), precio=Decimal("5.0000")
    )
    sesion.commit()

    filas = listar_margenes_sucursal(sesion, id_sucursal=id_sucursal)
    sesion.commit()

    por_producto = {f["id_producto"]: f for f in filas}
    assert por_producto[escenario["producto"].id_producto]["margen"] == Decimal("0.6000")
    assert por_producto[id_producto_2]["margen"] == Decimal("0.2000")  # (5-4)/5


def test_listar_margenes_no_crece_en_numero_de_consultas_con_mas_productos(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_sucursal = escenario["sucursal"].id_sucursal
    _agregar_producto_con_lote(sesion, id_sucursal=id_sucursal, costo=Decimal("1.0000"), precio=Decimal("2.0000"))
    sesion.commit()

    _, consultas_con_dos_productos = _contar_consultas(
        listar_margenes_sucursal, sesion, id_sucursal=id_sucursal
    )
    sesion.commit()

    for _ in range(5):
        _agregar_producto_con_lote(sesion, id_sucursal=id_sucursal, costo=Decimal("1.0000"), precio=Decimal("2.0000"))
    sesion.commit()

    _, consultas_con_siete_productos = _contar_consultas(
        listar_margenes_sucursal, sesion, id_sucursal=id_sucursal
    )

    assert consultas_con_siete_productos == consultas_con_dos_productos, (
        "El número de consultas SQL no debe crecer con el número de productos: "
        "listar_margenes_sucursal debe resolver toda la sucursal en una única consulta de "
        "conjunto y un único upsert masivo, nunca un bucle de N consultas por producto."
    )


def test_producto_sin_ningun_lote_en_la_sucursal_queda_no_calculable(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_sucursal = escenario["sucursal"].id_sucursal

    producto_sin_lote = Producto(
        nombre="Producto sin lote", es_granel=False, precio_vigente=Decimal("3.0000"), lleva_caducidad=False
    )
    sesion.add(producto_sin_lote)
    sesion.commit()

    filas = listar_margenes_sucursal(sesion, id_sucursal=id_sucursal)
    sesion.commit()

    fila = next(f for f in filas if f["id_producto"] == producto_sin_lote.id_producto)
    assert fila["costo_vigente"] is None
    assert fila["margen"] is None
    assert fila["confiable"] is True
