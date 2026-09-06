"""Funciones de dominio puras de los indicadores por operador (006-caja-mermas-fraude, US3 — T034).

Los indicadores por operador NO son una entidad — son cálculo derivado sobre `venta`,
`anulacion_venta`, `renglon_venta` y `movimiento_inventario` de 001 (research.md #2, #7). Estas
funciones reciben conteos ya agregados y devuelven proporciones y la decisión de "se desvía".

**Sin librería estadística** (`scipy`/`statsmodels`/`numpy`): la línea base es una razón sobre la
**mediana** de un conjunto de pares comparables (research.md #16). La mediana es robusta a un único
operador con valor extremo —justo el caso que interesa detectar—, que arrastraría la media.
"""

from decimal import Decimal

_CUATRO_DECIMALES = Decimal("0.0001")


def _proporcion(numerador: int, denominador: int) -> Decimal:
    if denominador <= 0:
        return Decimal("0")
    return (Decimal(numerador) / Decimal(denominador)).quantize(_CUATRO_DECIMALES)


def tasa_anulaciones(n_anulaciones: int, n_ventas: int) -> Decimal:
    """Anulaciones ejecutadas por el operador / ventas de sus turnos, en el período (FR-018)."""
    return _proporcion(n_anulaciones, n_ventas)


def concentracion_bajo_lista(n_renglones_bajo_lista: int, n_renglones: int) -> Decimal:
    """Renglones con `precio_aplicado < precio_efectivo` / total de renglones de sus turnos
    (FR-019).
    """
    return _proporcion(n_renglones_bajo_lista, n_renglones)


def mediana(valores: list[Decimal]) -> Decimal | None:
    """Mediana de una lista de `Decimal`. `None` si la lista está vacía. Aritmética de una línea,
    sin depender de `statistics` (para que la disciplina "sin librería" sea verificable por grep).
    """
    if not valores:
        return None
    ordenados = sorted(Decimal(v) for v in valores)
    n = len(ordenados)
    medio = n // 2
    if n % 2 == 1:
        return ordenados[medio]
    return ((ordenados[medio - 1] + ordenados[medio]) / Decimal(2)).quantize(_CUATRO_DECIMALES)


def se_desvia(valor: Decimal, mediana_pares: Decimal | None, razon: Decimal) -> bool:
    """`True` si `valor >= razon × mediana_pares` (FR-023). Si no hay pares comparables
    (`mediana_pares is None`) o la mediana es cero, no se puede afirmar una desviación: `False`.
    """
    if mediana_pares is None or mediana_pares <= 0:
        return False
    return Decimal(valor) >= Decimal(razon) * Decimal(mediana_pares)


def reparto_proporcional_faltante(
    faltante: Decimal, unidades_por_turno: dict[int, Decimal]
) -> dict[int, Decimal]:
    """Reparte `faltante` (>= 0) entre los turnos que movieron el producto en el período,
    proporcional a las unidades que cada turno movió (FR-020). Es un indicador para revisión, no
    una imputación individual (Edge Case del spec). Devuelve `{id_turno: cantidad_atribuida}`.
    El último turno absorbe el residuo de redondeo para que la suma cuadre exactamente.
    """
    total_unidades = sum(Decimal(u) for u in unidades_por_turno.values())
    if total_unidades <= 0 or Decimal(faltante) <= 0:
        return {t: Decimal("0") for t in unidades_por_turno}
    faltante = Decimal(faltante)
    reparto: dict[int, Decimal] = {}
    acumulado = Decimal("0")
    turnos = list(unidades_por_turno.items())
    for i, (id_turno, unidades) in enumerate(turnos):
        if i == len(turnos) - 1:
            reparto[id_turno] = (faltante - acumulado).quantize(Decimal("1"))
        else:
            parte = (faltante * Decimal(unidades) / total_unidades).quantize(Decimal("1"))
            reparto[id_turno] = parte
            acumulado += parte
    return reparto
