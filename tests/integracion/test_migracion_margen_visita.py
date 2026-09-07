"""T008 — Prueba obligatoria del contrato de migración (FR-022 de 003-precios-margenes,
research.md #8): `resolver_margen_visita` de 002, tras el refactor, produce el mismo valor que
combinar `servicios/margenes.resolver_margen_producto` de 003 por cada renglón de la venta,
ponderado por importe. Una `visita` ya creada conserva su `margen_relativo` como snapshot: no se
recalcula si el costo o el precio del producto cambian después (mismo principio que ya declaraba
la fórmula interina, FR-005 de 002).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import Lote, Producto
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.clientes import registrar_cliente, registrar_visita
from rasero.servicios.margen_resolver import resolver_margen_visita
from rasero.servicios.margenes import resolver_margen_producto
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def test_margen_de_visita_coincide_con_la_ponderacion_por_importe_de_resolver_margen_producto(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)  # costo 1.00, precio 2.50
    id_sucursal = escenario["sucursal"].id_sucursal

    # Segundo producto, distinto margen, en la misma sucursal.
    producto_2 = Producto(nombre="Producto B", es_granel=False, precio_vigente=Decimal("10.0000"), lleva_caducidad=False)
    sesion.add(producto_2)
    sesion.flush()
    lote_2 = Lote(
        id_producto=producto_2.id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal("2.0000"),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote_2)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=producto_2.id_producto,
        id_lote=lote_2.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(20),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.commit()

    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia="migracion-multi-renglon",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=2, cantidad_gramos=None),
            RenglonEntrada(id_producto=producto_2.id_producto, cantidad_unidades=1, cantidad_gramos=None),
        ],
    )

    margen_visita = resolver_margen_visita(sesion, id_venta=venta.id_venta)
    sesion.commit()

    margen_a = resolver_margen_producto(sesion, id_producto=escenario["producto"].id_producto, id_sucursal=id_sucursal)
    margen_b = resolver_margen_producto(sesion, id_producto=producto_2.id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    renglon_a = next(r for r in venta.renglones if r.id_producto == escenario["producto"].id_producto)
    renglon_b = next(r for r in venta.renglones if r.id_producto == producto_2.id_producto)
    esperado = ((renglon_a.importe * margen_a) + (renglon_b.importe * margen_b)) / venta.total
    esperado = esperado.quantize(Decimal("0.0001"))

    assert margen_a == Decimal("0.6000")  # (2.50-1.00)/2.50
    assert margen_b == Decimal("0.8000")  # (10.00-2.00)/10.00
    assert margen_visita == esperado


def test_producto_sin_costo_vigente_se_trata_como_margen_cien_por_ciento_no_propaga_error(sesion):
    # Existencia justa para 1 unidad: la venta la agota y, al resolver el margen, ningún lote
    # tiene ya saldo positivo -> `_costo_vigente_fefo` devuelve None (FR-003 de 003), el caso que
    # esta prueba cubre. (Antes se vendía en negativo; desde la Corrección 2026-09-07 eso se
    # rechaza, así que se parte de existencia 1 y se agota.)
    escenario = crear_escenario_basico(sesion, existencia_inicial=1)
    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia="migracion-sin-costo",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=1, cantidad_gramos=None)
        ],
    )

    margen = resolver_margen_visita(sesion, id_venta=venta.id_venta)
    sesion.commit()

    # FR-003 de 003: sin costo vigente, resolver_margen_producto devuelve None. El fallback
    # documentado en margen_resolver.py trata ese renglón como costo cero (margen 100%), el mismo
    # tratamiento que ya tenía la fórmula interina para un movimiento sin lote.
    assert margen == Decimal("1.0000")


def test_visita_ya_creada_conserva_su_margen_aunque_el_costo_cambie_despues(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)
    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia="migracion-snapshot",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=2, cantidad_gramos=None)
        ],
    )
    cliente = registrar_cliente(sesion, nombre="Snapshot", fecha_nacimiento=date(1990, 1, 1))
    visita, _creada_ahora = registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta)

    assert visita.margen_relativo == Decimal("0.6000")

    # El producto sube de precio después de la visita: el margen ya congelado no debe cambiar.
    escenario["producto"].precio_vigente = Decimal("50.0000")
    sesion.commit()

    sesion.expire(visita)
    assert visita.margen_relativo == Decimal("0.6000"), (
        "margen_relativo es un snapshot (FR-005 de 002): no se recalcula si el costo o el precio "
        "cambian después de la visita, con o sin la migración a 003."
    )
