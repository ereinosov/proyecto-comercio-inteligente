"""Endpoints POST /turnos y POST /turnos/{id_turno}/cierre (T028, T029)."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import turnos as servicio_turnos

router = APIRouter(tags=["turnos"])


class TurnoNuevo(BaseModel):
    id_operador: int
    id_sucursal: int
    caja: str
    pin: str = Field(pattern=r"^[0-9]{4}$")


class TurnoRespuesta(BaseModel):
    id_turno: int
    id_operador: int
    id_sucursal: int
    caja: str
    instante_apertura: datetime
    instante_cierre: datetime | None


def _a_respuesta(turno) -> TurnoRespuesta:
    return TurnoRespuesta(
        id_turno=turno.id_turno,
        id_operador=turno.id_operador,
        id_sucursal=turno.id_sucursal,
        caja=turno.caja,
        instante_apertura=turno.instante_apertura,
        instante_cierre=turno.instante_cierre,
    )


@router.post("/turnos", response_model=TurnoRespuesta, status_code=status.HTTP_201_CREATED)
def abrir_turno(cuerpo: TurnoNuevo, sesion: Session = Depends(obtener_sesion)) -> TurnoRespuesta:
    turno = servicio_turnos.abrir_turno(
        sesion,
        id_operador=cuerpo.id_operador,
        id_sucursal=cuerpo.id_sucursal,
        caja=cuerpo.caja,
        pin=cuerpo.pin,
    )
    sesion.commit()
    return _a_respuesta(turno)


@router.post("/turnos/{id_turno}/cierre", response_model=TurnoRespuesta)
def cerrar_turno(id_turno: int, sesion: Session = Depends(obtener_sesion)) -> TurnoRespuesta:
    turno = servicio_turnos.cerrar_turno(sesion, id_turno=id_turno)
    sesion.commit()
    return _a_respuesta(turno)
