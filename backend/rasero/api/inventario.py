"""Endpoints de inventario:

- `POST /entradas-inventario` (T046, US2) — registrar una compra a proveedor.
- `GET /existencias` (T047, US2) — saldo por producto, expone el negativo tal cual.
- `GET /capital-inmovilizado` (T082, US7) — lotes parados más allá del umbral de su categoría.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import inventario as servicio_inventario

router = APIRouter(tags=["inventario"])


class EntradaInventarioNueva(BaseModel):
    id_sucursal: int
    id_producto: int
    cantidad: int = Field(ge=1)
    costo_unitario: Decimal
    fecha_caducidad: date | None = None


@router.post("/entradas-inventario", status_code=status.HTTP_201_CREATED)
def registrar_entrada(
    cuerpo: EntradaInventarioNueva, sesion: Session = Depends(obtener_sesion)
) -> dict:
    lote = servicio_inventario.registrar_entrada(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        id_producto=cuerpo.id_producto,
        cantidad=cuerpo.cantidad,
        costo_unitario=cuerpo.costo_unitario,
        fecha_caducidad=cuerpo.fecha_caducidad,
    )
    restante = servicio_inventario.cantidad_restante_lote(sesion, lote.id_lote)
    return {
        "id_lote": lote.id_lote,
        "id_producto": lote.id_producto,
        "id_sucursal": lote.id_sucursal,
        "cantidad_restante": int(restante),
        "costo_unitario": f"{Decimal(lote.costo_unitario):.4f}",
        "moneda": lote.moneda,
        "fecha_caducidad": lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
        "instante_entrada": lote.instante_entrada,
    }


@router.get("/existencias")
def listar_existencias(
    id_sucursal: int,
    id_producto: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_inventario.listar_existencias(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto
    )


@router.get("/existencias/lotes")
def existencias_por_lote(
    id_sucursal: int,
    id_producto: int,
    incluir_costo: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    """Desglose por lote del saldo de un producto en una sucursal, en orden FEFO (US14).
    `incluir_costo` sólo lo usan las superficies con derecho a ver margen (traspasos de un
    encargado), nunca la pantalla de Venta.
    """
    return servicio_inventario.existencia_por_lote(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        incluir_costo=incluir_costo,
    )


@router.get("/capital-inmovilizado")
def capital_inmovilizado(
    id_sucursal: int | None = None, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    return servicio_inventario.capital_inmovilizado(sesion, id_sucursal=id_sucursal)
