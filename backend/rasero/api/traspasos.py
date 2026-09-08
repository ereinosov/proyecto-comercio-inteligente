"""Endpoints de traspaso entre sucursales (T076, T077, US6):

- `POST /traspasos` — despachar: mercancía a tránsito, sigue en el inventario total (FR-018).
- `POST /traspasos/{id_traspaso}/recepcion` — confirmar: entrada en destino, expone la
  discrepancia por producto sin clasificarla (FR-019).
"""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import traspasos as servicio_traspasos

# Traspasos entre sucursales: rol `encargado` (constitución v2.5.0, "Autorización de pantalla").
# Tanto el despacho como la recepción — la pantalla de recepción sólo se alcanza desde la de
# despacho, no hay flujo de `cajero` que traspase mercancía.
router = APIRouter(tags=["traspasos"], dependencies=[Depends(exige_rol("encargado"))])


class RenglonDespachoNuevo(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=1)


class TraspasoNuevo(BaseModel):
    id_sucursal_origen: int
    id_sucursal_destino: int
    renglones: list[RenglonDespachoNuevo] = Field(min_length=1)


class RenglonRecepcionNuevo(BaseModel):
    id_producto: int
    cantidad_recibida: int = Field(ge=0)


class RecepcionTraspaso(BaseModel):
    renglones: list[RenglonRecepcionNuevo] = Field(min_length=1)


@router.get("/traspasos")
def listar_traspasos(
    estado: str | None = Query(default=None),
    id_sucursal_origen: int | None = Query(default=None),
    id_sucursal_destino: int | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_traspasos.listar_traspasos(
        sesion,
        estado=estado,
        id_sucursal_origen=id_sucursal_origen,
        id_sucursal_destino=id_sucursal_destino,
    )


@router.post("/traspasos", status_code=status.HTTP_201_CREATED)
def despachar_traspaso(cuerpo: TraspasoNuevo, sesion: Session = Depends(obtener_sesion)) -> dict:
    traspaso = servicio_traspasos.despachar_traspaso(
        sesion,
        id_sucursal_origen=cuerpo.id_sucursal_origen,
        id_sucursal_destino=cuerpo.id_sucursal_destino,
        renglones=[
            servicio_traspasos.RenglonDespacho(id_producto=r.id_producto, cantidad=r.cantidad)
            for r in cuerpo.renglones
        ],
    )
    return servicio_traspasos.traspaso_a_respuesta(sesion, traspaso)


@router.post("/traspasos/{id_traspaso}/recepcion")
def recibir_traspaso(
    id_traspaso: int, cuerpo: RecepcionTraspaso, sesion: Session = Depends(obtener_sesion)
) -> dict:
    traspaso = servicio_traspasos.recibir_traspaso(
        sesion,
        id_traspaso=id_traspaso,
        renglones=[
            servicio_traspasos.RenglonRecepcion(
                id_producto=r.id_producto, cantidad_recibida=r.cantidad_recibida
            )
            for r in cuerpo.renglones
        ],
    )
    return servicio_traspasos.traspaso_a_respuesta(sesion, traspaso)
