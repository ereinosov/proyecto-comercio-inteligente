"""Construcción de la serie de demanda observada por día local de la sucursal (T005, T011 de
004-pronostico-demanda). Funciones puras: reciben movimientos ya cargados, no tocan la base de
datos — la orquestación y las consultas viven en `servicios/demanda.py`.

El período de la serie es un DÍA LOCAL de la sucursal (`instante AT TIME ZONE zona_horaria`),
igual que el cierre por día local de 001 (constitución, "Tiempo": las agregaciones de negocio se
calculan sobre el día local de la sucursal, no sobre el día UTC).
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

# --- Decisión de alcance NO cubierta explícitamente por el spec ------------------------------
# Mismo criterio que `MARGEN_SIN_COSTO_CONOCIDO` de 003: una constante nombrada con su razón, no
# una regla implícita. Un día local cuenta como censurado (dias_en_quiebre = 1) SÓLO si el
# producto estuvo sin existencia durante TODO el día. Un quiebre de parte del día todavía tuvo
# capacidad de venta el resto y no se descensura — el spec habla de "no tuvo existencia durante X
# DÍAS", no durante parte de un día. Conservador a propósito: evita inflar la demanda corregida
# por días que sí pudieron vender.
SALDO_MAXIMO_EN_QUIEBRE: Decimal = Decimal(0)

# Tipos de movimiento de 001 que representan demanda satisfecha (una salida real de mercancía) y
# su reverso. La demanda observada de un período es la salida NETA de estos dos: una venta
# anulada no es demanda satisfecha, la mercancía volvió al lote (research.md #3).
_TIPOS_DEMANDA = ("salida_venta", "entrada_anulacion")


def zona(zona_horaria: str) -> ZoneInfo:
    return ZoneInfo(zona_horaria)


def periodo_local(instante: datetime, zona_horaria: str) -> date:
    """Día local de la sucursal al que pertenece un instante (almacenado en UTC)."""
    return instante.astimezone(zona(zona_horaria)).date()


def inicio_dia_utc(dia: date, zona_horaria: str) -> datetime:
    """Instante UTC en que empieza `dia` en la zona horaria de la sucursal."""
    return datetime.combine(dia, time.min, tzinfo=zona(zona_horaria)).astimezone(timezone.utc)


def dias_del_rango(desde: date, hasta: date) -> list[date]:
    """Todos los días locales de `desde` a `hasta`, ambos inclusive."""
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


def demanda_observada_por_dia(
    movimientos: list[tuple[datetime, Decimal, str]], zona_horaria: str
) -> dict[date, Decimal]:
    """Demanda satisfecha neta por día local, a partir de los movimientos de un producto y
    sucursal. `movimientos` es una lista de `(instante, cantidad, tipo)`; en 001 la `cantidad` de
    una `salida_venta` es negativa y la de una `entrada_anulacion` positiva, así que la demanda
    del día es `-Σ cantidad` sobre esos dos tipos (nunca menor que 0).
    """
    por_dia: dict[date, Decimal] = {}
    for instante, cantidad, tipo in movimientos:
        if tipo not in _TIPOS_DEMANDA:
            continue
        dia = periodo_local(instante, zona_horaria)
        por_dia[dia] = por_dia.get(dia, Decimal(0)) - cantidad
    return {dia: max(valor, Decimal(0)) for dia, valor in por_dia.items()}


def dias_en_quiebre_por_dia(
    movimientos: list[tuple[datetime, Decimal, str]],
    *,
    saldo_inicial: Decimal,
    zona_horaria: str,
    dias: list[date],
) -> dict[date, Decimal]:
    """Fracción de cada día local en quiebre de stock (FR-002, FR-005).

    `movimientos` son TODOS los movimientos del producto y sucursal dentro de la ventana
    (`desde`..`hasta`), ordenados por instante; `saldo_inicial` es el saldo reconstruido justo
    antes del primer día de la ventana (suma de todos los movimientos anteriores — lo resuelve el
    servicio con una sola consulta de agregación, research.md #4).

    Un día devuelve 1.000 sólo si el saldo reconstruido estuvo <= SALDO_MAXIMO_EN_QUIEBRE durante
    TODO el día (ver la constante). El saldo sólo sube con entradas, así que el máximo alcanzado
    en el día es `max(saldo al inicio del día, saldo tras cada movimiento del día)`.
    """
    movs_por_dia: dict[date, list[Decimal]] = {}
    for instante, cantidad, _tipo in movimientos:
        dia = periodo_local(instante, zona_horaria)
        movs_por_dia.setdefault(dia, []).append(cantidad)

    resultado: dict[date, Decimal] = {}
    saldo = saldo_inicial
    dias_pedidos = set(dias)
    # Recorremos todos los días desde el primero con movimiento (o el primero pedido) hasta el
    # último pedido, para arrastrar el saldo correctamente aunque un día no tenga movimientos.
    primero = min([*movs_por_dia, *dias]) if (movs_por_dia or dias) else None
    ultimo = max(dias) if dias else None
    if primero is None or ultimo is None:
        return {dia: Decimal(0) for dia in dias}

    for dia in dias_del_rango(primero, ultimo):
        saldo_inicio_dia = saldo
        maximo_del_dia = saldo_inicio_dia
        for cantidad in movs_por_dia.get(dia, []):
            saldo += cantidad
            if saldo > maximo_del_dia:
                maximo_del_dia = saldo
        if dia in dias_pedidos:
            en_quiebre = maximo_del_dia <= SALDO_MAXIMO_EN_QUIEBRE
            resultado[dia] = Decimal(1) if en_quiebre else Decimal(0)
    return resultado


# --------------------------------------------------------------------------------------------
# Eje de precio (User Story 4, T046/T047) — FR-025 a FR-028
# --------------------------------------------------------------------------------------------

_CUATRO_DECIMALES = Decimal("0.0001")


def precio_vigente_por_dia(
    renglones: list[tuple[datetime, Decimal, Decimal]], zona_horaria: str
) -> dict[date, Decimal]:
    """Precio vigente reconstruido por día local, a partir de `renglon_venta.precio_aplicado` de
    001 —que es un valor COPIADO en cada venta, así que lleva el precio de cada transacción
    histórica (research.md #8b): 001 no conserva un histórico de precio y NO hace falta—.

    `renglones` es `(instante, precio_aplicado, cantidad)` del producto y sucursal. Por día se
    toma la MODA del precio (el que aparece en más renglones); si hay empate de frecuencia, la
    media de los precios empatados ponderada por cantidad (FR-025, research.md #8b).
    """
    por_dia: dict[date, list[tuple[Decimal, Decimal]]] = {}
    for instante, precio, cantidad in renglones:
        dia = periodo_local(instante, zona_horaria)
        por_dia.setdefault(dia, []).append((precio, cantidad))

    resultado: dict[date, Decimal] = {}
    for dia, pares in por_dia.items():
        frecuencia: dict[Decimal, int] = {}
        cantidad_por_precio: dict[Decimal, Decimal] = {}
        for precio, cantidad in pares:
            frecuencia[precio] = frecuencia.get(precio, 0) + 1
            cantidad_por_precio[precio] = cantidad_por_precio.get(precio, Decimal(0)) + cantidad
        frecuencia_maxima = max(frecuencia.values())
        modas = [p for p, f in frecuencia.items() if f == frecuencia_maxima]
        if len(modas) == 1:
            resultado[dia] = modas[0]
        else:
            peso_total = sum((cantidad_por_precio[p] for p in modas), Decimal(0))
            if peso_total > 0:
                resultado[dia] = (
                    sum((p * cantidad_por_precio[p] for p in modas), Decimal(0)) / peso_total
                ).quantize(_CUATRO_DECIMALES)
            else:
                resultado[dia] = (sum(modas, Decimal(0)) / Decimal(len(modas))).quantize(
                    _CUATRO_DECIMALES
                )
    return resultado


def normalizar_demanda_por_precio(
    *,
    cantidad: Decimal,
    precio_periodo: Decimal | None,
    precio_referencia: Decimal | None,
    epsilon: Decimal,
) -> tuple[Decimal, Decimal]:
    """Normaliza la demanda de un período hacia el precio de referencia por un factor de
    elasticidad simple `(precio_periodo / precio_referencia) ^ epsilon` (FR-025, research.md #8b).

    Devuelve `(valor_normalizado, delta)` donde `delta = valor_normalizado − cantidad` (puede ser
    negativo). Sin corrección —devuelve `(cantidad, 0)`— cuando falta un precio o alguno no es
    positivo: un período sin ventas no tiene precio reconstruible y va "sin corrección de precio"
    (FR-027).
    """
    if (
        precio_periodo is None
        or precio_referencia is None
        or precio_periodo <= 0
        or precio_referencia <= 0
    ):
        return cantidad, Decimal(0)
    factor = (precio_periodo / precio_referencia) ** epsilon
    normalizada = (cantidad * factor).quantize(_CUATRO_DECIMALES)
    return normalizada, normalizada - cantidad


# --------------------------------------------------------------------------------------------
# Eje de promoción (User Story 5, T053) — FR-029 a FR-031  [005-futuro]
# --------------------------------------------------------------------------------------------


def marca_promocion_por_dia(
    sesion, *, id_producto: int, id_sucursal: int, dias: list[date]
) -> dict[date, bool]:
    """**Gancho de integración con 005-promociones-inteligentes** (FR-030). La fuente de la marca
    "promoción activa" por producto, sucursal y período es `005`, que NO existe todavía: hoy
    devuelve `{}` (ningún período con promoción). El gancho queda aquí, presente y documentado, no
    oculto: cuando `005` exista, esta función consultará su calendario de campañas
    (`campania`/`envio_promocional`) para el producto, la sucursal y el rango de días.
    """
    _ = (sesion, id_producto, id_sucursal, dias)  # se usarán cuando 005 exista
    return {}
