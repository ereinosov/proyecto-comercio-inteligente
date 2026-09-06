"""Tarea invocable a mano: purga de tokens huérfanos (007, US4 — T042).

Un `token_pago` vive mientras su `venta` de 001 sea consultable. Como el PAN NUNCA se almacena, no
hay dato sensible que caduque con urgencia (research.md #4). Esta tarea elimina las filas cuyo
`id_venta` ya no resuelve en 001 (venta archivada o borrada) y deja rastro `token_purgado` en la
bitácora (conserva sólo `id_venta`, `ultimos_digitos`, `marca` — nada sensible).

007 NO dispara ningún archivado en 001 (Principio V: consultiva). Mismo patrón que `tareas/` de
002/005/006.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import TokenPago, Venta
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios import bitacora_pagos


def purgar_tokens_huerfanos(sesion: Session | None = None) -> int:
    """Devuelve cuántos tokens se purgaron."""
    propia = sesion is None
    sesion = sesion or SesionLocal()
    try:
        ids_venta_validas = set(sesion.execute(select(Venta.id_venta)).scalars())
        huerfanos = [
            t
            for t in sesion.execute(select(TokenPago)).scalars()
            if t.id_venta not in ids_venta_validas
        ]
        for token in huerfanos:
            bitacora_pagos.anexar_entrada(
                sesion,
                tipo_evento="token_purgado",
                id_sucursal=token.id_sucursal,
                iniciador_tipo="proceso",
                proceso="purgar_tokens_huerfanos",
                id_terminal_pago=token.id_terminal_pago,
                referencia_recurso_tipo="token_pago",
                referencia_recurso_id=token.token,
                plantilla_valores={"id_venta": token.id_venta},
            )
            sesion.delete(token)
        sesion.flush()
        if propia:
            sesion.commit()
        return len(huerfanos)
    finally:
        if propia:
            sesion.close()


if __name__ == "__main__":  # pragma: no cover
    print(f"{purgar_tokens_huerfanos()} token(s) purgado(s).")
