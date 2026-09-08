"""k-means (algoritmo de Lloyd) en Python puro — 008-reportes-inteligencia, User Story 4.

Sin `numpy`, `scipy` ni `scikit-learn` (Principio I; mismo rechazo que 006 hizo a las librerías
estadísticas). Con cientos de clientes y tres dimensiones el coste es trivial, y una
implementación de pocas líneas es auditable por un evaluador.

Determinismo (FR-019): toda la aleatoriedad sale de un `random.Random(semilla)` explícito y el
recorrido de los puntos es en el orden en que llegan (el llamador los ordena por `id_cliente`).
"""

from __future__ import annotations

import math
import random

Punto = tuple[float, float, float]


def _distancia2(a: Punto, b: Punto) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _media(puntos: list[Punto]) -> Punto:
    n = len(puntos)
    return (
        sum(p[0] for p in puntos) / n,
        sum(p[1] for p in puntos) / n,
        sum(p[2] for p in puntos) / n,
    )


def _init_plus_plus(puntos: list[Punto], k: int, rng: random.Random) -> list[Punto]:
    """k-means++ determinista: el primer centroide es el punto de índice 0 (los puntos ya vienen
    ordenados); los siguientes se eligen con probabilidad proporcional a la distancia² al
    centroide más cercano, usando `rng`.
    """
    centroides: list[Punto] = [puntos[0]]
    while len(centroides) < k:
        d2 = [min(_distancia2(p, c) for c in centroides) for p in puntos]
        total = sum(d2)
        if total == 0:  # todos los puntos ya coinciden con un centroide
            centroides.append(puntos[len(centroides) % len(puntos)])
            continue
        objetivo = rng.random() * total
        acumulado = 0.0
        for p, peso in zip(puntos, d2):
            acumulado += peso
            if acumulado >= objetivo:
                centroides.append(p)
                break
    return centroides


def agrupar(
    puntos: list[Punto], k: int, semilla: int, *, max_iter: int = 50
) -> tuple[list[int], list[Punto]]:
    """Devuelve (`grupo_por_punto`, `centroides`). `grupo_por_punto[i]` ∈ [0, k').

    Si hay menos puntos distintos que `k`, `k` se reduce a esa cantidad (FR-024): el llamador
    detecta `len(set(centroides)) < k_pedido` o simplemente usa los grupos que salgan.
    """
    if not puntos:
        return [], []
    distintos = list(dict.fromkeys(puntos))
    k_efectivo = min(k, len(distintos))
    rng = random.Random(semilla)
    centroides = _init_plus_plus(puntos, k_efectivo, rng)

    grupos = [0] * len(puntos)
    for _ in range(max_iter):
        nuevo = [
            min(range(k_efectivo), key=lambda j: _distancia2(p, centroides[j]))
            for p in puntos
        ]
        if nuevo == grupos:
            break
        grupos = nuevo
        for j in range(k_efectivo):
            miembros = [p for p, g in zip(puntos, grupos) if g == j]
            if miembros:
                centroides[j] = _media(miembros)
    return grupos, centroides


# --------------------------------------------------------------------------
# Estandarización y descripción del centroide (FR-018, FR-022)
# --------------------------------------------------------------------------


def estandarizar(
    filas: list[Punto],
) -> tuple[list[Punto], Punto, Punto]:
    """z-score por eje sobre la población. Devuelve (`puntos_z`, `medias`, `desviaciones`).
    Una desviación 0 (todos iguales en ese eje) se trata como 1 para no dividir por cero.
    """
    n = len(filas)
    medias = _media(filas)
    var = tuple(
        sum((f[e] - medias[e]) ** 2 for f in filas) / n for e in range(3)
    )
    desv = tuple(math.sqrt(v) or 1.0 for v in var)
    z = [
        tuple((f[e] - medias[e]) / desv[e] for e in range(3))  # type: ignore[misc]
        for f in filas
    ]
    return z, medias, desv  # type: ignore[return-value]


def _nivel(z: float) -> str:
    if z >= 0.5:
        return "alto"
    if z <= -0.5:
        return "bajo"
    return "medio"


def describir_centroide(centroide_z: Punto) -> str:
    """Frase en lenguaje llano derivada del centroide en unidades estandarizadas (FR-022).
    Ejes: (frecuencia, margen, recencia_invertida) — recencia ya viene invertida por el
    llamador para que "más reciente" sea "más alto", igual dirección que los otros dos.
    """
    frecuencia, margen, recencia = (_nivel(v) for v in centroide_z)
    partes = {
        "alto": ("vienen seguido", "dejan buen margen", "compraron hace poco"),
        "medio": ("vienen a veces", "dejan margen medio", "compraron hace un tiempo"),
        "bajo": ("vienen poco", "dejan poco margen", "compraron hace mucho"),
    }
    return ", ".join(
        (partes[frecuencia][0], partes[margen][1], partes[recencia][2])
    )
