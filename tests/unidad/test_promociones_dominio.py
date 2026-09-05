"""T006 (US1) y T020 (US2) — funciones puras de `dominio/promociones.py`.

T006: `ventana_validez_cupon` — research.md #6.
T020: `seleccionar_producto_recompra` y `cliente_en_ventana_recompra` — research.md #7.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.promociones import (
    cliente_en_ventana_recompra,
    contar_compras_por_producto,
    seleccionar_producto_recompra,
    ventana_validez_cupon,
)

# --- T006 -----------------------------------------------------------------


def test_ventana_validez_cupon_es_antelacion_antes_y_validez_despues():
    desde, hasta = ventana_validez_cupon(date(2026, 9, 15), antelacion_dias=7, validez_dias=14)
    assert desde == date(2026, 9, 8)
    assert hasta == date(2026, 9, 29)


def test_ventana_validez_cupon_cruza_fin_de_mes():
    desde, hasta = ventana_validez_cupon(date(2026, 3, 1), antelacion_dias=7, validez_dias=14)
    assert desde == date(2026, 2, 22)
    assert hasta == date(2026, 3, 15)


# --- T020 ---------------------------------------------------------------------


def _inst(dias_atras: int) -> datetime:
    return datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc) - timedelta(days=dias_atras)


def test_selecciona_el_producto_con_mas_compras_distintas():
    compras = {
        10: [_inst(30), _inst(60), _inst(90)],  # 3 compras
        20: [_inst(10), _inst(40)],  # 2 compras — no llega al mínimo
    }
    assert seleccionar_producto_recompra(compras, minimo_compras=3) == 10


def test_desempate_por_compra_mas_reciente():
    compras = {
        10: [_inst(30), _inst(60), _inst(90)],
        20: [_inst(5), _inst(35), _inst(65)],  # mismo conteo, más reciente
    }
    assert seleccionar_producto_recompra(compras, minimo_compras=3) == 20


def test_sin_ningun_producto_al_minimo_devuelve_none():
    compras = {10: [_inst(30), _inst(60)], 20: [_inst(10)]}
    assert seleccionar_producto_recompra(compras, minimo_compras=3) is None


def test_contar_compras_por_producto_deduplica_por_venta():
    # Una venta con dos renglones del mismo producto cuenta una vez.
    renglones = [(1, 10, _inst(5)), (1, 10, _inst(5)), (2, 10, _inst(20))]
    contadas = contar_compras_por_producto(renglones)
    assert len(contadas[10]) == 2


def test_cliente_en_ventana_recompra_solo_al_acercarse_sin_superar():
    intervalo = Decimal("20")
    margen = Decimal("0.20")  # ventana [16, 20]
    assert cliente_en_ventana_recompra(17.0, intervalo, margen=margen) is True
    assert cliente_en_ventana_recompra(16.0, intervalo, margen=margen) is True
    assert cliente_en_ventana_recompra(20.0, intervalo, margen=margen) is True
    assert cliente_en_ventana_recompra(15.0, intervalo, margen=margen) is False  # aún lejos
    assert cliente_en_ventana_recompra(21.0, intervalo, margen=margen) is False  # ya lo superó
