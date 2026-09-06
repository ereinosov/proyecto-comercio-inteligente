"""Datos de demostración de historial de ventas e inventario (001-core-ventas-inventario).

    python -m rasero.semilla_movimientos

Genera ~8 semanas de ventas diarias sobre el catálogo de `rasero.semilla_catalogo`, en las dos
sucursales, para que:

  * **Pronóstico (004)** tenga serie de demanda observable suficiente (> 14 períodos sin
    quiebre) para arriesgar un número, y **un intervalo de quiebre de stock documentado** que
    descensurar: el producto «Aceite girasol 1 L» en Quevedo Centro se agota por un pico de
    demanda alrededor del día -29 a -27 y se repone el día -26;
  * **Precios (003)** tenga margen real calculable en la mayoría de productos (las ventas
    consumen lotes pero no vacían la existencia salvo la del producto de quiebre), evitando que
    "Margen no calculable" sea el estado dominante de la demo;
  * **Venta.tsx** tenga un turno con movimiento reciente.

Frontera de propiedad de datos: módulo de 001. Usa el servicio público `registrar_venta` de
001 para la demanda y `registrar_movimiento` (entrada_compra) para la reposición — nunca toca
`existencia` directamente. No escribe en tablas de 002/003/004/005.

Idempotente: las ventas usan `clave_idempotencia` determinista (re-ejecutar devuelve la venta
existente, sin duplicar), y la reposición del producto de quiebre sólo se registra una vez.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import (
    Lote,
    MovimientoInventario,
    Operador,
    Producto,
    Sucursal,
    Turno,
)
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import SesionLocal
from rasero.semilla_catalogo import NOMBRE_PRODUCTO_QUIEBRE, SUCURSALES_DEMO
from rasero.semilla_catalogo import sembrar as sembrar_catalogo
from rasero.servicios.ventas import RenglonEntrada, registrar_venta

_SEMILLA = 20260905
_DIAS_HISTORIAL = 56

# Ventana del pico de demanda que agota «Aceite girasol 1 L» en Quevedo Centro.
_QUIEBRE_DESDE = 30  # días atrás
_QUIEBRE_HASTA = 27
_QUIEBRE_REPOSICION = 26
_QUIEBRE_REPOSICION_CANT = 260


def _turno_por_sucursal(sesion: Session, id_sucursal: int) -> Turno:
    turno = sesion.execute(
        select(Turno)
        .where(Turno.id_sucursal == id_sucursal, Turno.instante_cierre.is_(None))
        .order_by(Turno.id_turno)
        .limit(1)
    ).scalar_one_or_none()
    if turno is not None:
        return turno
    operador = sesion.execute(select(Operador).order_by(Operador.id_operador)).scalars().first()
    turno = Turno(
        id_operador=operador.id_operador,
        id_sucursal=id_sucursal,
        caja="caja-semilla-mov",
        instante_apertura=datetime.now(timezone.utc) - timedelta(days=_DIAS_HISTORIAL + 5),
    )
    sesion.add(turno)
    sesion.flush()
    sesion.commit()
    return turno


def _cantidad_dia(rng: random.Random, producto: Producto, dia_atras: int) -> int:
    """Demanda diaria con leve estacionalidad de quincena (picos en días 14-16 y fin de mes)."""
    base_unidades = rng.randint(2, 9)
    if producto.es_granel:
        return rng.randint(300, 1500)  # gramos
    dia_mes = (datetime.now(timezone.utc) - timedelta(days=dia_atras)).day
    if dia_mes in (14, 15, 16) or dia_mes >= 28:
        base_unidades += rng.randint(1, 4)
    return base_unidades


def _sembrar_demanda_general(
    sesion: Session,
    *,
    sucursal: Sucursal,
    turno: Turno,
    productos: list[Producto],
    rng: random.Random,
) -> int:
    ventas = 0
    for dia_atras in range(_DIAS_HISTORIAL, 0, -1):
        instante = datetime.now(timezone.utc) - timedelta(days=dia_atras, hours=rng.randint(9, 20))
        elegidos = [p for p in productos if rng.random() < 0.62]
        if not elegidos:
            continue
        renglones = []
        for p in elegidos:
            cant = _cantidad_dia(rng, p, dia_atras)
            if p.es_granel:
                renglones.append(
                    RenglonEntrada(
                        id_producto=p.id_producto, cantidad_unidades=None, cantidad_gramos=cant
                    )
                )
            else:
                renglones.append(
                    RenglonEntrada(
                        id_producto=p.id_producto, cantidad_unidades=cant, cantidad_gramos=None
                    )
                )
        clave = f"semilla-mov::{sucursal.nombre}::dia-{dia_atras:03d}"
        registrar_venta(
            sesion,
            clave_idempotencia=clave,
            id_turno=turno.id_turno,
            referencia_terminal_pago=None,
            instante_origen=instante,
            renglones=renglones,
        )
        ventas += 1
    return ventas


def _sembrar_quiebre(
    sesion: Session,
    *,
    sucursal: Sucursal,
    turno: Turno,
    producto: Producto,
    rng: random.Random,
) -> dict:
    """Pico de demanda que agota el producto, y su reposición. Ventas de un solo renglón para
    controlar el perfil día a día."""
    ventas = 0
    for dia_atras in range(_DIAS_HISTORIAL, 0, -1):
        if _QUIEBRE_HASTA <= dia_atras <= _QUIEBRE_DESDE:
            cant = rng.randint(14, 20)  # pico: agota los ~70 de existencia inicial
        elif dia_atras < _QUIEBRE_REPOSICION:
            cant = rng.randint(1, 3)
        else:
            cant = rng.randint(1, 2)
        instante = datetime.now(timezone.utc) - timedelta(days=dia_atras, hours=12)
        clave = f"semilla-mov::quiebre::{sucursal.nombre}::dia-{dia_atras:03d}"
        registrar_venta(
            sesion,
            clave_idempotencia=clave,
            id_turno=turno.id_turno,
            referencia_terminal_pago=None,
            instante_origen=instante,
            renglones=[
                RenglonEntrada(
                    id_producto=producto.id_producto, cantidad_unidades=cant, cantidad_gramos=None
                )
            ],
        )
        ventas += 1

    # Reposición el día -26, una sola vez.
    lote = (
        sesion.execute(
            select(Lote)
            .where(
                Lote.id_producto == producto.id_producto, Lote.id_sucursal == sucursal.id_sucursal
            )
            .order_by(Lote.id_lote)
        )
        .scalars()
        .first()
    )
    entradas = sesion.execute(
        select(func.count())
        .select_from(MovimientoInventario)
        .where(
            MovimientoInventario.id_lote == lote.id_lote,
            MovimientoInventario.tipo == "entrada_compra",
        )
    ).scalar_one()
    repuesto = False
    if entradas <= 1:
        registrar_movimiento(
            sesion,
            id_sucursal=sucursal.id_sucursal,
            id_producto=producto.id_producto,
            id_lote=lote.id_lote,
            tipo="entrada_compra",
            cantidad=Decimal(_QUIEBRE_REPOSICION_CANT),
            instante=datetime.now(timezone.utc) - timedelta(days=_QUIEBRE_REPOSICION, hours=7),
        )
        repuesto = True
    return {"ventas": ventas, "repuesto": repuesto}


def sembrar() -> dict:
    sembrar_catalogo()
    sesion = SesionLocal()
    try:
        rng = random.Random(_SEMILLA)
        sucursales = {
            n: sesion.execute(select(Sucursal).where(Sucursal.nombre == n)).scalar_one()
            for n in SUCURSALES_DEMO
        }
        quiebre_prod = sesion.execute(
            select(Producto).where(Producto.nombre == NOMBRE_PRODUCTO_QUIEBRE)
        ).scalar_one()

        total_ventas = 0
        resumen_quiebre = {}
        for nombre, sucursal in sucursales.items():
            turno = _turno_por_sucursal(sesion, sucursal.id_sucursal)
            productos = list(
                sesion.execute(
                    select(Producto)
                    .where(Producto.id_producto != quiebre_prod.id_producto)
                    .order_by(Producto.id_producto)
                ).scalars()
            )
            total_ventas += _sembrar_demanda_general(
                sesion, sucursal=sucursal, turno=turno, productos=productos, rng=rng
            )
            sesion.commit()
            if nombre == "Quevedo Centro":
                resumen_quiebre = _sembrar_quiebre(
                    sesion, sucursal=sucursal, turno=turno, producto=quiebre_prod, rng=rng
                )
                total_ventas += resumen_quiebre["ventas"]
                sesion.commit()

        print(
            f"Movimientos sembrados: {total_ventas} ventas de historial "
            f"({_DIAS_HISTORIAL} días, 2 sucursales)."
        )
        print(
            f"  Quiebre de «{NOMBRE_PRODUCTO_QUIEBRE}» en Quevedo Centro: "
            f"pico días -{_QUIEBRE_DESDE}..-{_QUIEBRE_HASTA}, reposición día -{_QUIEBRE_REPOSICION} "
            f"({'registrada ahora' if resumen_quiebre.get('repuesto') else 'ya existía'})."
        )
        return {"ventas": total_ventas, **resumen_quiebre}
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
