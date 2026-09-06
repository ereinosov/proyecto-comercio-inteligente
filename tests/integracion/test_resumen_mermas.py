"""US5 de 006-caja-mermas-fraude (FR-042..FR-045): `GET /caja/mermas/resumen` agrega la
valoración de merma por semana y por causa. Contra PostgreSQL real, puerto 5442.
"""

import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Merma
from tests.apoyo_caja import crear_operador, crear_producto, crear_sucursal

cliente = TestClient(app)


def _merma(sesion, *, id_sucursal, id_producto, id_operador, causa, periodo_hasta, valoracion):
    sesion.add(
        Merma(
            id_producto=id_producto,
            id_sucursal=id_sucursal,
            cantidad_faltante=Decimal("3"),
            causa=causa,
            valoracion=valoracion,
            periodo_desde=periodo_hasta - dt.timedelta(days=6),
            periodo_hasta=periodo_hasta,
            estado="clasificada" if causa != "pendiente_clasificar" else "pendiente_clasificar",
            id_operador_registro=id_operador,
            instante_registro=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        )
    )


def test_resumen_agrega_por_semana_y_causa_y_separa_lo_no_valorable(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion)
    operador = crear_operador(sesion)
    sesion.commit()

    ids = dict(
        id_sucursal=sucursal.id_sucursal,
        id_producto=producto.id_producto,
        id_operador=operador.id_operador,
    )
    sem1 = dt.date(2026, 3, 8)  # domingo
    sem2 = dt.date(2026, 3, 15)

    _merma(sesion, **ids, causa="vencimiento", periodo_hasta=sem1, valoracion=Decimal("10.00"))
    _merma(sesion, **ids, causa="dano", periodo_hasta=sem1, valoracion=Decimal("4.00"))
    _merma(sesion, **ids, causa="vencimiento", periodo_hasta=sem2, valoracion=Decimal("7.00"))
    _merma(sesion, **ids, causa="robo_externo", periodo_hasta=sem2, valoracion=None)
    _merma(sesion, **ids, causa="pendiente_clasificar", periodo_hasta=sem2, valoracion=Decimal("99.00"))
    sesion.commit()

    r = cliente.get(f"/caja/mermas/resumen?id_sucursal={sucursal.id_sucursal}")
    assert r.status_code == 200
    filas = {f["periodo"]: f for f in r.json()}

    assert len(filas) == 2  # dos semanas, `pendiente_clasificar` no crea causa pero su semana sí existe
    semanas = sorted(filas)
    b1, b2 = filas[semanas[0]], filas[semanas[1]]

    assert b1["vencimiento"] == 10.0
    assert b1["dano"] == 4.0
    assert b1["robo_externo"] == 0.0
    assert b1["sin_valor"] == 0

    assert b2["vencimiento"] == 7.0
    assert b2["robo_externo"] == 0.0  # su valoración era None: no suma
    assert b2["sin_valor"] == 1

    # `pendiente_clasificar` no aparece como serie en ningún bucket.
    assert "pendiente_clasificar" not in b1
    assert "pendiente_clasificar" not in b2
