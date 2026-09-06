"""Router de 005-promociones-inteligentes (T004 router base; T014 cupones + redención de US1;
T028 ofertas de recompra de US2; T042 experimentos de US3; T051 marca activa de US4).

Prefijo `/promociones` para todo el módulo. Cada endpoint hace su propio `commit`: los servicios
(`servicios/promociones.py`, `servicios/experimentos.py`) no comitean — dejan la transacción a
cargo de quien los invoque (mismo patrón que `servicios/margenes.py` de 003).

Este contrato NUNCA participa en `POST /ventas` de 001 ni es camino crítico de un cobro
(Principio II): la redención se registra DESPUÉS de la venta, por `POST /promociones/redenciones`
(mismo patrón que `POST /clientes/{id}/visitas` de 002). Error `{codigo, mensaje}` unificado con
001-004.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.api.paginacion import paginar
from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import experimentos as servicio_experimentos
from rasero.servicios import promociones as servicio_promociones

router = APIRouter(tags=["promociones"], prefix="/promociones")


# ==========================================================================
# User Story 1 — cupón por fecha fija + ciclo de redención (T014)
# ==========================================================================


class GeneracionCupones(BaseModel):
    desde: date
    hasta: date
    nombre_campania: str | None = None


class RedencionNueva(BaseModel):
    id_venta: int
    tipo_origen: str
    id_cupon: int | None = None
    id_oferta_recompra: int | None = None
    id_asignacion_experimento: int | None = None
    id_producto: int | None = None


@router.post("/cupones/generacion")
def generar_cupones(cuerpo: GeneracionCupones, sesion: Session = Depends(obtener_sesion)) -> dict:
    resultado = servicio_promociones.generar_cupones(
        sesion,
        desde=cuerpo.desde,
        hasta=cuerpo.hasta,
        nombre_campania=cuerpo.nombre_campania,
    )
    sesion.commit()
    return resultado


@router.get("/cupones")
def listar_cupones(
    id_cliente: int | None = None,
    estado: str | None = None,
    vigentes: bool = False,
    pagina: int | None = None,
    tamano_pagina: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    filas = servicio_promociones.listar_cupones(
        sesion, id_cliente=id_cliente, estado=estado, vigentes=vigentes
    )
    sesion.commit()
    return paginar(filas, pagina=pagina, tamano_pagina=tamano_pagina)


@router.post("/redenciones")
def registrar_redencion(
    cuerpo: RedencionNueva,
    response: Response,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    redencion, creada_ahora = servicio_promociones.registrar_redencion(
        sesion,
        id_venta=cuerpo.id_venta,
        tipo_origen=cuerpo.tipo_origen,
        id_cupon=cuerpo.id_cupon,
        id_oferta_recompra=cuerpo.id_oferta_recompra,
        id_asignacion_experimento=cuerpo.id_asignacion_experimento,
        id_producto=cuerpo.id_producto,
    )
    sesion.commit()
    response.status_code = status.HTTP_201_CREATED if creada_ahora else status.HTTP_200_OK
    return servicio_promociones.redencion_a_respuesta(redencion)


# ==========================================================================
# User Story 2 — empuje por recompra con reserva de precio (T028)
# ==========================================================================


class DeteccionRecompra(BaseModel):
    id_sucursal: int


@router.post("/ofertas-recompra/deteccion")
def detectar_ofertas_recompra(
    cuerpo: DeteccionRecompra, sesion: Session = Depends(obtener_sesion)
) -> dict:
    resultado = servicio_promociones.detectar_ofertas_recompra(
        sesion, id_sucursal=cuerpo.id_sucursal
    )
    sesion.commit()
    return resultado


@router.get("/ofertas-recompra")
def listar_ofertas_recompra(
    id_cliente: int | None = None,
    desenlace: str | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    filas = servicio_promociones.listar_ofertas_recompra(
        sesion, id_cliente=id_cliente, desenlace=desenlace
    )
    sesion.commit()
    return filas


# ==========================================================================
# User Story 3 — reactivación con experimento de control (T042)
# ==========================================================================


class ExperimentoNuevo(BaseModel):
    id_sucursal: int | None = None
    semilla: int | None = None
    ventana_medicion_dias: int | None = None
    porcentaje_descuento: str | float | int | None = None
    mde_puntos_porcentuales: str | float | int | None = None
    nombre_campania: str | None = None


@router.post("/experimentos", status_code=status.HTTP_201_CREATED)
def crear_experimento(cuerpo: ExperimentoNuevo, sesion: Session = Depends(obtener_sesion)) -> dict:
    experimento = servicio_experimentos.crear_experimento(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        semilla=cuerpo.semilla,
        ventana_medicion_dias=cuerpo.ventana_medicion_dias,
        porcentaje_descuento=cuerpo.porcentaje_descuento,
        mde_puntos_porcentuales=cuerpo.mde_puntos_porcentuales,
        nombre_campania=cuerpo.nombre_campania,
    )
    sesion.commit()
    return servicio_experimentos.experimento_a_respuesta(experimento)


@router.get("/experimentos/{id_experimento_reactivacion}")
def obtener_experimento(
    id_experimento_reactivacion: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    experimento = servicio_experimentos.obtener_experimento(
        sesion, id_experimento_reactivacion=id_experimento_reactivacion
    )
    return servicio_experimentos.experimento_a_respuesta(experimento)


@router.get("/experimentos/{id_experimento_reactivacion}/asignaciones")
def listar_asignaciones(
    id_experimento_reactivacion: int,
    grupo: str | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_experimentos.listar_asignaciones(
        sesion, id_experimento_reactivacion=id_experimento_reactivacion, grupo=grupo
    )


@router.post("/experimentos/{id_experimento_reactivacion}/cierre")
def cerrar_experimento(
    id_experimento_reactivacion: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    experimento = servicio_experimentos.cerrar_experimento(
        sesion, id_experimento_reactivacion=id_experimento_reactivacion
    )
    sesion.commit()
    return servicio_experimentos.experimento_a_respuesta(experimento)


# ==========================================================================
# User Story 4 — marca agregada de "promoción activa" para 004 (T051)
# ==========================================================================


@router.get("/marca-activa")
def marca_promocion_activa(
    id_sucursal: int,
    desde: date = Query(...),
    hasta: date = Query(...),
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_promociones.consultar_marca_activa(
        sesion, id_sucursal=id_sucursal, desde=desde, hasta=hasta
    )
