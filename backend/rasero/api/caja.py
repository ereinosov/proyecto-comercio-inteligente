"""Router de 006-caja-mermas-fraude (T004 router base; T013 arqueos US1; T025 mermas US2;
T037 indicadores + cruce US3; T046 anomalías US4).

Prefijo `/caja` para todo el módulo. Cada endpoint hace su propio `commit`: los servicios
(`servicios/arqueos.py`, `servicios/mermas.py`, `servicios/deteccion_fraude.py`) no comitean.

Este contrato NUNCA participa en `POST /ventas` de 001 ni es camino crítico de un cobro
(Principio II). 006 SÓLO LEE de 001. Error `{codigo, mensaje}` unificado con 001-005.

Las rutas bloqueadas (`POST /caja/cruce-operador`, y la rama de `POST /caja/mermas` con
`id_conteo_renglon`) devuelven `409 caja_bloqueado_por_001` mientras 001 no implemente su User
Story 5 (`conteo_fisico`/`conteo_renglon`, T065-T071) — comportamiento controlado y esperado.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import arqueos as servicio_arqueos
from rasero.servicios import deteccion_fraude as servicio_fraude
from rasero.servicios import mermas as servicio_mermas

router = APIRouter(tags=["caja"], prefix="/caja")


# ==========================================================================
# User Story 1 — arqueo de caja por turno (T013)
# ==========================================================================


class ArqueoNuevo(BaseModel):
    id_turno: int
    monto_contado: str
    motivo_conocido: str | None = None
    marca_tiempo_origen: datetime


class AjusteArqueo(BaseModel):
    monto_contado_nuevo: str
    id_operador: int
    nota: str


@router.post("/arqueos")
def registrar_arqueo(
    cuerpo: ArqueoNuevo, response: Response, sesion: Session = Depends(obtener_sesion)
) -> dict:
    arqueo, creado = servicio_arqueos.registrar_arqueo(
        sesion,
        id_turno=cuerpo.id_turno,
        monto_contado=cuerpo.monto_contado,
        motivo_conocido=cuerpo.motivo_conocido,
        marca_tiempo_origen=cuerpo.marca_tiempo_origen,
    )
    sesion.commit()
    response.status_code = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
    return servicio_arqueos.arqueo_a_respuesta(sesion, arqueo)


@router.get("/arqueos")
def listar_arqueos(
    id_sucursal: int | None = None,
    id_turno: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    solo_descuadrados: bool = False,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    arqueos = servicio_arqueos.listar_arqueos(
        sesion,
        id_sucursal=id_sucursal,
        id_turno=id_turno,
        desde=desde,
        hasta=hasta,
        solo_descuadrados=solo_descuadrados,
    )
    return [servicio_arqueos.arqueo_a_respuesta(sesion, a) for a in arqueos]


@router.get("/arqueos/{id_arqueo}")
def obtener_arqueo(id_arqueo: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    arqueo = servicio_arqueos.obtener_arqueo(sesion, id_arqueo=id_arqueo)
    return servicio_arqueos.arqueo_a_respuesta(sesion, arqueo)


@router.patch("/arqueos/{id_arqueo}")
def ajustar_arqueo(
    id_arqueo: int, cuerpo: AjusteArqueo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    arqueo = servicio_arqueos.ajustar_arqueo(
        sesion,
        id_arqueo=id_arqueo,
        monto_contado_nuevo=cuerpo.monto_contado_nuevo,
        id_operador=cuerpo.id_operador,
        nota=cuerpo.nota,
    )
    sesion.commit()
    return servicio_arqueos.arqueo_a_respuesta(sesion, arqueo)


# ==========================================================================
# User Story 2 — clasificar mermas + alerta de caducidad (T025)
# ==========================================================================


class MermaNueva(BaseModel):
    id_producto: int
    id_sucursal: int
    cantidad_faltante: int
    causa: str
    id_operador_registro: int
    id_conteo_renglon: int | None = None
    id_lote: int | None = None
    nota: str | None = None


@router.post("/mermas", status_code=status.HTTP_201_CREATED)
def registrar_merma(cuerpo: MermaNueva, sesion: Session = Depends(obtener_sesion)) -> dict:
    merma = servicio_mermas.clasificar_merma(
        sesion,
        id_producto=cuerpo.id_producto,
        id_sucursal=cuerpo.id_sucursal,
        cantidad_faltante=cuerpo.cantidad_faltante,
        causa=cuerpo.causa,
        id_operador_registro=cuerpo.id_operador_registro,
        id_conteo_renglon=cuerpo.id_conteo_renglon,
        id_lote=cuerpo.id_lote,
        nota=cuerpo.nota,
    )
    sesion.commit()
    return servicio_mermas.merma_a_respuesta(merma)


@router.get("/mermas")
def listar_mermas(
    id_sucursal: int | None = None,
    causa: str | None = None,
    id_producto: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    return servicio_mermas.listar_mermas(
        sesion,
        id_sucursal=id_sucursal,
        causa=causa,
        id_producto=id_producto,
        desde=desde,
        hasta=hasta,
    )


@router.get("/alertas-caducidad")
def alertas_caducidad(
    id_sucursal: int | None = None,
    dentro_de_dias: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    return servicio_mermas.alertas_caducidad(
        sesion, id_sucursal=id_sucursal, dentro_de_dias=dentro_de_dias
    )


# ==========================================================================
# User Story 3 — cruce por operador para detectar sub-registro (T037)
# ==========================================================================


class CruceOperador(BaseModel):
    id_sucursal: int
    desde: date
    hasta: date
    id_conteo_fisico: int | None = None


@router.get("/indicadores-operador")
def indicadores_operador(
    id_sucursal: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    return servicio_fraude.indicadores_operador(
        sesion, id_sucursal=id_sucursal, desde=desde, hasta=hasta
    )


@router.post("/cruce-operador")
def cruce_operador(cuerpo: CruceOperador, sesion: Session = Depends(obtener_sesion)) -> dict:
    resultado = servicio_fraude.cruce_inventario_ventas(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        desde=cuerpo.desde,
        hasta=cuerpo.hasta,
        id_conteo_fisico=cuerpo.id_conteo_fisico,
    )
    sesion.commit()
    return resultado


# ==========================================================================
# User Story 4 — gestionar anomalías sin explicación (T046)
# ==========================================================================


class ResolucionAnomalia(BaseModel):
    resolucion: str
    id_operador: int
    nota: str | None = None


@router.get("/anomalias")
def listar_anomalias(
    id_sucursal: int | None = None,
    estado: str | None = None,
    origen: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    anomalias = servicio_fraude.listar_anomalias(
        sesion,
        id_sucursal=id_sucursal,
        estado=estado,
        origen=origen,
        desde=desde,
        hasta=hasta,
    )
    return [servicio_fraude.anomalia_a_respuesta(a) for a in anomalias]


@router.get("/anomalias/{id_anomalia_caja}")
def obtener_anomalia(
    id_anomalia_caja: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    anomalia = servicio_fraude.obtener_anomalia(sesion, id_anomalia_caja=id_anomalia_caja)
    return servicio_fraude.anomalia_a_respuesta(anomalia)


@router.post("/anomalias/{id_anomalia_caja}/resolucion")
def resolver_anomalia(
    id_anomalia_caja: int,
    cuerpo: ResolucionAnomalia,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    anomalia = servicio_fraude.resolver_anomalia(
        sesion,
        id_anomalia_caja=id_anomalia_caja,
        resolucion=cuerpo.resolucion,
        id_operador=cuerpo.id_operador,
        nota=cuerpo.nota,
    )
    sesion.commit()
    return servicio_fraude.anomalia_a_respuesta(anomalia)
