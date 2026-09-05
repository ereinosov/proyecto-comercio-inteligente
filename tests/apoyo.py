"""Helpers de datos para pruebas de integración y contrato. No es un archivo de pruebas."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import (
    AnulacionVenta,
    Lote,
    Operador,
    Producto,
    Sucursal,
    Turno,
    Venta,
)
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.seguridad import hashear_pin


def venta_de_prueba(sesion, *, id_turno: int, instante: datetime) -> int:
    """Crea una `venta` mínima para poder colgar de ella un movimiento `salida_venta` con el
    instante que la prueba necesita (el `CHECK ck_movimiento_origen_unico` de 001 exige que toda
    `salida_venta` referencie una venta). No pasa por el servicio de venta a propósito: aquí sólo
    interesa el movimiento de inventario, no el flujo de cobro.
    """
    venta = Venta(
        clave_idempotencia=f"prueba-{uuid.uuid4()}",
        id_turno=id_turno,
        referencia_terminal_pago=None,
        instante=instante,
        total=Decimal("0.00"),
    )
    sesion.add(venta)
    sesion.flush()
    return venta.id_venta


def anulacion_de_prueba(sesion, *, id_venta: int, id_operador: int, instante: datetime) -> int:
    """Crea una `anulacion_venta` mínima para colgar de ella un movimiento `entrada_anulacion`
    con un instante controlado (el servicio real `anular_venta` usa `datetime.now`, no
    parametrizable).
    """
    anulacion = AnulacionVenta(
        id_venta=id_venta, id_operador=id_operador, instante=instante, motivo=None
    )
    sesion.add(anulacion)
    sesion.flush()
    return anulacion.id_anulacion_venta


_BASE_UTC = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def sembrar_ventas_diarias(
    sesion,
    escenario,
    *,
    dias: int,
    cantidad,
    precio=None,
    primer_dia_atras: int | None = None,
):
    """Registra `dias` días consecutivos de ventas de un producto, terminando `primer_dia_atras -
    dias + 1` días atrás. `cantidad` es un entero o un callable `(indice, fecha_utc) -> int`
    (índice 0 = día más antiguo); una cantidad 0 salta ese día (útil para simular quiebres). Deja
    una entrada de stock suficiente al inicio. 12:00 UTC = 07:00 local en America/Guayaquil, lejos
    de medianoche.
    """
    primer_dia_atras = primer_dia_atras if primer_dia_atras is not None else dias
    instantes = [_BASE_UTC - timedelta(days=primer_dia_atras - i) for i in range(dias)]
    cantidades = [
        cantidad(i, instantes[i]) if callable(cantidad) else int(cantidad) for i in range(dias)
    ]

    registrar_movimiento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(sum(cantidades) + dias + 100),
        instante=instantes[0] - timedelta(hours=2),
    )
    for i, instante in enumerate(instantes):
        if cantidades[i] <= 0:
            continue
        id_venta = venta_de_prueba(
            sesion, id_turno=escenario["turno"].id_turno, instante=instante
        )
        registrar_movimiento(
            sesion,
            id_sucursal=escenario["sucursal"].id_sucursal,
            id_producto=escenario["producto"].id_producto,
            id_lote=escenario["lote"].id_lote,
            tipo="salida_venta",
            cantidad=Decimal(-cantidades[i]),
            instante=instante,
            id_venta=id_venta,
        )
        if precio is not None:
            from rasero.persistencia.modelos import RenglonVenta

            valor = precio(i, instante) if callable(precio) else precio
            sesion.add(
                RenglonVenta(
                    id_venta=id_venta,
                    id_producto=escenario["producto"].id_producto,
                    cantidad_unidades=cantidades[i],
                    cantidad_gramos=None,
                    precio_aplicado=Decimal(str(valor)),
                    importe=Decimal(str(valor)) * Decimal(cantidades[i]),
                )
            )
    sesion.commit()


def crear_escenario_basico(sesion, *, existencia_inicial: int = 10, es_granel: bool = False):
    sucursal = Sucursal(
        nombre=f"Sucursal de prueba {datetime.now().timestamp()}",
        zona_horaria="America/Guayaquil",
    )
    sesion.add(sucursal)
    sesion.flush()

    producto = Producto(
        nombre="Producto de prueba",
        es_granel=es_granel,
        precio_vigente=Decimal("2.5000"),
        lleva_caducidad=False,
    )
    sesion.add(producto)
    sesion.flush()

    operador = Operador(nombre="Operador de prueba", pin_hash="", es_encargado=False, activo=True)
    sesion.add(operador)
    sesion.flush()
    operador.pin_hash = hashear_pin("1234", str(operador.id_operador))
    sesion.flush()

    turno = Turno(
        id_operador=operador.id_operador,
        id_sucursal=sucursal.id_sucursal,
        caja="caja-1",
        instante_apertura=datetime.now(timezone.utc),
    )
    sesion.add(turno)
    sesion.flush()

    lote = Lote(
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo_unitario=Decimal("1.0000"),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()

    if existencia_inicial:
        registrar_movimiento(
            sesion,
            id_sucursal=sucursal.id_sucursal,
            id_producto=producto.id_producto,
            id_lote=lote.id_lote,
            tipo="entrada_compra",
            cantidad=Decimal(existencia_inicial),
            instante=datetime.now(timezone.utc) - timedelta(days=1),
        )

    sesion.commit()

    return {
        "sucursal": sucursal,
        "producto": producto,
        "operador": operador,
        "turno": turno,
        "lote": lote,
        "pin": "1234",
    }
