"""Margen real de un producto: margen bruto sobre precio de venta, `(precio − costo) / precio`
(FR-001 de 003-precios-margenes, misma forma que la aproximación provisional de 002).
Funciones puras: reciben costo y precio ya resueltos, no tocan la base de datos.
"""

from decimal import ROUND_HALF_UP, Decimal

CUATRO_DECIMALES = Decimal("0.0001")


def calcular_margen(*, costo: Decimal | None, precio: Decimal) -> Decimal | None:
    """`None` cuando no hay costo vigente disponible (FR-003) — nunca cero ni un valor supuesto.

    Con costo cero o negativo el margen SÍ se calcula (FR-004 lo marca como no confiable con
    `es_confiable`, no lo oculta). `precio <= 0` no está contemplado por ningún requisito — es un
    dato de catálogo inconsistente, no un caso de negocio — y se trata igual que costo ausente
    para no dividir por cero.
    """
    if costo is None or precio <= 0:
        return None
    margen = (precio - costo) / precio
    return margen.quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)


def es_confiable(*, costo: Decimal | None) -> bool:
    """Falso únicamente cuando hay un costo vigente y es cero o negativo (FR-004). La ausencia
    de costo (`None`, FR-003) es una señal distinta — "no calculable", no "no confiable" — y no
    marca esta bandera en falso.
    """
    return costo is None or costo > 0
