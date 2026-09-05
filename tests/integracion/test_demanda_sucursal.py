"""T008 — Prueba obligatoria (Principio III): `reconstruir_serie` de una sucursal completa se
resuelve con un número FIJO de consultas SQL, independiente del número de productos (research.md
#3/#4, patrón N+1 explícitamente rechazado). Se verifica contando las sentencias ejecutadas: si
el número de productos crece pero el número de consultas no, no hay iteración por producto.
Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import event

from rasero.persistencia.modelos import Lote, Producto
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import engine
from rasero.servicios.demanda import reconstruir_serie
from tests.apoyo import crear_escenario_basico, venta_de_prueba

_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _en(dias_atras: int, horas: int = 0) -> datetime:
    return _BASE - timedelta(days=dias_atras) + timedelta(hours=horas)


def _venta(sesion, *, id_sucursal, id_producto, id_lote, id_turno, cantidad, instante):
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=id_lote,
        tipo="salida_venta",
        cantidad=Decimal(cantidad),
        instante=instante,
        id_venta=venta_de_prueba(sesion, id_turno=id_turno, instante=instante),
    )


def _producto_que_vende(sesion, *, id_sucursal: int, id_turno: int) -> int:
    producto = Producto(
        nombre="Producto extra",
        es_granel=False,
        precio_vigente=Decimal("2.0000"),
        lleva_caducidad=False,
    )
    sesion.add(producto)
    sesion.flush()
    lote = Lote(
        id_producto=producto.id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal("1.0000"),
        fecha_caducidad=None,
        instante_entrada=_en(8),
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=producto.id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(30),
        instante=_en(7),
    )
    for atras, cantidad in ((6, -5), (5, -6), (4, -4)):
        _venta(
            sesion,
            id_sucursal=id_sucursal,
            id_producto=producto.id_producto,
            id_lote=lote.id_lote,
            id_turno=id_turno,
            cantidad=cantidad,
            instante=_en(atras),
        )
    return producto.id_producto


def _contar_consultas(func, *args, **kwargs):
    contador = {"n": 0}

    def _contar(*_a, **_k):
        contador["n"] += 1

    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resultado = func(*args, **kwargs)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    return resultado, contador["n"]


def test_serie_de_sucursal_no_crece_en_numero_de_consultas_con_mas_productos(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_turno = escenario["turno"].id_turno
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(20),
        instante=_en(7),
    )
    _venta(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        id_turno=id_turno,
        cantidad=-4,
        instante=_en(6),
    )
    _producto_que_vende(sesion, id_sucursal=id_sucursal, id_turno=id_turno)
    sesion.commit()

    _, consultas_con_dos = _contar_consultas(reconstruir_serie, sesion, id_sucursal=id_sucursal)
    sesion.commit()

    for _ in range(5):
        _producto_que_vende(sesion, id_sucursal=id_sucursal, id_turno=id_turno)
    sesion.commit()

    _, consultas_con_siete = _contar_consultas(reconstruir_serie, sesion, id_sucursal=id_sucursal)
    sesion.commit()

    assert consultas_con_siete == consultas_con_dos, (
        "El número de consultas SQL no debe crecer con el número de productos: reconstruir_serie "
        "debe resolver la sucursal completa con un número fijo de consultas de conjunto."
    )


def test_serie_de_sucursal_incluye_los_productos_que_venden_con_sus_anotaciones(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_p2 = _producto_que_vende(
        sesion, id_sucursal=id_sucursal, id_turno=escenario["turno"].id_turno
    )
    sesion.commit()

    filas = reconstruir_serie(sesion, id_sucursal=id_sucursal, desde=_en(7).date())
    sesion.commit()

    productos = {f["id_producto"] for f in filas}
    assert id_p2 in productos
    assert all(
        f["id_sucursal"] == id_sucursal for f in filas
    ), "toda fila lleva su sucursal (FR-037)"
