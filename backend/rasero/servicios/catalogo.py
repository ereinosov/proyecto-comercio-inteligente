"""Catálogo de productos (T034). Añadido durante /speckit-implement: User Story 1 necesita
listar productos para construir una venta, y contracts/openapi.yaml no exponía ninguna
lectura de `producto` hasta ahora (ver GET /productos).

`fijar_precio_sucursal` (T002 de 003-precios-margenes) se agrega aquí, no en 003: la tabla
`producto_precio_sucursal` es propiedad de este módulo (FR-050), que declaraba la capacidad
del override sin implementar nunca su escritura. 003 la consume en proceso al aplicar una
sugerencia de precio (research.md #7 de 003); no crea rama nueva de alcance en 001.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.persistencia.modelos import Producto, ProductoPrecioSucursal


def listar_catalogo(sesion: Session, *, id_sucursal: int | None) -> list[dict]:
    productos = sesion.execute(select(Producto)).scalars().all()

    overrides: dict[int, Decimal] = {}
    if id_sucursal is not None:
        filas = sesion.execute(
            select(ProductoPrecioSucursal.id_producto, ProductoPrecioSucursal.precio_vigente).where(
                ProductoPrecioSucursal.id_sucursal == id_sucursal
            )
        ).all()
        overrides = {id_producto: precio for id_producto, precio in filas}

    resultado = []
    for producto in productos:
        precio_efectivo = resolver_precio_efectivo(
            precio_base=producto.precio_vigente,
            override_sucursal=overrides.get(producto.id_producto),
        )
        resultado.append(
            {
                "id_producto": producto.id_producto,
                "nombre": producto.nombre,
                "es_granel": producto.es_granel,
                "lleva_caducidad": producto.lleva_caducidad,
                "precio_efectivo": precio_efectivo,
                "moneda": producto.moneda,
            }
        )
    return resultado


def fijar_precio_sucursal(
    sesion: Session, *, id_producto: int, id_sucursal: int, precio_vigente: Decimal
) -> ProductoPrecioSucursal:
    """Crea el override de `id_producto`/`id_sucursal` si no existía, o lo actualiza si ya
    existía (FR-050). No hace commit: la transacción queda a cargo de quien la invoque, mismo
    patrón que `persistencia/movimientos.registrar_movimiento` usa para su propio upsert.
    """
    upsert = pg_insert(ProductoPrecioSucursal).values(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        precio_vigente=precio_vigente,
    )
    upsert = upsert.on_conflict_do_update(
        index_elements=[ProductoPrecioSucursal.id_producto, ProductoPrecioSucursal.id_sucursal],
        set_={"precio_vigente": upsert.excluded.precio_vigente},
    )
    sesion.execute(upsert)
    sesion.flush()
    # El upsert es una sentencia Core, invisible para el identity map del ORM: si la fila ya
    # estaba cargada en esta sesión, sesion.get la devolvería sin ver la actualización.
    sesion.expire_all()
    return sesion.get(ProductoPrecioSucursal, (id_producto, id_sucursal))
