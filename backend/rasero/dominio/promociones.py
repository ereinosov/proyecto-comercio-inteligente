"""Funciones de dominio puras de 005-promociones-inteligentes (T005, T010, T024).

No tocan la base de datos: reciben datos ya cargados y devuelven decisiones. Los servicios
(`servicios/promociones.py`) las orquestan.

Cubren los mecanismos 1 y 2:
- `ventana_validez_cupon` (T006/T010) — research.md #6.
- `periodo_local_venta` (T005) — día local de la sucursal de una venta, para
  `redencion_promocion.periodo` (research.md #4). 005 implementa el suyo, no importa el de 004.
- `seleccionar_producto_recompra` / `cliente_en_ventana_recompra` (T020/T024) — research.md #7.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo


def ventana_validez_cupon(
    fecha_objetivo: date, *, antelacion_dias: int, validez_dias: int
) -> tuple[date, date]:
    """`valido_desde = fecha_objetivo - antelacion_dias`; `valido_hasta = fecha_objetivo +
    validez_dias` (research.md #6). El cupón llega la semana previa al cumpleaños y sigue vigente
    la semana siguiente.
    """
    return (
        fecha_objetivo - timedelta(days=antelacion_dias),
        fecha_objetivo + timedelta(days=validez_dias),
    )


def periodo_local_venta(instante: datetime, zona_horaria: str) -> date:
    """Día local de la sucursal: `(instante AT TIME ZONE zona_horaria)::date` (constitución:
    agregaciones sobre el día local de la sucursal, no el día UTC). Mismo criterio que el cierre
    por día local de 001 y que `periodo_local` de 004 — 005 mantiene su propia copia de una
    función pura de una línea para no acoplarse al módulo de pronóstico.
    """
    return instante.astimezone(ZoneInfo(zona_horaria)).date()


def cliente_en_ventana_recompra(
    dias_sin_compra: float, intervalo_esperado_dias: Decimal, *, margen: Decimal
) -> bool:
    """`True` sólo si el cliente **se acerca** a su intervalo de compra esperado sin superarlo
    (FR-008): `dias_sin_compra` está en `[intervalo * (1 - margen), intervalo]`. Superar el
    intervalo es territorio de la `senal_fuga` de 002, no de la recompra.
    """
    intervalo = float(intervalo_esperado_dias)
    piso = intervalo * (1.0 - float(margen))
    return piso <= dias_sin_compra <= intervalo


def seleccionar_producto_recompra(
    compras_por_producto: dict[int, list[datetime]], *, minimo_compras: int
) -> int | None:
    """Elige el producto que el cliente **suele recomprar**: el de mayor número de ventas
    distintas en la ventana de historial (research.md #7), con al menos `minimo_compras`;
    desempate por compra más reciente. `compras_por_producto` mapea `id_producto` a la lista de
    instantes de las ventas (identificadas) que lo incluyen. Devuelve `None` si ninguno llega al
    mínimo. Nunca se infiere por correlación con otros clientes.
    """
    candidatos = [
        (id_producto, len(instantes), max(instantes))
        for id_producto, instantes in compras_por_producto.items()
        if len(instantes) >= minimo_compras
    ]
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: (c[1], c[2]), reverse=True)
    return candidatos[0][0]


def justificacion_recompra(instantes_por_venta: dict[int, datetime], *, ventana_dias: int) -> dict:
    """Contexto explicable (FR-009, Principio V) para `oferta_recompra.justificacion`: qué ventas
    del propio cliente sustentan la elección del producto.
    """
    ids = sorted(instantes_por_venta)
    return {
        "ventas_consideradas": ids,
        "compras_del_producto": len(ids),
        "ventana_dias": ventana_dias,
    }


def contar_compras_por_producto(
    renglones: list[tuple[int, int, datetime]],
) -> dict[int, list[datetime]]:
    """`renglones` = lista de `(id_venta, id_producto, instante_venta)`. Devuelve, por producto,
    la lista de instantes de las ventas **distintas** que lo incluyen (una venta con dos
    renglones del mismo producto cuenta una vez).
    """
    por_producto: dict[int, dict[int, datetime]] = {}
    for id_venta, id_producto, instante in renglones:
        por_producto.setdefault(id_producto, {})[id_venta] = instante
    return {p: list(v.values()) for p, v in por_producto.items()}
