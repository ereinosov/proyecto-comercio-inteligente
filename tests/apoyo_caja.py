"""Helpers de datos para las pruebas de 006-caja-mermas-fraude. No es un archivo de pruebas.

Crea sucursales, operadores, turnos (abiertos o cerrados), ventas con su `total`, renglones,
anulaciones y lotes directamente, para probar el arqueo, la clasificación de mermas y los
indicadores por operador. 006 sólo LEE de 001, así que las pruebas de frontera cuentan filas de
`venta`/`renglon_venta`/`movimiento_inventario`/`existencia` antes y después.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import (
    AnulacionVenta,
    Lote,
    Operador,
    Producto,
    RenglonVenta,
    Sucursal,
    Turno,
    Venta,
)
from rasero.seguridad import hashear_pin

_ZONA = "America/Guayaquil"


def crear_sucursal(sesion, *, zona: str = _ZONA) -> Sucursal:
    sucursal = Sucursal(
        nombre=f"Sucursal caja {datetime.now().timestamp()}-{uuid.uuid4().hex[:6]}",
        zona_horaria=zona,
    )
    sesion.add(sucursal)
    sesion.flush()
    return sucursal


def crear_operador(
    sesion, *, nombre: str | None = None, es_encargado: bool = False,
    rol: str | None = None, id_sucursal: int | None = None,
) -> Operador:
    # Enmienda v2.3.0: `rol` + `id_sucursal` en vez de `es_encargado` (alias conservado).
    if rol is None:
        rol = "encargado" if es_encargado else "cajero"
    if id_sucursal is None:
        id_sucursal = crear_sucursal(sesion).id_sucursal
    operador = Operador(
        nombre=nombre or f"Operador {uuid.uuid4().hex[:6]}",
        pin_hash="",
        rol=rol,
        id_sucursal=id_sucursal,
        activo=True,
    )
    sesion.add(operador)
    sesion.flush()
    operador.pin_hash = hashear_pin("1234", str(operador.id_operador))
    sesion.flush()
    return operador


def crear_producto(
    sesion, *, es_granel: bool = False, precio: str = "3.0000"
) -> Producto:
    producto = Producto(
        nombre=f"Producto caja {uuid.uuid4().hex[:6]}",
        es_granel=es_granel,
        precio_vigente=Decimal(precio),
        lleva_caducidad=False,
    )
    sesion.add(producto)
    sesion.flush()
    return producto


def crear_lote(
    sesion,
    *,
    id_producto: int,
    id_sucursal: int,
    costo: str | None = "2.0000",
    fecha_caducidad: date | None = None,
) -> Lote:
    lote = Lote(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal(costo) if costo is not None else Decimal("0"),
        fecha_caducidad=fecha_caducidad,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=3),
    )
    sesion.add(lote)
    sesion.flush()
    return lote


def crear_turno(
    sesion,
    *,
    id_operador: int,
    id_sucursal: int,
    cerrado: bool = True,
    instante_cierre: datetime | None = None,
) -> Turno:
    apertura = datetime.now(timezone.utc) - timedelta(hours=8)
    cierre = None
    if cerrado:
        cierre = instante_cierre or (datetime.now(timezone.utc) - timedelta(hours=1))
    turno = Turno(
        id_operador=id_operador,
        id_sucursal=id_sucursal,
        caja="caja-1",
        instante_apertura=apertura,
        instante_cierre=cierre,
    )
    sesion.add(turno)
    sesion.flush()
    return turno


def crear_venta(
    sesion,
    *,
    id_turno: int,
    total: str,
    instante: datetime | None = None,
    id_producto: int | None = None,
    cantidad_unidades: int = 1,
    precio_aplicado: str | None = None,
) -> Venta:
    venta = Venta(
        clave_idempotencia=f"caja-{uuid.uuid4()}",
        id_turno=id_turno,
        referencia_terminal_pago=None,
        instante=instante or (datetime.now(timezone.utc) - timedelta(hours=2)),
        total=Decimal(str(total)),
    )
    sesion.add(venta)
    sesion.flush()
    if id_producto is not None:
        precio = Decimal(str(precio_aplicado if precio_aplicado is not None else total))
        sesion.add(
            RenglonVenta(
                id_venta=venta.id_venta,
                id_producto=id_producto,
                cantidad_unidades=cantidad_unidades,
                cantidad_gramos=None,
                precio_aplicado=precio,
                importe=(precio * Decimal(cantidad_unidades)).quantize(Decimal("0.01")),
            )
        )
        sesion.flush()
    return venta


def anular_venta(
    sesion, *, id_venta: int, id_operador: int, instante: datetime | None = None
) -> AnulacionVenta:
    anulacion = AnulacionVenta(
        id_venta=id_venta,
        id_operador=id_operador,
        instante=instante or (datetime.now(timezone.utc) - timedelta(hours=1)),
        motivo=None,
    )
    sesion.add(anulacion)
    sesion.flush()
    return anulacion


def escenario_arqueo(sesion, *, totales: list[str], motivo: str | None = None):
    """Sucursal + operador + turno CERRADO con una venta por cada total en `totales`.
    Devuelve `(sucursal, operador, turno, ventas)`.
    """
    sucursal = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    turno = crear_turno(sesion, id_operador=operador.id_operador, id_sucursal=sucursal.id_sucursal)
    ventas = [crear_venta(sesion, id_turno=turno.id_turno, total=t) for t in totales]
    sesion.commit()
    return sucursal, operador, turno, ventas
