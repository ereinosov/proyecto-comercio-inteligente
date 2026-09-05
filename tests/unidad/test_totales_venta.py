"""T017 — Prueba obligatoria (Principio III): totales de venta con producto a peso y
redondeo a 2 decimales. La suma es de importes ya redondeados, no el redondeo de la suma.
"""

from decimal import Decimal

from rasero.dominio.totales import calcular_importe_renglon, calcular_total_venta


def test_renglon_a_peso_con_precio_impar_redondea_a_dos_decimales():
    # 0.7 kg a $4.75/kg = 3.325 -> redondeo ROUND_HALF_UP a 3.33 (no 3.32)
    importe = calcular_importe_renglon(
        cantidad_unidades=None, cantidad_gramos=700, precio_por_unidad_o_kg=Decimal("4.75")
    )
    assert importe == Decimal("3.33")


def test_renglon_por_unidad():
    importe = calcular_importe_renglon(
        cantidad_unidades=3, cantidad_gramos=None, precio_por_unidad_o_kg=Decimal("1.50")
    )
    assert importe == Decimal("4.50")


def test_renglon_sin_ninguna_cantidad_es_invalido():
    import pytest

    with pytest.raises(ValueError):
        calcular_importe_renglon(
            cantidad_unidades=None, cantidad_gramos=None, precio_por_unidad_o_kg=Decimal("1.00")
        )


def test_total_es_suma_de_importes_ya_redondeados_no_redondeo_de_la_suma():
    # Dos renglones que redondean individualmente a .335 y .335 -> .34 + .34 = .68,
    # y NO el resultado de sumar 3.35 crudo y redondear (que también da .68 aquí, así que se
    # usa un caso donde difiere: 0.005 y 0.005 redondean cada uno a 0.01 (total 0.02),
    # mientras que sumar crudo 0.01 y redondear da 0.01 — deben diferir.
    r1 = calcular_importe_renglon(
        cantidad_unidades=None, cantidad_gramos=500, precio_por_unidad_o_kg=Decimal("0.0100")
    )  # 0.5 * 0.01 = 0.005 -> redondea a 0.01 (ROUND_HALF_UP)
    r2 = calcular_importe_renglon(
        cantidad_unidades=None, cantidad_gramos=500, precio_por_unidad_o_kg=Decimal("0.0100")
    )
    assert r1 == Decimal("0.01")
    assert r2 == Decimal("0.01")
    total = calcular_total_venta([r1, r2])
    assert total == Decimal("0.02")  # suma de los ya redondeados, no 0.01 (redondeo de 0.01 crudo)


def test_total_de_venta_mixta_de_cinco_renglones():
    importes = [
        calcular_importe_renglon(cantidad_unidades=2, cantidad_gramos=None, precio_por_unidad_o_kg=Decimal("1.50")),
        calcular_importe_renglon(cantidad_unidades=None, cantidad_gramos=700, precio_por_unidad_o_kg=Decimal("4.75")),
        calcular_importe_renglon(cantidad_unidades=1, cantidad_gramos=None, precio_por_unidad_o_kg=Decimal("3.00")),
        calcular_importe_renglon(cantidad_unidades=None, cantidad_gramos=250, precio_por_unidad_o_kg=Decimal("6.00")),
        calcular_importe_renglon(cantidad_unidades=4, cantidad_gramos=None, precio_por_unidad_o_kg=Decimal("0.75")),
    ]
    assert calcular_total_venta(importes) == Decimal("3.00") + Decimal("3.33") + Decimal(
        "3.00"
    ) + Decimal("1.50") + Decimal("3.00")
