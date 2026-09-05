"""Funciones puras del experimento de reactivación (T039, 005-promociones-inteligentes, US3).

No tocan la base de datos. Todo con `Decimal` (incluida la raíz vía `Decimal.sqrt()`); el ÚNICO
punto que toca `float` es `math.erf` para el valor p, y su salida se cuantiza a `NUMERIC` antes
de persistirse (research.md #9, #10a, #10b).

- `asignar_grupos` — aleatorización REAL con semilla fija: `random.Random` (Mersenne Twister
  MT19937 de la biblioteca estándar) + Fisher–Yates (`shuffle`). La semilla sólo fija el punto
  de partida del PRNG, no qué cliente va a qué grupo en relación con sus atributos. PROHIBIDO
  cualquier reparto determinista (id % 2, orden alfabético, ...) — FR-016. Sin `numpy`.
- `tamano_minimo_muestra` — poder estadístico: `n*` por grupo para detectar el `mde` con
  `alfa`/`poder` dados (research.md #10b). Con p_c=0.15, MDE=15pp, alfa=0.05, poder=0.80 -> ~121.
- `prueba_z_dos_proporciones` — z de dos proporciones + valor p de dos colas `1 - erf(|z|/sqrt(2))`.
  Sin `scipy`/`statsmodels`.
- `veredicto` — 'efectivo' si y sólo si `incrementalidad > 0` y `valor_p < alfa` (FR-021).
"""

import math
import random
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

_DOS = Decimal(2)
_UNO = Decimal(1)
_CIEN = Decimal(100)
_RAIZ_DE_DOS = Decimal(2).sqrt()


def asignar_grupos(
    ids_elegibles: list[int], *, semilla: int, proporcion_tratamiento: Decimal
) -> dict[int, str]:
    """Reparte `ids_elegibles` en 'tratamiento'/'control'. Reproducible: mismos ids + misma
    semilla -> exactamente los mismos grupos. El `sorted` previo hace determinista la ENTRADA al
    shuffle (el orden de filas de la BD no está garantizado); el `shuffle` la transforma en una
    permutación uniforme.
    """
    rng = random.Random(semilla)
    ordenados = sorted(ids_elegibles)
    rng.shuffle(ordenados)
    corte = round(len(ordenados) * float(proporcion_tratamiento))
    tratamiento = set(ordenados[:corte])
    return {id_: ("tratamiento" if id_ in tratamiento else "control") for id_ in ids_elegibles}


def tamano_minimo_muestra(
    *,
    p_control: Decimal,
    mde_puntos_porcentuales: Decimal,
    z_alfa_medios: Decimal,
    z_beta: Decimal,
) -> int:
    """`n*` por grupo (dos proporciones, dos colas, grupos iguales), research.md #10b:

        n* = ( z_{a/2}·sqrt(2·p_bar·(1-p_bar)) + z_b·sqrt(p_c·q_c + p_t·q_t) )^2 / (p_t - p_c)^2

    con `p_t = p_control + mde/100`. Se redondea hacia arriba.
    """
    p_c = p_control
    p_t = p_c + mde_puntos_porcentuales / _CIEN
    p_bar = (p_c + p_t) / _DOS
    termino_a = z_alfa_medios * (_DOS * p_bar * (_UNO - p_bar)).sqrt()
    termino_b = z_beta * (p_c * (_UNO - p_c) + p_t * (_UNO - p_t)).sqrt()
    n = ((termino_a + termino_b) ** 2) / ((p_t - p_c) ** 2)
    return int(n.quantize(Decimal(1), rounding=ROUND_CEILING))


@dataclass
class ResultadoPrueba:
    retorno_tratamiento: Decimal
    retorno_control: Decimal
    incrementalidad: Decimal
    estadistico_z: Decimal
    valor_p: Decimal


def prueba_z_dos_proporciones(
    retornos_t: int, n_t: int, retornos_c: int, n_c: int
) -> ResultadoPrueba:
    """Prueba z de dos proporciones (research.md #10a). Requiere `n_t > 0` y `n_c > 0`.

    p_agrupada     = (rt + rc) / (nt + nc)
    error_estandar = sqrt( p_agrupada·(1 - p_agrupada)·(1/nt + 1/nc) )
    z              = (p_t - p_c) / error_estandar
    valor_p        = 1 - erf(|z| / sqrt(2))          # dos colas
    """
    p_t = Decimal(retornos_t) / Decimal(n_t)
    p_c = Decimal(retornos_c) / Decimal(n_c)
    incrementalidad = p_t - p_c
    p_agrupada = Decimal(retornos_t + retornos_c) / Decimal(n_t + n_c)
    error_estandar = (
        p_agrupada * (_UNO - p_agrupada) * (_UNO / Decimal(n_t) + _UNO / Decimal(n_c))
    ).sqrt()
    if error_estandar == 0:
        z = Decimal(0)
        valor_p = Decimal(1)
    else:
        z = incrementalidad / error_estandar
        valor_p = Decimal(1) - Decimal(str(math.erf(float(abs(z)) / float(_RAIZ_DE_DOS))))
    return ResultadoPrueba(
        retorno_tratamiento=p_t.quantize(Decimal("0.0001")),
        retorno_control=p_c.quantize(Decimal("0.0001")),
        incrementalidad=incrementalidad.quantize(Decimal("0.0001")),
        estadistico_z=z.quantize(Decimal("0.00001")),
        valor_p=max(Decimal(0), valor_p).quantize(Decimal("0.000001")),
    )


def veredicto(incrementalidad: Decimal, valor_p: Decimal, alfa: Decimal) -> str:
    """'efectivo' si y sólo si la incrementalidad es positiva Y estadísticamente significativa
    (FR-021). Una incrementalidad negativa —aunque "significativa"— nunca es 'efectivo' (Edge Case).
    """
    if incrementalidad > 0 and valor_p < alfa:
        return "efectivo"
    return "no_efectivo"
