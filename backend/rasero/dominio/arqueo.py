"""Funciones de dominio puras del arqueo de caja (006-caja-mermas-fraude, US1 — T005, T010).

No tocan la base de datos: reciben datos ya cargados y devuelven decisiones. El servicio
(`servicios/arqueos.py`) las orquesta.

- `dia_local` (T005) — día local de la sucursal de un instante (constitución: agregaciones sobre
  el día local, no el día UTC). 006 mantiene su propia copia de esta función de una línea, como
  005 (`periodo_local_venta`) y 004 (`periodo_local`), para no acoplarse a otro módulo.
- `diferencia_con_signo` / `debe_generar_anomalia` (T010) — research.md #4.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

_DOS_DECIMALES = Decimal("0.01")


def dia_local(instante: datetime, zona_horaria: str) -> date:
    """`(instante AT TIME ZONE zona_horaria)::date`."""
    return instante.astimezone(ZoneInfo(zona_horaria)).date()


def diferencia_con_signo(monto_contado: Decimal, monto_esperado: Decimal) -> Decimal:
    """`monto_contado - monto_esperado`, cuantizada a 2 decimales. Negativa = faltante;
    positiva = sobrante (FR-003).
    """
    return (Decimal(monto_contado) - Decimal(monto_esperado)).quantize(_DOS_DECIMALES)


def debe_generar_anomalia(
    diferencia: Decimal, motivo_conocido: str | None, tolerancia: Decimal
) -> bool:
    """`True` sólo si la diferencia excede la tolerancia (en valor absoluto) **y** no se anotó un
    motivo conocido (FR-004). Una diferencia con motivo anotado NO genera anomalía; una sin motivo
    queda como `anomalia_caja` de origen efectivo (FR-027).
    """
    if motivo_conocido is not None and motivo_conocido.strip():
        return False
    return abs(Decimal(diferencia)) > Decimal(tolerancia)
