"""Router de operadores.

- `GET /operadores` (T037): listado de operadores activos para elegir al abrir turno. Incluye
  `rol` e `id_sucursal` (User Story 10). Nunca expone `pin_hash`.
- `POST /operadores`, `PUT /operadores/{id}`, `POST /operadores/{id}/activo` (User Story 10,
  Principio VI): gestión **exclusiva del rol `admin`**. **User Story 11 (enmienda v2.4.0)**: la
  identidad del solicitante se deriva del token de sesión de turno (`Authorization: Bearer`),
  no del cuerpo — la dependency `exige_rol("admin")` la resuelve y valida el rol de una vez. El
  campo `id_operador_solicitante` se retiró de los cuerpos.

Cada endpoint de escritura hace su propio `commit`; el servicio no comitea (mismo patrón que
`api/administracion.py`).
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Operador
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import operadores as servicio_operadores

router = APIRouter(tags=["turnos"])

_Admin = Depends(exige_rol("admin"))


class OperadorCuerpo(BaseModel):
    nombre: str
    rol: str
    id_sucursal: int
    pin: str | None = None


class ActivoCuerpo(BaseModel):
    activo: bool


@router.get("/operadores")
def listar_operadores(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    operadores = servicio_operadores.listar_operadores_activos(sesion)
    return [servicio_operadores.a_dict(o) for o in operadores]


@router.post("/operadores", status_code=status.HTTP_201_CREATED)
def crear_operador(
    cuerpo: OperadorCuerpo,
    sesion: Session = Depends(obtener_sesion),
    solicitante: Operador = _Admin,
) -> dict:
    operador = servicio_operadores.crear_operador(
        sesion,
        nombre=cuerpo.nombre,
        rol=cuerpo.rol,
        id_sucursal=cuerpo.id_sucursal,
        pin=cuerpo.pin or "",
        solicitante=solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)


@router.put("/operadores/{id_operador:int}")
def editar_operador(
    id_operador: int,
    cuerpo: OperadorCuerpo,
    sesion: Session = Depends(obtener_sesion),
    solicitante: Operador = _Admin,
) -> dict:
    operador = servicio_operadores.actualizar_operador(
        sesion,
        id_operador=id_operador,
        nombre=cuerpo.nombre,
        rol=cuerpo.rol,
        id_sucursal=cuerpo.id_sucursal,
        pin=cuerpo.pin,
        solicitante=solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)


@router.post("/operadores/{id_operador:int}/activo")
def cambiar_activo_operador(
    id_operador: int,
    cuerpo: ActivoCuerpo,
    sesion: Session = Depends(obtener_sesion),
    solicitante: Operador = _Admin,
) -> dict:
    operador = servicio_operadores.fijar_activo_operador(
        sesion,
        id_operador=id_operador,
        activo=cuerpo.activo,
        solicitante=solicitante,
    )
    sesion.commit()
    return servicio_operadores.a_dict(operador)
