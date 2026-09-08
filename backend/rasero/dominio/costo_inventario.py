"""Valoración monetaria de una cantidad de existencia contra el costo de su lote.

`Lote.costo_unitario` está **por unidad** para un producto por unidad y **por kilogramo** para
uno a granel (ver el comentario de `semilla_catalogo.py`: "Para los productos a peso el costo y
el precio son por kilogramo; la venta a granel se registra en gramos"). La existencia y los
movimientos de un granel se registran en **gramos**. Multiplicar `cantidad_en_gramos ×
costo_por_kg` sin convertir infla el valor exactamente ×1000.

Este módulo centraliza esa conversión — mismo patrón que `dominio/totales.py` para el importe de
un renglón de venta y que `_costo_por_unidad_de_cantidad` de `servicios/mermas.py` para valorar
una merma. Cualquier cálculo de "valor de inventario", "capital inmovilizado", "valor en riesgo"
o "valor estimado del faltante" que trabaje sobre lotes debe pasar por aquí.
"""

from decimal import Decimal

GRAMOS_POR_KG = Decimal(1000)


def valor_existencia(cantidad, costo_unitario, *, es_granel: bool) -> Decimal:
    """Valor monetario de `cantidad` de existencia al `costo_unitario` del lote.

    - `cantidad`: en unidades, o en **gramos** si `es_granel`.
    - `costo_unitario`: por unidad, o por **kilogramo** si `es_granel`.

    Devuelve un `Decimal` sin cuantizar; el llamador aplica su propio `.quantize` si lo necesita.
    """
    cantidad = Decimal(cantidad)
    costo_unitario = Decimal(costo_unitario)
    if es_granel:
        cantidad = cantidad / GRAMOS_POR_KG
    return cantidad * costo_unitario
