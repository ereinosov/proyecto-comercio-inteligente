"""Catálogo de productos (T034). Añadido durante /speckit-implement: User Story 1 necesita
listar productos para construir una venta, y contracts/openapi.yaml no exponía ninguna
lectura de `producto` hasta ahora (ver GET /productos).
"""

from decimal import Decimal

from sqlalchemy import select
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
