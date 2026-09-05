"""T021 — Prueba unitaria: resolución de precio efectivo por sucursal. Override de
`producto_precio_sucursal` si existe, si no el precio base del producto (FR-050).
"""

from decimal import Decimal

from rasero.dominio.resolucion_precio import resolver_precio_efectivo


def test_usa_el_override_cuando_existe():
    precio = resolver_precio_efectivo(
        precio_base=Decimal("10.0000"), override_sucursal=Decimal("9.0000")
    )
    assert precio == Decimal("9.0000")


def test_usa_el_precio_base_cuando_no_hay_override():
    precio = resolver_precio_efectivo(precio_base=Decimal("10.0000"), override_sucursal=None)
    assert precio == Decimal("10.0000")


def test_dos_sucursales_resuelven_distinto_para_el_mismo_producto():
    # Escenario 5 de User Story 4: mismo producto, precio distinto por sucursal.
    precio_quevedo = resolver_precio_efectivo(
        precio_base=Decimal("10.0000"), override_sucursal=None
    )
    precio_buena_fe = resolver_precio_efectivo(
        precio_base=Decimal("10.0000"), override_sucursal=Decimal("9.0000")
    )
    assert precio_quevedo == Decimal("10.0000")
    assert precio_buena_fe == Decimal("9.0000")
    assert precio_quevedo != precio_buena_fe
