"""Suite obligatoria 4 (US1) — ciclo del cupón: generación (frontera con 002, idempotencia) y
redención (frontera con 001). Contra PostgreSQL real, puerto 5442.

- T007: la generación usa la consulta de cumpleañeros de 002 (FR-002), nunca
  `cliente.fecha_nacimiento`; un cliente anonimizado no recibe cupón (FR-003).
- T008: ejecutar la generación dos veces no duplica el cupón (FR-007).
- T009: redimir un cupón vigente lo deja 'redimido' (FR-005); fuera de ventana -> 400; segundo
  POST idempotente; `POST /promociones/redenciones` no toca `movimiento_inventario`/`existencia`/
  `venta`/`renglon_venta` (FR-029).
"""

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import (
    Cupon,
    Existencia,
    MovimientoInventario,
    RenglonVenta,
)
from rasero.servicios.promociones import generar_cupones, registrar_redencion
from tests.apoyo import crear_escenario_basico
from tests.apoyo_promociones import _venta, crear_cliente_cumpleanos

cliente_http = TestClient(app)


# --- T007 ---------------------------------------------------------------------


def test_generacion_via_consulta_de_002_y_excluye_anonimizados(sesion):
    con_cumple = crear_cliente_cumpleanos(
        sesion, nombre="Cumple Sí T007", fecha_nacimiento=date(1990, 11, 15)
    )
    fuera_de_rango = crear_cliente_cumpleanos(
        sesion, nombre="Cumple No T007", fecha_nacimiento=date(1985, 12, 3)
    )
    anonimo = crear_cliente_cumpleanos(
        sesion, nombre="Anon T007", fecha_nacimiento=date(1980, 11, 10), anonimizado=True
    )

    generar_cupones(sesion, desde=date(2026, 11, 1), hasta=date(2026, 11, 28))
    sesion.commit()

    ids_con_cupon = set(
        sesion.execute(
            select(Cupon.id_cliente).where(
                Cupon.fecha_objetivo.between(date(2026, 11, 1), date(2026, 11, 28))
            )
        ).scalars()
    )
    assert con_cumple.id_cliente in ids_con_cupon
    assert fuera_de_rango.id_cliente not in ids_con_cupon
    assert anonimo.id_cliente not in ids_con_cupon

    generado = sesion.execute(
        select(Cupon).where(Cupon.id_cliente == con_cumple.id_cliente)
    ).scalar_one()
    assert generado.fecha_objetivo == date(2026, 11, 15)
    assert generado.valido_desde == date(2026, 11, 8)
    assert generado.valido_hasta == date(2026, 11, 29)
    assert generado.estado == "generado"


# --- T008 -------------------------------------------------------------------


def test_generacion_es_idempotente_por_cliente_y_fecha_objetivo(sesion):
    cli = crear_cliente_cumpleanos(
        sesion, nombre="Repite T008", fecha_nacimiento=date(1992, 10, 10)
    )

    primera = generar_cupones(sesion, desde=date(2026, 10, 1), hasta=date(2026, 10, 30))
    sesion.commit()
    segunda = generar_cupones(sesion, desde=date(2026, 10, 5), hasta=date(2026, 11, 5))
    sesion.commit()

    assert segunda["cupones_generados"] == 0
    assert segunda["cupones_ya_existentes"] >= 1

    total = sesion.execute(
        select(func.count()).select_from(Cupon).where(Cupon.id_cliente == cli.id_cliente)
    ).scalar_one()
    assert total == 1
    _ = primera  # la primera corrida creó el cupón; la segunda no lo duplicó


# --- T009 -----------------------------------------------------------------------


def _cupon_para(sesion, escenario, *, fecha_objetivo: date):
    cli = crear_cliente_cumpleanos(
        sesion,
        nombre=f"Redime {fecha_objetivo} {datetime.now(timezone.utc).timestamp()}",
        fecha_nacimiento=fecha_objetivo.replace(year=1991),
    )
    generar_cupones(
        sesion, desde=fecha_objetivo.replace(day=1), hasta=fecha_objetivo.replace(day=28)
    )
    sesion.commit()
    return sesion.execute(select(Cupon).where(Cupon.id_cliente == cli.id_cliente)).scalar_one()


def test_redencion_de_cupon_vigente_lo_marca_redimido_sin_tocar_001(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000)
    cupon = _cupon_para(sesion, escenario, fecha_objetivo=date(2026, 9, 15))
    venta = _venta(sesion, escenario, instante=datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc))

    mov_antes = sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
    exist_antes = sesion.execute(select(func.sum(Existencia.cantidad))).scalar_one()
    renglones_antes = sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one()

    redencion, creada = registrar_redencion(
        sesion, id_venta=venta.id_venta, tipo_origen="cupon", id_cupon=cupon.id_cupon
    )
    sesion.commit()

    assert creada is True
    sesion.refresh(cupon)
    assert cupon.estado == "redimido"
    assert redencion.id_sucursal == escenario["sucursal"].id_sucursal
    assert redencion.periodo == date(2026, 9, 15)

    assert (
        sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
        == mov_antes
    )
    assert sesion.execute(select(func.sum(Existencia.cantidad))).scalar_one() == exist_antes
    assert (
        sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one()
        == renglones_antes
    )


def test_redencion_fuera_de_la_ventana_de_validez_es_400(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000)
    cupon = _cupon_para(sesion, escenario, fecha_objetivo=date(2026, 9, 15))
    venta = _venta(sesion, escenario, instante=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))
    respuesta = cliente_http.post(
        "/promociones/redenciones",
        json={"id_venta": venta.id_venta, "tipo_origen": "cupon", "id_cupon": cupon.id_cupon},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "cupon_fuera_de_ventana"


def test_segundo_post_de_redencion_es_idempotente(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000)
    cupon = _cupon_para(sesion, escenario, fecha_objetivo=date(2026, 9, 15))
    venta = _venta(sesion, escenario, instante=datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc))
    cuerpo = {"id_venta": venta.id_venta, "tipo_origen": "cupon", "id_cupon": cupon.id_cupon}

    primera = cliente_http.post("/promociones/redenciones", json=cuerpo)
    segunda = cliente_http.post("/promociones/redenciones", json=cuerpo)

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert primera.json()["id_redencion_promocion"] == segunda.json()["id_redencion_promocion"]
