"""Cobros por venta y su medio de pago (007-pagos-seguridad, apoyo a US1/US4).

La "Bitácora de pagos" (`bitacora_auditoria`) es el registro de SEGURIDAD (tokens, PAN
rechazado, firmware). Esto es lo otro que el encargado espera de "Pagos": el libro de ventas
con la forma de pago que el cliente eligió en el POS (`venta.id_medio_pago`, enmienda v2.7.2).

007 SÓLO LEE de 001: consulta `venta`, `turno`, `medio_pago`, `operador`, `anulacion_venta`.
Nunca escribe. Exige `id_sucursal` — nunca mezcla sucursales.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.errores import ErrorPagos
from rasero.persistencia.modelos import (
    AnulacionVenta,
    MedioPago,
    Operador,
    Sucursal,
    Turno,
    Venta,
)


def listar_cobros(
    sesion: Session,
    *,
    id_sucursal: int | None,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    if id_sucursal is None:
        raise ErrorPagos(
            "pagos_sucursal_requerida",
            "Indica una sucursal para consultar sus cobros (no se mezclan sucursales).",
        )
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorPagos("pagos_sucursal_no_existe", "Esa sucursal no existe.", status_code=404)
    zona = ZoneInfo(sucursal.zona_horaria)

    stmt = (
        select(Venta, Turno.id_operador, MedioPago.nombre)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(MedioPago, MedioPago.id_medio_pago == Venta.id_medio_pago)
        .where(Turno.id_sucursal == id_sucursal)
        .order_by(Venta.instante.desc())
    )

    if desde is not None:
        inicio_utc = datetime.combine(desde, time.min, tzinfo=zona).astimezone(timezone.utc)
        stmt = stmt.where(Venta.instante >= inicio_utc)
    if hasta is not None:
        fin_utc = datetime.combine(
            hasta + timedelta(days=1), time.min, tzinfo=zona
        ).astimezone(timezone.utc)
        stmt = stmt.where(Venta.instante < fin_utc)

    anuladas = {
        id_venta
        for (id_venta,) in sesion.execute(select(AnulacionVenta.id_venta)).all()
    }
    nombres_operador = dict(
        sesion.execute(select(Operador.id_operador, Operador.nombre)).all()
    )

    cobros: list[dict] = []
    total_por_medio: dict[str, Decimal] = {}
    for venta, id_operador, medio_nombre in sesion.execute(stmt).all():
        anulada = venta.id_venta in anuladas
        medio = medio_nombre or "sin_declarar"
        if not anulada:
            total_por_medio[medio] = total_por_medio.get(medio, Decimal("0")) + Decimal(
                venta.total
            )
        cobros.append(
            {
                "id_venta": venta.id_venta,
                "instante": venta.instante.astimezone(zona).isoformat(),
                "total": f"{Decimal(venta.total):.2f}",
                "moneda": venta.moneda,
                "medio_pago": medio_nombre,
                "id_operador": id_operador,
                "operador": nombres_operador.get(id_operador, f"Operador {id_operador}"),
                "anulada": anulada,
            }
        )

    return {
        "id_sucursal": id_sucursal,
        "cobros": cobros,
        "total_por_medio": [
            {"medio_pago": medio, "total": f"{monto:.2f}"}
            for medio, monto in sorted(total_por_medio.items())
        ],
    }
