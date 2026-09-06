"""Unidad (006-caja-mermas-fraude, US3 — T030): funciones puras de los indicadores por operador.

`tasa_anulaciones`, `concentracion_bajo_lista`, `mediana`, `se_desvia`,
`reparto_proporcional_faltante` (research.md #7, #16). Sin librería estadística, sin base de datos.
"""

from decimal import Decimal

from rasero.dominio.indicadores_operador import (
    concentracion_bajo_lista,
    mediana,
    reparto_proporcional_faltante,
    se_desvia,
    tasa_anulaciones,
)


def test_tasa_anulaciones():
    assert tasa_anulaciones(8, 40) == Decimal("0.2000")


def test_tasa_con_denominador_cero_es_cero():
    assert tasa_anulaciones(0, 0) == Decimal("0")


def test_concentracion_bajo_lista():
    assert concentracion_bajo_lista(3, 12) == Decimal("0.2500")


def test_mediana_impar():
    assert mediana([Decimal("0.03"), Decimal("0.20"), Decimal("0.04")]) == Decimal("0.04")


def test_mediana_par_promedia_los_centrales():
    assert mediana([Decimal("0.02"), Decimal("0.04"), Decimal("0.06"), Decimal("0.20")]) == Decimal(
        "0.0500"
    )


def test_mediana_vacia_es_none():
    assert mediana([]) is None


def test_mediana_robusta_a_un_outlier():
    # Un operador extremo (0.90) no arrastra la mediana como haría la media.
    valores = [Decimal("0.03"), Decimal("0.03"), Decimal("0.04"), Decimal("0.04"), Decimal("0.90")]
    assert mediana(valores) == Decimal("0.04")


def test_se_desvia_cuando_supera_la_razon_por_la_mediana():
    assert se_desvia(Decimal("0.20"), Decimal("0.03"), Decimal("2.0")) is True  # 0.20 >= 0.06
    assert se_desvia(Decimal("0.05"), Decimal("0.03"), Decimal("2.0")) is False  # 0.05 < 0.06


def test_se_desvia_sin_pares_o_mediana_cero_es_falso():
    assert se_desvia(Decimal("0.50"), None, Decimal("2.0")) is False
    assert se_desvia(Decimal("0.50"), Decimal("0"), Decimal("2.0")) is False


def test_reparto_proporcional_suma_exactamente_el_faltante():
    reparto = reparto_proporcional_faltante(
        Decimal("10"), {1: Decimal("6"), 2: Decimal("3"), 3: Decimal("1")}
    )
    assert sum(reparto.values()) == Decimal("10")
    assert reparto[1] >= reparto[2] >= reparto[3]


def test_reparto_sin_movimiento_o_sin_faltante_es_cero():
    assert reparto_proporcional_faltante(Decimal("10"), {1: Decimal("0")}) == {1: Decimal("0")}
    assert reparto_proporcional_faltante(Decimal("0"), {1: Decimal("5")}) == {1: Decimal("0")}
