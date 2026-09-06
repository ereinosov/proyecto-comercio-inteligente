"""Apertura y cierre de turno, con verificación de PIN (T025, FR-005, FR-006).

Autorización de sucursal (User Story 10, Principio VI, enmienda v2.3.0): un operador con rol
`cajero` o `encargado` sólo puede abrir turno en `operador.id_sucursal`; el frontend ya no le
muestra selector. Un `admin` abre turno en cualquier sucursal (su `id_sucursal` es dato de
registro, no restricción). El rechazo de backend es defensa en profundidad — el formato
`{codigo, mensaje}` es el del resto del sistema.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from rasero.errores import ErrorDominio, OperadorInvalido, PinIncorrecto, RecursoNoEncontrado
from rasero.persistencia.modelos import Operador, Sucursal, Turno
from rasero.seguridad import verificar_pin


class TurnoSucursalNoAsignada(ErrorDominio):
    codigo = "turno_sucursal_no_asignada"
    status_code = 422


def abrir_turno(sesion: Session, *, id_operador: int, id_sucursal: int, caja: str, pin: str) -> Turno:
    operador = sesion.get(Operador, id_operador)
    if operador is None or not operador.activo:
        raise OperadorInvalido()
    if not verificar_pin(pin, str(id_operador), operador.pin_hash):
        raise PinIncorrecto()

    if operador.rol != "admin" and id_sucursal != operador.id_sucursal:
        asignada = sesion.get(Sucursal, operador.id_sucursal)
        nombre = asignada.nombre if asignada is not None else f"#{operador.id_sucursal}"
        raise TurnoSucursalNoAsignada(
            f"Este operador está asignado a {nombre}, no puede abrir turno en otra sucursal."
        )

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
