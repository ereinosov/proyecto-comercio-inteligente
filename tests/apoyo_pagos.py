"""Helpers de datos para las pruebas de 007-pagos-seguridad. No es un archivo de pruebas.

007 SÓLO LEE de 001 (`venta`, `turno`, `sucursal`, `operador`); las pruebas de frontera cuentan
filas de esas tablas antes y después. Los números de tarjeta de abajo son de PRUEBA públicos
(pasan Luhn) — no corresponden a ninguna tarjeta real.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import Operador, Sucursal, TerminalPago, Turno, Venta
from rasero.servicios import terminales_pago

_ZONA = "America/Guayaquil"

# Números de tarjeta de prueba públicos (pasan validación de Luhn).
TARJETA_VISA = "4111111111111111"
TARJETA_MASTERCARD = "5555555555554444"
TARJETA_AMEX = "378282246310005"
TARJETA_INVALIDA_LUHN = "4111111111111112"


def crear_sucursal(sesion, *, zona: str = _ZONA) -> Sucursal:
    sucursal = Sucursal(
        nombre=f"Sucursal pagos {datetime.now().timestamp()}-{uuid.uuid4().hex[:6]}",
        zona_horaria=zona,
    )
    sesion.add(sucursal)
    sesion.flush()
    return sucursal


def crear_operador(
    sesion, *, es_encargado: bool = False, rol: str | None = None, id_sucursal: int | None = None
) -> Operador:
    # Enmienda v2.3.0: `rol` + `id_sucursal` en vez de `es_encargado` (alias conservado; los
    # archivos de tests, fuera de `backend/`, no los alcanza SC-013).
    if rol is None:
        rol = "encargado" if es_encargado else "cajero"
    if id_sucursal is None:
        id_sucursal = crear_sucursal(sesion).id_sucursal
    operador = Operador(
        nombre=f"Operador {uuid.uuid4().hex[:6]}",
        pin_hash="",
        rol=rol,
        id_sucursal=id_sucursal,
        activo=True,
    )
    sesion.add(operador)
    sesion.flush()
    return operador


def crear_turno(sesion, *, id_operador: int, id_sucursal: int) -> Turno:
    turno = Turno(
        id_operador=id_operador,
        id_sucursal=id_sucursal,
        caja="caja-1",
        instante_apertura=datetime.now(timezone.utc) - timedelta(hours=8),
        instante_cierre=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    sesion.add(turno)
    sesion.flush()
    return turno


def crear_venta(sesion, *, id_turno: int, total: str = "10.00") -> Venta:
    venta = Venta(
        clave_idempotencia=f"pagos-{uuid.uuid4()}",
        id_turno=id_turno,
        referencia_terminal_pago=None,
        instante=datetime.now(timezone.utc) - timedelta(hours=2),
        total=Decimal(str(total)),
    )
    sesion.add(venta)
    sesion.flush()
    return venta


def crear_terminal(
    sesion,
    *,
    id_sucursal: int,
    id_operador_encargado: int,
    modelo: str = "P400",
    version_firmware: str = "3.2.0",
    identificador: str | None = None,
) -> TerminalPago:
    terminal = terminales_pago.registrar_terminal(
        sesion,
        identificador=identificador or f"TERM-{uuid.uuid4().hex[:8]}",
        modelo=modelo,
        id_sucursal=id_sucursal,
        version_firmware=version_firmware,
        id_operador=id_operador_encargado,
    )
    sesion.flush()
    return terminal


def escenario_cobro_con_tarjeta(sesion):
    """Sucursal + operador encargado + turno cerrado + venta + terminal. Devuelve un dict."""
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    turno = crear_turno(sesion, id_operador=encargado.id_operador, id_sucursal=sucursal.id_sucursal)
    venta = crear_venta(sesion, id_turno=turno.id_turno)
    terminal = crear_terminal(
        sesion,
        id_sucursal=sucursal.id_sucursal,
        id_operador_encargado=encargado.id_operador,
    )
    sesion.commit()
    return {
        "sucursal": sucursal,
        "encargado": encargado,
        "turno": turno,
        "venta": venta,
        "terminal": terminal,
    }
