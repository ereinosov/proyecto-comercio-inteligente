"""Seguridad del operador: hash de PIN (autenticación) y verificación de rol (autorización).

**Autenticación** (FR-006, sin cambios): un PIN de 4 dígitos tiene solo 10 000 combinaciones,
así que un algoritmo lento tipo bcrypt no aporta frente a fuerza bruta offline; SHA-256 con sal
por operador basta para no guardarlo en claro.

**Autorización** (Principio VI, enmienda constitucional v2.3.0): `requiere_rol` es el ÚNICO
mecanismo de verificación de rol del backend. Reemplaza las tres comprobaciones locales de
"sólo encargado" que estaban duplicadas en `servicios/administracion.py`,
`servicios/cobertura_pago.py` y `servicios/terminales_pago.py`. La jerarquía es cerrada y
acumulativa: `cajero` (1) < `encargado` (2) < `admin` (3).
"""

import hashlib
import hmac

from sqlalchemy.orm import Session

from rasero.errores import ErrorDominio, OperadorInvalido
from rasero.persistencia.modelos import Operador

# --------------------------------------------------------------------------
# Autenticación
# --------------------------------------------------------------------------


def hashear_pin(pin: str, sal: str) -> str:
    return hashlib.sha256(f"{sal}:{pin}".encode()).hexdigest()


def verificar_pin(pin: str, sal: str, pin_hash: str) -> bool:
    return hmac.compare_digest(hashear_pin(pin, sal), pin_hash)


# --------------------------------------------------------------------------
# Autorización por rol
# --------------------------------------------------------------------------

RANGO_ROL: dict[str, int] = {"cajero": 1, "encargado": 2, "admin": 3}
ROLES = tuple(RANGO_ROL)


class RolInsuficiente(ErrorDominio):
    """El operador existe y está activo, pero su rol no alcanza el mínimo exigido."""

    codigo = "rol_insuficiente"
    status_code = 403


def requiere_rol(sesion: Session, id_operador: int, rol_minimo: str) -> Operador:
    """Resuelve el operador, valida que existe y está activo, y valida que su rol es
    >= `rol_minimo` según `RANGO_ROL`. Devuelve el `Operador` para que el llamador lo use.

    Único punto de verificación de rol del backend (Principio VI). Levanta `ErrorDominio`
    con los códigos ya establecidos del sistema:
      - `operador_invalido` (422) si no existe o está inactivo,
      - `rol_insuficiente` (403) si el rol no alcanza.
    """
    if rol_minimo not in RANGO_ROL:
        raise ValueError(f"rol_minimo desconocido: {rol_minimo!r}")
    operador = sesion.get(Operador, id_operador)
    if operador is None or not operador.activo:
        raise OperadorInvalido()
    if RANGO_ROL.get(operador.rol, 0) < RANGO_ROL[rol_minimo]:
        raise RolInsuficiente(
            f"Esta acción requiere un operador con rol «{rol_minimo}» o superior."
        )
    return operador


def exige_rol(rol_minimo: str):
    """Factory de dependency de FastAPI: `Depends(exige_rol("encargado"))`.

    La dependency lee `id_operador` de la query (convención de parámetro, como `id_sucursal`
    en los listados) y devuelve el `Operador` autorizado. Los routers cuyo `id_operador` viaja
    en el cuerpo del request llaman directamente a `requiere_rol` desde el servicio — es la
    misma función, no un segundo mecanismo.
    """
    from fastapi import Depends

    from rasero.persistencia.sesion import obtener_sesion

    def _dep(id_operador: int, sesion: Session = Depends(obtener_sesion)) -> Operador:
        return requiere_rol(sesion, id_operador, rol_minimo)

    return _dep
