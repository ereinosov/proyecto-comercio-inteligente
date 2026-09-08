"""Límites de períodos (semana / mes) en la zona horaria de una sucursal (008-reportes-inteligencia).

Función pura: no toca la base de datos. Mismo criterio que 006 usa para `dia_local` — una venta
a las 23:30 hora local del domingo pertenece a esa semana, no a la siguiente en UTC.

`semana` = semana ISO local (lunes 00:00 → lunes 00:00 siguiente).
`mes` = mes calendario local (día 1 00:00 → día 1 00:00 del mes siguiente).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_MESES = (
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
)


@dataclass(frozen=True)
class Periodo:
    inicio_utc: datetime
    fin_utc: datetime  # exclusivo
    etiqueta: str
    inicio_local: date
    completo: bool  # False si el período se extiende más allá de "ahora" (parcial en el borde)


def _medianoche_local_utc(d: date, tz: ZoneInfo) -> datetime:
    """Medianoche local de `d` en `tz`, expresada en UTC."""
    return datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(ZoneInfo("UTC"))


def _inicio_de_semana(d: date) -> date:
    return d - timedelta(days=d.weekday())  # lunes


def _inicio_de_mes(d: date) -> date:
    return d.replace(day=1)


def _sumar_mes(d: date) -> date:
    return date(d.year + (d.month // 12), (d.month % 12) + 1, 1)


def periodos_locales(
    zona_horaria: str, granularidad: str, n: int, *, ahora: datetime | None = None
) -> list[Periodo]:
    """Los `n` últimos períodos (`granularidad` ∈ {"semana", "mes"}) que terminan en el período
    que contiene `ahora` (UTC), incluido. El más reciente puede estar `completo=False`.
    """
    if granularidad not in ("semana", "mes"):
        raise ValueError(f"granularidad no soportada: {granularidad!r}")
    if n < 1:
        return []

    tz = ZoneInfo(zona_horaria)
    ahora = ahora or datetime.now(ZoneInfo("UTC"))
    hoy_local = ahora.astimezone(tz).date()

    if granularidad == "semana":
        inicio_actual = _inicio_de_semana(hoy_local)
        inicios = [inicio_actual - timedelta(weeks=k) for k in range(n - 1, -1, -1)]
        fin_de = lambda ini: ini + timedelta(weeks=1)
        etiqueta_de = lambda ini: f"sem. del {ini.day} {_MESES[ini.month - 1]}"
    else:
        inicio_actual = _inicio_de_mes(hoy_local)
        inicios = []
        cursor = inicio_actual
        for _ in range(n):
            inicios.append(cursor)
            cursor = date(
                cursor.year - (1 if cursor.month == 1 else 0),
                12 if cursor.month == 1 else cursor.month - 1,
                1,
            )
        inicios.reverse()
        fin_de = _sumar_mes
        etiqueta_de = lambda ini: f"{_MESES[ini.month - 1]} {ini.year}"

    periodos: list[Periodo] = []
    for ini in inicios:
        fin = fin_de(ini)
        ini_utc = _medianoche_local_utc(ini, tz)
        fin_utc = _medianoche_local_utc(fin, tz)
        periodos.append(
            Periodo(
                inicio_utc=ini_utc,
                fin_utc=fin_utc,
                etiqueta=etiqueta_de(ini),
                inicio_local=ini,
                completo=fin_utc <= ahora,
            )
        )
    return periodos


def dia_local(instante: datetime, zona_horaria: str) -> date:
    """Fecha local de un instante en la zona de la sucursal (mismo criterio que 006)."""
    return instante.astimezone(ZoneInfo(zona_horaria)).date()
