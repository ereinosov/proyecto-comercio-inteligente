"""Servicio de tokenización de datos de pago (007, US3 — T034, T035).

Cuando una `venta` de 001 se cobra con tarjeta, `emitir_token` recibe el número, extrae los últimos
4 dígitos + marca + tipo, genera un token OPACO y persiste SÓLO eso + terminal + `id_venta`. **El
número se descarta; no toca disco ni log.** El PAN, el CVV y los datos de banda/chip NUNCA se
almacenan, registran ni transmiten (FR-017).

Idempotencia (research.md #15): PRIMARIA por `id_venta` (un token por cobro). `clave_idempotencia`
la genera el cliente. Tres casos ante un reintento de red del datáfono:
  1. misma `id_venta` + misma clave  → 200 con el token existente.
  2. misma `id_venta` + clave distinta → 200 con el token existente + evento
     `token_idempotencia_divergente`.
  3. clave ya usada + `id_venta` distinta → 409 `pagos_clave_idempotencia_reusada`.

NO camino crítico (FR-020): si `emitir_token` falla, la venta de 001 se completa igual. 007 NUNCA
ejecuta `UPDATE` sobre `venta` de 001 (research.md #7).
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.config import pagos as cfg
from rasero.dominio import token as dom_token
from rasero.dominio.pagos import dia_local
from rasero.errores import ErrorPagos, PanDetectado
from rasero.persistencia.modelos import Sucursal, TerminalPago, TokenPago, Turno, Venta
from rasero.servicios import bitacora_pagos


def _venta_o_404(sesion: Session, id_venta: int) -> Venta:
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise ErrorPagos("pagos_venta_no_existe", "Esa venta no existe.", status_code=404)
    return venta


def _sucursal_de_venta(sesion: Session, venta: Venta) -> Sucursal:
    turno = sesion.get(Turno, venta.id_turno)
    return sesion.get(Sucursal, turno.id_sucursal)


def emitir_token(
    sesion: Session,
    *,
    id_venta: int,
    id_terminal_pago: int,
    numero_tarjeta: str,
    clave_idempotencia: str,
    marca_tiempo_origen: datetime,
    tipo: str = "desconocido",
) -> tuple[TokenPago, bool]:
    """Devuelve `(token_pago, creado)`. `creado=False` en un reintento idempotente."""
    # --- Idempotencia PRIMARIA: un token por `id_venta` ---
    existente = sesion.execute(
        select(TokenPago).where(TokenPago.id_venta == id_venta)
    ).scalar_one_or_none()
    if existente is not None:
        if existente.clave_idempotencia != clave_idempotencia:
            bitacora_pagos.anexar_entrada(
                sesion,
                tipo_evento="token_idempotencia_divergente",
                id_sucursal=existente.id_sucursal,
                iniciador_tipo="proceso",
                proceso="tokenizacion",
                id_terminal_pago=existente.id_terminal_pago,
                referencia_recurso_tipo="token_pago",
                referencia_recurso_id=existente.token,
                plantilla_valores={"id_venta": id_venta},
            )
        return existente, False

    # --- Segunda barrera: `clave_idempotencia` reusada para otra venta ---
    if sesion.execute(
        select(TokenPago).where(TokenPago.clave_idempotencia == clave_idempotencia)
    ).scalar_one_or_none() is not None:
        raise ErrorPagos(
            "pagos_clave_idempotencia_reusada",
            "Esa clave de idempotencia ya se usó para otro cobro.",
            status_code=409,
        )

    venta = _venta_o_404(sesion, id_venta)
    terminal = sesion.get(TerminalPago, id_terminal_pago)
    if terminal is None:
        raise ErrorPagos(
            "pagos_terminal_no_existe", "Esa terminal de pago no existe.", status_code=404
        )
    if tipo not in ("debito", "credito", "desconocido"):
        tipo = "desconocido"

    # --- Rechazo de PAN / validación del número ---
    if not dom_token.es_luhn_valido(numero_tarjeta):
        raise ErrorPagos(
            "pagos_numero_tarjeta_invalido",
            "El número de tarjeta no es válido (longitud o dígito de control).",
        )
    ultimos, marca = dom_token.extraer_metadato(
        numero_tarjeta, cfg.BIN_MARCA, digitos_conservados=cfg.DIGITOS_CONSERVADOS
    )
    if len(ultimos) != 4 or not ultimos.isdigit():
        # El CHECK de esquema lo impediría igual; esto da un error legible antes.
        _registrar_pan_rechazado(sesion, id_sucursal=_sucursal_de_venta(sesion, venta).id_sucursal)
        raise PanDetectado()

    sucursal = _sucursal_de_venta(sesion, venta)
    instante = datetime.now(timezone.utc)
    token_pago = TokenPago(
        token=dom_token.generar_token(),
        id_venta=id_venta,
        clave_idempotencia=clave_idempotencia,
        ultimos_digitos=ultimos,
        marca=marca,
        tipo=tipo,
        id_terminal_pago=id_terminal_pago,
        id_sucursal=sucursal.id_sucursal,
        instante=instante,
        dia_local=dia_local(instante, sucursal.zona_horaria),
        marca_tiempo_origen=marca_tiempo_origen,
    )
    # `numero_tarjeta` sale de alcance aquí: no se guarda en ninguna variable de larga vida.
    del numero_tarjeta
    sesion.add(token_pago)
    sesion.flush()
    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="token_emitido",
        id_sucursal=sucursal.id_sucursal,
        iniciador_tipo="proceso",
        proceso="tokenizacion",
        id_terminal_pago=id_terminal_pago,
        referencia_recurso_tipo="token_pago",
        referencia_recurso_id=token_pago.token,
        plantilla_valores={"id_venta": id_venta},
    )
    return token_pago, True


def _registrar_pan_rechazado(sesion: Session, *, id_sucursal: int) -> None:
    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="pan_rechazado",
        id_sucursal=id_sucursal,
        iniciador_tipo="proceso",
        proceso="tokenizacion",
    )


def rechazar_pan_en_campos(sesion: Session, *, id_sucursal: int, textos: list[str | None]) -> None:
    """Barrera de FR-018: si cualquier campo de entrada contiene un PAN, se rechaza y se registra
    SIN el número. Llamado por el endpoint antes de tocar el servicio.
    """
    if any(dom_token.detectar_pan(t) for t in textos):
        _registrar_pan_rechazado(sesion, id_sucursal=id_sucursal)
        sesion.commit()
        raise PanDetectado()


def consultar_pago_de_venta(sesion: Session, *, id_venta: int) -> dict:
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise ErrorPagos("pagos_venta_no_existe", "Esa venta no existe.", status_code=404)
    token_pago = sesion.execute(
        select(TokenPago).where(TokenPago.id_venta == id_venta)
    ).scalar_one_or_none()
    if token_pago is None:
        raise ErrorPagos(
            "pagos_venta_sin_tokenizacion",
            "Esa venta no tiene un pago con tarjeta tokenizado (se cobró en efectivo o la "
            "tokenización no llegó a completarse).",
            status_code=404,
        )
    return token_pago_a_respuesta(token_pago)


def token_pago_a_respuesta(token_pago: TokenPago) -> dict:
    return {
        "token": token_pago.token,
        "id_venta": token_pago.id_venta,
        "ultimos_digitos": token_pago.ultimos_digitos,
        "marca": token_pago.marca,
        "tipo": token_pago.tipo,
        "id_terminal_pago": token_pago.id_terminal_pago,
        "id_sucursal": token_pago.id_sucursal,
        "instante": token_pago.instante.isoformat(),
        "dia_local": token_pago.dia_local.isoformat(),
    }
