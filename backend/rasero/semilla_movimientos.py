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
from rasero.persistencia.movimientos import obtener_existencia_total, registrar_movimiento
from rasero.persistencia.sesion import SesionLocal
from rasero.semilla_catalogo import NOMBRE_PRODUCTO_QUIEBRE, SUCURSALES_DEMO, reponer_inventario
from rasero.semilla_catalogo import sembrar as sembrar_catalogo
from rasero.servicios.ventas import RenglonEntrada, registrar_venta

_SEMILLA = 20260905
_DIAS_HISTORIAL = 56

# Cada cuántos días de la simulación el "minorista" reabastece la góndola (ver
# `semilla_catalogo.reponer_inventario`). Sin esto, las 8 semanas de venta agotan el catálogo
# —y en particular los dos productos de `rasero/semilla.py`, que entran con existencia mínima—
# ahora que `registrar_venta` rechaza el saldo negativo (bloqueo duro de existencia, 001).
_DIAS_ENTRE_REPOSICIONES = 7

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
    reposiciones = 0
    for dia_atras in range(_DIAS_HISTORIAL, 0, -1):
        # Reabastecimiento periódico ANTES de la venta del día (hora 23 atrás = temprano en el
        # día): un minorista repone su góndola cada semana.
        if (_DIAS_HISTORIAL - dia_atras) % _DIAS_ENTRE_REPOSICIONES == 0:
            reposiciones += reponer_inventario(
                sesion,
                id_sucursal=sucursal.id_sucursal,
                productos=productos,
                instante=datetime.now(timezone.utc) - timedelta(days=dia_atras, hours=23),
            )
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
    return ventas, reposiciones


def _sembrar_quiebre(
    sesion: Session,
    *,
    sucursal: Sucursal,
    turno: Turno,
    producto: Producto,
    rng: random.Random,
) -> dict:
    """Pico de demanda que agota el producto, y su reposición el día -26 — el intervalo de
    quiebre que 004 (pronóstico) necesita descensurar. El perfil de demanda no cambia: sigue
    "queriendo" 14-20 u/día en el pico. Lo que cambia es que la venta se limita a lo que hay en
    góndola (`min(demanda, existencia)`): cuando el stock llega a 0, los días de pico restantes
    quedan SIN venta —un quiebre de stock real, demanda censurada— hasta la reposición. Antes
    del bloqueo duro de existencia (001) esto se registraba como saldo negativo; ahora se
    modela como lo que es. Idempotente: si la reposición ya existe, no regenera nada."""
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
    entradas_previas = sesion.execute(
        select(func.count())
        .select_from(MovimientoInventario)
        .where(
            MovimientoInventario.id_lote == lote.id_lote,
            MovimientoInventario.tipo == "entrada_compra",
        )
    ).scalar_one()
    if entradas_previas > 1:  # catálogo deja 1; >1 = una corrida anterior ya sembró el quiebre
        return {"ventas": 0, "repuesto": False, "dia_agotado": None, "ya_estaba": True}

    ventas = 0
    repuesto = False
    dia_agotado = None
    dia_recuperado = None
    for dia_atras in range(_DIAS_HISTORIAL, 0, -1):
        # Reposición al llegar al día -26, ANTES de la venta de ese día (para que los días
        # posteriores vuelvan a tener stock que vender).
        if dia_atras == _QUIEBRE_REPOSICION:
            registrar_movimiento(
                sesion,
                id_sucursal=sucursal.id_sucursal,
                id_producto=producto.id_producto,
                id_lote=lote.id_lote,
                tipo="entrada_compra",
                cantidad=Decimal(_QUIEBRE_REPOSICION_CANT),
                instante=datetime.now(timezone.utc)
                - timedelta(days=_QUIEBRE_REPOSICION, hours=7),
            )
            repuesto = True

        if _QUIEBRE_HASTA <= dia_atras <= _QUIEBRE_DESDE:
            cant = rng.randint(14, 20)  # pico: la demanda "quiere" agotar los ~70 iniciales
        elif dia_atras < _QUIEBRE_REPOSICION:
            cant = rng.randint(1, 3)
        else:
            cant = rng.randint(1, 2)

        disponible = int(
            obtener_existencia_total(
                sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto
            )
        )
        vendible = min(cant, disponible)
        if vendible <= 0:
            if dia_agotado is None:
                dia_agotado = dia_atras
            continue
        if dia_agotado is not None and dia_recuperado is None:
            dia_recuperado = dia_atras

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
                    id_producto=producto.id_producto,
                    cantidad_unidades=vendible,
                    cantidad_gramos=None,
                )
            ],
        )
        ventas += 1

    return {
        "ventas": ventas,
        "repuesto": repuesto,
        "dia_agotado": dia_agotado,
        "dia_recuperado": dia_recuperado,
    }


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
        total_reposiciones = 0
        resumen_quiebre = {}
        for nombre, sucursal in sucursales.items():
            turno = _turno_por_sucursal(sesion, sucursal.id_sucursal)
            # Sólo los productos que esa sucursal maneja (tienen lote ahí). Los dos productos de
            # `rasero/semilla.py` sólo tienen lote en Quevedo Centro; no se venden en Buena Fe.
            con_lote = set(
                sesion.execute(
                    select(Lote.id_producto).where(Lote.id_sucursal == sucursal.id_sucursal)
                ).scalars()
            )
            productos = list(
                sesion.execute(
                    select(Producto)
                    .where(
                        Producto.id_producto != quiebre_prod.id_producto,
                        Producto.id_producto.in_(con_lote),
                    )
                    .order_by(Producto.id_producto)
                ).scalars()
            )
            ventas_suc, reposiciones_suc = _sembrar_demanda_general(
                sesion, sucursal=sucursal, turno=turno, productos=productos, rng=rng
            )
            total_ventas += ventas_suc
            total_reposiciones += reposiciones_suc
            sesion.commit()
            if nombre == "Quevedo Centro":
                resumen_quiebre = _sembrar_quiebre(
                    sesion, sucursal=sucursal, turno=turno, producto=quiebre_prod, rng=rng
                )
                total_ventas += resumen_quiebre["ventas"]
                sesion.commit()

        print(
            f"Movimientos sembrados: {total_ventas} ventas de historial "
            f"({_DIAS_HISTORIAL} días, 2 sucursales); {total_reposiciones} reabastecimientos "
            f"periódicos de góndola."
        )
        if resumen_quiebre.get("ya_estaba"):
            print(
                f"  Quiebre de «{NOMBRE_PRODUCTO_QUIEBRE}» en Quevedo Centro: ya sembrado en una "
                "corrida anterior."
            )
        else:
            agotado = resumen_quiebre.get("dia_agotado")
            recuperado = resumen_quiebre.get("dia_recuperado")
            if agotado is not None:
                ultimo_vacio = (recuperado + 1) if recuperado is not None else 1
                ventana = f"góndola vacía los días -{agotado}..-{ultimo_vacio}"
            else:
                ventana = "el pico no llegó a agotar el stock"
            print(
                f"  Quiebre de «{NOMBRE_PRODUCTO_QUIEBRE}» en Quevedo Centro: pico días "
                f"-{_QUIEBRE_DESDE}..-{_QUIEBRE_HASTA}; {ventana}; reposición día "
                f"-{_QUIEBRE_REPOSICION} "
                f"({'registrada ahora' if resumen_quiebre.get('repuesto') else 'no registrada'})."
            )
        return {"ventas": total_ventas, "reposiciones": total_reposiciones, **resumen_quiebre}
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
