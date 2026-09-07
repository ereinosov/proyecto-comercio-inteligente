"""Endpoints de precios de competencia (T059, T060, T061, US4):

- `GET/POST /canales-competencia` — catálogo abierto, sin duplicados por nombre normalizado.
- `POST /observaciones-precio` — captura manual o por archivo (nunca automática).
- `GET /productos/{id_producto}/comparacion-precios` — precio propio de la sucursal contra las
  observaciones vigentes, con la antigüedad calculada al leer.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import CanalCompetencia
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import competencia as servicio_competencia

# Pantalla "Competencia": táctica/gerencial, rol `encargado` (constitución v2.5.0). Sin uso en
# ningún flujo de caja de un `cajero`.
router = APIRouter(tags=["competencia"], dependencies=[Depends(exige_rol("encargado"))])


class CanalNuevo(BaseModel):
    nombre: str


class ObservacionNueva(BaseModel):
    id_producto: int
    id_canal_competencia: int
    presentacion_cantidad: Decimal
    presentacion_unidad: str
    precio_observado: Decimal
    fuente: str
    origen_captura: str
    moneda: str = "USD"
    id_turno: int | None = None


def _canal_a_respuesta(canal: CanalCompetencia) -> dict:
    return {
        "id_canal_competencia": canal.id_canal_competencia,
        "nombre": canal.nombre,
        "nombre_normalizado": canal.nombre_normalizado,
    }


@router.get("/canales-competencia")
def listar_canales(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    canales = sesion.execute(
        select(CanalCompetencia).order_by(CanalCompetencia.nombre_normalizado)
    ).scalars().all()
    return [_canal_a_respuesta(c) for c in canales]


@router.post("/canales-competencia")
def agregar_canal(
    cuerpo: CanalNuevo, response: Response, sesion: Session = Depends(obtener_sesion)
) -> dict:
    canal, creado = servicio_competencia.crear_o_devolver_canal(sesion, nombre=cuerpo.nombre)
    response.status_code = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
    return _canal_a_respuesta(canal)


@router.post("/observaciones-precio", status_code=status.HTTP_201_CREATED)
def capturar_observacion(
    cuerpo: ObservacionNueva, sesion: Session = Depends(obtener_sesion)
) -> dict:
    obs = servicio_competencia.capturar_observacion(
        sesion,
        id_producto=cuerpo.id_producto,
        id_canal_competencia=cuerpo.id_canal_competencia,
        presentacion_cantidad=cuerpo.presentacion_cantidad,
        presentacion_unidad=cuerpo.presentacion_unidad,
        precio_observado=cuerpo.precio_observado,
        fuente=cuerpo.fuente,
        origen_captura=cuerpo.origen_captura,
        moneda=cuerpo.moneda,
        id_turno=cuerpo.id_turno,
    )
    return {
        "id_observacion_precio": obs.id_observacion_precio,
        "id_producto": obs.id_producto,
        "id_canal_competencia": obs.id_canal_competencia,
        "presentacion_cantidad": f"{Decimal(obs.presentacion_cantidad):g}",
        "presentacion_unidad": obs.presentacion_unidad,
        "precio_observado": f"{Decimal(obs.precio_observado):.2f}",
        "moneda": obs.moneda,
        "fuente": obs.fuente,
        "origen_captura": obs.origen_captura,
        "instante_captura": obs.instante_captura,
        "id_turno": obs.id_turno,
        "comparable": obs.comparable,
    }


@router.get("/productos/{id_producto}/comparacion-precios")
def comparar_precios(
    id_producto: int, id_sucursal: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    return servicio_competencia.comparar_precios(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal
    )
