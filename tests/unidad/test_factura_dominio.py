"""Prueba obligatoria (Principio III) del dominio de 009: descomposición del IVA (incluido en el
precio) y formateo del secuencial.
"""

from decimal import Decimal

import pytest

from rasero.dominio.factura import descomponer_iva, formatear_secuencial


@pytest.mark.parametrize(
    "total",
    ["8.63", "10.00", "0.01", "1234.57", "99.99", "3.33"],
)
def test_subtotal_mas_iva_igual_total_sin_perdida(total):
    subtotal, iva = descomponer_iva(Decimal(total), Decimal("0.15"))
    assert subtotal + iva == Decimal(total)
    assert iva >= 0


def test_descomposicion_ejemplo_del_spec():
    # Escenario 1 del quickstart: total 8,63 con IVA incluido al 15 %.
    subtotal, iva = descomponer_iva(Decimal("8.63"), Decimal("0.15"))
    assert subtotal == Decimal("7.50")
    assert iva == Decimal("1.13")


def test_formatear_secuencial():
    assert formatear_secuencial("001", "001", 42) == "001-001-000000042"
    assert formatear_secuencial("1", "2", 1) == "001-002-000000001"
    assert formatear_secuencial("001", "001", 123456789) == "001-001-123456789"
