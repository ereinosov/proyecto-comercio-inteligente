"""Listado de operadores activos (T036). Nunca expone `pin_hash`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Operador


def listar_operadores_activos(sesion: Session) -> list[Operador]:
    return list(
        sesion.execute(select(Operador).where(Operador.activo.is_(True))).scalars().all()
    )
