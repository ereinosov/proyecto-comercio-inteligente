"""Endpoint GET /productos (T035). Ver servicios/catalogo.py para el porqué de esta adición.

GET /categorias se añade aquí (Parte 3): las pantallas de Venta y Precios necesitan resolver
`id_categoria` -> nombre para elegir el ícono de familia de categoría (La Regla del Ícono por
Categoría, DESIGN.md v1.2.0), sin pasar por el envoltorio de administración.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Categoria
from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import catalogo as servicio_catalogo

router = APIRouter(tags=["productos"])


@router.get("/categorias")
def listar_categorias(
    incluir_inactivas: bool = False, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    consulta = select(Categoria).order_by(Categoria.id_categoria)
    if not incluir_inactivas:
        consulta = consulta.where(Categoria.activo.is_(True))
    return [
        {
            "id_categoria": c.id_categoria,
            "nombre": c.nombre,
            "dias_umbral_inmovilizado": c.dias_umbral_inmovilizado,
            "activo": c.activo,
        }
        for c in sesion.execute(consulta).scalars()
    ]


@router.get("/productos")
def listar_productos(
    id_sucursal: int | None = None, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    productos = servicio_catalogo.listar_catalogo(sesion, id_sucursal=id_sucursal)
    return [
        {
            "id_producto": p["id_producto"],
            "nombre": p["nombre"],
            "es_granel": p["es_granel"],
            "lleva_caducidad": p["lleva_caducidad"],
            "precio_efectivo": f"{p['precio_efectivo']:.4f}",
            "moneda": p["moneda"],
            "id_categoria": p["id_categoria"],
            "url_imagen": p["url_imagen"],
        }
        for p in productos
    ]
