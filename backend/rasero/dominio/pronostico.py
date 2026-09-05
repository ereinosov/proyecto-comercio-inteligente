"""Pronóstico de demanda (T035 de 004-pronostico-demanda, User Story 3). Funciones puras: reciben
la serie ya corregida, no tocan la base de datos.

Método fijado por `/speckit-clarify` (FR-020): **suavizado exponencial simple** sobre la serie ya
corregida por censura. Un único parámetro `alfa` (config/pronostico.py, research.md #7); la
recurrencia es una línea de aritmética, sin librería de series temporales.

Línea base determinista (FR-022): promedio móvil de la demanda OBSERVADA sin corregir. Un
pronóstico sólo se presenta como vigente si su error retrospectivo es menor que el de esta línea
base (SC-004).

Horizonte medio (FR-019, research.md #8d): además del nivel del suavizado, se aplica un
multiplicador por tramo del mes = media de la demanda corregida en ese tramo / media global. NO
es descomposición estacional formal ni cubre estacionalidad anual.
"""

from datetime import date
from decimal import Decimal


def tramo_de(dia: date, tramos: tuple[tuple[int, int], ...]) -> int:
    """Índice (0-based) del tramo del mes al que pertenece `dia`. Los días 29-31 de meses cortos
    caen en el último tramo."""
    dm = dia.day
    for i, (ini, fin) in enumerate(tramos):
        if ini <= dm <= fin:
            return i
    return len(tramos) - 1


def suavizado_exponencial_simple(serie: list[Decimal], alfa: Decimal) -> Decimal:
    """`nivel_t = alfa · x_t + (1 − alfa) · nivel_{t−1}`. Devuelve el nivel tras el último dato.
    `serie` en orden cronológico y no vacía.
    """
    nivel = serie[0]
    uno_menos = Decimal(1) - alfa
    for x in serie[1:]:
        nivel = alfa * x + uno_menos * nivel
    return nivel


def linea_base_promedio_movil(serie_observada: list[Decimal], n: int) -> Decimal:
    """Promedio de los últimos `n` valores de la demanda OBSERVADA sin corregir (FR-022)."""
    ventana = serie_observada[-n:]
    if not ventana:
        return Decimal(0)
    return sum(ventana, Decimal(0)) / Decimal(len(ventana))


def multiplicadores_tramo_mes(
    historicos: list[tuple[date, Decimal]],
    tramos: tuple[tuple[int, int], ...],
    *,
    minimo_por_tramo: int,
) -> dict[str, str]:
    """Multiplicador de estacionalidad intramensual por tramo del mes (research.md #8d):
    `media de la demanda corregida del tramo / media global`. Un tramo con menos de
    `minimo_por_tramo` observaciones usa 1.0 (sin ajuste). Devuelto con claves y valores de
    texto para persistirse tal cual en `pronostico.multiplicadores_tramo` (JSONB).
    """
    if not historicos:
        return {}
    media_global = sum((v for _d, v in historicos), Decimal(0)) / Decimal(len(historicos))
    por_tramo: dict[int, list[Decimal]] = {}
    for d, v in historicos:
        por_tramo.setdefault(tramo_de(d, tramos), []).append(v)

    salida: dict[str, str] = {}
    for i in range(len(tramos)):
        vals = por_tramo.get(i, [])
        if media_global == 0 or len(vals) < minimo_por_tramo:
            salida[str(i)] = "1.0000"
        else:
            media_tramo = sum(vals, Decimal(0)) / Decimal(len(vals))
            salida[str(i)] = f"{media_tramo / media_global:.4f}"
    return salida


def proyectar(
    *,
    nivel: Decimal,
    dias_futuros: list[date],
    multiplicadores: dict[str, str] | None,
    tramos: tuple[tuple[int, int], ...],
) -> list[tuple[date, Decimal]]:
    """Proyección día a día: el nivel del suavizado, escalado por el multiplicador del tramo del
    mes si el horizonte lo usa (medio); plano si no (corto). Nunca negativo.
    """
    salida: list[tuple[date, Decimal]] = []
    for d in dias_futuros:
        factor = Decimal(1)
        if multiplicadores:
            factor = Decimal(multiplicadores.get(str(tramo_de(d, tramos)), "1"))
        salida.append((d, max(Decimal(0), nivel * factor)))
    return salida


def comparar_contra_linea_base(
    *,
    corregida: list[Decimal],
    observada: list[Decimal],
    alfa: Decimal,
    n_linea_base: int,
    cola: int,
) -> tuple[Decimal | None, Decimal | None]:
    """Error medio absoluto retrospectivo del suavizado exponencial frente al de la línea base
    determinista, sobre la cola de validación (FR-022, SC-004).

    Ambos predictores se puntúan contra los valores CORREGIDOS de la cola —nuestra mejor
    estimación de la demanda real—; el suavizado se alimenta de la serie corregida y la línea base
    de la observada sin corregir. Devuelve `(None, None)` si no hay suficiente historia
    (`len(corregida) < cola + 2`).
    """
    if len(corregida) < cola + 2 or len(observada) < cola + 2:
        return None, None

    objetivo = corregida[-cola:]

    # Suavizado exponencial: nivel entrenado con todo menos la cola, luego un paso a la vez.
    nivel = corregida[0]
    uno_menos = Decimal(1) - alfa
    for x in corregida[:-cola][1:]:
        nivel = alfa * x + uno_menos * nivel
    errores_ses: list[Decimal] = []
    for real in objetivo:
        errores_ses.append(abs(nivel - real))
        nivel = alfa * real + uno_menos * nivel

    # Línea base: promedio móvil de la demanda observada, un paso a la vez.
    errores_base: list[Decimal] = []
    total = len(observada)
    for k in range(total - cola, total):
        ventana = observada[max(0, k - n_linea_base) : k]
        pred = sum(ventana, Decimal(0)) / Decimal(len(ventana)) if ventana else Decimal(0)
        errores_base.append(abs(pred - objetivo[k - (total - cola)]))

    media = lambda xs: sum(xs, Decimal(0)) / Decimal(len(xs))  # noqa: E731
    return media(errores_ses), media(errores_base)
