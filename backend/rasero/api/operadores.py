"""Endpoint GET /operadores (T037). Ver servicios/operadores.py para el porqué de esta adición."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import operadores as servicio_operadores

router = APIRouter(tags=["turnos"])


@router.get("/operadores")
def listar_operadores(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    operadores = servicio_operadores.listar_operadores_activos(sesion)
    return [
        {"id_operador": o.id_operador, "nombre": o.nombre, "es_encargado": o.es_encargado}
        for o in operadores
    ]
