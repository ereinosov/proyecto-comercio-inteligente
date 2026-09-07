"""Helpers de datos para las pruebas de 005-promociones-inteligentes. No es un archivo de pruebas.

Crean clientes reales (vía los servicios públicos de 001/002) con el historial que cada mecanismo
necesita: cumpleañeros para el cupón, clientes en su ventana de recompra, y clientes con
`senal_fuga` activa para el experimento de reactivación.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from rasero.servicios.clientes import (
    evaluar_fugas_pendientes,
    registrar_cliente,
    registrar_visita,
)
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _venta(sesion, escenario, *, instante: datetime, id_producto=None, unidades=1):
    venta, _c, _a, _l = registrar_venta(
        sesion,
        clave_idempotencia=f"promo-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=instante,
        renglones=[
            RenglonEntrada(
                id_producto=id_producto or escenario["producto"].id_producto,
                cantidad_unidades=unidades,
                cantidad_gramos=None,
            )
        ],
    )
    return venta


def crear_cliente_cumpleanos(
    sesion, *, nombre: str, fecha_nacimiento: date, anonimizado: bool = False
):
    cliente = registrar_cliente(sesion, nombre=nombre, fecha_nacimiento=fecha_nacimiento)
    if anonimizado:
        cliente.anonimizado = True
        cliente.nombre = None
        cliente.fecha_nacimiento = None
        cliente.contacto = None
        cliente.instante_anonimizacion = datetime.now(timezone.utc)
        sesion.commit()
    return cliente


def crear_cliente_churned(
    sesion,
    escenario,
    *,
    nombre: str,
    intervalo_dias: int = 20,
    dias_desde_ultima: int = 45,
):
    """Cliente con 4 visitas separadas `intervalo_dias`, la última hace `dias_desde_ultima` días.
    Tras `evaluar_fugas_pendientes` queda con `senal_fuga.estado = 'activa'` (dias_sin_visita en
    [intervalo, max(5*intervalo, 365))).
    """
    cliente = registrar_cliente(sesion, nombre=nombre, fecha_nacimiento=date(1990, 1, 1))
    ahora = datetime.now(timezone.utc)
    # 3 visitas (2 intervalos) es el mínimo para `intervalo_compra.estado = 'calculado'`.
    offsets = [
        dias_desde_ultima + 2 * intervalo_dias,
        dias_desde_ultima + 1 * intervalo_dias,
        dias_desde_ultima,
    ]
    for offset in offsets:
        venta = _venta(sesion, escenario, instante=ahora - timedelta(days=offset))
        registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta)
    return cliente


def crear_cliente_en_ventana_recompra(
    sesion,
    escenario,
    *,
    nombre: str,
    id_producto: int,
    compras_del_producto: int = 4,
    intervalo_dias: int = 20,
    dias_desde_ultima: int = 17,
):
    """Cliente con `intervalo_compra.estado = 'calculado'` que compró `id_producto` varias veces
    y cuya última compra fue hace `dias_desde_ultima` (dentro de la ventana de recompra).
    """
    cliente = registrar_cliente(sesion, nombre=nombre, fecha_nacimiento=date(1990, 1, 1))
    ahora = datetime.now(timezone.utc)
    # Compras del producto objetivo, la más reciente hace `dias_desde_ultima`.
    for i in range(compras_del_producto):
        offset = dias_desde_ultima + (compras_del_producto - 1 - i) * intervalo_dias
        venta = _venta(
            sesion,
            escenario,
            instante=ahora - timedelta(days=offset),
            id_producto=id_producto,
        )
        registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta)
    return cliente


def marcar_fugas(sesion) -> int:
    """Ejecuta el job de 002 que crea las `senal_fuga` activas. Devuelve cuántos clientes tocó."""
    return evaluar_fugas_pendientes(sesion)


def limpiar_experimentos(sesion) -> None:
    """La regla "un experimento de reactivación a la vez" es global (data-model.md); como el
    conftest no hace rollback entre pruebas, cada prueba de experimento parte de un estado sin
    experimentos `en_curso`.
    """
    from sqlalchemy import delete

    from rasero.persistencia.modelos import (
        AsignacionExperimento,
        Campania,
        ExperimentoReactivacion,
        RedencionPromocion,
    )

    sesion.execute(
        delete(RedencionPromocion).where(RedencionPromocion.tipo_origen == "reactivacion")
    )
    sesion.execute(delete(AsignacionExperimento))
    sesion.execute(delete(ExperimentoReactivacion))
    sesion.execute(delete(Campania).where(Campania.tipo == "reactivacion"))
    sesion.commit()


def escenario_dos_productos(sesion):
    """Escenario básico + un segundo producto, para pruebas de recompra y de la marca activa."""
    from datetime import timedelta
    from decimal import Decimal

    from rasero.persistencia.modelos import Lote, Producto
    from rasero.persistencia.movimientos import registrar_movimiento

    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    otro = Producto(
        nombre="Segundo producto",
        es_granel=False,
        precio_vigente=Decimal("4.0000"),
        lleva_caducidad=False,
    )
    sesion.add(otro)
    sesion.flush()

    # El segundo producto también necesita existencia: desde la Corrección 2026-09-07 una venta
    # que excede el saldo se rechaza (antes se registraba en negativo).
    lote_otro = Lote(
        id_producto=otro.id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
        costo_unitario=Decimal("2.0000"),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote_otro)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=otro.id_producto,
        id_lote=lote_otro.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(100000),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.commit()
    escenario["producto_2"] = otro
    escenario["lote_2"] = lote_otro
    return escenario
