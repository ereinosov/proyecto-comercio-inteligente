"""T006 (parte pura) — margen real como margen bruto sobre precio de venta, `(precio - costo) /
precio` (FR-001). `calcular_margen`/`es_confiable` son funciones puras: no hay conversión
gramos/kg aquí — a diferencia de `movimiento_inventario.cantidad` (que sí está en gramos y por
eso `002` necesita convertir antes de multiplicar), `costo_unitario` y `precio_vigente` ya están
expresados en la MISMA base (por unidad, o por kilogramo si `es_granel`, data-model.md de 001)
para cualquier producto, así que su cociente no requiere ninguna conversión.
"""

from decimal import Decimal

from rasero.dominio.margenes import calcular_margen, es_confiable


def test_margen_de_costo_seis_precio_diez_es_cuarenta_por_ciento():
    margen = calcular_margen(costo=Decimal("6.0000"), precio=Decimal("10.0000"))
    assert margen == Decimal("0.4000")


def test_sin_costo_vigente_el_margen_no_es_calculable():
    assert calcular_margen(costo=None, precio=Decimal("10.0000")) is None


def test_costo_cero_o_negativo_si_calcula_margen_pero_no_es_confiable():
    margen = calcular_margen(costo=Decimal("0.0000"), precio=Decimal("10.0000"))
    assert margen == Decimal("1.0000"), "FR-004: se calcula igual, no se oculta como no calculable"
    assert es_confiable(costo=Decimal("0.0000")) is False

    margen_negativo = calcular_margen(costo=Decimal("-2.0000"), precio=Decimal("10.0000"))
    assert margen_negativo == Decimal("1.2000")
    assert es_confiable(costo=Decimal("-2.0000")) is False


def test_costo_positivo_es_confiable():
    assert es_confiable(costo=Decimal("6.0000")) is True


def test_sin_costo_vigente_es_confiable_por_defecto_no_es_la_misma_senal_que_no_confiable():
    # "no calculable" (FR-003) y "no confiable" (FR-004) son señales distintas: la ausencia de
    # costo no debe leerse como una advertencia de dato sucio.
    assert es_confiable(costo=None) is True


def test_precio_costo_por_kilogramo_no_necesita_conversion_de_unidades():
    # Producto a granel: costo_unitario y precio_vigente ya están expresados por kilogramo
    # (data-model.md de 001) — el mismo cálculo que por unidad, sin factor de 1000 de por medio.
    margen = calcular_margen(costo=Decimal("3.0000"), precio=Decimal("4.0000"))
    assert margen == Decimal("0.2500")


def test_precio_cero_no_calcula_margen_sin_lanzar_excepcion():
    assert calcular_margen(costo=Decimal("1.0000"), precio=Decimal("0.0000")) is None
