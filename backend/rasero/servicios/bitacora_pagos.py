"""Bitácora de auditoría de pagos (007-pagos-seguridad — T006 anexar_entrada; T040 consultar).

`bitacora_auditoria` es de SOLO ANEXADO (Principio IV, FR-025): sólo `INSERT`. Un TRIGGER
`BEFORE UPDATE OR DELETE` (migración 0007) rechaza cualquier modificación o borrado a nivel de
motor — este servicio no tiene ningún método que los ejecute, y no existe ningún endpoint de
edición o borrado.

`resultado` se construye desde una PLANTILLA por `tipo_evento` (research.md #6), nunca desde texto
libre del cliente: así ningún campo puede arrastrar un PAN, un CVV ni datos de banda/chip (FR-026).

`anexar_entrada` es la función que US1–US4 llaman para dejar rastro. Es idempotente cuando se le
pasa `clave_idempotencia` (evita la entrada duplicada por reintento, FR-037).
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.dominio.pagos import dia_local
from rasero.errores import ErrorPagos
from rasero.persistencia.modelos import BitacoraAuditoria, Sucursal

# Plantillas de `resultado` por tipo de evento. `{...}` se rellena con valores no sensibles
# (ids, nombres de medio, versiones de firmware) — nunca con un número de tarjeta.
_PLANTILLAS: dict[str, str] = {
    "token_emitido": "Token emitido para la venta {id_venta} (terminal {id_terminal_pago}).",
    "token_idempotencia_divergente": (
        "Reintento de tokenización de la venta {id_venta} con una clave de idempotencia distinta; "
        "se devolvió el token ya emitido."
    ),
    "token_purgado": "Token purgado: la venta {id_venta} ya no es consultable en 001.",
    "pan_rechazado": (
        "Se rechazó un intento de guardar un número de tarjeta completo. Sólo se conservan la "
        "marca y los últimos cuatro dígitos."
    ),
    "firmware_actualizado": "Firmware de la terminal {id_terminal_pago} actualizado a {version}.",
    "firmware_desactualizado_detectado": (
        "Terminal {id_terminal_pago}: firmware {version_actual} por debajo de la última versión "
        "de referencia {version_referencia}."
    ),
    "terminal_expuesta_detectada": (
        "Terminal {id_terminal_pago}: firmware o modelo con vulnerabilidad de clonación conocida "
        "({referencia})."
    ),
    "terminal_registrada": "Terminal {id_terminal_pago} registrada en la sucursal {id_sucursal}.",
    "terminal_movida": "Terminal {id_terminal_pago}: {detalle}.",
    "medio_pago_alta": "Medio de pago {nombre} dado de alta en el catálogo.",
    "medio_pago_baja": "Medio de pago {nombre} dado de baja del catálogo.",
    "cobertura_declarada": (
        "La sucursal {id_sucursal} {verbo} el medio de pago {nombre} desde {fecha_desde}."
    ),
    "intencion_no_atendida": (
        "Un cliente no pudo completar la compra en la sucursal {id_sucursal}: quería pagar con "
        "{nombre} y no está disponible."
    ),
    "config_firmware_cambiada": "Se actualizó la configuración de referencia de firmware.",
}


def _sucursal_o_404(sesion: Session, id_sucursal: int) -> Sucursal:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorPagos("pagos_sucursal_no_existe", "Esa sucursal no existe.", status_code=404)
    return sucursal


def anexar_entrada(
    sesion: Session,
    *,
    tipo_evento: str,
    id_sucursal: int,
    iniciador_tipo: str,
    id_operador: int | None = None,
    proceso: str | None = None,
    id_terminal_pago: int | None = None,
    id_medio_pago: int | None = None,
    referencia_recurso_tipo: str | None = None,
    referencia_recurso_id: str | int | None = None,
    clave_idempotencia: str | None = None,
    instante: datetime | None = None,
    plantilla_valores: dict | None = None,
) -> BitacoraAuditoria:
    """Anexa (INSERT, nunca UPDATE) una entrada a la bitácora. Idempotente por `clave_idempotencia`.

    `plantilla_valores` rellena la plantilla de `resultado` del tipo de evento — sólo valores no
    sensibles. El llamador NUNCA pasa un número de tarjeta.
    """
    if clave_idempotencia is not None:
        existente = sesion.execute(
            select(BitacoraAuditoria).where(
                BitacoraAuditoria.clave_idempotencia == clave_idempotencia
            )
        ).scalar_one_or_none()
        if existente is not None:
            return existente

    sucursal = _sucursal_o_404(sesion, id_sucursal)
    instante = instante or datetime.now(timezone.utc)
    plantilla = _PLANTILLAS.get(tipo_evento, "{tipo_evento}")
    try:
        resultado = plantilla.format(
            **{
                "tipo_evento": tipo_evento,
                "id_sucursal": id_sucursal,
                "id_terminal_pago": id_terminal_pago,
                **(plantilla_valores or {}),
            }
        )
    except KeyError:
        resultado = plantilla

    entrada = BitacoraAuditoria(
        tipo_evento=tipo_evento,
        instante=instante,
        dia_local=dia_local(instante, sucursal.zona_horaria),
        id_sucursal=id_sucursal,
        id_terminal_pago=id_terminal_pago,
        id_medio_pago=id_medio_pago,
        iniciador_tipo=iniciador_tipo,
        id_operador=id_operador,
        proceso=proceso,
        resultado=resultado,
        referencia_recurso_tipo=referencia_recurso_tipo,
        referencia_recurso_id=(
            str(referencia_recurso_id) if referencia_recurso_id is not None else None
        ),
        clave_idempotencia=clave_idempotencia,
    )
    sesion.add(entrada)
    sesion.flush()
    return entrada


def consultar_bitacora(
    sesion: Session,
    *,
    id_sucursal: int | None,
    id_terminal_pago: int | None = None,
    tipo_evento: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[BitacoraAuditoria]:
    """Rastro filtrable, sólo lectura (FR-027). Exige `id_sucursal` — nunca se mezclan sucursales."""
    if id_sucursal is None:
        raise ErrorPagos(
            "pagos_sucursal_requerida",
            "Indica una sucursal para consultar su bitácora de pagos (no se mezclan sucursales).",
        )
    if desde is not None and hasta is not None and hasta < desde:
        raise ErrorPagos(
            "pagos_rango_invalido", "El rango de fechas no es válido: 'hasta' es anterior a 'desde'."
        )
    consulta = select(BitacoraAuditoria).where(BitacoraAuditoria.id_sucursal == id_sucursal)
    if id_terminal_pago is not None:
        consulta = consulta.where(BitacoraAuditoria.id_terminal_pago == id_terminal_pago)
    if tipo_evento is not None:
        consulta = consulta.where(BitacoraAuditoria.tipo_evento == tipo_evento)
    if desde is not None:
        consulta = consulta.where(BitacoraAuditoria.dia_local >= desde)
    if hasta is not None:
        consulta = consulta.where(BitacoraAuditoria.dia_local <= hasta)
    consulta = consulta.order_by(BitacoraAuditoria.id_bitacora_auditoria.desc())
    return list(sesion.execute(consulta).scalars())


def entrada_a_respuesta(entrada: BitacoraAuditoria) -> dict:
    return {
        "id_bitacora_auditoria": entrada.id_bitacora_auditoria,
        "tipo_evento": entrada.tipo_evento,
        "instante": entrada.instante.isoformat(),
        "dia_local": entrada.dia_local.isoformat(),
        "id_sucursal": entrada.id_sucursal,
        "id_terminal_pago": entrada.id_terminal_pago,
        "id_medio_pago": entrada.id_medio_pago,
        "iniciador_tipo": entrada.iniciador_tipo,
        "id_operador": entrada.id_operador,
        "proceso": entrada.proceso,
        "resultado": entrada.resultado,
        "referencia_recurso_tipo": entrada.referencia_recurso_tipo,
        "referencia_recurso_id": entrada.referencia_recurso_id,
    }
