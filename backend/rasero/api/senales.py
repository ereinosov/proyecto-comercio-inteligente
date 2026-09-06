"""Endpoint POST /consultas-no-atendidas (T052, FR-020).

Acción de dos toques desde la pantalla de venta. El cuerpo admite **exactamente** producto,
turno y —sólo para operaciones registradas sin conectividad— el instante de origen. Cualquier
otro campo se rechaza (`extra="forbid"`): la constitución y FR-020 prohíben capturar dato
alguno del cliente en esta señal.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import senales as servicio_senales

router = APIRouter(tags=["senales"])


class ConsultaNoAtendidaNueva(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int
    id_turno: int
    instante_origen: datetime | None = None


@router.post("/consultas-no-atendidas", status_code=status.HTTP_201_CREATED)
def registrar_consulta_no_atendida(
    cuerpo: ConsultaNoAtendidaNueva, sesion: Session = Depends(obtener_sesion)
) -> dict:
    consulta = servicio_senales.registrar_consulta_no_atendida(
        sesion,
        id_producto=cuerpo.id_producto,
        id_turno=cuerpo.id_turno,
        instante_origen=cuerpo.instante_origen,
    )
    return {
        "id_consulta_no_atendida": consulta.id_consulta_no_atendida,
        "id_producto": consulta.id_producto,
        "id_sucursal": consulta.id_sucursal,
        "instante": consulta.instante,
        "saldo_en_el_instante": int(consulta.saldo_en_el_instante),
    }
