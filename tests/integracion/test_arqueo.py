"""Suite obligatoria 1 (006-caja-mermas-fraude, US1 — T007/T008/T009). Contra PostgreSQL real,
puerto 5442.

- T007: `monto_esperado` = SUM(venta.total) del turno, CONGELADO — anular una venta después NO lo
  cambia (research.md #4); diferencia con signo.
- T008: idempotencia por `id_turno` (SC-003); turno sin ventas -> esperado 0 (FR-007); 0 escrituras
  en `venta`/`renglon_venta`/`movimiento_inventario` (SC-002, SC-011).
- T009: diferencia sin motivo -> `anomalia_caja` de origen efectivo (FR-004, FR-027); con motivo ->
  sin anomalía (FR-031, SC-010).
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import (
    AnomaliaCaja,
    Arqueo,
    MovimientoInventario,
    RenglonVenta,
    Venta,
)
from rasero.servicios.arqueos import registrar_arqueo
from tests.apoyo_caja import anular_venta, escenario_arqueo

cliente = TestClient(app)
_MARCA = datetime.now(timezone.utc).isoformat()


# --- T007 ---------------------------------------------------------------------


def test_monto_esperado_es_la_suma_de_cobros_del_turno_y_queda_congelado(sesion):
    sucursal, operador, turno, ventas = escenario_arqueo(sesion, totales=["10.00", "5.50", "4.00"])

    arqueo, creado = registrar_arqueo(
        sesion,
        id_turno=turno.id_turno,
        monto_contado="19.50",
        marca_tiempo_origen=datetime.now(timezone.utc),
    )
    sesion.commit()

    assert creado is True
    assert arqueo.monto_esperado == Decimal("19.50")
    assert arqueo.diferencia == Decimal("0.00")
    assert arqueo.id_operador == operador.id_operador
    assert arqueo.id_sucursal == sucursal.id_sucursal

    # Anular una venta DESPUÉS del arqueo no cambia lo esperado ni la diferencia (congelado).
    anular_venta(sesion, id_venta=ventas[0].id_venta, id_operador=operador.id_operador)
    sesion.commit()
    sesion.refresh(arqueo)
    assert arqueo.monto_esperado == Decimal("19.50")
    assert arqueo.diferencia == Decimal("0.00")


def test_diferencia_faltante_tiene_signo_negativo(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["100.00"])
    arqueo, _c = registrar_arqueo(
        sesion,
        id_turno=turno.id_turno,
        monto_contado="92.00",
        marca_tiempo_origen=datetime.now(timezone.utc),
    )
    sesion.commit()
    assert arqueo.diferencia == Decimal("-8.00")


# --- T008 -------------------------------------------------------------------


def test_arqueo_es_idempotente_por_turno(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["10.00", "10.00"])
    cuerpo = {
        "id_turno": turno.id_turno,
        "monto_contado": "20.00",
        "marca_tiempo_origen": _MARCA,
    }
    primera = cliente.post("/caja/arqueos", json=cuerpo)
    respuestas = [cliente.post("/caja/arqueos", json=cuerpo) for _ in range(9)]

    assert primera.status_code == 201
    assert all(r.status_code == 200 for r in respuestas)
    ids = {r.json()["id_arqueo"] for r in respuestas} | {primera.json()["id_arqueo"]}
    assert len(ids) == 1

    total = sesion.execute(
        select(func.count()).select_from(Arqueo).where(Arqueo.id_turno == turno.id_turno)
    ).scalar_one()
    assert total == 1


def test_turno_sin_ventas_tiene_esperado_cero_no_error(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=[])
    respuesta = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "0.00", "marca_tiempo_origen": _MARCA},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["monto_esperado"] == "0.00"
    assert respuesta.json()["diferencia"] == "0.00"


def test_arqueo_no_escribe_en_datos_de_001(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["12.00"])
    mov_antes = sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar_one()
    renglones_antes = sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one()

    respuesta = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "11.00", "marca_tiempo_origen": _MARCA},
    )
    assert respuesta.status_code == 201

    assert (
        sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
        == mov_antes
    )
    assert sesion.execute(select(func.count()).select_from(Venta)).scalar_one() == ventas_antes
    assert (
        sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one()
        == renglones_antes
    )


def test_turno_abierto_es_400(sesion):
    from tests.apoyo_caja import crear_operador, crear_sucursal, crear_turno

    sucursal = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    turno = crear_turno(
        sesion, id_operador=operador.id_operador, id_sucursal=sucursal.id_sucursal, cerrado=False
    )
    sesion.commit()
    respuesta = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "0.00", "marca_tiempo_origen": _MARCA},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "caja_turno_abierto"


# --- T009 -----------------------------------------------------------------------


def test_faltante_sin_motivo_genera_anomalia_de_efectivo(sesion):
    _s, operador, turno, _v = escenario_arqueo(sesion, totales=["100.00"])
    respuesta = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "92.00", "marca_tiempo_origen": _MARCA},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["genero_anomalia"] is True
    id_anomalia = cuerpo["id_anomalia_caja"]

    anomalia = sesion.get(AnomaliaCaja, id_anomalia)
    assert anomalia.origen == "efectivo"
    assert anomalia.estado == "sin_explicacion"
    assert anomalia.id_turno == turno.id_turno
    assert anomalia.id_operador == operador.id_operador
    assert anomalia.monto == Decimal("-8.00")


def test_faltante_con_motivo_no_genera_anomalia(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["100.00"])
    anomalias_antes = sesion.execute(
        select(func.count()).select_from(AnomaliaCaja)
    ).scalar_one()

    respuesta = cliente.post(
        "/caja/arqueos",
        json={
            "id_turno": turno.id_turno,
            "monto_contado": "98.00",
            "motivo_conocido": "mal dado el cambio",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["genero_anomalia"] is False
    assert (
        sesion.execute(select(func.count()).select_from(AnomaliaCaja)).scalar_one()
        == anomalias_antes
    )
