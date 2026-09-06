"""Funciones de dominio puras de la cobertura de medios de pago (007, US1 — T009).

- `cobertura_en_fecha` — resuelve si un `(medio, sucursal)` estaba aceptado en una fecha dada,
  a partir de sus tramos de vigencia `[fecha_desde, fecha_hasta]` (research.md #5, FR-002).
- `cuota_no_atendida` — razón de eventos de intención no atendida por medio deseado sobre el total
  del período, como cadena decimal (Lectura Crítica n.º 4). Nunca coma flotante.
- `cerrar_tramo_anterior` — la fecha en que se cierra el tramo vigente al declarar uno nuevo.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

_CUATRO_DECIMALES = Decimal("0.0001")


def cobertura_en_fecha(tramos: list[tuple[date, date | None]], fecha: date) -> bool:
    """`tramos` es una lista de `(fecha_desde, fecha_hasta)` (`fecha_hasta` `None` = vigente).
    Devuelve `True` si `fecha` cae dentro de algún tramo (bordes incluidos).
    """
    for desde, hasta in tramos:
        if fecha >= desde and (hasta is None or fecha <= hasta):
            return True
    return False


def cuota_no_atendida(eventos_por_medio: dict[int, int], total: int) -> dict[int, str]:
    """`{id_medio: "0.NNNN"}`. `"0"` para todos si `total == 0`."""
    if total <= 0:
        return {medio: "0" for medio in eventos_por_medio}
    return {
        medio: (
            "0"
            if n == 0
            else str(
                (Decimal(n) / Decimal(total)).quantize(_CUATRO_DECIMALES, rounding=ROUND_HALF_UP)
            )
        )
        for medio, n in eventos_por_medio.items()
    }


def cerrar_tramo_anterior(nueva_fecha_desde: date) -> date:
    """El tramo vigente se cierra el día anterior al inicio del nuevo (sin solape)."""
    return nueva_fecha_desde - timedelta(days=1)
