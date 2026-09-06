"""Router de operadores.

- `GET /operadores` (T037): listado de operadores activos para elegir al abrir turno. Incluye
  `rol` e `id_sucursal` (User Story 10). Nunca expone `pin_hash`.
- `POST /operadores`, `PUT /operadores/{id}`, `POST /operadores/{id}/activo` (User Story 10,
  Principio VI): gestión **exclusiva del rol `admin`**. El `id_operador` del solicitante viaja
  en el cuerpo, igual que en el resto de escrituras del sistema. La verificación pasa por el
  mecanismo central `requiere_rol` dentro del servicio.

Cada endpoint de escritura hace su propio `commit`; el servicio no comitea (mismo patrón que
`api/administracion.py`).
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import operadores as servicio_operadores

router = APIRouter(tags=["turnos"])


class OperadorCuerpo(BaseModel):
    nombre: str
    rol: str
    id_sucursal: int
    pin: str | None = None
    id_operador_solicitante: int


class ActivoCuerpo(BaseModel):
    activo: bool
    id_operador_solicitante: int


@router.get("/operadores")
def listar_operadores(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    operadores = servicio_operadores.listar_operadores_activos(sesion)
    return [servicio_operadores.a_dict(o) for o in operadores]


@router.post("/operadores", status_code=status.HTTP_201_CREATED)
def crear_operador(cuerpo: OperadorCuerpo, sesion: Session = Depends(obtener_sesion)) -> dict:
    operador = servicio_operadores.crear_operador(
        sesion,
        nombre=cuerpo.nombre,
        rol=cuerpo.rol,
        id_sucursal=cuerpo.id_sucursal,
        pin=cuerpo.pin or "",
        id_operador_solicitante=cuerpo.id_operador_solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)


@router.put("/operadores/{id_operador:int}")
def editar_operador(
    id_operador: int, cuerpo: OperadorCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    operador = servicio_operadores.actualizar_operador(
        sesion,
        id_operador=id_operador,
        nombre=cuerpo.nombre,
        rol=cuerpo.rol,
        id_sucursal=cuerpo.id_sucursal,
        pin=cuerpo.pin,
        id_operador_solicitante=cuerpo.id_operador_solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)


@router.post("/operadores/{id_operador:int}/activo")
def cambiar_activo_operador(
    id_operador: int, cuerpo: ActivoCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    operador = servicio_operadores.fijar_activo_operador(
        sesion,
        id_operador=id_operador,
        activo=cuerpo.activo,
        id_operador_solicitante=cuerpo.id_operador_solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)
