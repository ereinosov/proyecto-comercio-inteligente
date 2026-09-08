"""Router de 008-reportes-inteligencia. Capa de SOLO LECTURA sobre 001–007.

Toda la superficie exige rol `encargado` (constitución v2.5.0/v2.6.0), a nivel de router — mismo
mecanismo central (`exige_rol`) que precios/competencia/pronóstico/traspasos. Ningún endpoint
modifica datos de 001–007; los que escriben lo hacen sobre las tres tablas DERIVADAS de 008
(`agregado_reporte`, `segmento_cliente`, `asignacion_segmento`).
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import (
    reportes_comparativo,
    reportes_tablero,
    reportes_tendencia,
    segmentacion_clientes,
)

router = APIRouter(
    tags=["reportes"],
    prefix="/reportes",
    dependencies=[Depends(exige_rol("encargado"))],
)


def _mes_en_curso() -> tuple[date, date]:
    hoy = date.today()
    return hoy.replace(day=1), hoy


@router.get("/comparativo")
def comparativo(
    periodo_inicio: date | None = None,
    periodo_fin: date | None = None,
    actualizar: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    ini, fin = _mes_en_curso()
    return reportes_comparativo.comparativo(
        sesion,
        periodo_inicio=periodo_inicio or ini,
        periodo_fin=periodo_fin or fin,
        actualizar=actualizar,
    )


@router.get("/tendencia")
def tendencia(
    indicador: str,
    granularidad: str,
    id_sucursal: int | None = None,
    id_producto: int | None = None,
    periodos: int | None = None,
    actualizar: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    return reportes_tendencia.tendencia(
        sesion,
        indicador=indicador,
        granularidad=granularidad,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        periodos=periodos,
        actualizar=actualizar,
    )


@router.get("/tablero")
def tablero(
    actualizar: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    return reportes_tablero.tablero(sesion, actualizar=actualizar)


@router.get("/segmentos")
def segmentos(sesion: Session = Depends(obtener_sesion)) -> dict:
    """Última corrida de clustering. NO recalcula."""
    return segmentacion_clientes.leer(sesion)


@router.post("/segmentos/recalculo")
def recalcular_segmentos(sesion: Session = Depends(obtener_sesion)) -> dict:
    """Recalcula por lote (k-means, semilla fija). Escribe sólo en entidades derivadas de 008."""
    return segmentacion_clientes.recalcular(sesion)


@router.get("/segmentos/cliente/{id_cliente}")
def segmento_de_cliente(id_cliente: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    """Etiqueta de segmento de un cliente, para el detalle de Clientes (002) — 002 no gana
    ningún campo por esto (constitución v2.6.0).
    """
    return segmentacion_clientes.etiqueta_de_cliente(sesion, id_cliente=id_cliente)
