"""T058 (parte pura) — ajuste cruzado por sustituto (FR-009 b, research.md #6). Funciones puras:
no tocan la base de datos.
"""

from decimal import Decimal

from rasero.dominio.censura import ajuste_cruzado, exceso_sustituto


def test_exceso_es_lo_que_el_sustituto_vendio_por_encima_de_su_nivel_tipico():
    assert exceso_sustituto(
        demanda_sustituto=Decimal(18), maximo_n_sustituto=Decimal(12)
    ) == Decimal(6)


def test_sin_exceso_cuando_el_sustituto_no_supera_su_nivel_tipico():
    assert exceso_sustituto(
        demanda_sustituto=Decimal(9), maximo_n_sustituto=Decimal(12)
    ) == Decimal(0)


def test_sin_exceso_cuando_el_nivel_tipico_del_sustituto_no_es_estimable():
    assert exceso_sustituto(demanda_sustituto=Decimal(30), maximo_n_sustituto=None) == Decimal(0)


def test_ajuste_cruzado_suma_los_excesos_y_no_reemplaza_el_metodo_base():
    # El ajuste es aditivo sobre el estimado base (research.md #6): devuelve sólo la suma de
    # excesos; el llamador hace `valor = estimado_base + ajuste`.
    assert ajuste_cruzado(estimado_base=Decimal(10), excesos=[Decimal(6), Decimal(3)]) == Decimal(9)


def test_ajuste_cruzado_cero_sin_sustitutos_con_exceso():
    assert ajuste_cruzado(estimado_base=Decimal(10), excesos=[]) == Decimal(0)
