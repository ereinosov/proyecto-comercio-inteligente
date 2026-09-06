"""Helper de tiempo de 007-pagos-seguridad (T005).

Mismo criterio de día local que 001/004/005/006: toda entrada de `bitacora_auditoria` y toda
agregación de `cobertura_pago` se fecha por el día local de la sucursal (constitución, "Tiempo";
research.md #8). 007 implementa el suyo, no importa el de otro módulo.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def dia_local(instante: datetime, zona_horaria: str) -> date:
    """`(instante AT TIME ZONE zona)::date`. Acepta un `datetime` con o sin tzinfo (los sin tzinfo
    se interpretan como UTC, coherente con `TIMESTAMPTZ`).
    """
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(ZoneInfo(zona_horaria)).date()


def hoy_local(zona_horaria: str) -> date:
    """El día local actual de una sucursal."""
    return datetime.now(ZoneInfo(zona_horaria)).date()
