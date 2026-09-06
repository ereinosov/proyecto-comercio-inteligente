"""Unidad (006-caja-mermas-fraude, US1 — T006): funciones puras del arqueo.

`diferencia_con_signo`, `debe_generar_anomalia` y `dia_local` (research.md #4). Sin base de datos.
"""

from datetime import datetime, timezone
from decimal import Decimal

from rasero.dominio.arqueo import dia_local, debe_generar_anomalia, diferencia_con_signo


def test_diferencia_con_signo_faltante_es_negativa():
    assert diferencia_con_signo(Decimal("92.00"), Decimal("100.00")) == Decimal("-8.00")


def test_diferencia_con_signo_sobrante_es_positiva():
    assert diferencia_con_signo(Decimal("103.50"), Decimal("100.00")) == Decimal("3.50")


def test_diferencia_cero_cuando_cuadra():
    assert diferencia_con_signo(Decimal("19.50"), Decimal("19.50")) == Decimal("0.00")


def test_genera_anomalia_si_hay_diferencia_y_no_hay_motivo():
    assert debe_generar_anomalia(Decimal("-8.00"), None, Decimal("0.00")) is True


def test_no_genera_anomalia_si_hay_motivo_conocido():
    assert debe_generar_anomalia(Decimal("-8.00"), "mal dado el cambio", Decimal("0.00")) is False


def test_no_genera_anomalia_dentro_de_la_tolerancia():
    assert debe_generar_anomalia(Decimal("-0.03"), None, Decimal("0.05")) is False
    assert debe_generar_anomalia(Decimal("-0.10"), None, Decimal("0.05")) is True


def test_no_genera_anomalia_cuando_cuadra_exacto():
    assert debe_generar_anomalia(Decimal("0.00"), None, Decimal("0.00")) is False


def test_motivo_en_blanco_no_cuenta_como_motivo():
    assert debe_generar_anomalia(Decimal("-5.00"), "   ", Decimal("0.00")) is True


def test_dia_local_usa_la_zona_de_la_sucursal():
    # 03:00 UTC del 16 = 22:00 local del 15 en America/Guayaquil (UTC-5).
    instante = datetime(2026, 9, 16, 3, 0, tzinfo=timezone.utc)
    assert dia_local(instante, "America/Guayaquil").isoformat() == "2026-09-15"
