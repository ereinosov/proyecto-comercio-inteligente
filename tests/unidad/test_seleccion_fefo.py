"""T018 — Prueba obligatoria (Principio III): selección de lote FEFO, incluido el caso de un
lote posterior que caduca antes que uno más antiguo.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from rasero.dominio.seleccion_lote import ordenar_fefo


@dataclass
class LoteFalso:
    id_lote: int
    instante_entrada: datetime
    fecha_caducidad: date | None


def _instante(dias_desde_1_sep: int) -> datetime:
    return datetime(2026, 9, 1, tzinfo=timezone.utc).replace(day=1 + dias_desde_1_sep)


def test_lote_posterior_que_caduca_antes_sale_primero():
    lote_antiguo_caduca_tarde = LoteFalso(
        id_lote=1, instante_entrada=_instante(0), fecha_caducidad=date(2026, 10, 1)
    )
    lote_nuevo_caduca_pronto = LoteFalso(
        id_lote=2, instante_entrada=_instante(5), fecha_caducidad=date(2026, 9, 10)
    )
    resultado = ordenar_fefo([lote_antiguo_caduca_tarde, lote_nuevo_caduca_pronto])
    assert [l.id_lote for l in resultado] == [2, 1]


def test_sin_caducidad_decide_la_entrada_mas_antigua():
    a = LoteFalso(id_lote=1, instante_entrada=_instante(3), fecha_caducidad=None)
    b = LoteFalso(id_lote=2, instante_entrada=_instante(1), fecha_caducidad=None)
    resultado = ordenar_fefo([a, b])
    assert [l.id_lote for l in resultado] == [2, 1]


def test_lote_sin_caducidad_nunca_se_adelanta_a_uno_que_si_caduca():
    sin_caducidad = LoteFalso(id_lote=1, instante_entrada=_instante(0), fecha_caducidad=None)
    con_caducidad = LoteFalso(
        id_lote=2, instante_entrada=_instante(10), fecha_caducidad=date(2026, 12, 31)
    )
    resultado = ordenar_fefo([sin_caducidad, con_caducidad])
    assert [l.id_lote for l in resultado] == [2, 1]


def test_misma_fecha_de_caducidad_desempata_por_entrada():
    misma_fecha = date(2026, 10, 1)
    primero = LoteFalso(id_lote=1, instante_entrada=_instante(1), fecha_caducidad=misma_fecha)
    segundo = LoteFalso(id_lote=2, instante_entrada=_instante(2), fecha_caducidad=misma_fecha)
    resultado = ordenar_fefo([segundo, primero])
    assert [l.id_lote for l in resultado] == [1, 2]
