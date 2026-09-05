"""Endpoints de venta: POST /ventas, GET /ventas/{id_venta}, POST /ventas/{id_venta}/anulacion
(T030, T031, T032).
"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.errores import RecursoNoEncontrado
from rasero.persistencia.modelos import AnulacionVenta, RenglonVenta, Turno, Venta
from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import ventas as servicio_ventas

router = APIRouter(tags=["ventas"])


class RenglonVentaNuevo(BaseModel):
    id_producto: int
    cantidad_unidades: int | None = None
    cantidad_gramos: int | None = None


class VentaNueva(BaseModel):
    clave_idempotencia: str = Field(min_length=8)
    id_turno: int
    referencia_terminal_pago: str | None = None
    instante_origen: datetime | None = None
    renglones: list[RenglonVentaNuevo] = Field(min_length=1)


class AnulacionNueva(BaseModel):
    id_operador: int
    motivo: str | None = None


def _importe(valor: Decimal) -> str:
    return f"{valor:.2f}"


def _precio_unitario(valor: Decimal) -> str:
    return f"{valor:.4f}"


def _venta_a_respuesta(
    sesion: Session,
    venta: Venta,
    advertencias: list[dict],
    lotes_consumidos_por_renglon: dict[int, list[dict]],
) -> dict:
    turno = sesion.get(Turno, venta.id_turno)
    anulada = (
        sesion.execute(
            select(AnulacionVenta.id_anulacion_venta).where(AnulacionVenta.id_venta == venta.id_venta)
        ).scalar_one_or_none()
        is not None
    )
    renglones = sesion.execute(
        select(RenglonVenta).where(RenglonVenta.id_venta == venta.id_venta).order_by(RenglonVenta.id_renglon_venta)
    ).scalars().all()

    return {
        "id_venta": venta.id_venta,
        "clave_idempotencia": venta.clave_idempotencia,
        "id_turno": venta.id_turno,
        "id_operador": turno.id_operador,
        "id_sucursal": turno.id_sucursal,
        "referencia_terminal_pago": venta.referencia_terminal_pago,
        "instante": venta.instante,
        "total": _importe(venta.total),
        "moneda": venta.moneda,
        "anulada": anulada,
        "renglones": [
            {
                "id_renglon_venta": r.id_renglon_venta,
                "id_producto": r.id_producto,
                "cantidad_unidades": r.cantidad_unidades,
                "cantidad_gramos": r.cantidad_gramos,
                "precio_aplicado": _precio_unitario(r.precio_aplicado),
                "importe": _importe(r.importe),
                "moneda": r.moneda,
                "lotes_consumidos": [
                    {"id_lote": l["id_lote"], "cantidad": int(l["cantidad"])}
                    for l in lotes_consumidos_por_renglon.get(r.id_renglon_venta, [])
                ],
            }
            for r in renglones
        ],
        "advertencias": advertencias,
    }


@router.post("/ventas")
def registrar_venta(cuerpo: VentaNueva, response: Response, sesion: Session = Depends(obtener_sesion)) -> dict:
    entradas = [
        servicio_ventas.RenglonEntrada(
            id_producto=r.id_producto,
            cantidad_unidades=r.cantidad_unidades,
            cantidad_gramos=r.cantidad_gramos,
        )
        for r in cuerpo.renglones
    ]
    venta, creada_ahora, advertencias, lotes_por_renglon = servicio_ventas.registrar_venta(
        sesion,
        clave_idempotencia=cuerpo.clave_idempotencia,
        id_turno=cuerpo.id_turno,
        referencia_terminal_pago=cuerpo.referencia_terminal_pago,
        instante_origen=cuerpo.instante_origen,
        renglones=entradas,
    )
    response.status_code = status.HTTP_201_CREATED if creada_ahora else status.HTTP_200_OK
    return _venta_a_respuesta(sesion, venta, advertencias, lotes_por_renglon)


@router.get("/ventas/{id_venta}")
def obtener_venta(id_venta: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")
    return _venta_a_respuesta(sesion, venta, [], {})


@router.post("/ventas/{id_venta}/anulacion", status_code=status.HTTP_201_CREATED)
def anular_venta(id_venta: int, cuerpo: AnulacionNueva, sesion: Session = Depends(obtener_sesion)) -> dict:
    anulacion = servicio_ventas.anular_venta(
        sesion, id_venta=id_venta, id_operador_ejecuta=cuerpo.id_operador, motivo=cuerpo.motivo
    )
    return {
        "id_anulacion_venta": anulacion.id_anulacion_venta,
        "id_venta": anulacion.id_venta,
        "id_operador": anulacion.id_operador,
        "instante": anulacion.instante,
        "motivo": anulacion.motivo,
    }
