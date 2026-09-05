"""Suite obligatoria 1 (US3, T035) — `asignar_grupos`: aleatorización real con semilla fija.

- Reproducible: mismos ids + misma semilla -> exactamente los mismos grupos (SC-005).
- No sesgada: sobre MÚLTIPLES semillas, la fracción media en tratamiento converge a la proporción,
  y la proporción de ids pares en tratamiento no difiere de la de control (SC-006).
- Semilla distinta -> grupos distintos.
"""

from decimal import Decimal

from rasero.dominio.experimento import asignar_grupos

_MITAD = Decimal("0.5")
_IDS = list(range(1, 401))  # 400 clientes (pares e impares en igual número)


def test_misma_semilla_mismos_grupos_exactamente():
    a = asignar_grupos(_IDS, semilla=20260905, proporcion_tratamiento=_MITAD)
    b = asignar_grupos(_IDS, semilla=20260905, proporcion_tratamiento=_MITAD)
    assert a == b


def test_semilla_distinta_grupos_distintos():
    a = asignar_grupos(_IDS, semilla=1, proporcion_tratamiento=_MITAD)
    b = asignar_grupos(_IDS, semilla=2, proporcion_tratamiento=_MITAD)
    assert a != b


def test_proporcion_de_tratamiento_es_la_pedida():
    grupos = asignar_grupos(_IDS, semilla=20260905, proporcion_tratamiento=_MITAD)
    n_t = sum(1 for g in grupos.values() if g == "tratamiento")
    assert n_t == 200  # round(400 * 0.5)


def test_sobre_muchas_semillas_la_fraccion_media_converge_y_no_hay_sesgo_por_paridad():
    """200 semillas distintas. En cada una: ¿qué fracción de los ids PARES cae en tratamiento?
    Si la asignación fuera `id % 2` esa fracción sería 0 o 1 siempre. Con aleatorización real,
    la media sobre semillas ronda 0.5 y la desviación entre pares e impares es pequeña.
    """
    fracciones_pares = []
    fracciones_impares = []
    for semilla in range(1000, 1200):
        grupos = asignar_grupos(_IDS, semilla=semilla, proporcion_tratamiento=_MITAD)
        pares = [i for i in _IDS if i % 2 == 0]
        impares = [i for i in _IDS if i % 2 == 1]
        fracciones_pares.append(sum(1 for i in pares if grupos[i] == "tratamiento") / len(pares))
        fracciones_impares.append(
            sum(1 for i in impares if grupos[i] == "tratamiento") / len(impares)
        )

    media_pares = sum(fracciones_pares) / len(fracciones_pares)
    media_impares = sum(fracciones_impares) / len(fracciones_impares)

    # La fracción media en tratamiento converge a 0.5 para pares y para impares por igual.
    assert abs(media_pares - 0.5) < 0.02
    assert abs(media_impares - 0.5) < 0.02
    # Y no hay sesgo sistemático por paridad del id.
    assert abs(media_pares - media_impares) < 0.02


def test_sin_correlacion_con_el_orden_de_entrada():
    """El `sorted` interno hace que el orden de la lista de entrada no cambie el resultado."""
    a = asignar_grupos(_IDS, semilla=7, proporcion_tratamiento=_MITAD)
    b = asignar_grupos(list(reversed(_IDS)), semilla=7, proporcion_tratamiento=_MITAD)
    assert a == b
