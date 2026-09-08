"""Prueba obligatoria (Principio III) del k-means propio de 008 — User Story 4.

- determinismo: misma semilla + mismos datos → misma partición (FR-019, SC-003);
- separación: tres nubes deliberadamente separadas caen ≥ 80 % cada una en un grupo (SC-004);
- k > n puntos distintos → no se fuerza k (FR-024);
- `describir_centroide` traduce el signo/magnitud de cada eje, no un texto fijo.
"""

from rasero.dominio.kmeans import agrupar, describir_centroide, estandarizar


def _nube(centro, n, paso=0.03):
    return [
        (centro[0] + i * paso, centro[1] + i * paso, centro[2] + i * paso)
        for i in range(n)
    ]


def test_determinismo_misma_semilla_misma_particion():
    puntos = _nube((0, 0, 0), 10) + _nube((5, 5, 5), 10) + _nube((0, 5, 0), 10)
    a, _ = agrupar(puntos, k=3, semilla=20260907)
    b, _ = agrupar(puntos, k=3, semilla=20260907)
    assert a == b


def test_semilla_distinta_puede_diferir_pero_misma_estructura():
    puntos = _nube((0, 0, 0), 12) + _nube((9, 9, 9), 12)
    a, _ = agrupar(puntos, k=2, semilla=1)
    b, _ = agrupar(puntos, k=2, semilla=999)
    # Ambas separan las dos nubes (aunque el índice del grupo pueda intercambiarse).
    def bloques(grupos):
        return {frozenset(i for i, g in enumerate(grupos) if g == v) for v in set(grupos)}
    assert bloques(a) == bloques(b)


def test_separacion_tres_patrones_caen_juntos():
    frecuentes = _nube((10, 10, 10), 15)
    dormidos = _nube((10, 10, -10), 15)
    esporadicos = _nube((-10, -10, 0), 15)
    puntos = frecuentes + dormidos + esporadicos
    grupos, _ = agrupar(puntos, k=3, semilla=20260907)

    for inicio in (0, 15, 30):
        tramo = grupos[inicio:inicio + 15]
        dominante = max(set(tramo), key=tramo.count)
        assert tramo.count(dominante) / 15 >= 0.8


def test_k_mayor_que_puntos_distintos_no_se_fuerza():
    puntos = [(1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (2.0, 2.0, 2.0)]  # 2 distintos
    grupos, centroides = agrupar(puntos, k=4, semilla=7)
    assert len(set(grupos)) <= 2
    assert len(centroides) <= 2


def test_estandarizar_z_score():
    filas = [(0.0, 10.0, 100.0), (2.0, 20.0, 300.0), (4.0, 30.0, 500.0)]
    z, medias, desv = estandarizar(filas)
    assert medias == (2.0, 20.0, 300.0)
    # media de cada eje estandarizado ≈ 0
    for e in range(3):
        assert abs(sum(f[e] for f in z) / 3) < 1e-9


def test_describir_centroide_deriva_del_centroide():
    alto = describir_centroide((1.5, 1.5, 1.5))
    bajo = describir_centroide((-1.5, -1.5, -1.5))
    assert "seguido" in alto and "buen margen" in alto and "hace poco" in alto
    assert "poco" in bajo and "hace mucho" in bajo
    assert alto != bajo
