"""Intervalo de compra esperado y valor de cliente (research.md #3 y #4 de
002-clientes-fidelizacion). Funciones puras, sin acceso a base de datos.

El intervalo de compra esperado se deriva EXCLUSIVAMENTE del propio historial de visitas de un
cliente (constitución, Lectura Crítica n.º 5) — nunca de un umbral compartido con otros clientes.
"""

import statistics
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal("0.01")
VISITAS_MINIMAS_PARA_INTERVALO = 3
# Piso del intervalo esperado: un cliente con visitas casi simultáneas (varias en el mismo día,
# p. ej. corrigió un renglón olvidado en una segunda venta) produciría una mediana de 0.00 días.
# Un intervalo de 0 es una división por cero en el percentil de frecuencia (research.md #4) y,
# en la detección de fuga (FR-008), marcaría "activa" casi al instante siguiente a la propia
# visita. Ninguna de las dos cosas es la intención del dato; un piso de 1 día entero es la
# unidad mínima con la que este módulo razona en todas partes (días, nunca horas), y no cambia
# la lectura de riesgo: un cliente que compra a diario o más seguido sigue siendo, a esta
# escala, "el más frecuente posible".
INTERVALO_MINIMO_DIAS = Decimal("1.00")


@dataclass
class ResultadoIntervalo:
    estado: str  # "datos_insuficientes" | "calculado"
    visitas_consideradas: int
    intervalo_esperado_dias: Decimal | None


def calcular_intervalo_esperado(instantes_visitas: list[datetime]) -> ResultadoIntervalo:
    """Mediana de los intervalos (en días) entre visitas consecutivas.

    Con menos de `VISITAS_MINIMAS_PARA_INTERVALO` visitas hay como mucho un intervalo,
    indistinguible de una ocurrencia aislada (research.md #3): el cliente queda en
    `datos_insuficientes`, nunca con un intervalo por defecto. Con exactamente 3 visitas (2
    intervalos) la mediana coincide con el promedio — caso degenerado esperado, no un error;
    desde la tercera visita en adelante deja de arrastrarse por un solo intervalo atípico.
    """
    visitas_consideradas = len(instantes_visitas)
    if visitas_consideradas < VISITAS_MINIMAS_PARA_INTERVALO:
        return ResultadoIntervalo(
            estado="datos_insuficientes",
            visitas_consideradas=visitas_consideradas,
            intervalo_esperado_dias=None,
        )

    ordenados = sorted(instantes_visitas)
    intervalos_dias = [
        (ordenados[i + 1] - ordenados[i]).total_seconds() / 86400
        for i in range(len(ordenados) - 1)
    ]
    mediana = Decimal(str(statistics.median(intervalos_dias))).quantize(
        DOS_DECIMALES, rounding=ROUND_HALF_UP
    )
    mediana = max(mediana, INTERVALO_MINIMO_DIAS)
    return ResultadoIntervalo(
        estado="calculado",
        visitas_consideradas=visitas_consideradas,
        intervalo_esperado_dias=mediana,
    )


@dataclass
class AgregadoCliente:
    """Insumo de un cliente para `calcular_percentiles_y_compuesto`. Quien arma esta lista
    (servicios/clientes.py) ya excluyó a los clientes en `datos_insuficientes`: esta función
    nunca decide esa exclusión, solo puntúa a quien recibe (FR-007)."""

    id_cliente: int
    intervalo_esperado_dias: Decimal
    monto_total: Decimal
    margen_ponderado: Decimal  # ratio, ponderado por monto de cada visita (research.md #4)


@dataclass
class ValorCliente:
    id_cliente: int
    percentil_frecuencia: float
    percentil_monto: float
    percentil_margen: float
    compuesto: float


UN_DECIMAL = 1


def _percentil(valor: float, valores: list[float]) -> float:
    """Percentil de rango medio: (menores + 0.5 × iguales) / n × 100.

    Con una población de un solo cliente el percentil no está definido por ningún valor de
    comparación; se define en 50.0 (neutro) en vez de 0 o 100, para no sugerir que ese único
    cliente es el mejor o el peor sin ninguna base de comparación real.
    """
    n = len(valores)
    if n == 1:
        return 50.0
    menores = sum(1 for v in valores if v < valor)
    iguales = sum(1 for v in valores if v == valor)
    return round((menores + 0.5 * iguales) / n * 100, UN_DECIMAL)


def calcular_percentiles_y_compuesto(poblacion: list[AgregadoCliente]) -> list[ValorCliente]:
    """Percentil de cada una de las tres dimensiones — frecuencia (inverso del intervalo
    esperado), monto acumulado, margen ponderado — contra la propia población recibida, y
    promedio simple de los tres percentiles como puntuación compuesta (research.md #4: pesos
    iguales, no una ponderación arbitraria).

    El percentil, no el valor crudo, es lo que hace comparables tres magnitudes de escalas
    incompatibles (días, moneda, ratio) sin inventar una tasa de conversión entre ellas.
    """
    if not poblacion:
        return []

    frecuencias = [1.0 / float(c.intervalo_esperado_dias) for c in poblacion]
    montos = [float(c.monto_total) for c in poblacion]
    margenes = [float(c.margen_ponderado) for c in poblacion]

    resultado: list[ValorCliente] = []
    for i, cliente in enumerate(poblacion):
        percentil_frecuencia = _percentil(frecuencias[i], frecuencias)
        percentil_monto = _percentil(montos[i], montos)
        percentil_margen = _percentil(margenes[i], margenes)
        compuesto = round(
            (percentil_frecuencia + percentil_monto + percentil_margen) / 3, UN_DECIMAL
        )
        resultado.append(
            ValorCliente(
                id_cliente=cliente.id_cliente,
                percentil_frecuencia=percentil_frecuencia,
                percentil_monto=percentil_monto,
                percentil_margen=percentil_margen,
                compuesto=compuesto,
            )
        )
    return resultado
