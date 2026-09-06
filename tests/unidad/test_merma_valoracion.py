"""Unidad (006-caja-mermas-fraude, US2 — T018): valoración de la merma.

`valorar_merma` (FR-010, SC-005): con costo -> cantidad × costo; sin costo -> None ("no
calculable"), NUNCA Decimal("0.00"). Sin base de datos.
"""

from decimal import Decimal

from rasero.dominio.merma import periodo_entre_conteos, valorar_merma
from datetime import date


def test_valoracion_con_costo_conocido():
    assert valorar_merma(Decimal("3"), Decimal("2.0000")) == Decimal("6.00")


def test_valoracion_granel_sobre_gramos_al_costo_por_gramo():
    # 2,35 kg de fresco = 2350 g; costo por kg 4.00 -> por gramo 0.004; 2350 × 0.004 = 9.40.
    costo_por_gramo = Decimal("4.0000") / Decimal("1000")
    assert valorar_merma(Decimal("2350"), costo_por_gramo) == Decimal("9.40")


def test_sin_costo_es_no_calculable_nunca_cero():
    valor = valorar_merma(Decimal("5"), None)
    assert valor is None
    assert valor != Decimal("0.00")


def test_periodo_fuera_de_conteo_es_el_dia_de_la_declaracion():
    hoy = date(2026, 9, 10)
    assert periodo_entre_conteos(
        fecha_conteo_actual=None, fecha_conteo_anterior=None, fecha_declaracion=hoy
    ) == (hoy, hoy)


def test_periodo_entre_conteos_va_del_anterior_al_actual():
    assert periodo_entre_conteos(
        fecha_conteo_actual=date(2026, 9, 15),
        fecha_conteo_anterior=date(2026, 9, 1),
        fecha_declaracion=date(2026, 9, 15),
    ) == (date(2026, 9, 1), date(2026, 9, 15))
