"""T019 — Prueba obligatoria (Principio III): idempotencia de venta. Diez reintentos con la
misma clave_idempotencia producen una sola venta y un solo juego de movimientos.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import MovimientoInventario, Venta
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def test_diez_reintentos_con_la_misma_clave_producen_una_sola_venta(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=100)
    clave = f"idem-{uuid.uuid4()}"
    renglones = [
        RenglonEntrada(id_producto=escenario["producto"].id_producto, cantidad_unidades=2, cantidad_gramos=None)
    ]

    resultados = []
    for _ in range(10):
        venta, creada_ahora, _advertencias, _lotes = registrar_venta(
            sesion,
            clave_idempotencia=clave,
            id_turno=escenario["turno"].id_turno,
            referencia_terminal_pago="datafono-1",
            instante_origen=None,
            renglones=renglones,
        )
        resultados.append((venta.id_venta, creada_ahora))

    ids = {r[0] for r in resultados}
    assert len(ids) == 1, "Los diez reintentos deben referirse a la misma venta"
    assert resultados[0][1] is True, "El primer intento crea la venta"
    assert all(r[1] is False for r in resultados[1:]), "Los reintentos no crean una venta nueva"

    total_ventas = sesion.execute(
        select(func.count()).select_from(Venta).where(Venta.clave_idempotencia == clave)
    ).scalar_one()
    assert total_ventas == 1

    total_movimientos = sesion.execute(
        select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.id_venta == ids.pop())
    ).scalar_one()
    assert total_movimientos == 1, "Un solo renglón de 2 unidades debe generar un solo movimiento"
