"""Conteo físico de inventario (001-core-ventas-inventario, US5 — T066, T067).

FR-029: se inicia un conteo programado, acotado a una sucursal y opcionalmente a un subconjunto
de productos. FR-030: al resolver, se compara lo contado contra el saldo calculado a partir de
los movimientos y se expone la diferencia **por producto y por lote**, sin clasificar su causa
(FR-031 — clasificar es de `006-caja-mermas-fraude`). FR-032: cada diferencia distinta de cero
genera un movimiento `ajuste_conteo` trazable al conteo, y el saldo anterior sigue siendo
reconstruible (el ajuste es un movimiento más, no una reescritura del saldo).

El servicio comitea: `existencia` se mueve por delta en la misma transacción del movimiento
(`persistencia/movimientos.py`).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.errores import ConteoInvalido, RecursoNoEncontrado
from rasero.persistencia.modelos import (
    ConteoFisico,
    ConteoRenglon,
    Existencia,
    Producto,
    Sucursal,
)
from rasero.persistencia.movimientos import registrar_movimiento


@dataclass
class RenglonContado:
    id_producto: int
    cantidad_contada: int
    id_lote: int | None = None


def iniciar_conteo(
    sesion: Session, *, id_sucursal: int, id_productos: list[int] | None = None
) -> ConteoFisico:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    alcance = {"id_productos": sorted(set(id_productos))} if id_productos else None
    conteo = ConteoFisico(
        id_sucursal=id_sucursal,
        estado="abierto",
        alcance=alcance,
        instante_inicio=datetime.now(timezone.utc),
    )
    sesion.add(conteo)
    sesion.commit()
    return conteo


def _saldo_calculado(
    sesion: Session, *, id_sucursal: int, id_producto: int, id_lote: int | None
) -> Decimal:
    """Saldo derivado de `existencia` para un (sucursal, producto) y —si se indica— un lote.
    Sin `id_lote`, agrega todos los lotes del producto en la sucursal (el conteo de esa línea
    es a nivel de producto).
    """
    condiciones = [
        Existencia.id_sucursal == id_sucursal,
        Existencia.id_producto == id_producto,
    ]
    if id_lote is not None:
        condiciones.append(Existencia.id_lote == id_lote)
    total = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(*condiciones)
    ).scalar_one()
    return Decimal(total)


def resolver_conteo(
    sesion: Session, *, id_conteo_fisico: int, renglones: list[RenglonContado]
) -> tuple[ConteoFisico, list[ConteoRenglon]]:
    conteo = sesion.get(ConteoFisico, id_conteo_fisico)
    if conteo is None:
        raise RecursoNoEncontrado(f"El conteo {id_conteo_fisico} no existe.")
    if conteo.estado == "resuelto":
        raise ConteoInvalido("Ese conteo ya fue resuelto; no se puede volver a resolver.")
    if not renglones:
        raise ConteoInvalido("El conteo debe resolverse con al menos un renglón contado.")

    instante = datetime.now(timezone.utc)
    guardados: list[ConteoRenglon] = []

    for entrada in renglones:
        producto = sesion.get(Producto, entrada.id_producto)
        if producto is None:
            raise RecursoNoEncontrado(f"El producto {entrada.id_producto} no existe.")

        cantidad_contada = Decimal(entrada.cantidad_contada)
        cantidad_esperada = _saldo_calculado(
            sesion,
            id_sucursal=conteo.id_sucursal,
            id_producto=entrada.id_producto,
            id_lote=entrada.id_lote,
        )
        diferencia = cantidad_contada - cantidad_esperada

        renglon = ConteoRenglon(
            id_conteo_fisico=conteo.id_conteo_fisico,
            id_producto=entrada.id_producto,
            id_lote=entrada.id_lote,
            cantidad_contada=cantidad_contada,
            cantidad_esperada=cantidad_esperada,
            diferencia=diferencia,
        )
        sesion.add(renglon)
        sesion.flush()
        guardados.append(renglon)

        if diferencia != 0:
            # FR-032: el ajuste es un movimiento trazable al conteo. Deja `existencia` en lo
            # contado sumando el delta; el saldo anterior sigue siendo reconstruible sin este
            # movimiento.
            registrar_movimiento(
                sesion,
                id_sucursal=conteo.id_sucursal,
                id_producto=entrada.id_producto,
                id_lote=entrada.id_lote,
                tipo="ajuste_conteo",
                cantidad=diferencia,
                instante=instante,
                id_conteo_fisico=conteo.id_conteo_fisico,
            )

    conteo.estado = "resuelto"
    conteo.instante_resolucion = instante
    sesion.commit()
    return conteo, guardados


def conteo_a_respuesta(conteo: ConteoFisico, renglones: list[ConteoRenglon] | None = None) -> dict:
    cuerpo = {
        "id_conteo_fisico": conteo.id_conteo_fisico,
        "id_sucursal": conteo.id_sucursal,
        "estado": conteo.estado,
        "instante_inicio": conteo.instante_inicio,
        "instante_resolucion": conteo.instante_resolucion,
    }
    if renglones is not None:
        cuerpo["renglones"] = [
            {
                "id_producto": r.id_producto,
                "id_lote": r.id_lote,
                "cantidad_esperada": int(r.cantidad_esperada),
                "cantidad_contada": int(r.cantidad_contada),
                "diferencia": int(r.diferencia),
            }
            for r in renglones
        ]
    return cuerpo
