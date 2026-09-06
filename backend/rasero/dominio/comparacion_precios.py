"""Reglas puras de la comparación de precios de competencia (001-core-ventas-inventario, US4 —
T058). No tocan la base de datos.

- `normalizar_nombre_canal` — para el catálogo abierto de canales sin duplicados (FR-025).
- `precio_por_unidad_de_medida` — normaliza una observación al mismo eje que el precio propio:
  por unidad para un producto por unidad, por kilogramo para uno a granel. Devuelve `None`
  ("no comparable") cuando la presentación observada no admite conversión (FR-023, Edge Case).
- `dias_de_antiguedad` / `texto_antiguedad` / `indicador_forma` — la antigüedad se calcula en el
  momento de la lectura, NUNCA se almacena (FR-024). Se comunica con tres portadores simultáneos:
  color (lo pone el frontend), forma (`indicador_forma`) y texto (`texto_antiguedad`).
"""

import unicodedata
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from rasero.config.competencia import ANTIGUEDAD_HUECO_DIAS, ANTIGUEDAD_LLENO_DIAS

_CUATRO_DECIMALES = Decimal("0.0001")
_GRAMOS_POR_KG = Decimal(1000)


def normalizar_nombre_canal(nombre: str) -> str:
    """Minúsculas, sin acentos, sin espacios extremos ni repetidos. Dos capturas con el mismo
    nombre normalizado son el mismo canal (FR-025)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    return " ".join(sin_acentos.lower().split())


def precio_por_unidad_de_medida(
    *,
    precio_observado: Decimal,
    presentacion_cantidad: Decimal,
    presentacion_unidad: str,
    producto_es_granel: bool,
) -> Decimal | None:
    """Precio de la observación llevado al eje del precio propio. `None` si no es convertible."""
    cantidad = Decimal(presentacion_cantidad)
    if cantidad <= 0:
        return None
    precio = Decimal(precio_observado)

    if producto_es_granel:
        # El precio propio de un granel es por kilogramo. Solo una presentación en gramos es
        # convertible; una en unidades o mililitros no lo es.
        if presentacion_unidad != "gramo":
            return None
        kilos = cantidad / _GRAMOS_POR_KG
        return (precio / kilos).quantize(_CUATRO_DECIMALES, rounding=ROUND_HALF_UP)

    # El precio propio de un producto por unidad es por unidad. Solo una presentación en unidades
    # es convertible.
    if presentacion_unidad != "unidad":
        return None
    return (precio / cantidad).quantize(_CUATRO_DECIMALES, rounding=ROUND_HALF_UP)


def dias_de_antiguedad(instante_captura: datetime, ahora: datetime) -> int:
    delta = ahora - instante_captura
    return max(0, delta.days)


def texto_antiguedad(dias: int) -> str:
    if dias <= 0:
        return "hoy"
    if dias == 1:
        return "hace 1 d"
    return f"hace {dias} d"


def indicador_forma(dias: int) -> str:
    """`lleno` (reciente) / `medio` / `hueco` (vieja), por los umbrales de config/competencia.py
    (research.md §12). Es presentación pura; no entra en ningún cálculo."""
    if dias <= ANTIGUEDAD_LLENO_DIAS:
        return "lleno"
    if dias <= ANTIGUEDAD_HUECO_DIAS:
        return "medio"
    return "hueco"
