"""T054 [US4] — Reglas puras de la comparación de precios de competencia (FR-023, FR-024, FR-025).

- normalización de una observación a precio por unidad de medida;
- `comparable = false` cuando la presentación no admite conversión;
- normalización del nombre de canal para evitar duplicados;
- antigüedad calculada al leer: texto e indicador de forma por los umbrales de config.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.comparacion_precios import (
    dias_de_antiguedad,
    indicador_forma,
    normalizar_nombre_canal,
    precio_por_unidad_de_medida,
    texto_antiguedad,
)


def test_producto_por_unidad_observado_en_otra_presentacion_se_normaliza():
    # Competidor vende 3 unidades por 4.50 -> 1.50 por unidad.
    p = precio_por_unidad_de_medida(
        precio_observado=Decimal("4.50"),
        presentacion_cantidad=Decimal("3"),
        presentacion_unidad="unidad",
        producto_es_granel=False,
    )
    assert p == Decimal("1.5000")


def test_producto_granel_observado_en_gramos_se_normaliza_a_kilo():
    # Competidor vende 500 g por 3.00 -> 6.00 por kg.
    p = precio_por_unidad_de_medida(
        precio_observado=Decimal("3.00"),
        presentacion_cantidad=Decimal("500"),
        presentacion_unidad="gramo",
        producto_es_granel=True,
    )
    assert p == Decimal("6.0000")


def test_presentacion_no_convertible_devuelve_none_no_comparable():
    # Producto por unidad, observación en gramos -> no comparable.
    assert (
        precio_por_unidad_de_medida(
            precio_observado=Decimal("2.00"),
            presentacion_cantidad=Decimal("250"),
            presentacion_unidad="gramo",
            producto_es_granel=False,
        )
        is None
    )
    # Granel, observación en mililitros -> peso contra volumen, no comparable.
    assert (
        precio_por_unidad_de_medida(
            precio_observado=Decimal("2.00"),
            presentacion_cantidad=Decimal("330"),
            presentacion_unidad="mililitro",
            producto_es_granel=True,
        )
        is None
    )


def test_normalizar_nombre_canal_colapsa_acentos_mayusculas_y_espacios():
    assert normalizar_nombre_canal("  Tía  Quevedo ") == "tia quevedo"
    assert normalizar_nombre_canal("TÍA QUEVEDO") == normalizar_nombre_canal("tía quevedo")


def test_antiguedad_calculada_al_leer_texto_e_indicador_de_forma():
    ahora = datetime(2026, 9, 20, tzinfo=timezone.utc)
    reciente = ahora - timedelta(days=3)
    quincena = ahora - timedelta(days=14)
    vieja = ahora - timedelta(days=40)

    assert dias_de_antiguedad(reciente, ahora) == 3
    assert texto_antiguedad(0) == "hoy"
    assert texto_antiguedad(3) == "hace 3 d"

    assert indicador_forma(dias_de_antiguedad(reciente, ahora)) == "lleno"
    assert indicador_forma(dias_de_antiguedad(quincena, ahora)) == "medio"  # 14 d fuera de lleno
    assert indicador_forma(dias_de_antiguedad(vieja, ahora)) == "hueco"
