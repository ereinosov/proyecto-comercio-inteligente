"""T016 — Prueba obligatoria (Principio III): con 2 visitas el intervalo queda
`datos_insuficientes`; con 3 (dos intervalos) queda `calculado` con la mediana correcta
(research.md #3 de 002-clientes-fidelizacion).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.valor_cliente import calcular_intervalo_esperado


def _hace(dias: float, base: datetime) -> datetime:
    return base - timedelta(days=dias)


def test_con_dos_visitas_queda_datos_insuficientes():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    resultado = calcular_intervalo_esperado([_hace(20, base), base])

    assert resultado.estado == "datos_insuficientes"
    assert resultado.visitas_consideradas == 2
    assert resultado.intervalo_esperado_dias is None


def test_con_tres_visitas_queda_calculado_con_la_mediana():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Intervalos: 10 días y 12 días -> mediana de dos valores = promedio = 11.
    instantes = [_hace(22, base), _hace(12, base), base]

    resultado = calcular_intervalo_esperado(instantes)

    assert resultado.estado == "calculado"
    assert resultado.visitas_consideradas == 3
    assert resultado.intervalo_esperado_dias == Decimal("11.00")


def test_el_orden_de_entrada_no_importa_se_ordena_por_instante():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instantes_desordenados = [base, _hace(22, base), _hace(12, base)]

    resultado = calcular_intervalo_esperado(instantes_desordenados)

    assert resultado.intervalo_esperado_dias == Decimal("11.00")


def test_visitas_casi_simultaneas_no_producen_intervalo_cero():
    """Regresión: descubierto en verificación manual de /speckit-implement — un cliente con
    tres visitas el mismo día producía intervalo_esperado_dias=0.00, lo que rompía la división
    de la frecuencia en el valor de cliente (ZeroDivisionError) y habría marcado la fuga como
    'activa' casi al instante. El piso de 1 día lo evita en la fuente.
    """
    base = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    instantes = [base, base + timedelta(minutes=5), base + timedelta(minutes=10)]

    resultado = calcular_intervalo_esperado(instantes)

    assert resultado.estado == "calculado"
    assert resultado.intervalo_esperado_dias == Decimal("1.00")


def test_un_intervalo_atipico_no_arrastra_la_mediana_desde_la_tercera_visita():
    """Con 4 visitas (3 intervalos), un solo intervalo atípico no debe mover la mediana tanto
    como movería un promedio simple — es la razón declarada en research.md #3 para usar
    mediana en vez de promedio.
    """
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Intervalos: 10, 10, 200 (un salto atípico, p. ej. vacaciones).
    instantes = [_hace(220, base), _hace(210, base), _hace(200, base), base]

    resultado = calcular_intervalo_esperado(instantes)

    assert resultado.estado == "calculado"
    assert resultado.intervalo_esperado_dias == Decimal("10.00")
