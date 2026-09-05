"""Resolución de precio efectivo por sucursal: override si existe, si no el precio base
(FR-050, data-model.md `producto_precio_sucursal`). Función pura: recibe los dos valores ya
consultados, no toca la base de datos.
"""

from decimal import Decimal


def resolver_precio_efectivo(
    *, precio_base: Decimal, override_sucursal: Decimal | None
) -> Decimal:
    return override_sucursal if override_sucursal is not None else precio_base
