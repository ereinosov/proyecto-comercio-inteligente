"""Endpoint GET /sucursales. Añadido durante /speckit-implement (Bloque B): la pantalla de
despacho de traspaso (US6) necesita elegir la sucursal de destino y el contrato no exponía
ninguna lectura de `sucursal`. Mismo motivo por el que US1 añadió GET /productos y GET
/operadores. Codificar en cualquier parte que las sucursales son dos está PROHIBIDO (FR-046):
esta lista es la fuente para poblar cualquier selector de sucursal.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Sucursal
from rasero.persistencia.sesion import obtener_sesion

router = APIRouter(tags=["catalogo"])


@router.get("/sucursales")
def listar_sucursales(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    sucursales = sesion.execute(select(Sucursal).order_by(Sucursal.id_sucursal)).scalars().all()
    return [
        {"id_sucursal": s.id_sucursal, "nombre": s.nombre, "zona_horaria": s.zona_horaria}
        for s in sucursales
    ]
