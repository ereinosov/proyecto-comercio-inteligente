"""Regresión #3 de la auditoría end-to-end (parte pura): `dominio/costo_inventario`.

`Lote.costo_unitario` es por unidad, o por kilogramo si el producto es granel; la existencia de
un granel se registra en gramos. Multiplicar gramos × costo/kg en crudo inflaba el valor ×1000.
"""

from decimal import Decimal

from rasero.dominio.costo_inventario import valor_existencia


def test_producto_por_unidad_multiplica_directo():
    assert valor_existencia(3, Decimal("1.50"), es_granel=False) == Decimal("4.50")


def test_granel_convierte_gramos_a_kilogramos():
    # 700 g de un producto a 4.00 / kg = 2.80, nunca 2800.00
    assert valor_existencia(700, Decimal("4.00"), es_granel=True) == Decimal("2.80")


def test_granel_cantidad_grande_no_se_infla_mil_veces():
    # 50 kg a 2.0000 / kg = 100.0000 (el bug daría 100 000.0000)
    assert valor_existencia(50_000, Decimal("2.0000"), es_granel=True) == Decimal("100.0000")


def test_acepta_str_y_enteros():
    assert valor_existencia("1500", "3.0000", es_granel=True) == Decimal("4.5000")
