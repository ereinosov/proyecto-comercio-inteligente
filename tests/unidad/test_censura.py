"""T006 (parte pura) — método base de descensura por quiebre (FR-009 a), fijado por
`/speckit-clarify`: la demanda de un período censurado se sustituye por el MÁXIMO de la demanda
observada del producto entre los N períodos recientes SIN quiebre (research.md #5). Funciones
puras: no tocan la base de datos.

El ajuste cruzado por sustituto (FR-009 b) y la evidencia real de `consulta_no_atendida` (FR-007)
NO se ejercen aquí — pertenecen a la User Story 6 y a una rama bloqueada por 001 respectivamente.
"""

from datetime import date, timedelta
from decimal import Decimal

from rasero.dominio.censura import (
    ESTADO_CENSURA_TOTAL,
    ESTADO_OK,
    RESPALDO_METODO_BASE,
    RESPALDO_NO_APLICA,
    PeriodoObservado,
    corregir_serie_por_quiebre,
    estimar_latente_metodo_base,
)

BASE = date(2026, 6, 1)


def _dia(n: int) -> date:
    return BASE + timedelta(days=n)


def _serie(cantidades_y_quiebre: list[tuple[int, int]]) -> list[PeriodoObservado]:
    return [
        PeriodoObservado(periodo=_dia(i), cantidad=Decimal(c), dias_en_quiebre=Decimal(q))
        for i, (c, q) in enumerate(cantidades_y_quiebre)
    ]


def test_metodo_base_toma_el_maximo_de_los_n_periodos_recientes_sin_quiebre():
    assert estimar_latente_metodo_base(
        periodos_sin_quiebre_previos=[Decimal(8), Decimal(12), Decimal(5)], n=30
    ) == Decimal(12)


def test_metodo_base_limita_la_ventana_a_los_n_mas_recientes():
    # n=2: sólo cuentan los dos últimos (5 y 20), no el 100 antiguo.
    assert estimar_latente_metodo_base(
        periodos_sin_quiebre_previos=[Decimal(100), Decimal(5), Decimal(20)], n=2
    ) == Decimal(20)


def test_sin_ningun_periodo_sin_quiebre_previo_el_metodo_base_no_estima_nada():
    assert estimar_latente_metodo_base(periodos_sin_quiebre_previos=[], n=30) is None


def test_periodo_de_quiebre_se_corrige_al_maximo_reciente_y_nunca_por_debajo_de_lo_observado():
    # 3 días vendiendo (10, 12, 9), luego 2 días en quiebre con ventas 0.
    serie = _serie([(10, 0), (12, 0), (9, 0), (0, 1), (0, 1)])
    corregidos = {c.periodo: c for c in corregir_serie_por_quiebre(serie, n=30)}

    for i in (0, 1, 2):
        assert corregidos[_dia(i)].correccion_quiebre == Decimal(0)
        assert corregidos[_dia(i)].respaldo_quiebre == RESPALDO_NO_APLICA
        assert corregidos[_dia(i)].valor == corregidos[_dia(i)].valor_observado

    for i in (3, 4):
        c = corregidos[_dia(i)]
        assert c.valor == Decimal(12), "FR-009 a: máximo de los períodos recientes sin quiebre"
        assert c.valor >= c.valor_observado, "FR-006: corregida nunca menor que observada"
        assert c.correccion_quiebre == Decimal(12)
        assert c.respaldo_quiebre == RESPALDO_METODO_BASE
        assert c.censura_total is False
        assert c.estado == ESTADO_OK


def test_periodo_sin_quiebre_no_recibe_correccion_aunque_su_demanda_sea_alta():
    serie = _serie([(5, 0), (0, 1), (50, 0)])
    corregidos = {c.periodo: c for c in corregir_serie_por_quiebre(serie, n=30)}
    # FR-011: el día 2 vendió 50 sin quiebre — se conserva tal cual.
    assert corregidos[_dia(2)].valor == Decimal(50)
    assert corregidos[_dia(2)].correccion_quiebre == Decimal(0)


def test_censura_total_cuando_no_hay_ningun_periodo_sin_quiebre():
    # Agotado todo el histórico disponible, sin consultas no atendidas (FR-012).
    serie = _serie([(0, 1), (0, 1), (0, 1)])
    corregidos = corregir_serie_por_quiebre(serie, n=30)
    for c in corregidos:
        assert c.censura_total is True
        assert c.valor is None, "nunca un 0 ni un valor inventado"
        assert c.estado == ESTADO_CENSURA_TOTAL
        assert c.correccion_quiebre == Decimal(0)


def test_quiebre_antes_de_la_primera_actividad_del_producto_es_censura_total_no_un_numero():
    # research.md #5: sólo se descensura con períodos sin quiebre PREVIOS. Un quiebre antes de
    # que el producto tuviera stock por primera vez no se puede estimar — no se fabrica un número
    # a partir de días posteriores (FR-012, honesto en vez de inventado).
    serie = _serie([(0, 1), (0, 1), (7, 0), (9, 0)])
    corregidos = {c.periodo: c for c in corregir_serie_por_quiebre(serie, n=30)}
    assert corregidos[_dia(0)].censura_total is True
    assert corregidos[_dia(0)].valor is None
    assert corregidos[_dia(0)].estado == ESTADO_CENSURA_TOTAL
    # El día 3, sin quiebre, intacto.
    assert corregidos[_dia(3)].valor == Decimal(9)
