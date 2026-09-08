"""Prueba de unidad de `dominio/periodo_local` — 008-reportes-inteligencia, User Story 2.

- una venta a las 23:30 hora local del domingo cae en esa semana, no en la siguiente (UTC);
- "mes" = mes calendario local, no ventanas de 30 días;
- el período más reciente puede estar `completo=False` (parcial en el borde).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from rasero.dominio.periodo_local import dia_local, periodos_locales

GYE = "America/Guayaquil"  # UTC-5, sin horario de verano


def test_semana_local_no_desfasada_por_utc():
    # Domingo 6 sep 2026, 23:30 local (GYE, UTC-5) = lunes 7 sep 04:30 UTC.
    instante_utc = datetime(2026, 9, 7, 4, 30, tzinfo=ZoneInfo("UTC"))
    assert dia_local(instante_utc, GYE) == datetime(2026, 9, 6).date()

    # `ahora` = jueves 10 sep → la semana actual empieza el lunes 7 sep. Pedimos 2 semanas:
    # la venta del domingo 6 cae en la semana anterior (empieza lunes 31 ago), NUNCA en la del 7.
    ahora = datetime(2026, 9, 10, 12, 0, tzinfo=ZoneInfo("UTC"))
    semanas = periodos_locales(GYE, "semana", 2, ahora=ahora)
    assert semanas[0].inicio_local == datetime(2026, 8, 31).date()
    assert semanas[1].inicio_local == datetime(2026, 9, 7).date()
    assert semanas[0].inicio_utc <= instante_utc < semanas[0].fin_utc


def test_mes_es_mes_calendario_no_ventana_de_30_dias():
    ahora = datetime(2026, 9, 15, 12, 0, tzinfo=ZoneInfo("UTC"))
    meses = periodos_locales(GYE, "mes", 3, ahora=ahora)
    assert [m.inicio_local.month for m in meses] == [7, 8, 9]
    assert [m.inicio_local.day for m in meses] == [1, 1, 1]


def test_periodo_de_borde_incompleto():
    # Estamos a media semana → la semana actual no está completa.
    ahora = datetime(2026, 9, 9, 12, 0, tzinfo=ZoneInfo("UTC"))  # miércoles
    semanas = periodos_locales(GYE, "semana", 3, ahora=ahora)
    assert semanas[-1].completo is False
    assert all(s.completo for s in semanas[:-1])


def test_n_cero_devuelve_lista_vacia():
    assert periodos_locales(GYE, "mes", 0) == []
