"""Hallazgo #7 de la auditoría end-to-end: `rasero.semilla_pagos` completa el hueco de datos de
demostración de 007 —ningún seed declaraba `cobertura_pago`, así que la pantalla "Pagos /
Cobertura" mostraba todo como NO cubierto pese a que Venta cobra en efectivo—.

No es un cambio de lógica: `cobertura_en_fecha` ya era correcta. Contra PostgreSQL real, 5442.
"""

from sqlalchemy import func, select
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import CoberturaPago
from rasero.semilla_pagos import APERTURA_COMERCIO, sembrar
from tests.apoyo_pagos import crear_operador, crear_sucursal

cliente = TestClient(app)


def test_sembrar_declara_todos_los_medios_como_cubiertos_en_cada_sucursal(sesion):
    sucursal = crear_sucursal(sesion)
    crear_operador(sesion, es_encargado=True, id_sucursal=sucursal.id_sucursal)
    sesion.commit()

    resumen = sembrar()
    assert resumen["tramos_creados"] >= resumen["medios"] >= 1

    # Efectivo aparece cubierto en la sucursal, con la fecha de apertura del comercio.
    r = cliente.get(f"/pagos/cobertura?id_sucursal={sucursal.id_sucursal}")
    assert r.status_code == 200, r.text
    efectivo = next(m for m in r.json()["medios"] if m["nombre"] == "efectivo")
    assert efectivo["cubierto"] is True

    tramo = sesion.execute(
        select(CoberturaPago).where(CoberturaPago.id_sucursal == sucursal.id_sucursal)
    ).scalars().first()
    assert tramo is not None and tramo.fecha_desde == APERTURA_COMERCIO and tramo.fecha_hasta is None


def test_sembrar_es_idempotente(sesion):
    sucursal = crear_sucursal(sesion)
    crear_operador(sesion, es_encargado=True, id_sucursal=sucursal.id_sucursal)
    sesion.commit()

    sembrar()
    antes = sesion.execute(select(func.count()).select_from(CoberturaPago)).scalar_one()
    segunda = sembrar()
    despues = sesion.execute(select(func.count()).select_from(CoberturaPago)).scalar_one()

    # La segunda corrida no crea ningún tramo para pares que ya tienen uno vigente.
    assert despues == antes
    # (puede crear tramos para sucursales de OTROS tests sin cobertura previa, no para ésta)
    assert isinstance(segunda["tramos_creados"], int)
