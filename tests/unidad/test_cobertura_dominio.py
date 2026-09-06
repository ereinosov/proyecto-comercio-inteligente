"""Unidad de las funciones puras de cobertura (007, US1 — T007)."""

from datetime import date

from rasero.dominio.cobertura import cerrar_tramo_anterior, cobertura_en_fecha, cuota_no_atendida


def test_cobertura_en_fecha_respeta_tramos_historicos():
    tramos = [(date(2026, 1, 1), date(2026, 3, 31)), (date(2026, 6, 1), None)]
    assert cobertura_en_fecha(tramos, date(2026, 2, 15)) is True
    assert cobertura_en_fecha(tramos, date(2026, 4, 15)) is False  # entre tramos
    assert cobertura_en_fecha(tramos, date(2026, 9, 1)) is True  # tramo vigente
    assert cobertura_en_fecha([], date(2026, 1, 1)) is False


def test_cuota_no_atendida_como_cadena_decimal():
    cuotas = cuota_no_atendida({1: 3, 2: 1, 3: 0}, total=4)
    assert cuotas == {1: "0.7500", 2: "0.2500", 3: "0"}


def test_cuota_no_atendida_total_cero():
    assert cuota_no_atendida({1: 0, 2: 0}, total=0) == {1: "0", 2: "0"}


def test_cerrar_tramo_anterior_es_el_dia_previo():
    assert cerrar_tramo_anterior(date(2026, 3, 1)) == date(2026, 2, 28)
