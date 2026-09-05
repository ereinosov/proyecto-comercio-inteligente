"""Apertura y cierre de turno, con verificación de PIN (T025, FR-005, FR-006)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from rasero.errores import OperadorInvalido, PinIncorrecto, RecursoNoEncontrado
from rasero.persistencia.modelos import Operador, Turno
from rasero.seguridad import verificar_pin


def abrir_turno(sesion: Session, *, id_operador: int, id_sucursal: int, caja: str, pin: str) -> Turno:
    operador = sesion.get(Operador, id_operador)
    if operador is None or not operador.activo:
        raise OperadorInvalido()
    if not verificar_pin(pin, str(id_operador), operador.pin_hash):
        raise PinIncorrecto()

    turno = Turno(
        id_operador=id_operador,
        id_sucursal=id_sucursal,
        caja=caja,
        instante_apertura=datetime.now(timezone.utc),
    )
    sesion.add(turno)
    sesion.flush()
    return turno


def cerrar_turno(sesion: Session, *, id_turno: int) -> Turno:
    turno = sesion.get(Turno, id_turno)
    if turno is None:
        raise RecursoNoEncontrado("El turno indicado no existe.")
    if turno.instante_cierre is None:
        turno.instante_cierre = datetime.now(timezone.utc)
        sesion.flush()
    return turno
