"""Servicio de terminales de pago (007, US2 — T020, T021, T022).

- `registrar_terminal` / `mover_o_retirar_terminal` / `registrar_actualizacion_firmware` —
  reservados al encargado (FR-015). Una terminal retirada se marca `activa = False`, NUNCA se borra
  (Principio IV).
- `listar_terminales` — CALCULA al leer los indicadores de firmware con `dominio/firmware.py`
  (research.md #3): no hay tabla de indicadores. NINGUNA señal deshabilita la terminal (FR-012).

Una señal de firmware se atribuye a la sucursal donde estaba la terminal en el momento evaluado
(FR-014), vía `historial_ubicacion`.
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from rasero.config import pagos as cfg
from rasero.dominio.firmware import comparar_version, evaluar_terminal
from rasero.dominio.pagos import hoy_local
from rasero.errores import ErrorPagos
from rasero.seguridad import requiere_rol
from rasero.persistencia.modelos import Sucursal, TerminalPago
from rasero.servicios import bitacora_pagos

_VERSION = r"^[0-9]+\.[0-9]+\.[0-9]+$"


def _sucursal_o_404(sesion: Session, id_sucursal: int) -> Sucursal:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorPagos("pagos_sucursal_no_existe", "Esa sucursal no existe.", status_code=404)
    return sucursal



def _terminal_o_404(sesion: Session, id_terminal_pago: int) -> TerminalPago:
    terminal = sesion.get(TerminalPago, id_terminal_pago)
    if terminal is None:
        raise ErrorPagos(
            "pagos_terminal_no_existe", "Esa terminal de pago no existe.", status_code=404
        )
    return terminal


def _valida_version(version: str) -> None:
    import re

    if not re.match(_VERSION, version or ""):
        raise ErrorPagos(
            "pagos_version_firmware_invalida",
            "La versión de firmware debe tener el formato mayor.menor.parche (por ejemplo 3.2.0).",
        )


def registrar_terminal(
    sesion: Session,
    *,
    identificador: str,
    modelo: str,
    id_sucursal: int,
    version_firmware: str,
    id_operador: int,
    fecha_ultima_actualizacion_firmware: date | None = None,
) -> TerminalPago:
    _valida_version(version_firmware)
    _sucursal_o_404(sesion, id_sucursal)
    requiere_rol(sesion, id_operador, "encargado")
    if sesion.execute(
        select(TerminalPago).where(TerminalPago.identificador == identificador)
    ).scalar_one_or_none() is not None:
        raise ErrorPagos(
            "pagos_identificador_duplicado", "Ya hay una terminal con ese identificador."
        )

    hoy = hoy_local(_sucursal_o_404(sesion, id_sucursal).zona_horaria)
    terminal = TerminalPago(
        identificador=identificador,
        modelo=modelo,
        id_sucursal=id_sucursal,
        version_firmware=version_firmware,
        fecha_ultima_actualizacion_firmware=fecha_ultima_actualizacion_firmware,
        historial_ubicacion=[{"id_sucursal": id_sucursal, "desde": hoy.isoformat(), "hasta": None}],
        historial_firmware=[],
        id_operador_registro=id_operador,
        instante_registro=datetime.now(timezone.utc),
        activa=True,
    )
    sesion.add(terminal)
    sesion.flush()
    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="terminal_registrada",
        id_sucursal=id_sucursal,
        iniciador_tipo="operador",
        id_operador=id_operador,
        id_terminal_pago=terminal.id_terminal_pago,
        referencia_recurso_tipo="terminal_pago",
        referencia_recurso_id=terminal.id_terminal_pago,
    )
    return terminal


def mover_o_retirar_terminal(
    sesion: Session,
    *,
    id_terminal_pago: int,
    id_operador: int,
    id_sucursal_destino: int | None = None,
    fecha_movimiento: date | None = None,
    retirar: bool = False,
) -> TerminalPago:
    terminal = _terminal_o_404(sesion, id_terminal_pago)
    requiere_rol(sesion, id_operador, "encargado")
    zona = _sucursal_o_404(sesion, terminal.id_sucursal).zona_horaria
    fecha = fecha_movimiento or hoy_local(zona)

    if retirar:
        terminal.activa = False
        detalle = "retirada del servicio"
    elif id_sucursal_destino is not None:
        _sucursal_o_404(sesion, id_sucursal_destino)
        historial = list(terminal.historial_ubicacion)
        if historial and historial[-1].get("hasta") is None:
            historial[-1]["hasta"] = (fecha - date.resolution).isoformat()
        historial.append(
            {"id_sucursal": id_sucursal_destino, "desde": fecha.isoformat(), "hasta": None}
        )
        terminal.historial_ubicacion = historial
        flag_modified(terminal, "historial_ubicacion")
        terminal.id_sucursal = id_sucursal_destino
        detalle = f"movida a la sucursal {id_sucursal_destino}"
    else:
        raise ErrorPagos(
            "pagos_movimiento_invalido",
            "Indica una sucursal de destino o marca 'retirar'.",
        )

    sesion.flush()
    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="terminal_movida",
        id_sucursal=terminal.id_sucursal,
        iniciador_tipo="operador",
        id_operador=id_operador,
        id_terminal_pago=terminal.id_terminal_pago,
        referencia_recurso_tipo="terminal_pago",
        referencia_recurso_id=terminal.id_terminal_pago,
        plantilla_valores={"detalle": detalle},
    )
    return terminal


def registrar_actualizacion_firmware(
    sesion: Session,
    *,
    id_terminal_pago: int,
    version: str,
    fecha: date,
    id_operador: int,
) -> TerminalPago:
    _valida_version(version)
    terminal = _terminal_o_404(sesion, id_terminal_pago)
    requiere_rol(sesion, id_operador, "encargado")
    if comparar_version(version, terminal.version_firmware) <= 0:
        raise ErrorPagos(
            "pagos_version_no_avanza",
            "La nueva versión de firmware debe ser posterior a la actual.",
        )
    historial = list(terminal.historial_firmware)
    historial.append({"version": version, "fecha": fecha.isoformat(), "id_operador": id_operador})
    terminal.historial_firmware = historial
    flag_modified(terminal, "historial_firmware")
    terminal.version_firmware = version
    terminal.fecha_ultima_actualizacion_firmware = fecha
    sesion.flush()
    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="firmware_actualizado",
        id_sucursal=terminal.id_sucursal,
        iniciador_tipo="operador",
        id_operador=id_operador,
        id_terminal_pago=terminal.id_terminal_pago,
        referencia_recurso_tipo="terminal_pago",
        referencia_recurso_id=terminal.id_terminal_pago,
        plantilla_valores={"version": version},
    )
    return terminal


def _terminal_a_respuesta(terminal: TerminalPago) -> dict:
    indicadores = evaluar_terminal(
        version_firmware=terminal.version_firmware,
        modelo=terminal.modelo,
        ultima_version_referencia=cfg.ULTIMA_VERSION_FIRMWARE.get(terminal.modelo),
        lista_vulnerable=cfg.LISTA_FIRMWARE_VULNERABLE,
    )
    return {
        "id_terminal_pago": terminal.id_terminal_pago,
        "identificador": terminal.identificador,
        "modelo": terminal.modelo,
        "id_sucursal": terminal.id_sucursal,
        "version_firmware": terminal.version_firmware,
        "fecha_ultima_actualizacion_firmware": (
            terminal.fecha_ultima_actualizacion_firmware.isoformat()
            if terminal.fecha_ultima_actualizacion_firmware
            else None
        ),
        "historial_ubicacion": terminal.historial_ubicacion,
        "historial_firmware": terminal.historial_firmware,
        "activa": terminal.activa,
        **indicadores,
    }


def listar_terminales(
    sesion: Session, *, id_sucursal: int | None, solo_con_senal: bool = False
) -> list[dict]:
    if id_sucursal is None:
        raise ErrorPagos(
            "pagos_sucursal_requerida",
            "Indica una sucursal para consultar sus terminales de pago.",
        )
    terminales = list(
        sesion.execute(
            select(TerminalPago)
            .where(TerminalPago.id_sucursal == id_sucursal)
            .order_by(TerminalPago.id_terminal_pago)
        ).scalars()
    )
    respuestas = [_terminal_a_respuesta(t) for t in terminales]
    if solo_con_senal:
        respuestas = [
            r
            for r in respuestas
            if r["desactualizada"] or r["expuesta_a_clonacion"] or r["version_referencia_desconocida"]
        ]
    return respuestas
