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
from rasero.servicios import reportes_comparativo

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
