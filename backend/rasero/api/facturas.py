"""Endpoints de facturación electrónica SIMULADA (009-facturacion-electronica).

Rol `cajero` (sesión de turno válida): la factura es parte del flujo de venta que ya opera un
cajero. La generación es INDEPENDIENTE de `POST /ventas` — el frontend la llama después del
cobro, sin bloquear su resultado (Principio II). Toda respuesta que contiene una factura incluye
`aviso_simulacion`.
"""

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.errores import RecursoNoEncontrado
from rasero.persistencia.modelos import Operador
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import operador_de_sesion
from rasero.servicios import facturacion

router = APIRouter(tags=["facturas"], prefix="/facturas")

_Sesion = Depends(operador_de_sesion)


class FacturaNueva(BaseModel):
    id_venta: int


@router.post("")
def generar_factura(
    cuerpo: FacturaNueva,
    response: Response,
    sesion: Session = Depends(obtener_sesion),
    _operador: Operador = _Sesion,
) -> dict:
    factura, creada = facturacion.generar_factura(sesion, id_venta=cuerpo.id_venta)
    response.status_code = status.HTTP_201_CREATED if creada else status.HTTP_200_OK
    return facturacion.factura_a_respuesta(factura)


@router.get("/venta/{id_venta}")
def facturas_de_venta(
    id_venta: int,
    sesion: Session = Depends(obtener_sesion),
    _operador: Operador = _Sesion,
) -> dict:
    r = facturacion.obtener_facturas_de_venta(sesion, id_venta=id_venta)
    return {
        "id_venta": id_venta,
        "factura": facturacion.factura_a_respuesta(r["factura"]) if r["factura"] else None,
        "nota_credito": facturacion.factura_a_respuesta(r["nota_credito"]) if r["nota_credito"] else None,
    }


@router.post("/nota-credito/{id_venta}", response_model=None)
def emitir_nota_credito(
    id_venta: int,
    response: Response,
    sesion: Session = Depends(obtener_sesion),
    _operador: Operador = _Sesion,
) -> dict | Response:
    nota, creada = facturacion.emitir_nota_credito(sesion, id_venta=id_venta)
    if nota is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    response.status_code = status.HTTP_201_CREATED if creada else status.HTTP_200_OK
    return facturacion.factura_a_respuesta(nota)


@router.get("/{id_factura_simulada}/documento")
def documento(
    id_factura_simulada: int,
    sesion: Session = Depends(obtener_sesion),
    _operador: Operador = _Sesion,
) -> dict:
    try:
        f = facturacion.obtener_factura(sesion, id_factura=id_factura_simulada)
    except RecursoNoEncontrado:
        raise
    return facturacion.factura_a_respuesta(f)
