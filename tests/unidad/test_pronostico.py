"""T033 (parte pura) — suavizado exponencial simple, línea base determinista y multiplicadores de
tramo del mes (FR-020, FR-022, research.md #7 y #8d). Funciones puras: no tocan la base de datos.
"""

from datetime import date
from decimal import Decimal

from rasero.dominio.pronostico import (
    comparar_contra_linea_base,
    linea_base_promedio_movil,
    multiplicadores_tramo_mes,
    proyectar,
    suavizado_exponencial_simple,
    tramo_de,
)

_TRAMOS = ((1, 7), (8, 15), (16, 22), (23, 31))


def test_suavizado_exponencial_formula():
    # nivel_0 = 10; nivel_1 = 0.3*20 + 0.7*10 = 13
    assert suavizado_exponencial_simple([Decimal(10), Decimal(20)], Decimal("0.3")) == Decimal(13)


def test_suavizado_de_serie_estable_converge_al_nivel():
    assert suavizado_exponencial_simple([Decimal(10)] * 20, Decimal("0.3")) == Decimal(10)


def test_linea_base_es_el_promedio_de_los_ultimos_n():
    assert linea_base_promedio_movil([Decimal(10), Decimal(20), Decimal(30)], 2) == Decimal(25)


def test_tramo_de_ubica_el_dia_del_mes():
    assert tramo_de(date(2026, 1, 3), _TRAMOS) == 0
    assert tramo_de(date(2026, 1, 10), _TRAMOS) == 1
    assert tramo_de(date(2026, 1, 25), _TRAMOS) == 3
    # febrero no tiene días 29-31: el 28 cae en el último tramo igual.
    assert tramo_de(date(2026, 2, 28), _TRAMOS) == 3


def test_multiplicadores_de_tramo_relativos_a_la_media_global():
    tramos = ((1, 15), (16, 31))
    hist = [
        (date(2026, 1, d), Decimal(v))
        for d, v in [(1, 10), (2, 10), (3, 10), (20, 20), (21, 20), (22, 20)]
    ]
    m = multiplicadores_tramo_mes(hist, tramos, minimo_por_tramo=2)
    assert m["0"] == "0.6667"  # media tramo 10 / media global 15
    assert m["1"] == "1.3333"  # media tramo 20 / media global 15


def test_multiplicador_1_cuando_el_tramo_tiene_pocas_observaciones():
    tramos = ((1, 15), (16, 31))
    hist = [
        (date(2026, 1, 1), Decimal(10)),
        (date(2026, 1, 2), Decimal(10)),
        (date(2026, 1, 20), Decimal(30)),
    ]
    m = multiplicadores_tramo_mes(hist, tramos, minimo_por_tramo=2)
    assert m["1"] == "1.0000"  # sólo una observación en el tramo 1: sin ajuste


def test_suavizado_gana_a_la_linea_base_en_serie_con_tendencia():
    creciente = [Decimal(i) for i in range(1, 41)]
    err_ses, err_base = comparar_contra_linea_base(
        corregida=creciente,
        observada=list(creciente),
        alfa=Decimal("0.3"),
        n_linea_base=30,
        cola=14,
    )
    assert err_ses is not None and err_base is not None
    assert err_ses < err_base


def test_comparar_devuelve_none_sin_historia_suficiente():
    err_ses, err_base = comparar_contra_linea_base(
        corregida=[Decimal(1)] * 5,
        observada=[Decimal(1)] * 5,
        alfa=Decimal("0.3"),
        n_linea_base=30,
        cola=14,
    )
    assert err_ses is None and err_base is None


def test_proyeccion_plana_en_horizonte_corto():
    dias = [date(2026, 1, 1), date(2026, 1, 2)]
    p = proyectar(nivel=Decimal(10), dias_futuros=dias, multiplicadores=None, tramos=_TRAMOS)
    assert [v for _d, v in p] == [Decimal(10), Decimal(10)]


def test_proyeccion_aplica_el_multiplicador_del_tramo_en_horizonte_medio():
    tramos = ((1, 15), (16, 31))
    dias = [date(2026, 1, 3), date(2026, 1, 20)]
    p = proyectar(
        nivel=Decimal(10),
        dias_futuros=dias,
        multiplicadores={"0": "0.5", "1": "2.0"},
        tramos=tramos,
    )
    assert [v for _d, v in p] == [Decimal(5), Decimal(20)]
