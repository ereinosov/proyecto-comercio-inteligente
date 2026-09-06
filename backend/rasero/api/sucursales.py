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
def listar_sucursales(
    incluir_inactivas: bool = False, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    """Por defecto excluye las sucursales con `activo = false` — igual que `listar_catalogo`
    con los productos: esta lista alimenta los selectores de "elegir sucursal para una acción
    nueva" (abrir turno, crear registros), y una sucursal desactivada no debe poder elegirse.

    `incluir_inactivas=true` devuelve todas: lo usan las pantallas de reporte / historial, que
    siguen viendo sus datos ya existentes (un turno cerrado contra una sucursal desactivada no
    se rompe ni desaparece — el filtro sólo aplica a los selectores de acción nueva).
    """
    consulta = select(Sucursal).order_by(Sucursal.id_sucursal)
    if not incluir_inactivas:
        consulta = consulta.where(Sucursal.activo.is_(True))
    sucursales = sesion.execute(consulta).scalars().all()
    return [
        {
            "id_sucursal": s.id_sucursal,
            "nombre": s.nombre,
            "zona_horaria": s.zona_horaria,
            "activo": s.activo,
        }
        for s in sucursales
    ]
