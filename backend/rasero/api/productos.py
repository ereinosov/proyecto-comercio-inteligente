"""Endpoint GET /productos (T035). Ver servicios/catalogo.py para el porqué de esta adición."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import catalogo as servicio_catalogo

router = APIRouter(tags=["productos"])


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
        }
        for p in productos
    ]
