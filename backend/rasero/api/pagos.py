"""Router de 007-pagos-seguridad (T004 base; T012 cobertura US1; T023 terminales US2;
T036 tokenización US3; T041 bitácora US4).

Prefijo `/pagos` para todo el módulo. Cada endpoint hace su propio `commit`; los servicios no
comitean (salvo el registro de un PAN rechazado, que debe sobrevivir al `raise`).

Este contrato NUNCA participa en `POST /ventas` de 001 ni es camino crítico de un cobro (Principio
II, FR-020). 007 SÓLO LEE de 001 y NUNCA escribe `venta.referencia_terminal_pago`. NUNCA integra
una pasarela real ni mueve dinero (FR-036). Error `{codigo, mensaje}` unificado con 001-006.

`numero_tarjeta` de `POST /pagos/tokens` es `writeOnly`: nunca aparece en ninguna respuesta, log ni
entrada de bitácora (FR-017). El cuerpo de esa petición no se registra literalmente.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.api.paginacion import paginar
from rasero.persistencia.modelos import Operador
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import bitacora_pagos as servicio_bitacora
from rasero.servicios import cobertura_pago as servicio_cobertura
from rasero.servicios import cobros_pagos as servicio_cobros
from rasero.servicios import terminales_pago as servicio_terminales
from rasero.servicios import tokenizacion as servicio_token
from rasero.servicios.tokenizacion import token_pago_a_respuesta

router = APIRouter(tags=["pagos"], prefix="/pagos")

# Identidad del operador de escritura desde el token de sesión de turno (User Story 11). Las
# acciones de este router reservadas a `encargado` la resuelven y validan el rol de una vez.
_Encargado = Depends(exige_rol("encargado"))


# ==========================================================================
# User Story 1 — cobertura de medios de pago por sucursal (T012)
# ==========================================================================


class CoberturaDeclarada(BaseModel):
    id_sucursal: int
    id_medio_pago: int
    acepta: bool
    fecha_desde: date


class IntencionNoAtendida(BaseModel):
    id_sucursal: int
    id_medio_pago_deseado: int
    id_operador: int
    nota: str | None = None
    clave_idempotencia: str


@router.get("/medios")
def listar_medios(sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    return servicio_cobertura.listar_medios(sesion)


@router.put("/cobertura")
def declarar_cobertura(
    cuerpo: CoberturaDeclarada,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    tramo = servicio_cobertura.declarar_cobertura(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        id_medio_pago=cuerpo.id_medio_pago,
        acepta=cuerpo.acepta,
        fecha_desde=cuerpo.fecha_desde,
        operador=operador,
    )
    sesion.commit()
    if tramo is None:
        return {
            "id_cobertura_pago": None,
            "id_medio_pago": cuerpo.id_medio_pago,
            "id_sucursal": cuerpo.id_sucursal,
            "fecha_desde": cuerpo.fecha_desde.isoformat(),
            "fecha_hasta": None,
            "id_operador": operador.id_operador,
        }
    return {
        "id_cobertura_pago": tramo.id_cobertura_pago,
        "id_medio_pago": tramo.id_medio_pago,
        "id_sucursal": tramo.id_sucursal,
        "fecha_desde": tramo.fecha_desde.isoformat(),
        "fecha_hasta": tramo.fecha_hasta.isoformat() if tramo.fecha_hasta else None,
        "id_operador": tramo.id_operador,
    }


@router.get("/cobertura")
def obtener_cobertura(
    id_sucursal: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    return servicio_cobertura.resumen_cobertura(
        sesion, id_sucursal=id_sucursal, desde=desde, hasta=hasta
    )


@router.post("/intencion-no-atendida")
def registrar_intencion_no_atendida(
    cuerpo: IntencionNoAtendida, response: Response, sesion: Session = Depends(obtener_sesion)
) -> dict:
    entrada, creado = servicio_cobertura.registrar_intencion_no_atendida(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        id_medio_pago_deseado=cuerpo.id_medio_pago_deseado,
        id_operador=cuerpo.id_operador,
        clave_idempotencia=cuerpo.clave_idempotencia,
        nota=cuerpo.nota,
    )
    sesion.commit()
    response.status_code = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
    return servicio_bitacora.entrada_a_respuesta(entrada)


# ==========================================================================
# User Story 2 — terminales y vigilancia de firmware (T023)
# ==========================================================================


class TerminalNueva(BaseModel):
    identificador: str
    modelo: str
    id_sucursal: int
    version_firmware: str
    fecha_ultima_actualizacion_firmware: date | None = None


class TerminalMovida(BaseModel):
    id_sucursal_destino: int | None = None
    fecha_movimiento: date | None = None
    retirar: bool = False


class ActualizacionFirmware(BaseModel):
    version: str
    fecha: date


@router.post("/terminales", status_code=status.HTTP_201_CREATED)
def registrar_terminal(
    cuerpo: TerminalNueva,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    terminal = servicio_terminales.registrar_terminal(
        sesion,
        identificador=cuerpo.identificador,
        modelo=cuerpo.modelo,
        id_sucursal=cuerpo.id_sucursal,
        version_firmware=cuerpo.version_firmware,
        fecha_ultima_actualizacion_firmware=cuerpo.fecha_ultima_actualizacion_firmware,
        operador=operador,
    )
    sesion.commit()
    return servicio_terminales._terminal_a_respuesta(terminal)


@router.get("/modelos-firmware")
def listar_modelos_firmware() -> list[dict]:
    """Modelos de datáfono con una última versión de referencia conocida. Un modelo fuera de
    esta lista queda con "versión de referencia desconocida" hasta que el negocio registre su
    versión (variable de entorno `PAGOS_ULTIMA_VERSION_FIRMWARE`).
    """
    from rasero.config import pagos as cfg

    return [
        {"modelo": modelo, "ultima_version_referencia": version}
        for modelo, version in sorted(cfg.ULTIMA_VERSION_FIRMWARE.items())
    ]


@router.get("/terminales")
def listar_terminales(
    id_sucursal: int | None = None,
    solo_con_senal: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_terminales.listar_terminales(
        sesion, id_sucursal=id_sucursal, solo_con_senal=solo_con_senal
    )


@router.patch("/terminales/{id_terminal_pago}")
def mover_terminal(
    id_terminal_pago: int,
    cuerpo: TerminalMovida,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    terminal = servicio_terminales.mover_o_retirar_terminal(
        sesion,
        id_terminal_pago=id_terminal_pago,
        id_sucursal_destino=cuerpo.id_sucursal_destino,
        fecha_movimiento=cuerpo.fecha_movimiento,
        retirar=cuerpo.retirar,
        operador=operador,
    )
    sesion.commit()
    return servicio_terminales._terminal_a_respuesta(terminal)


@router.post("/terminales/{id_terminal_pago}/firmware")
def actualizar_firmware(
    id_terminal_pago: int,
    cuerpo: ActualizacionFirmware,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    terminal = servicio_terminales.registrar_actualizacion_firmware(
        sesion,
        id_terminal_pago=id_terminal_pago,
        version=cuerpo.version,
        fecha=cuerpo.fecha,
        operador=operador,
    )
    sesion.commit()
    return servicio_terminales._terminal_a_respuesta(terminal)


# ==========================================================================
# User Story 3 — tokenización de los datos de pago (T036)
# ==========================================================================


class TokenNuevo(BaseModel):
    id_venta: int
    id_terminal_pago: int
    numero_tarjeta: str = Field(..., json_schema_extra={"writeOnly": True})
    tipo: str = "desconocido"
    clave_idempotencia: str
    marca_tiempo_origen: datetime


@router.post("/tokens")
def emitir_token(
    cuerpo: TokenNuevo, response: Response, sesion: Session = Depends(obtener_sesion)
) -> dict:
    # Barrera de FR-018: un PAN en un campo que no es `numero_tarjeta` (bug de integración) se
    # rechaza y se registra SIN el número. `numero_tarjeta` se valida por Luhn en el servicio.
    servicio_token.rechazar_pan_en_campos(
        sesion,
        id_sucursal=_sucursal_de_venta_segura(sesion, cuerpo.id_venta),
        textos=[cuerpo.tipo, cuerpo.clave_idempotencia],
    )
    token_pago, creado = servicio_token.emitir_token(
        sesion,
        id_venta=cuerpo.id_venta,
        id_terminal_pago=cuerpo.id_terminal_pago,
        numero_tarjeta=cuerpo.numero_tarjeta,
        clave_idempotencia=cuerpo.clave_idempotencia,
        marca_tiempo_origen=cuerpo.marca_tiempo_origen,
        tipo=cuerpo.tipo,
    )
    sesion.commit()
    response.status_code = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
    return token_pago_a_respuesta(token_pago)


def _sucursal_de_venta_segura(sesion: Session, id_venta: int) -> int:
    from rasero.persistencia.modelos import Sucursal, Turno, Venta

    venta = sesion.get(Venta, id_venta)
    if venta is None:
        return 0
    turno = sesion.get(Turno, venta.id_turno)
    if turno is None:
        return 0
    return turno.id_sucursal


@router.get("/ventas/{id_venta}/pago")
def consultar_pago_de_venta(
    id_venta: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    return servicio_token.consultar_pago_de_venta(sesion, id_venta=id_venta)


# ==========================================================================
# User Story 4 — bitácora de auditoría de pagos (T041)
# ==========================================================================


@router.get("/cobros")
def listar_cobros(
    id_sucursal: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    """Libro de ventas de la sucursal con la forma de pago de cada una y el total cobrado por
    medio en el período. Sólo lectura sobre 001.
    """
    return servicio_cobros.listar_cobros(
        sesion, id_sucursal=id_sucursal, desde=desde, hasta=hasta
    )


@router.get("/bitacora")
def consultar_bitacora(
    id_sucursal: int | None = None,
    id_terminal_pago: int | None = None,
    tipo_evento: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int | None = None,
    tamano_pagina: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    entradas = servicio_bitacora.consultar_bitacora(
        sesion,
        id_sucursal=id_sucursal,
        id_terminal_pago=id_terminal_pago,
        tipo_evento=tipo_evento,
        desde=desde,
        hasta=hasta,
    )
    respuestas = [servicio_bitacora.entrada_a_respuesta(e) for e in entradas]
    return paginar(respuestas, pagina=pagina, tamano_pagina=tamano_pagina)
