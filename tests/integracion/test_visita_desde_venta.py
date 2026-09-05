"""T004 — Prueba obligatoria (Principio III): una venta que identifica cliente crea exactamente
una visita con monto_total/margen_relativo congelados (FR-005); una venta sin cliente no crea
ninguna; un reintento sobre la misma id_venta devuelve la visita original (idempotencia, igual
patrón que venta en 001).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import Visita
from rasero.servicios.clientes import registrar_cliente, registrar_visita
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _completar_venta(sesion, escenario, *, clave: str, cantidad_unidades: int = 2):
    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=clave,
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(
                id_producto=escenario["producto"].id_producto,
                cantidad_unidades=cantidad_unidades,
                cantidad_gramos=None,
            )
        ],
    )
    return venta


def test_venta_que_identifica_cliente_crea_una_visita_con_snapshot_correcto(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)
    # costo_unitario=1.0000, precio_vigente=2.5000 (apoyo.py) -> margen relativo = (2.5-1)/2.5 = 0.6
    venta = _completar_venta(sesion, escenario, clave="visita-1")

    cliente = registrar_cliente(sesion, nombre="Ana Pérez", fecha_nacimiento=date(1990, 5, 1))
    visita, creada_ahora = registrar_visita(
        sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta
    )

    assert creada_ahora is True
    assert visita.id_cliente == cliente.id_cliente
    assert visita.id_venta == venta.id_venta
    assert visita.monto_total == venta.total == Decimal("5.00")
    assert visita.margen_relativo == Decimal("0.6000")

    total_visitas = sesion.execute(
        select(func.count()).select_from(Visita).where(Visita.id_venta == venta.id_venta)
    ).scalar_one()
    assert total_visitas == 1


def test_venta_sin_cliente_no_crea_ninguna_visita(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)
    venta = _completar_venta(sesion, escenario, clave="visita-sin-cliente")

    total_visitas = sesion.execute(
        select(func.count()).select_from(Visita).where(Visita.id_venta == venta.id_venta)
    ).scalar_one()
    assert total_visitas == 0


def test_reintento_sobre_la_misma_venta_devuelve_la_visita_original(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)
    venta = _completar_venta(sesion, escenario, clave="visita-reintento")
    cliente = registrar_cliente(sesion, nombre="Luis Gómez", fecha_nacimiento=date(1985, 3, 20))

    primera, creada_primera = registrar_visita(
        sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta
    )
    segunda, creada_segunda = registrar_visita(
        sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta
    )

    assert creada_primera is True
    assert creada_segunda is False
    assert segunda.id_visita == primera.id_visita

    total_visitas = sesion.execute(
        select(func.count()).select_from(Visita).where(Visita.id_venta == venta.id_venta)
    ).scalar_one()
    assert total_visitas == 1
