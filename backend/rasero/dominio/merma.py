"""Funciones de dominio puras de la merma (006-caja-mermas-fraude, US2 — T022).

- `valorar_merma` — `cantidad_faltante × costo_unitario_lote`. Con `costo_unitario_lote is None`
  devuelve `None` ("no calculable"), NUNCA `Decimal("0.00")` (FR-010, SC-005; mismo criterio que
  001 para el capital inmovilizado). Para un producto a granel, `cantidad_faltante` está en gramos
  y el costo es por kilogramo: el llamador pasa el costo ya en la misma base que la cantidad (por
  gramo) — la conversión, si aplica, la resuelve el servicio con `producto.es_granel` de 001.
- `periodo_entre_conteos` — el período de atribución de la merma (FR-011): entre el conteo que la
  reveló y el conteo anterior del mismo alcance; para una merma declarada fuera de conteo, el
  propio día de la declaración (research.md #5).
"""

from datetime import date
from decimal import Decimal

_DOS_DECIMALES = Decimal("0.01")


def valorar_merma(
    cantidad_faltante: Decimal, costo_unitario_lote: Decimal | None
) -> Decimal | None:
    """Valor de la pérdida. `None` = "no calculable" (falta el costo del lote)."""
    if costo_unitario_lote is None:
        return None
    return (Decimal(cantidad_faltante) * Decimal(costo_unitario_lote)).quantize(_DOS_DECIMALES)


def periodo_entre_conteos(
    *,
    fecha_conteo_actual: date | None,
    fecha_conteo_anterior: date | None,
    fecha_declaracion: date,
) -> tuple[date, date]:
    """`(periodo_desde, periodo_hasta)` en días locales.

    - Merma de un conteo: desde la fecha de resolución del conteo anterior del mismo alcance (o la
      del conteo actual si no hubo anterior) hasta la fecha de resolución del conteo actual.
    - Merma declarada fuera de conteo: el propio día de la declaración (desde == hasta).
    """
    if fecha_conteo_actual is None:
        return (fecha_declaracion, fecha_declaracion)
    desde = fecha_conteo_anterior or fecha_conteo_actual
    return (min(desde, fecha_conteo_actual), fecha_conteo_actual)
