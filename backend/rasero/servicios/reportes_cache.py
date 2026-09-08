"""Caché de agregados de 008-reportes-inteligencia (FR-026, FR-027).

`agregado_reporte` es una tabla DERIVADA de 008: su `contenido` es exactamente lo que producen
los servicios de reporte sobre 001–006. Se puebla a demanda y el encargado la invalida con
"Actualizar" (`DELETE` + recálculo). No hay TTL ni trabajo programado (FR-028).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import AgregadoReporte


def _filtro(tipo: str, ambito_sucursal: int | None, ini: date, fin: date, gran: str):
    cond = [
        AgregadoReporte.tipo == tipo,
        AgregadoReporte.periodo_inicio == ini,
        AgregadoReporte.periodo_fin == fin,
        AgregadoReporte.granularidad == gran,
    ]
    if ambito_sucursal is None:
        cond.append(AgregadoReporte.ambito_sucursal.is_(None))
    else:
        cond.append(AgregadoReporte.ambito_sucursal == ambito_sucursal)
    return cond


def leer(
    sesion: Session,
    *,
    tipo: str,
    ambito_sucursal: int | None,
    periodo_inicio: date,
    periodo_fin: date,
    granularidad: str,
) -> dict | None:
    """`{contenido, instante_calculo}` de la caché, o `None` si no está."""
    fila = sesion.execute(
        select(AgregadoReporte).where(
            *_filtro(tipo, ambito_sucursal, periodo_inicio, periodo_fin, granularidad)
        )
    ).scalar_one_or_none()
    if fila is None:
        return None
    return {"contenido": fila.contenido, "instante_calculo": fila.instante_calculo}


def guardar(
    sesion: Session,
    *,
    tipo: str,
    ambito_sucursal: int | None,
    periodo_inicio: date,
    periodo_fin: date,
    granularidad: str,
    contenido: dict,
) -> datetime:
    """Reemplaza la entrada de caché de esa clave. Devuelve el `instante_calculo` grabado."""
    sesion.execute(
        delete(AgregadoReporte).where(
            *_filtro(tipo, ambito_sucursal, periodo_inicio, periodo_fin, granularidad)
        )
    )
    ahora = datetime.now(timezone.utc)
    sesion.add(
        AgregadoReporte(
            tipo=tipo,
            ambito_sucursal=ambito_sucursal,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            granularidad=granularidad,
            contenido=contenido,
            instante_calculo=ahora,
        )
    )
    sesion.flush()
    return ahora
