"""Servicio de cobertura de medios de pago (007, US1 — T010, T011).

- `declarar_cobertura` — abre/cierra tramos de aceptación de un medio en una sucursal (histórico,
  FR-002). Reservado al encargado (FR-007). La restricción de exclusión `gist` rechaza cualquier
  solape.
- `resumen_cobertura` — por medio, si la sucursal lo aceptaba en el período; DERIVA la cuota de
  intención no atendida de `bitacora_auditoria` (research.md #5). Exige `id_sucursal` (FR-006).
- `registrar_intencion_no_atendida` — SÓLO anexa un evento a la bitácora. NUNCA crea `venta` ni
  `consulta_no_atendida` de 001 (Lectura Crítica n.º 4, FR-005).

007 SÓLO LEE de 001 (`sucursal`, `operador`).
"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.dominio.cobertura import cerrar_tramo_anterior, cobertura_en_fecha, cuota_no_atendida
from rasero.dominio.pagos import hoy_local
from rasero.errores import ErrorPagos
from rasero.persistencia.modelos import (
    BitacoraAuditoria,
    CoberturaPago,
    MedioPago,
    Operador,
    Sucursal,
)
from rasero.servicios import bitacora_pagos


def _sucursal_o_404(sesion: Session, id_sucursal: int) -> Sucursal:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorPagos("pagos_sucursal_no_existe", "Esa sucursal no existe.", status_code=404)
    return sucursal


def _medio_o_404(sesion: Session, id_medio_pago: int) -> MedioPago:
    medio = sesion.get(MedioPago, id_medio_pago)
    if medio is None:
        raise ErrorPagos("pagos_medio_no_existe", "Ese medio de pago no existe.", status_code=404)
    return medio


def _encargado_o_error(sesion: Session, id_operador: int) -> Operador:
    operador = sesion.get(Operador, id_operador)
    if operador is None:
        raise ErrorPagos("pagos_operador_no_existe", "Ese operador no existe.", status_code=404)
    if not operador.es_encargado:
        raise ErrorPagos(
            "pagos_operador_no_encargado",
            "Sólo un encargado puede cambiar qué medios de pago acepta una sucursal.",
        )
    return operador


def listar_medios(sesion: Session) -> list[dict]:
    medios = list(sesion.execute(select(MedioPago).order_by(MedioPago.id_medio_pago)).scalars())
    return [
        {
            "id_medio_pago": m.id_medio_pago,
            "nombre": m.nombre,
            "requiere_terminal": m.requiere_terminal,
            "admite_tokenizacion": m.admite_tokenizacion,
            "activo": m.activo,
        }
        for m in medios
    ]


def declarar_cobertura(
    sesion: Session,
    *,
    id_sucursal: int,
    id_medio_pago: int,
    acepta: bool,
    fecha_desde: date,
    id_operador: int,
) -> CoberturaPago | None:
    _sucursal_o_404(sesion, id_sucursal)
    medio = _medio_o_404(sesion, id_medio_pago)
    _encargado_o_error(sesion, id_operador)

    # Cierra el tramo vigente (fecha_hasta IS NULL) para este (medio, sucursal).
    tramo_vigente = sesion.execute(
        select(CoberturaPago).where(
            CoberturaPago.id_sucursal == id_sucursal,
            CoberturaPago.id_medio_pago == id_medio_pago,
            CoberturaPago.fecha_hasta.is_(None),
        )
    ).scalar_one_or_none()
    if tramo_vigente is not None:
        cierre = cerrar_tramo_anterior(fecha_desde)
        if cierre < tramo_vigente.fecha_desde:
            raise ErrorPagos(
                "pagos_fecha_invalida",
                "La fecha de inicio es anterior o igual al inicio del tramo vigente.",
            )
        tramo_vigente.fecha_hasta = cierre
        sesion.flush()

    nuevo: CoberturaPago | None = None
    if acepta:
        nuevo = CoberturaPago(
            id_medio_pago=id_medio_pago,
            id_sucursal=id_sucursal,
            fecha_desde=fecha_desde,
            fecha_hasta=None,
            id_operador=id_operador,
            instante_registro=datetime.now(timezone.utc),
        )
        sesion.add(nuevo)
        try:
            sesion.flush()
        except Exception as exc:  # ExclusionViolation de la restricción gist
            if "ex_cobertura_pago_sin_solape" in str(exc):
                raise ErrorPagos(
                    "pagos_solape_de_tramos",
                    "Ya hay un tramo de cobertura que se solapa con estas fechas para ese medio.",
                )
            raise

    bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="cobertura_declarada",
        id_sucursal=id_sucursal,
        iniciador_tipo="operador",
        id_operador=id_operador,
        id_medio_pago=id_medio_pago,
        referencia_recurso_tipo="cobertura_pago",
        referencia_recurso_id=(nuevo.id_cobertura_pago if nuevo is not None else None),
        plantilla_valores={
            "nombre": medio.nombre,
            "fecha_desde": fecha_desde.isoformat(),
            "verbo": "acepta" if acepta else "deja de aceptar",
        },
    )
    return nuevo


def registrar_intencion_no_atendida(
    sesion: Session,
    *,
    id_sucursal: int,
    id_medio_pago_deseado: int,
    id_operador: int,
    clave_idempotencia: str,
    nota: str | None = None,
) -> tuple[BitacoraAuditoria, bool]:
    """Devuelve `(entrada, creado)`. `creado=False` en un reintento con la misma clave."""
    _sucursal_o_404(sesion, id_sucursal)
    medio = _medio_o_404(sesion, id_medio_pago_deseado)
    if sesion.get(Operador, id_operador) is None:
        raise ErrorPagos("pagos_operador_no_existe", "Ese operador no existe.", status_code=404)
    ya_existe = sesion.execute(
        select(BitacoraAuditoria.id_bitacora_auditoria).where(
            BitacoraAuditoria.clave_idempotencia == clave_idempotencia
        )
    ).scalar_one_or_none()
    # SÓLO anexa a la bitácora. NUNCA crea venta ni consulta_no_atendida de 001 (FR-005).
    entrada = bitacora_pagos.anexar_entrada(
        sesion,
        tipo_evento="intencion_no_atendida",
        id_sucursal=id_sucursal,
        iniciador_tipo="operador",
        id_operador=id_operador,
        id_medio_pago=id_medio_pago_deseado,
        clave_idempotencia=clave_idempotencia,
        plantilla_valores={"nombre": medio.nombre},
    )
    return entrada, ya_existe is None


def resumen_cobertura(
    sesion: Session,
    *,
    id_sucursal: int | None,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    if id_sucursal is None:
        raise ErrorPagos(
            "pagos_sucursal_requerida",
            "Indica una sucursal para consultar su cobertura de medios de pago.",
        )
    if desde is not None and hasta is not None and hasta < desde:
        raise ErrorPagos(
            "pagos_rango_invalido", "El rango de fechas no es válido: 'hasta' es anterior a 'desde'."
        )
    sucursal = sesion.get(Sucursal, id_sucursal)
    medios = list(sesion.execute(select(MedioPago).order_by(MedioPago.id_medio_pago)).scalars())

    if sucursal is None:
        return {
            "id_sucursal": id_sucursal,
            "periodo": "sucursal inexistente en el período",
            "medios": [],
            "total_intencion_no_atendida": 0,
        }

    hoy = hoy_local(sucursal.zona_horaria)
    ref_desde = desde or hoy
    ref_hasta = hasta or hoy

    tramos_por_medio: dict[int, list[tuple[date, date | None]]] = {}
    for fila in sesion.execute(
        select(CoberturaPago).where(CoberturaPago.id_sucursal == id_sucursal)
    ).scalars():
        tramos_por_medio.setdefault(fila.id_medio_pago, []).append(
            (fila.fecha_desde, fila.fecha_hasta)
        )

    # Eventos de intención no atendida de la sucursal en el período, por medio deseado.
    consulta_eventos = select(
        BitacoraAuditoria.id_medio_pago, func.count()
    ).where(
        BitacoraAuditoria.id_sucursal == id_sucursal,
        BitacoraAuditoria.tipo_evento == "intencion_no_atendida",
    )
    if desde is not None:
        consulta_eventos = consulta_eventos.where(BitacoraAuditoria.dia_local >= desde)
    if hasta is not None:
        consulta_eventos = consulta_eventos.where(BitacoraAuditoria.dia_local <= hasta)
    consulta_eventos = consulta_eventos.group_by(BitacoraAuditoria.id_medio_pago)
    eventos_por_medio = {
        medio_id: n for medio_id, n in sesion.execute(consulta_eventos).all()
    }
    total_eventos = sum(eventos_por_medio.values())
    cuotas = cuota_no_atendida(
        {m.id_medio_pago: eventos_por_medio.get(m.id_medio_pago, 0) for m in medios},
        total_eventos,
    )

    return {
        "id_sucursal": id_sucursal,
        "periodo": f"{ref_desde.isoformat()} a {ref_hasta.isoformat()}",
        "medios": [
            {
                "id_medio_pago": m.id_medio_pago,
                "nombre": m.nombre,
                "cubierto": cobertura_en_fecha(tramos_por_medio.get(m.id_medio_pago, []), ref_desde)
                and cobertura_en_fecha(tramos_por_medio.get(m.id_medio_pago, []), ref_hasta),
                "intencion_no_atendida": eventos_por_medio.get(m.id_medio_pago, 0),
                "cuota_no_atendida": cuotas[m.id_medio_pago],
            }
            for m in medios
        ],
        "total_intencion_no_atendida": total_eventos,
    }
