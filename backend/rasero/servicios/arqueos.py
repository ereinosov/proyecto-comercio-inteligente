"""Servicio del arqueo de caja (006-caja-mermas-fraude, US1 — T011, T012).

- `registrar_arqueo` — cuadre de un `turno` cerrado de 001. Calcula `monto_esperado` =
  SUM(venta.total) del turno (consulta a 001) y lo **congela**; idempotente por `UNIQUE (id_turno)`
  (FR-005). Una diferencia sin `motivo_conocido` fuera de la tolerancia crea una `AnomaliaCaja` de
  origen efectivo en la misma transacción (FR-004, FR-027). NUNCA escribe en `venta` ni en ninguna
  tabla de 001 (SC-002, SC-011).
- `listar_arqueos` / `ajustar_arqueo` — consulta por sucursal y período (exige `id_sucursal`,
  FR-038); una corrección se anota en `ajustes` (JSONB) sin reescribir `monto_esperado`
  (research.md #13).

El servicio NO comitea: deja la transacción a cargo del endpoint (mismo patrón que
`servicios/promociones.py` de 005).
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config import caja as cfg
from rasero.dominio.arqueo import dia_local, debe_generar_anomalia, diferencia_con_signo
from rasero.errores import ErrorCaja
from rasero.persistencia.modelos import AnomaliaCaja, Arqueo, Sucursal, Turno, Venta

_DOS_DECIMALES = Decimal("0.01")


def _turno_no_existe() -> ErrorCaja:
    return ErrorCaja(
        "caja_turno_no_existe",
        "Ese turno no existe. Verifica el número de turno.",
        status_code=404,
    )


def _monto_a_decimal(valor) -> Decimal:
    try:
        monto = Decimal(str(valor)).quantize(_DOS_DECIMALES)
    except (InvalidOperation, ValueError):
        raise ErrorCaja(
            "caja_monto_invalido",
            "El monto contado no es un número válido. Escríbelo con dos decimales, por ejemplo 19.50.",
        )
    if monto < 0:
        raise ErrorCaja(
            "caja_monto_invalido", "El monto contado no puede ser negativo."
        )
    return monto


def registrar_arqueo(
    sesion: Session,
    *,
    id_turno: int,
    monto_contado,
    motivo_conocido: str | None = None,
    marca_tiempo_origen: datetime,
) -> tuple[Arqueo, bool]:
    """Devuelve `(arqueo, creado_ahora)`. `creado_ahora = False` cuando el turno ya estaba
    arqueado (idempotencia FR-005).
    """
    turno = sesion.get(Turno, id_turno)
    if turno is None:
        raise _turno_no_existe()

    existente = sesion.execute(
        select(Arqueo).where(Arqueo.id_turno == id_turno)
    ).scalar_one_or_none()
    if existente is not None:
        return existente, False

    if turno.instante_cierre is None:
        raise ErrorCaja(
            "caja_turno_abierto",
            "El turno todavía está abierto. Ciérralo antes de arquear la caja.",
        )

    monto = _monto_a_decimal(monto_contado)
    motivo = motivo_conocido.strip() if motivo_conocido and motivo_conocido.strip() else None

    sucursal = sesion.get(Sucursal, turno.id_sucursal)
    # `monto_esperado` = suma de los cobros del turno, CONGELADA (research.md #4). Consulta de solo
    # lectura a `venta` de 001.
    monto_esperado = sesion.execute(
        select(func.coalesce(func.sum(Venta.total), Decimal("0"))).where(
            Venta.id_turno == id_turno
        )
    ).scalar_one()
    monto_esperado = Decimal(monto_esperado).quantize(_DOS_DECIMALES)

    diferencia = diferencia_con_signo(monto, monto_esperado)
    dia = dia_local(turno.instante_cierre, sucursal.zona_horaria)
    ahora = datetime.now(timezone.utc)

    arqueo = Arqueo(
        id_turno=id_turno,
        id_operador=turno.id_operador,
        id_sucursal=turno.id_sucursal,
        dia_local=dia,
        monto_esperado=monto_esperado,
        monto_contado=monto,
        diferencia=diferencia,
        motivo_conocido=motivo,
        ajustes=[],
        instante_cierre_arqueo=ahora,
        marca_tiempo_origen=marca_tiempo_origen,
    )
    sesion.add(arqueo)
    sesion.flush()

    if debe_generar_anomalia(diferencia, motivo, cfg.TOLERANCIA_CUADRE_ARQUEO):
        anomalia = AnomaliaCaja(
            origen="efectivo",
            estado="sin_explicacion",
            id_sucursal=turno.id_sucursal,
            id_arqueo=arqueo.id_arqueo,
            id_turno=id_turno,
            id_operador=turno.id_operador,
            monto=diferencia,
            dia_local=dia,
            historial=[
                {
                    "estado": "sin_explicacion",
                    "instante": ahora.isoformat(),
                    "id_operador": None,
                    "nota": "Creada automáticamente: diferencia de arqueo sin motivo conocido.",
                }
            ],
            instante_deteccion=ahora,
        )
        sesion.add(anomalia)
        sesion.flush()

    return arqueo, True


def ajustar_arqueo(
    sesion: Session,
    *,
    id_arqueo: int,
    monto_contado_nuevo,
    id_operador: int,
    nota: str,
) -> Arqueo:
    arqueo = sesion.get(Arqueo, id_arqueo)
    if arqueo is None:
        raise ErrorCaja(
            "caja_arqueo_no_existe", "Ese arqueo no existe.", status_code=404
        )
    monto_nuevo = _monto_a_decimal(monto_contado_nuevo)
    ahora = datetime.now(timezone.utc)
    # Nunca se reescribe `monto_esperado` (research.md #13): la corrección queda en el historial de
    # ajustes y sólo recalcula la diferencia.
    entrada = {
        "instante": ahora.isoformat(),
        "id_operador": id_operador,
        "monto_contado_anterior": str(arqueo.monto_contado),
        "monto_contado_nuevo": str(monto_nuevo),
        "nota": nota,
    }
    arqueo.ajustes = list(arqueo.ajustes) + [entrada]
    arqueo.monto_contado = monto_nuevo
    arqueo.diferencia = diferencia_con_signo(monto_nuevo, arqueo.monto_esperado)
    sesion.flush()
    return arqueo


def listar_arqueos(
    sesion: Session,
    *,
    id_sucursal: int | None = None,
    id_turno: int | None = None,
    desde=None,
    hasta=None,
    solo_descuadrados: bool = False,
) -> list[Arqueo]:
    if id_sucursal is None and id_turno is None:
        raise ErrorCaja(
            "caja_sucursal_requerida",
            "Indica una sucursal para consultar sus arqueos (no se mezclan sucursales).",
        )
    consulta = select(Arqueo)
    if id_turno is not None:
        consulta = consulta.where(Arqueo.id_turno == id_turno)
    if id_sucursal is not None:
        consulta = consulta.where(Arqueo.id_sucursal == id_sucursal)
    if desde is not None:
        consulta = consulta.where(Arqueo.dia_local >= desde)
    if hasta is not None:
        consulta = consulta.where(Arqueo.dia_local <= hasta)
    if solo_descuadrados:
        consulta = consulta.where(Arqueo.diferencia != Decimal("0.00"))
    consulta = consulta.order_by(Arqueo.dia_local.desc(), Arqueo.id_arqueo.desc())
    return list(sesion.execute(consulta).scalars())


def obtener_arqueo(sesion: Session, *, id_arqueo: int) -> Arqueo:
    arqueo = sesion.get(Arqueo, id_arqueo)
    if arqueo is None:
        raise ErrorCaja(
            "caja_arqueo_no_existe", "Ese arqueo no existe.", status_code=404
        )
    return arqueo


def arqueo_a_respuesta(sesion: Session, arqueo: Arqueo) -> dict:
    anomalia = sesion.execute(
        select(AnomaliaCaja.id_anomalia_caja).where(AnomaliaCaja.id_arqueo == arqueo.id_arqueo)
    ).scalar_one_or_none()
    return {
        "id_arqueo": arqueo.id_arqueo,
        "id_turno": arqueo.id_turno,
        "id_operador": arqueo.id_operador,
        "id_sucursal": arqueo.id_sucursal,
        "dia_local": arqueo.dia_local.isoformat(),
        "monto_esperado": str(arqueo.monto_esperado),
        "monto_contado": str(arqueo.monto_contado),
        "diferencia": str(arqueo.diferencia),
        "motivo_conocido": arqueo.motivo_conocido,
        "genero_anomalia": anomalia is not None,
        "id_anomalia_caja": anomalia,
        "ajustes": arqueo.ajustes,
        "instante_cierre_arqueo": arqueo.instante_cierre_arqueo.isoformat(),
    }
