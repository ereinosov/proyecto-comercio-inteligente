"""Margen real por producto y sucursal (T010, T011 de 003-precios-margenes).

`margen_calculado` se recalcula y sobrescribe (upsert) en cada lectura, nunca por disparador de
base de datos ni tarea de fondo (research.md #4): los dos insumos —costo y precio— cambian por
eventos de `001` (una compra, un cambio de precio o de override), no de `003`.

`resolver_margen_producto` es también la función del contrato de migración con 002 (FR-022,
research.md #8): `resolver_margen_visita` de 002 la llamará por cada renglón de una venta en vez
de calcular su propio costo.

Frontera de propiedad de datos: `producto`, `producto_precio_sucursal`, `lote` y `existencia` son
de 001. Este módulo los CONSULTA, no los posee — mismo patrón que 002 ya usa para leer
`lote`/`movimiento_inventario` (research.md #2 de 002).
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select, true
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from rasero.dominio.margenes import calcular_margen, es_confiable
from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.errores import RecursoNoEncontrado
from rasero.persistencia.modelos import (
    Existencia,
    Lote,
    MargenCalculado,
    Producto,
    ProductoPrecioSucursal,
)

_CAMPOS_ACTUALIZABLES = ("costo_vigente", "precio_vigente", "margen", "confiable", "instante_calculo")


def _upsert_margen_calculado(sesion: Session, filas: list[dict]) -> None:
    """Único punto de escritura en `margen_calculado`: un solo `INSERT ... ON CONFLICT DO
    UPDATE`, con una o varias filas (research.md #4 — nunca un bucle de upserts individuales
    desde el listado de una sucursal).
    """
    if not filas:
        return
    upsert = pg_insert(MargenCalculado).values(filas)
    upsert = upsert.on_conflict_do_update(
        index_elements=[MargenCalculado.id_producto, MargenCalculado.id_sucursal],
        set_={campo: getattr(upsert.excluded, campo) for campo in _CAMPOS_ACTUALIZABLES},
    )
    sesion.execute(upsert)
    sesion.flush()


def _costo_vigente_fefo(sesion: Session, *, id_producto: int, id_sucursal: int) -> Decimal | None:
    """Costo del lote que la política de salida FEFO de 001 consumiría primero para este
    producto y sucursal — mismo orden que su índice de selección
    `(id_sucursal, id_producto, fecha_caducidad NULLS LAST, instante_entrada, id_lote)` — entre
    los lotes con existencia todavía positiva. `None` si ninguno tiene saldo disponible (FR-003).
    """
    return sesion.execute(
        select(Lote.costo_unitario)
        .join(
            Existencia,
            and_(
                Existencia.id_sucursal == Lote.id_sucursal,
                Existencia.id_producto == Lote.id_producto,
                Existencia.id_lote == Lote.id_lote,
            ),
        )
        .where(
            Lote.id_producto == id_producto,
            Lote.id_sucursal == id_sucursal,
            Existencia.cantidad > 0,
        )
        .order_by(Lote.fecha_caducidad.asc().nulls_last(), Lote.instante_entrada.asc(), Lote.id_lote.asc())
        .limit(1)
    ).scalar_one_or_none()


def resolver_margen_producto(sesion: Session, *, id_producto: int, id_sucursal: int) -> Decimal | None:
    """Margen real vigente de un producto en una sucursal (FR-001). Recalcula y sobrescribe la
    fila de `margen_calculado` correspondiente en cada llamada.
    """
    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    override = sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()
    precio_vigente = resolver_precio_efectivo(
        precio_base=producto.precio_vigente, override_sucursal=override
    )

    costo_vigente = _costo_vigente_fefo(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    margen = calcular_margen(costo=costo_vigente, precio=precio_vigente)
    confiable = es_confiable(costo=costo_vigente)

    _upsert_margen_calculado(
        sesion,
        [
            {
                "id_producto": id_producto,
                "id_sucursal": id_sucursal,
                "costo_vigente": costo_vigente,
                "precio_vigente": precio_vigente,
                "margen": margen,
                "confiable": confiable,
                "instante_calculo": datetime.now(timezone.utc),
            }
        ],
    )
    return margen


def listar_margenes_sucursal(sesion: Session, *, id_sucursal: int) -> list[dict]:
    """Margen real de todos los productos del catálogo para una sucursal, en una única consulta
    de conjunto y un único upsert masivo — nunca iterando `resolver_margen_producto` una vez por
    producto (research.md #4, patrón N+1 explícitamente rechazado).
    """
    costo_lateral = (
        select(Lote.costo_unitario.label("costo_vigente"))
        .join(
            Existencia,
            and_(
                Existencia.id_sucursal == Lote.id_sucursal,
                Existencia.id_producto == Lote.id_producto,
                Existencia.id_lote == Lote.id_lote,
            ),
        )
        .where(
            Lote.id_producto == Producto.id_producto,
            Lote.id_sucursal == id_sucursal,
            Existencia.cantidad > 0,
        )
        .order_by(Lote.fecha_caducidad.asc().nulls_last(), Lote.instante_entrada.asc(), Lote.id_lote.asc())
        .limit(1)
        .lateral()
    )

    consulta_conjunto = (
        select(
            Producto.id_producto,
            Producto.precio_vigente.label("precio_base"),
            ProductoPrecioSucursal.precio_vigente.label("precio_override"),
            costo_lateral.c.costo_vigente,
        )
        .outerjoin(
            ProductoPrecioSucursal,
            and_(
                ProductoPrecioSucursal.id_producto == Producto.id_producto,
                ProductoPrecioSucursal.id_sucursal == id_sucursal,
            ),
        )
        .outerjoin(costo_lateral, true())
    )

    ahora = datetime.now(timezone.utc)
    filas_upsert: list[dict] = []
    resultado: list[dict] = []
    for id_producto, precio_base, precio_override, costo_vigente in sesion.execute(consulta_conjunto).all():
        precio_vigente = resolver_precio_efectivo(precio_base=precio_base, override_sucursal=precio_override)
        margen = calcular_margen(costo=costo_vigente, precio=precio_vigente)
        confiable = es_confiable(costo=costo_vigente)

        fila = {
            "id_producto": id_producto,
            "id_sucursal": id_sucursal,
            "costo_vigente": costo_vigente,
            "precio_vigente": precio_vigente,
            "margen": margen,
            "confiable": confiable,
            "instante_calculo": ahora,
        }
        filas_upsert.append(fila)
        resultado.append(fila)

    _upsert_margen_calculado(sesion, filas_upsert)
    return resultado
