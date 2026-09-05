"""T044 (parte pura) — normalización de la demanda por el precio vigente del período (FR-025,
research.md #8b). Función pura: no toca la base de datos.
"""

from decimal import Decimal

from rasero.dominio.serie_demanda import normalizar_demanda_por_precio


def test_precio_historico_mayor_que_el_de_referencia_ajusta_la_demanda_al_alza():
    # p_hist 12, p_ref 10, epsilon 1 -> factor 1.2 -> 10 unidades pasan a 12.
    valor, delta = normalizar_demanda_por_precio(
        cantidad=Decimal(10),
        precio_periodo=Decimal("12.0000"),
        precio_referencia=Decimal("10.0000"),
        epsilon=Decimal("1.000"),
    )
    assert valor == Decimal("12.0000")
    assert delta == Decimal("2.0000")


def test_precio_historico_menor_ajusta_la_demanda_a_la_baja():
    valor, delta = normalizar_demanda_por_precio(
        cantidad=Decimal(10),
        precio_periodo=Decimal("8.0000"),
        precio_referencia=Decimal("10.0000"),
        epsilon=Decimal("1.000"),
    )
    assert valor == Decimal("8.0000")
    assert delta == Decimal("-2.0000")


def test_precio_igual_no_corrige():
    valor, delta = normalizar_demanda_por_precio(
        cantidad=Decimal(10),
        precio_periodo=Decimal("10.0000"),
        precio_referencia=Decimal("10.0000"),
        epsilon=Decimal("1.000"),
    )
    assert valor == Decimal("10.0000")
    assert delta == Decimal(0)


def test_sin_precio_del_periodo_no_hay_correccion():
    valor, delta = normalizar_demanda_por_precio(
        cantidad=Decimal(10),
        precio_periodo=None,
        precio_referencia=Decimal("10.0000"),
        epsilon=Decimal("1.000"),
    )
    assert valor == Decimal(10)
    assert delta == Decimal(0)


def test_elasticidad_distinta_de_uno_se_aplica_como_exponente():
    # epsilon 2: factor (12/10)^2 = 1.44 -> 10 -> 14.4
    valor, _delta = normalizar_demanda_por_precio(
        cantidad=Decimal(10),
        precio_periodo=Decimal("12.0000"),
        precio_referencia=Decimal("10.0000"),
        epsilon=Decimal("2.000"),
    )
    assert valor == Decimal("14.4000")
