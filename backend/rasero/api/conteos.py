"""Endpoints de conteo físico (T068, T069):

- `POST /conteos-fisicos` — iniciar un conteo programado (FR-029).
- `POST /conteos-fisicos/{id_conteo_fisico}/resolucion` — resolver: expone la diferencia por
  producto y lote y genera los ajustes trazables (FR-030, FR-032). No clasifica la causa.
"""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import conteos as servicio_conteos

router = APIRouter(tags=["conteos"])


class ConteoNuevo(BaseModel):
    id_sucursal: int
    id_productos: list[int] | None = None


class RenglonContadoNuevo(BaseModel):
    id_producto: int
    id_lote: int | None = None
    cantidad_contada: int


class ResolucionConteo(BaseModel):
    renglones: list[RenglonContadoNuevo] = Field(min_length=1)


@router.get("/conteos-fisicos")
def listar_conteos(
    id_sucursal: int | None = Query(default=None),
    estado: str | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_conteos.listar_conteos(sesion, id_sucursal=id_sucursal, estado=estado)


@router.get("/conteos-fisicos/{id_conteo_fisico}")
def obtener_conteo(id_conteo_fisico: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    return servicio_conteos.obtener_conteo(sesion, id_conteo_fisico=id_conteo_fisico)


@router.post("/conteos-fisicos", status_code=status.HTTP_201_CREATED)
def iniciar_conteo(cuerpo: ConteoNuevo, sesion: Session = Depends(obtener_sesion)) -> dict:
    conteo = servicio_conteos.iniciar_conteo(
        sesion, id_sucursal=cuerpo.id_sucursal, id_productos=cuerpo.id_productos
    )
    return servicio_conteos.conteo_a_respuesta(conteo)


@router.post("/conteos-fisicos/{id_conteo_fisico}/resolucion")
def resolver_conteo(
    id_conteo_fisico: int,
    cuerpo: ResolucionConteo,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    entradas = [
        servicio_conteos.RenglonContado(
            id_producto=r.id_producto,
            id_lote=r.id_lote,
            cantidad_contada=r.cantidad_contada,
        )
        for r in cuerpo.renglones
    ]
    conteo, renglones = servicio_conteos.resolver_conteo(
        sesion, id_conteo_fisico=id_conteo_fisico, renglones=entradas
    )
    return servicio_conteos.conteo_a_respuesta(conteo, renglones)
