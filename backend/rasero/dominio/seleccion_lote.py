"""Selección de lote para consumo: caducidad primero, entrada como desempate (FR-048,
data-model.md — "criterio efectivo es por tanto caducidad primero y entrada como desempate,
no FIFO puro").

Función pura: opera sobre cualquier objeto con `.fecha_caducidad`, `.instante_entrada` e
`.id_lote`, sin tocar la base de datos, para que sea comprobable sin PostgreSQL.
"""

from datetime import date, datetime
from typing import Protocol, TypeVar


class TieneCriteriosFefo(Protocol):
    fecha_caducidad: date | None
    instante_entrada: datetime
    id_lote: int


T = TypeVar("T", bound=TieneCriteriosFefo)


def ordenar_fefo(lotes: list[T]) -> list[T]:
    """Ordena por fecha_caducidad ascendente (nulos al final), luego instante_entrada, luego
    id_lote. Un lote sin caducidad nunca se adelanta a uno que sí caduca.
    """
    return sorted(
        lotes,
        key=lambda lote: (
            lote.fecha_caducidad is None,
            lote.fecha_caducidad or date.max,
            lote.instante_entrada,
            lote.id_lote,
        ),
    )
