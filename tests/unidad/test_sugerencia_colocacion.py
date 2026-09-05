"""T037 — algoritmo de sugerencia de colocación (Lectura Crítica n.º 3 de la constitución,
research.md #6 de 003): ranking por margen real contra `grado_privilegio`, nunca por
`rol_producto` (que solo se snapshot-ea como explicación). Función pura, sin base de datos.
"""

from rasero.dominio.sugerencias import sugerir_colocacion


def test_producto_de_mayor_margen_va_a_la_zona_mas_privilegiada():
    zonas = [10, 20, 30]  # ya ordenadas por grado_privilegio descendente
    assert sugerir_colocacion(rango=1, total_con_margen=3, zonas_ordenadas=zonas) == 10


def test_producto_de_menor_margen_va_a_la_zona_mas_relegada():
    zonas = [10, 20, 30]
    assert sugerir_colocacion(rango=3, total_con_margen=3, zonas_ordenadas=zonas) == 30


def test_reparte_en_franjas_cuando_hay_mas_productos_que_zonas():
    zonas = [10, 20]  # 2 zonas, 4 productos -> 2 por franja
    assert sugerir_colocacion(rango=1, total_con_margen=4, zonas_ordenadas=zonas) == 10
    assert sugerir_colocacion(rango=2, total_con_margen=4, zonas_ordenadas=zonas) == 10
    assert sugerir_colocacion(rango=3, total_con_margen=4, zonas_ordenadas=zonas) == 20
    assert sugerir_colocacion(rango=4, total_con_margen=4, zonas_ordenadas=zonas) == 20


def test_sin_zonas_catalogadas_no_hay_sugerencia():
    assert sugerir_colocacion(rango=1, total_con_margen=1, zonas_ordenadas=[]) is None


def test_sin_ningun_producto_con_margen_no_hay_sugerencia():
    assert sugerir_colocacion(rango=1, total_con_margen=0, zonas_ordenadas=[10]) is None
