"""Router de 004-pronostico-demanda: serie de demanda (User Story 1), validación sintética (User
Story 2), pronóstico (User Story 3) y relaciones de sustitución (User Story 6). Los ejes de precio
(User Story 4) y promoción (User Story 5) viajan en las anotaciones de `GET /demanda`.

Cada endpoint hace su propio `commit`: los servicios no comitean — dejan la transacción a cargo de
quien los invoque (mismo patrón que `servicios/margenes.py` de 003).
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import demanda as servicio_demanda
from rasero.servicios import demanda_sintetica as servicio_sintetica
from rasero.servicios import pronostico as servicio_pronostico
from rasero.servicios import sustitucion as servicio_sustitucion

router = APIRouter(tags=["pronostico"])


@router.get("/demanda")
def obtener_serie_demanda(
    id_sucursal: int,
    id_producto: int | None = None,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    """Serie de demanda observada y corregida por período (día local de la sucursal). Sin
    `id_producto`, la sucursal completa. La ventana se materializa al leer (recompute-on-read).
    Nunca incluye filas sintéticas: se reconstruye desde `movimiento_inventario` (FR-017).
    """
    filas = servicio_demanda.reconstruir_serie(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        desde=desde,
        hasta=hasta,
    )
    sesion.commit()
    return filas


# --------------------------------------------------------------------------
# User Story 2 — validación de la descensura con datos sintéticos (T027)
# --------------------------------------------------------------------------


class PeriodoSintetico(BaseModel):
    periodo: str
    demanda_observada: str | float | int
    dias_en_quiebre: str | float | int
    demanda_latente_verdadera: str | float | int | None = None


class ConsultaSintetica(BaseModel):
    periodo: str
    conteo: int


class CargaSintetica(BaseModel):
    id_producto: int
    id_sucursal: int
    periodos: list[PeriodoSintetico]
    consultas_no_atendidas_sinteticas: list[ConsultaSintetica] = []


@router.post("/demanda-sintetica", status_code=201)
def cargar_demanda_sintetica(
    cuerpo: CargaSintetica, sesion: Session = Depends(obtener_sesion)
) -> dict:
    """FR-013, FR-016. Carga una serie histórica sintética con demanda latente conocida. Estos
    datos nunca se mezclan con datos reales en una consulta de producción (FR-017).
    """
    resultado = servicio_sintetica.cargar_serie(sesion, cuerpo.model_dump())
    sesion.commit()
    return resultado


@router.get("/demanda-sintetica/validacion")
def validacion_descensura(
    id_sucursal: int, id_producto: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    """FR-014, FR-015, SC-002. Reporte de error: qué tan cerca queda la demanda corregida de la
    demanda latente verdadera, frente a no corregir nada. Es la prueba de fondo de que el método
    base de FR-009 funciona.
    """
    return servicio_sintetica.reporte_error_descensura(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal
    )


# --------------------------------------------------------------------------
# User Story 3 — pronóstico (T038)
# --------------------------------------------------------------------------


@router.get("/productos/{id_producto}/pronostico")
def obtener_pronostico(
    id_producto: int,
    id_sucursal: int,
    horizonte: str = Query(default="corto"),
    solo_ultimo: bool = Query(default=False),
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    """FR-018 a FR-024. Genera (o devuelve el último, con `solo_ultimo=true`) un pronóstico
    derivado de la serie corregida, con sus factores, su período de datos y el valor de la línea
    base determinista. `vigente=false` si no supera la línea base (SC-004) o si el histórico es
    insuficiente (FR-023).
    """
    if solo_ultimo:
        fila = servicio_pronostico.ultimo_pronostico(
            sesion, id_producto=id_producto, id_sucursal=id_sucursal, horizonte=horizonte
        )
        if fila is None:
            from rasero.errores import RecursoNoEncontrado

            raise RecursoNoEncontrado("Todavía no se ha generado ningún pronóstico para eso.")
        return servicio_pronostico.a_respuesta(fila)

    fila = servicio_pronostico.generar_pronostico(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, horizonte=horizonte
    )
    sesion.commit()
    return servicio_pronostico.a_respuesta(fila)


# --------------------------------------------------------------------------
# User Story 6 — relaciones de sustitución (T063)
# --------------------------------------------------------------------------


class SustitucionNueva(BaseModel):
    id_producto: int
    id_producto_sustituto: int


@router.get("/sustituciones")
def listar_sustituciones(
    id_producto: int | None = None, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    return [
        servicio_sustitucion.a_respuesta(f)
        for f in servicio_sustitucion.listar(sesion, id_producto=id_producto)
    ]


@router.post("/sustituciones", status_code=201)
def declarar_sustitucion(
    cuerpo: SustitucionNueva, sesion: Session = Depends(obtener_sesion)
) -> dict:
    """FR-032. Declaración manual y dirigida de que un producto puede sustituir a otro."""
    fila = servicio_sustitucion.declarar(
        sesion,
        id_producto=cuerpo.id_producto,
        id_producto_sustituto=cuerpo.id_producto_sustituto,
    )
    sesion.commit()
    return servicio_sustitucion.a_respuesta(fila)


@router.delete("/sustituciones/{id_sustitucion_producto}", status_code=204)
def retirar_sustitucion(
    id_sustitucion_producto: int, sesion: Session = Depends(obtener_sesion)
) -> None:
    servicio_sustitucion.retirar(sesion, id_sustitucion_producto=id_sustitucion_producto)
    sesion.commit()
