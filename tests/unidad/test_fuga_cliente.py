"""T028 — Prueba obligatoria (Principio III): supera 1× su intervalo esperado -> `activa`;
supera 5× su intervalo o 12 meses (el que sea mayor) -> `confirmada`; por debajo de 1x -> sin
señal. La resolución por nueva visita (FR-009) es responsabilidad del servicio (T032), no de
esta función pura — se prueba en tests/integracion/test_anonimizacion.py.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.fuga_cliente import evaluar_estado_fuga

AHORA = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_por_debajo_del_intervalo_esperado_no_hay_senal():
    resultado = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("20"), dias_sin_visita=10, ahora=AHORA
    )
    assert resultado.estado == "sin_senal"
    assert resultado.instante_purga_programada is None


def test_supera_una_vez_el_intervalo_esperado_queda_activa():
    resultado = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("20"), dias_sin_visita=21, ahora=AHORA
    )
    assert resultado.estado == "activa"
    assert resultado.instante_purga_programada is None


def test_supera_cinco_veces_el_intervalo_esperado_queda_confirmada_con_purga_programada():
    # intervalo=20 -> 5x=100 días, muy por debajo del piso de 365, así que 100 no basta;
    # se necesita superar el piso de 12 meses en este caso (ver siguiente prueba). Con un
    # intervalo más largo, 5x sí puede superar el piso.
    resultado = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("100"), dias_sin_visita=501, ahora=AHORA
    )
    assert resultado.estado == "confirmada"
    assert resultado.instante_purga_programada == AHORA + timedelta(days=90)


def test_intervalo_corto_no_confirma_fuga_hasta_el_piso_de_doce_meses():
    """Cliente muy frecuente (intervalo de 7 días): 5x serían apenas 35 días, un plazo
    demasiado corto para confirmar la fuga en términos absolutos (research.md #FR-014, el piso
    existe exactamente para este caso).
    """
    resultado_a_los_35_dias = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("7"), dias_sin_visita=35, ahora=AHORA
    )
    assert resultado_a_los_35_dias.estado == "activa", "35 días (5x) no debe confirmar todavía"

    resultado_a_los_365_dias = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("7"), dias_sin_visita=365, ahora=AHORA
    )
    assert resultado_a_los_365_dias.estado == "confirmada"
    assert resultado_a_los_365_dias.instante_purga_programada == AHORA + timedelta(days=90)


def test_el_umbral_de_confirmacion_es_el_mayor_entre_5x_y_el_piso():
    # intervalo=200 -> 5x=1000, mayor que el piso de 365: manda el múltiplo, no el piso.
    justo_por_debajo = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("200"), dias_sin_visita=999, ahora=AHORA
    )
    assert justo_por_debajo.estado == "activa"

    justo_en_el_umbral = evaluar_estado_fuga(
        intervalo_esperado_dias=Decimal("200"), dias_sin_visita=1000, ahora=AHORA
    )
    assert justo_en_el_umbral.estado == "confirmada"
