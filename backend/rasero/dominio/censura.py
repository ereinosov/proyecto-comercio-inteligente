"""Descensura de la demanda por quiebre de stock (T010 de 004-pronostico-demanda). Funciones
puras: reciben la serie observada ya construida, no tocan la base de datos.

Método fijado por `/speckit-clarify` (FR-009), en dos niveles:

  (a) Método base — `estimar_latente_metodo_base`: la demanda de un período censurado se sustituye
      por el MÁXIMO de la demanda observada del mismo producto y sucursal entre los N períodos más
      recientes SIN quiebre, previos al inicio del intervalo de quiebre (research.md #5). Aritmética
      simple, sin estimadores de máxima verosimilitud ni supuestos de distribución.

  (b) Ajuste cruzado por sustituto (FR-009 b) — `exceso_sustituto` + `ajuste_cruzado`: si el
      producto en quiebre tiene un sustituto DECLARADO (`sustitucion_producto`, User Story 6) que
      durante el quiebre vendió por encima de su propio nivel típico, ese exceso se SUMA al
      estimado del método base, complementándolo, nunca reemplazándolo (research.md #6, política
      de atribución: 100 % del exceso del sustituto). Sólo aplica cuando el método base produjo un
      valor: si el producto está en censura total, no hay base que complementar y sigue en censura
      total.

El camino de EVIDENCIA REAL de `consulta_no_atendida` (FR-007) está BLOQUEADO por 001 (su User
Story 3 / tareas T050-T053 sin implementar): mientras tanto todo período de quiebre se descensura
por el método base y se marca `respaldo_quiebre = 'metodo_base'` (menor confianza que uno
respaldado por consultas no atendidas). Ver `servicios/demanda.py` y tasks.md, "Bloqueado por 001".
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# Estados expuestos de un período de la serie corregida.
ESTADO_OK = "ok"
ESTADO_CENSURA_TOTAL = "no_estimable_censura_total"

# Valores de `demanda_corregida.respaldo_quiebre`.
RESPALDO_NO_APLICA = "no_aplica"
RESPALDO_METODO_BASE = "metodo_base"
RESPALDO_CONSULTA_NO_ATENDIDA = "consulta_no_atendida"  # sólo cuando 001 desbloquee FR-007


@dataclass(frozen=True)
class PeriodoObservado:
    periodo: date
    cantidad: Decimal
    dias_en_quiebre: Decimal  # 0..1 (ver serie_demanda.SALDO_MAXIMO_EN_QUIEBRE)


@dataclass(frozen=True)
class PeriodoCorregido:
    periodo: date
    valor_observado: Decimal
    valor: Decimal | None  # None => censura total, se expone como "no estimable", nunca 0
    correccion_quiebre: Decimal
    respaldo_quiebre: str
    censura_total: bool
    estado: str


def estimar_latente_metodo_base(
    *, periodos_sin_quiebre_previos: list[Decimal], n: int
) -> Decimal | None:
    """Demanda latente estimada para un período censurado (método base, FR-009 a).

    `periodos_sin_quiebre_previos`: cantidades observadas de los períodos SIN quiebre ANTERIORES
    al período censurado, en orden cronológico (research.md #5: "los N períodos más recientes sin
    quiebre, previos al inicio del intervalo de quiebre"). Se toma el máximo de los N más
    recientes.

    Devuelve `None` cuando NO hay ningún período sin quiebre previo del cual tomar el máximo — es
    la "censura total" de FR-012: nunca se sustituye por 0 ni por un valor supuesto. Un período de
    quiebre sin ninguna actividad previa del producto (antes de su primer día con stock) cae aquí:
    el modelo no puede saber si había demanda latente, y así lo dice en vez de fabricar un número.
    """
    ventana = periodos_sin_quiebre_previos[-n:]
    if not ventana:
        return None
    return max(ventana)


def corregir_serie_por_quiebre(
    observados: list[PeriodoObservado], *, n: int
) -> list[PeriodoCorregido]:
    """Aplica la descensura por quiebre a una serie observada completa (un producto y sucursal),
    en orden cronológico. Garantiza `valor >= cantidad observada` en todo período de quiebre
    (FR-006) y no toca los períodos sin quiebre (FR-011).
    """
    observados = sorted(observados, key=lambda o: o.periodo)

    corregidos: list[PeriodoCorregido] = []
    for obs in observados:
        if obs.dias_en_quiebre == 0:
            corregidos.append(
                PeriodoCorregido(
                    periodo=obs.periodo,
                    valor_observado=obs.cantidad,
                    valor=obs.cantidad,
                    correccion_quiebre=Decimal(0),
                    respaldo_quiebre=RESPALDO_NO_APLICA,
                    censura_total=False,
                    estado=ESTADO_OK,
                )
            )
            continue

        previos = [
            o.cantidad for o in observados if o.dias_en_quiebre == 0 and o.periodo < obs.periodo
        ]
        estimado = estimar_latente_metodo_base(periodos_sin_quiebre_previos=previos, n=n)
        if estimado is None:
            corregidos.append(
                PeriodoCorregido(
                    periodo=obs.periodo,
                    valor_observado=obs.cantidad,
                    valor=None,
                    correccion_quiebre=Decimal(0),
                    respaldo_quiebre=RESPALDO_NO_APLICA,
                    censura_total=True,
                    estado=ESTADO_CENSURA_TOTAL,
                )
            )
            continue

        # El estimado se aplica proporcionalmente a la fracción del período en quiebre: un día
        # entero en quiebre toma el estimado completo; una fracción, sólo esa parte por encima de
        # lo observado. Con grano diario `dias_en_quiebre` es 0 o 1, así que esto es el estimado
        # completo — pero se deja explícito para no romper si el grano cambia.
        objetivo = obs.cantidad + (estimado - obs.cantidad) * obs.dias_en_quiebre
        valor = max(objetivo, obs.cantidad)
        corregidos.append(
            PeriodoCorregido(
                periodo=obs.periodo,
                valor_observado=obs.cantidad,
                valor=valor,
                correccion_quiebre=valor - obs.cantidad,
                respaldo_quiebre=RESPALDO_METODO_BASE,
                censura_total=False,
                estado=ESTADO_OK,
            )
        )
    return corregidos


def exceso_sustituto(*, demanda_sustituto: Decimal, maximo_n_sustituto: Decimal | None) -> Decimal:
    """Demanda del sustituto por encima de su nivel típico durante el quiebre del producto
    original (FR-009 b, research.md #6). El nivel típico es el mismo máximo-de-N del método base.

    Devuelve 0 si el sustituto no vendió por encima de lo típico, o si su nivel típico no es
    estimable (sin ningún período previo sin quiebre) — no se fabrica un exceso a partir de la nada.
    """
    if maximo_n_sustituto is None:
        return Decimal(0)
    return max(Decimal(0), demanda_sustituto - maximo_n_sustituto)


def ajuste_cruzado(*, estimado_base: Decimal, excesos: list[Decimal]) -> Decimal:
    """Suma de los excesos observados de cada sustituto declarado (FR-009 b). Complementa el
    estimado del método base: `demanda_corregida = estimado_base + Σ excesos`. Nunca reemplaza el
    método base ni lo reduce (política: 100 % del exceso del sustituto se atribuye al original).
    """
    _ = estimado_base  # se documenta que el ajuste es aditivo sobre el estimado base, no un reemplazo
    return sum(excesos, Decimal(0))
