"""T072 [US6] — Prueba OBLIGATORIA (Principio III, suite n.º 5): la existencia total del sistema
es idéntica antes y después de despachar un traspaso.

`inventario_total = Σ existencia.cantidad
                  + Σ |cantidad| de movimientos salida_traspaso de traspasos en_transito`

(data-model.md). La mercancía en tránsito no está disponible en ninguna sucursal pero **sigue
contando en el total** (FR-018). Al confirmar la recepción completa, el total tampoco cambia.
"""

from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import Existencia, MovimientoInventario, Traspaso
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.traspasos import (
    RenglonDespacho,
    RenglonRecepcion,
    despachar_traspaso,
    recibir_traspaso,
)
from tests.apoyo import crear_escenario_basico


def _inventario_total(sesion) -> Decimal:
    suma_existencia = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0))
    ).scalar_one()
    en_transito = sesion.execute(
        select(func.coalesce(func.sum(func.abs(MovimientoInventario.cantidad)), 0))
        .join(Traspaso, Traspaso.id_traspaso == MovimientoInventario.id_traspaso)
        .where(
            MovimientoInventario.tipo == "salida_traspaso",
            Traspaso.estado == "en_transito",
        )
    ).scalar_one()
    return Decimal(suma_existencia) + Decimal(en_transito)


def test_inventario_total_identico_al_despachar_y_al_recibir(sesion):
    origen = crear_escenario_basico(sesion, existencia_inicial=0)
    destino = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = origen["producto"].id_producto

    # El producto de destino es otro; para el traspaso usamos el mismo id_producto en ambas
    # sucursales -> registramos una entrada del producto de origen también en la sucursal destino
    # NO: el traspaso mueve el producto de origen. Basta con stock en origen.
    registrar_entrada(
        sesion,
        id_sucursal=origen["sucursal"].id_sucursal,
        id_producto=id_producto,
        cantidad=20,
        costo_unitario=Decimal("1.5000"),
    )

    total_inicial = _inventario_total(sesion)

    traspaso = despachar_traspaso(
        sesion,
        id_sucursal_origen=origen["sucursal"].id_sucursal,
        id_sucursal_destino=destino["sucursal"].id_sucursal,
        renglones=[RenglonDespacho(id_producto=id_producto, cantidad=8)],
    )
    assert traspaso.estado == "en_transito"
    assert _inventario_total(sesion) == total_inicial, "el total no cambia al despachar (FR-018)"

    # Origen queda con 12 disponibles; destino sigue en 0 disponibles de ese producto.
    saldo_origen = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
            Existencia.id_sucursal == origen["sucursal"].id_sucursal,
            Existencia.id_producto == id_producto,
        )
    ).scalar_one()
    assert Decimal(saldo_origen) == Decimal(12)

    recibido = recibir_traspaso(
        sesion,
        id_traspaso=traspaso.id_traspaso,
        renglones=[RenglonRecepcion(id_producto=id_producto, cantidad_recibida=8)],
    )
    assert recibido.estado == "recibido"
    assert _inventario_total(sesion) == total_inicial, "el total no cambia al recibir completo"

    saldo_destino = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
            Existencia.id_sucursal == destino["sucursal"].id_sucursal,
            Existencia.id_producto == id_producto,
        )
    ).scalar_one()
    assert Decimal(saldo_destino) == Decimal(8)
