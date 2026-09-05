"""T006 (parte de integración) — `resolver_margen_producto` (servicios/margenes.py) contra
PostgreSQL real: costo vigente vía el lote FEFO de 001, precio vigente vía override/base
(producto_precio_sucursal/producto), y el upsert resultante en `margen_calculado`.

Nota de alcance frente a la redacción original de esta tarea en tasks.md: no existe ningún caso
de conversión gramos/kg que probar aquí. `costo_unitario` (lote) y `precio_vigente`
(producto/producto_precio_sucursal) ya están expresados en la misma base para un producto a
granel (por kilogramo, data-model.md de 001); a diferencia de `margen_resolver.py` de 002 (que sí
convierte porque multiplica `costo_unitario` por `movimiento_inventario.cantidad`, una cantidad en
gramos), `resolver_margen_producto` nunca multiplica por ninguna cantidad — solo divide costo
entre precio, ya consistentes. Ver `tests/unidad/test_margen_calculado.py` para el detalle.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from rasero.persistencia.modelos import Lote, MargenCalculado, ProductoPrecioSucursal
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.margenes import resolver_margen_producto
from tests.apoyo import crear_escenario_basico


def test_margen_por_unidad_con_costo_y_precio_conocidos(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio 2.50

    margen = resolver_margen_producto(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
    )
    sesion.commit()

    assert margen == Decimal("0.6000")  # (2.50 - 1.00) / 2.50

    fila = sesion.get(
        MargenCalculado, (escenario["producto"].id_producto, escenario["sucursal"].id_sucursal)
    )
    assert fila.costo_vigente == Decimal("1.0000")
    assert fila.precio_vigente == Decimal("2.5000")
    assert fila.margen == Decimal("0.6000")
    assert fila.confiable is True


def test_margen_producto_a_granel_usa_costo_y_precio_por_kilogramo_sin_conversion(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0, es_granel=True)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    escenario["producto"].precio_vigente = Decimal("4.0000")  # por kilogramo
    lote = Lote(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal("3.0000"),  # por kilogramo
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(5000),  # 5 kg, en gramos — el movimiento sí está en gramos
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.commit()

    margen = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    # (4.00 - 3.00) / 4.00 = 0.25 — la cantidad en gramos del movimiento (5000) es irrelevante
    # para el margen: costo_unitario y precio_vigente ya son "por kilogramo", no se multiplican
    # por ninguna cantidad aquí.
    assert margen == Decimal("0.2500")


def test_sin_existencia_con_lote_el_margen_no_es_calculable(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)

    margen = resolver_margen_producto(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
    )
    sesion.commit()

    assert margen is None
    fila = sesion.get(
        MargenCalculado, (escenario["producto"].id_producto, escenario["sucursal"].id_sucursal)
    )
    assert fila.costo_vigente is None
    assert fila.margen is None
    assert fila.confiable is True, "sin costo no es 'no confiable', es 'no calculable' (FR-003)"


def test_lote_con_existencia_agotada_no_cuenta_como_costo_vigente(sesion):
    # Lote A (del escenario básico): sin caducidad, costo 1.00, existencia 5.
    # Lote B: caduca antes que el A (FEFO lo probaría primero), pero su existencia se agota a
    # cero — no debe contarse como costo vigente.
    escenario = crear_escenario_basico(sesion, existencia_inicial=5)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    lote_b = Lote(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal("9.0000"),
        fecha_caducidad=date.today() + timedelta(days=1),
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=2),
    )
    sesion.add(lote_b)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote_b.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(3),
        instante=datetime.now(timezone.utc) - timedelta(days=2),
    )
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote_b.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(-3),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.commit()

    margen = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    # (2.50 - 1.00) / 2.50 = 0.60 — usa el costo del lote A, el único con existencia positiva.
    assert margen == Decimal("0.6000")


def test_costo_cero_marca_el_margen_como_no_confiable(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    lote = Lote(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal("0.0000"),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(10),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.commit()

    margen = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    assert margen is not None, "FR-004: con costo conocido (aunque sea cero) sí se calcula"
    fila = sesion.get(MargenCalculado, (id_producto, id_sucursal))
    assert fila.confiable is False


def test_override_de_precio_por_sucursal_se_refleja_en_el_margen(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio base 2.50
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    sesion.add(
        ProductoPrecioSucursal(id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("2.0000"))
    )
    sesion.commit()

    margen = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    assert margen == Decimal("0.5000")  # (2.00 - 1.00) / 2.00, no (2.50 - 1.00) / 2.50


def test_recalcula_y_sobrescribe_en_cada_llamada(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    primero = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()
    assert primero == Decimal("0.6000")

    escenario["producto"].precio_vigente = Decimal("5.0000")
    sesion.commit()

    segundo = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()
    assert segundo == Decimal("0.8000")  # (5.00 - 1.00) / 5.00 — refleja el precio nuevo

    filas = sesion.execute(
        select(MargenCalculado).where(
            MargenCalculado.id_producto == id_producto, MargenCalculado.id_sucursal == id_sucursal
        )
    ).scalars().all()
    assert len(filas) == 1, "upsert: una sola fila por (id_producto, id_sucursal), no un histórico"
