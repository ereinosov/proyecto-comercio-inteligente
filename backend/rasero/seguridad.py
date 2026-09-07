"""Seguridad del operador: hash de PIN (autenticación), token de sesión de turno (identidad de
sesión) y verificación de rol (autorización). Un solo mecanismo, sin duplicar.

**Autenticación** (FR-006, sin cambios): un PIN de 4 dígitos tiene solo 10 000 combinaciones,
así que un algoritmo lento tipo bcrypt no aporta frente a fuerza bruta offline; SHA-256 con sal
por operador basta para no guardarlo en claro. Es la credencial que se presenta al abrir turno.

**Identidad de sesión** (Principio VI, sub-sección "Identidad de sesión", enmienda v2.4.0; User
Story 11): al abrir turno, tras validar el PIN, `emitir_token_turno` firma un JWT (HS256) con
los claims `id_operador`, `id_turno`, `rol` y `exp` (12 h). La dependency `operador_de_sesion`
lo verifica en cada petición sujeta a rol —firma, expiración, turno abierto, operador activo— y
devuelve el `Operador`. El backend NUNCA autoriza confiando en el `rol` del claim: `requiere_rol`
resuelve el rango desde el `Operador` real que la dependency cargó de la base.

**Autorización** (Principio VI, enmienda constitucional v2.3.0): `requiere_rol` es el ÚNICO
mecanismo de verificación de rol del backend. Reemplaza las tres comprobaciones locales de
"sólo encargado" que estaban duplicadas en `servicios/administracion.py`,
`servicios/cobertura_pago.py` y `servicios/terminales_pago.py`. La jerarquía es cerrada y
acumulativa: `cajero` (1) < `encargado` (2) < `admin` (3). Desde v2.4.0 recibe el `Operador` ya
resuelto por `operador_de_sesion`, no un `id_operador` crudo del cuerpo.
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from rasero.configuracion import JWT_ALGORITMO, JWT_HORAS_EXPIRACION, JWT_SECRET_KEY
from rasero.errores import ErrorDominio, OperadorInvalido, SesionExpirada, SesionInvalida
from rasero.persistencia.modelos import Operador, Turno
from rasero.persistencia.sesion import obtener_sesion as _obtener_sesion

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


def requiere_rol(operador: Operador, rol_minimo: str) -> Operador:
    """Valida que `operador` está activo y que su rol es >= `rol_minimo` según `RANGO_ROL`.
    Devuelve el mismo `Operador` para encadenar.

    Único punto de verificación de rol del backend (Principio VI). Desde la enmienda v2.4.0
    recibe el `Operador` ya resuelto por `operador_de_sesion` (identidad del token de turno),
    no un `id_operador` del cuerpo. Levanta `ErrorDominio` con los códigos ya establecidos:
      - `operador_invalido` (422) si está inactivo,
      - `rol_insuficiente` (403) si el rol no alcanza.
    """
    if rol_minimo not in RANGO_ROL:
        raise ValueError(f"rol_minimo desconocido: {rol_minimo!r}")
    if operador is None or not operador.activo:
        raise OperadorInvalido()
    if RANGO_ROL.get(operador.rol, 0) < RANGO_ROL[rol_minimo]:
        raise RolInsuficiente(
            f"Esta acción requiere un operador con rol «{rol_minimo}» o superior."
        )
    return operador


# --------------------------------------------------------------------------
# Identidad de sesión de turno (token JWT) — Principio VI, enmienda v2.4.0
# --------------------------------------------------------------------------


def emitir_token_turno(*, id_operador: int, id_turno: int, rol: str) -> str:
    """Firma el token de sesión de turno. Se emite en `POST /turnos`, sólo tras validar el PIN.
    Un token por turno abierto. El `rol` va en el claim SÓLO para la interfaz; el backend nunca
    autoriza confiando en él.
    """
    ahora = datetime.now(timezone.utc)
    carga = {
        "id_operador": id_operador,
        "id_turno": id_turno,
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(hours=JWT_HORAS_EXPIRACION),
    }
    return jwt.encode(carga, JWT_SECRET_KEY, algorithm=JWT_ALGORITMO)


def _claims_de_token(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise SesionInvalida()
    token = authorization[7:].strip()
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise SesionExpirada()
    except jwt.InvalidTokenError:
        raise SesionInvalida()


def resolver_operador_de_sesion(sesion: Session, authorization: str | None) -> Operador:
    """Resuelve el `Operador` de la petición desde el token de turno. Rechaza con `401`:
      - `sesion_invalida`: header ausente/mal formado, firma inválida, turno cerrado, operador
        inexistente o desactivado;
      - `sesion_expirada`: el `exp` del token ya pasó.
    Es la única fuente de identidad de operador en un endpoint sujeto a rol (FR-067). Función
    pura (sin FastAPI) para poder probarla directamente; la dependency es `operador_de_sesion`.
    """
    claims = _claims_de_token(authorization)
    turno = sesion.get(Turno, claims.get("id_turno"))
    if turno is None or turno.instante_cierre is not None:
        raise SesionInvalida()
    operador = sesion.get(Operador, claims.get("id_operador"))
    if operador is None or not operador.activo:
        raise SesionInvalida()
    return operador


def operador_de_sesion(
    authorization: str | None = Header(default=None),
    sesion: Session = Depends(_obtener_sesion),
) -> Operador:
    """Dependency de FastAPI: `operador: Operador = Depends(operador_de_sesion)`. Verifica el
    token de sesión de turno del header `Authorization` y devuelve el `Operador`.
    """
    return resolver_operador_de_sesion(sesion, authorization)


def exige_rol(rol_minimo: str):
    """Factory de dependency de FastAPI: `operador: Operador = Depends(exige_rol("encargado"))`.

    Compone `operador_de_sesion` (identidad del token de turno) con `requiere_rol` (rango). Es
    el único camino para exigir rol en un router; ningún servicio vuelve a chequear identidad.
    """

    def _dep(operador: Operador = Depends(operador_de_sesion)) -> Operador:
        return requiere_rol(operador, rol_minimo)

    return _dep
