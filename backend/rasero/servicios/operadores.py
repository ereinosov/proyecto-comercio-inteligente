"""Operadores: listado (T036) y gestión admin-only (User Story 10, Principio VI).

`listar_operadores_activos` nunca expone `pin_hash`. El alta, la edición de rol/sucursal y la
desactivación son **exclusivas del rol `admin`** (FR-059): ningún `encargado` puede ascender a
otro operador. La verificación pasa por el mecanismo central `requiere_rol`. La **identidad**
del solicitante llega ya resuelta desde el token de sesión de turno (dependency `exige_rol` del
router), no de un campo del cuerpo — enmienda v2.4.0, User Story 11.

Los servicios no comitean: la transacción queda a cargo del endpoint (mismo patrón que
`servicios/administracion.py`).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.errores import ErrorAdministracion
from rasero.persistencia.modelos import Operador, Sucursal
from rasero.seguridad import ROLES, hashear_pin, requiere_rol


def listar_operadores_activos(sesion: Session) -> list[Operador]:
    return list(
        sesion.execute(select(Operador).where(Operador.activo.is_(True))).scalars().all()
    )


def _valida_rol(rol: str) -> str:
    if rol not in ROLES:
        raise ErrorAdministracion(
            "admin_rol_invalido", "El rol debe ser uno de: cajero, encargado o admin."
        )
    return rol


def _valida_sucursal(sesion: Session, id_sucursal: int) -> None:
    if sesion.get(Sucursal, id_sucursal) is None:
        raise ErrorAdministracion("admin_sucursal_no_existe", "Esa sucursal no existe.")


def _texto(valor: str, campo: str) -> str:
    limpio = (valor or "").strip()
    if not limpio:
        raise ErrorAdministracion(
            "admin_campo_requerido", f"El campo «{campo}» es obligatorio."
        )
    return limpio


def _valida_pin(pin: str) -> str:
    pin = (pin or "").strip()
    if not (len(pin) == 4 and pin.isdigit()):
        raise ErrorAdministracion(
            "admin_pin_invalido", "El PIN debe ser exactamente 4 dígitos."
        )
    return pin


def crear_operador(
    sesion: Session,
    *,
    nombre: str,
    rol: str,
    id_sucursal: int,
    pin: str,
    solicitante: Operador,
) -> Operador:
    requiere_rol(solicitante, "admin")
    nombre = _texto(nombre, "nombre")
    _valida_rol(rol)
    _valida_sucursal(sesion, id_sucursal)
    _valida_pin(pin)
    operador = Operador(nombre=nombre, rol=rol, id_sucursal=id_sucursal, pin_hash="", activo=True)
    sesion.add(operador)
    sesion.flush()
    operador.pin_hash = hashear_pin(pin, str(operador.id_operador))
    sesion.flush()
    return operador


def actualizar_operador(
    sesion: Session,
    *,
    id_operador: int,
    nombre: str,
    rol: str,
    id_sucursal: int,
    pin: str | None,
    solicitante: Operador,
) -> Operador:
    requiere_rol(solicitante, "admin")
    operador = sesion.get(Operador, id_operador)
    if operador is None:
        raise ErrorAdministracion(
            "admin_operador_no_existe", "Ese operador no existe.", status_code=404
        )
    operador.nombre = _texto(nombre, "nombre")
    operador.rol = _valida_rol(rol)
    _valida_sucursal(sesion, id_sucursal)
    operador.id_sucursal = id_sucursal
    if pin is not None and pin.strip():
        operador.pin_hash = hashear_pin(_valida_pin(pin), str(operador.id_operador))
    sesion.flush()
    return operador


def fijar_activo_operador(
    sesion: Session, *, id_operador: int, activo: bool, solicitante: Operador
) -> Operador:
    requiere_rol(solicitante, "admin")
    operador = sesion.get(Operador, id_operador)
    if operador is None:
        raise ErrorAdministracion(
            "admin_operador_no_existe", "Ese operador no existe.", status_code=404
        )
    operador.activo = bool(activo)
    sesion.flush()
    return operador


def a_dict(o: Operador) -> dict:
    return {
        "id_operador": o.id_operador,
        "nombre": o.nombre,
        "rol": o.rol,
        "id_sucursal": o.id_sucursal,
        "activo": o.activo,
    }
