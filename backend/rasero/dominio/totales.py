"""Cálculo de totales de venta. Precisión exacta con Decimal; coma flotante prohibida
(constitución, Restricciones Técnicas). El total es la suma de importes ya redondeados por
renglón, nunca el redondeo de la suma (research.md, decisión 1).
"""

from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal("0.01")
GRAMOS_POR_KG = Decimal(1000)


def calcular_importe_renglon(
    *, cantidad_unidades: int | None, cantidad_gramos: int | None, precio_por_unidad_o_kg: Decimal
) -> Decimal:
    """Importe de un renglón, redondeado a 2 decimales con mitad hacia arriba.

    Para productos a granel, `precio_por_unidad_o_kg` es el precio por kilogramo y
    `cantidad_gramos` el peso entero leído en báscula; se convierte a kg antes de multiplicar.
    """
    if cantidad_gramos is not None:
        cantidad = Decimal(cantidad_gramos) / GRAMOS_POR_KG
    elif cantidad_unidades is not None:
        cantidad = Decimal(cantidad_unidades)
    else:
        raise ValueError("Un renglón debe traer cantidad_unidades o cantidad_gramos.")

    importe = cantidad * precio_por_unidad_o_kg
    return importe.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def calcular_total_venta(importes: list[Decimal]) -> Decimal:
    """Suma de los importes ya redondeados de cada renglón (no redondea la suma)."""
    total = sum(importes, Decimal("0.00"))
    return total.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
