"""Endpoint de sincronización offline (T086, US8): `POST /operaciones-pendientes/sincronizacion`.

Recibe un lote de operaciones registradas sin conectividad, lo ordena por `marca_tiempo_origen`
y lo aplica resolviendo conflictos por `recurso_afectado`. La operación desplazada queda visible
en `conflicto_resuelto`, nunca se elimina.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import sincronizacion as servicio_sincronizacion

router = APIRouter(tags=["sincronizacion"])


class OperacionPendienteNueva(BaseModel):
    id_operacion_pendiente: str
    tipo_operacion: str
    carga: dict
    recurso_afectado: str
    marca_tiempo_origen: datetime


class LoteSincronizacion(BaseModel):
    operaciones: list[OperacionPendienteNueva] = Field(min_length=1)


@router.post("/operaciones-pendientes/sincronizacion")
def sincronizar(
    cuerpo: LoteSincronizacion, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    filas = servicio_sincronizacion.sincronizar(
        sesion,
        operaciones=[
            servicio_sincronizacion.OperacionEntrante(
                id_operacion_pendiente=o.id_operacion_pendiente,
                tipo_operacion=o.tipo_operacion,
                carga=o.carga,
                recurso_afectado=o.recurso_afectado,
                marca_tiempo_origen=o.marca_tiempo_origen,
            )
            for o in cuerpo.operaciones
        ],
    )
    return [servicio_sincronizacion.operacion_a_respuesta(f) for f in filas]
