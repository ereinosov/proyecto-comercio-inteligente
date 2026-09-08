"""Traspasos entre sucursales (001-core-ventas-inventario, US6 — T074, T075).

Un traspaso es **una operación con dos asientos enlazados por `id_traspaso`** (FR-017): al
despachar se crean movimientos `salida_traspaso` en la sucursal de origen; al confirmar la
recepción, movimientos `entrada_traspaso` en la de destino. `traspaso` no tiene tabla de
renglones: sus líneas son esos propios movimientos (data-model.md).

Mientras `traspaso.estado = 'en_transito'` la mercancía pertenece a la operación: no cuenta como
disponible en ninguna sucursal, pero **sigue contando en el inventario total del sistema**
(FR-018), porque la invariante suma el valor absoluto de los `salida_traspaso` de traspasos en
tránsito. La discrepancia entre lo despachado y lo confirmado se **expone**, sin clasificar ni
absorber (FR-019).

Existencia insuficiente en origen: **bloqueo duro** (spec 001, Corrección 2026-09-07), mismo
criterio que la venta. Se validan TODOS los renglones contra la existencia disponible en origen
ANTES de escribir ningún movimiento; si cualquiera no alcanza, se rechaza el traspaso COMPLETO
con `ExistenciaInsuficiente` (409). Antes el excedente se imputaba a saldo negativo.

El servicio comitea; `existencia` se mueve por delta en la misma transacción de cada movimiento.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.dominio.seleccion_lote import ordenar_fefo
from rasero.errores import (
    ExistenciaInsuficiente,
    RecursoNoEncontrado,
    RenglonInvalido,
    TraspasoInvalido,
)
from rasero.persistencia.modelos import Lote, MovimientoInventario, Producto, Sucursal, Traspaso
from rasero.persistencia.movimientos import (
    obtener_existencia,
    obtener_existencia_total,
    registrar_movimiento,
)


@dataclass
class RenglonDespacho:
    id_producto: int
    cantidad: int


@dataclass
class RenglonRecepcion:
    id_producto: int
    cantidad_recibida: int


def _lote_destino(
    sesion: Session, *, id_producto: int, id_sucursal: int, costo: Decimal, caducidad, moneda: str
) -> Lote:
    lote = sesion.execute(
        select(Lote)
        .where(
            Lote.id_producto == id_producto,
            Lote.id_sucursal == id_sucursal,
            Lote.costo_unitario == costo,
            Lote.fecha_caducidad.is_(None) if caducidad is None else Lote.fecha_caducidad == caducidad,
        )
        .order_by(Lote.instante_entrada)
        .limit(1)
    ).scalar_one_or_none()
    if lote is None:
        lote = Lote(
            id_producto=id_producto,
            id_sucursal=id_sucursal,
            costo_unitario=costo,
            fecha_caducidad=caducidad,
            instante_entrada=datetime.now(timezone.utc),
            moneda=moneda,
        )
        sesion.add(lote)
        sesion.flush()
    return lote


def despachar_traspaso(
    sesion: Session,
    *,
    id_sucursal_origen: int,
    id_sucursal_destino: int,
    renglones: list[RenglonDespacho],
) -> Traspaso:
    if id_sucursal_origen == id_sucursal_destino:
        raise RenglonInvalido("El origen y el destino de un traspaso deben ser distintos.")
    if not renglones:
        raise RenglonInvalido("El traspaso debe llevar al menos un renglón.")
    for nombre, id_s in (("origen", id_sucursal_origen), ("destino", id_sucursal_destino)):
        if sesion.get(Sucursal, id_s) is None:
            raise RecursoNoEncontrado(f"La sucursal de {nombre} ({id_s}) no existe.")

    # Bloqueo duro por existencia insuficiente (Corrección 2026-09-07): se valida el traspaso
    # COMPLETO contra la existencia disponible en origen ANTES de escribir ningún movimiento.
    requerido_por_producto: dict[int, Decimal] = {}
    for renglon in renglones:
        if renglon.cantidad <= 0:
            raise RenglonInvalido("La cantidad de un renglón de traspaso debe ser positiva.")
        requerido_por_producto[renglon.id_producto] = (
            requerido_por_producto.get(renglon.id_producto, Decimal(0)) + Decimal(renglon.cantidad)
        )
    for id_producto, requerido in requerido_por_producto.items():
        disponible = obtener_existencia_total(
            sesion, id_sucursal=id_sucursal_origen, id_producto=id_producto
        )
        if disponible < requerido:
            producto = sesion.get(Producto, id_producto)
            nombre = producto.nombre if producto is not None else f"producto {id_producto}"
            raise ExistenciaInsuficiente(nombre, disponible, requerido)

    instante = datetime.now(timezone.utc)
    traspaso = Traspaso(
        id_sucursal_origen=id_sucursal_origen,
        id_sucursal_destino=id_sucursal_destino,
        estado="en_transito",
        instante_despacho=instante,
    )
    sesion.add(traspaso)
    sesion.flush()

    for renglon in renglones:
        lotes = ordenar_fefo(
            sesion.execute(
                select(Lote)
                .where(
                    Lote.id_producto == renglon.id_producto,
                    Lote.id_sucursal == id_sucursal_origen,
                )
                .with_for_update()
            ).scalars().all()
        )
        restante = Decimal(renglon.cantidad)
        for lote in lotes:
            if restante <= 0:
                break
            disponible = obtener_existencia(
                sesion,
                id_sucursal=id_sucursal_origen,
                id_producto=renglon.id_producto,
                id_lote=lote.id_lote,
            )
            tomar = min(restante, disponible) if disponible > 0 else Decimal(0)
            if tomar > 0:
                registrar_movimiento(
                    sesion,
                    id_sucursal=id_sucursal_origen,
                    id_producto=renglon.id_producto,
                    id_lote=lote.id_lote,
                    tipo="salida_traspaso",
                    cantidad=-tomar,
                    instante=instante,
                    id_traspaso=traspaso.id_traspaso,
                )
                restante -= tomar
        if restante > 0:
            # Inalcanzable en el flujo normal: ya se validó la existencia total de cada producto
            # en origen antes de crear el traspaso. Defensa por si el saldo disponible está en una
            # fila sin lote que FEFO no puede consumir — bloqueo duro, nunca un saldo negativo.
            disponible = obtener_existencia_total(
                sesion, id_sucursal=id_sucursal_origen, id_producto=renglon.id_producto
            )
            producto = sesion.get(Producto, renglon.id_producto)
            nombre = producto.nombre if producto is not None else f"producto {renglon.id_producto}"
            raise ExistenciaInsuficiente(nombre, disponible, Decimal(renglon.cantidad))

    sesion.commit()
    return traspaso


def recibir_traspaso(
    sesion: Session, *, id_traspaso: int, renglones: list[RenglonRecepcion]
) -> Traspaso:
    traspaso = sesion.get(Traspaso, id_traspaso)
    if traspaso is None:
        raise RecursoNoEncontrado(f"El traspaso {id_traspaso} no existe.")
    if traspaso.estado != "en_transito":
        raise TraspasoInvalido("Ese traspaso ya fue recibido; no se puede confirmar dos veces.")

    recibido_por_producto = {r.id_producto: max(0, r.cantidad_recibida) for r in renglones}

    salidas = sesion.execute(
        select(MovimientoInventario)
        .where(
            MovimientoInventario.id_traspaso == id_traspaso,
            MovimientoInventario.tipo == "salida_traspaso",
        )
        .order_by(MovimientoInventario.id_movimiento_inventario)
    ).scalars().all()

    despachado_por_producto: dict[int, Decimal] = {}
    salidas_por_producto: dict[int, list[MovimientoInventario]] = {}
    for mov in salidas:
        despachado_por_producto[mov.id_producto] = despachado_por_producto.get(
            mov.id_producto, Decimal(0)
        ) + (-Decimal(mov.cantidad))
        salidas_por_producto.setdefault(mov.id_producto, []).append(mov)

    instante = datetime.now(timezone.utc)
    detalle: list[dict] = []

    for id_producto, despachada in despachado_por_producto.items():
        recibida = Decimal(recibido_por_producto.get(id_producto, int(despachada)))
        # Se ingresa lo recibido, repartido sobre los lotes de origen en el orden en que
        # salieron, conservando el costo y la caducidad de cada uno (FR-017, research.md #5).
        restante = recibida
        for mov in salidas_por_producto[id_producto]:
            if restante <= 0:
                break
            lote_origen = sesion.get(Lote, mov.id_lote) if mov.id_lote is not None else None
            tramo = min(restante, -Decimal(mov.cantidad))
            costo = Decimal(lote_origen.costo_unitario) if lote_origen is not None else Decimal("0")
            caducidad = lote_origen.fecha_caducidad if lote_origen is not None else None
            moneda = lote_origen.moneda if lote_origen is not None else "USD"
            lote_dest = _lote_destino(
                sesion,
                id_producto=id_producto,
                id_sucursal=traspaso.id_sucursal_destino,
                costo=costo,
                caducidad=caducidad,
                moneda=moneda,
            )
            registrar_movimiento(
                sesion,
                id_sucursal=traspaso.id_sucursal_destino,
                id_producto=id_producto,
                id_lote=lote_dest.id_lote,
                tipo="entrada_traspaso",
                cantidad=tramo,
                instante=instante,
                id_traspaso=id_traspaso,
            )
            restante -= tramo

        detalle.append(
            {
                "id_producto": id_producto,
                "cantidad_despachada": int(despachada),
                "cantidad_recibida": int(recibida),
                "discrepancia": int(recibida - despachada),
            }
        )

    traspaso.estado = "recibido"
    traspaso.instante_recepcion = instante
    sesion.commit()
    traspaso._detalle_recepcion = detalle  # type: ignore[attr-defined]
    return traspaso


def renglones_de_traspaso(sesion: Session, traspaso: Traspaso) -> list[dict]:
    """Reconstruye los renglones (despachado / recibido / discrepancia) desde los movimientos."""
    detalle_cacheado = getattr(traspaso, "_detalle_recepcion", None)
    if detalle_cacheado is not None:
        return detalle_cacheado

    movs = sesion.execute(
        select(MovimientoInventario).where(
            MovimientoInventario.id_traspaso == traspaso.id_traspaso
        )
    ).scalars().all()
    despachado: dict[int, Decimal] = {}
    recibido: dict[int, Decimal] = {}
    for mov in movs:
        if mov.tipo == "salida_traspaso":
            despachado[mov.id_producto] = despachado.get(mov.id_producto, Decimal(0)) + (
                -Decimal(mov.cantidad)
            )
        elif mov.tipo == "entrada_traspaso":
            recibido[mov.id_producto] = recibido.get(mov.id_producto, Decimal(0)) + Decimal(
                mov.cantidad
            )

    renglones = []
    for id_producto, cant_desp in despachado.items():
        recibida = recibido.get(id_producto)
        renglones.append(
            {
                "id_producto": id_producto,
                "cantidad_despachada": int(cant_desp),
                "cantidad_recibida": None if recibida is None else int(recibida),
                "discrepancia": None if recibida is None else int(recibida - cant_desp),
            }
        )
    return renglones


def listar_traspasos(
    sesion: Session,
    *,
    estado: str | None = None,
    id_sucursal_origen: int | None = None,
    id_sucursal_destino: int | None = None,
) -> list[dict]:
    """Traspasos filtrados por estado y/o sucursal. Un traspaso `en_transito` cuya recepción
    todavía no se confirmó reaparece por aquí en cuanto se vuelve a la pantalla de Traspasos —
    así deja de depender de que el operador no cambie de pantalla tras despachar.
    """
    stmt = select(Traspaso)
    if estado is not None:
        stmt = stmt.where(Traspaso.estado == estado)
    if id_sucursal_origen is not None and id_sucursal_destino is not None:
        stmt = stmt.where(
            (Traspaso.id_sucursal_origen == id_sucursal_origen)
            | (Traspaso.id_sucursal_destino == id_sucursal_destino)
        )
    elif id_sucursal_origen is not None:
        stmt = stmt.where(Traspaso.id_sucursal_origen == id_sucursal_origen)
    elif id_sucursal_destino is not None:
        stmt = stmt.where(Traspaso.id_sucursal_destino == id_sucursal_destino)
    stmt = stmt.order_by(Traspaso.instante_despacho.desc())
    return [traspaso_a_respuesta(sesion, t) for t in sesion.execute(stmt).scalars().all()]


def traspaso_a_respuesta(sesion: Session, traspaso: Traspaso) -> dict:
    return {
        "id_traspaso": traspaso.id_traspaso,
        "id_sucursal_origen": traspaso.id_sucursal_origen,
        "id_sucursal_destino": traspaso.id_sucursal_destino,
        "estado": traspaso.estado,
        "instante_despacho": traspaso.instante_despacho,
        "instante_recepcion": traspaso.instante_recepcion,
        "renglones": renglones_de_traspaso(sesion, traspaso),
    }
