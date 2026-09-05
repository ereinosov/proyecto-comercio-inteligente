"""Suite obligatoria 6 (US4, T049) — marca agregada de "promoción activa" para 004.
Contra PostgreSQL real, puerto 5442.

- Tras una redención de cupón (`id_producto = NULL`) y una de oferta de recompra (`id_producto`
  fijado) sobre ventas de 001, `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` devuelve
  cada `(id_producto, id_sucursal, periodo)` con su `tipo` (FR-031, FR-032, FR-035, SC-009).
- La redención de cupón se **expande** a todos los productos de su venta vía `renglon_venta`.
- Un producto sin redención en ese período no aparece.
- La consulta **exige** `id_sucursal` y nunca mezcla dos sucursales.
"""

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.apoyo_promociones import (
    _venta,
    crear_cliente_cumpleanos,
    crear_cliente_en_ventana_recompra,
    escenario_dos_productos,
)

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Cupon, OfertaRecompra
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.promociones import detectar_ofertas_recompra, generar_cupones

cliente_http = TestClient(app)

_HOY = date.today()


def _cupon_de_cumpleanos(sesion, escenario):
    """Un cliente cuyo cumpleaños cae hoy, con su cupón vigente ya generado."""
    cli = crear_cliente_cumpleanos(
        sesion,
        nombre=f"Marca cupón {datetime.now().timestamp()}",
        fecha_nacimiento=date(1990, _HOY.month, _HOY.day),
    )
    generar_cupones(sesion, desde=_HOY, hasta=_HOY)
    sesion.commit()
    return sesion.execute(select(Cupon).where(Cupon.id_cliente == cli.id_cliente)).scalar_one()


def test_marca_activa_agrega_los_origenes_y_expande_el_cupon(sesion):
    escenario = escenario_dos_productos(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto_1 = escenario["producto"].id_producto
    id_producto_2 = escenario["producto_2"].id_producto

    # --- redención de cupón (id_producto NULL) sobre una venta con producto_1 ---
    cupon = _cupon_de_cumpleanos(sesion, escenario)
    venta_cupon = _venta(
        sesion,
        escenario,
        instante=datetime.now(timezone.utc),
        id_producto=id_producto_1,
    )
    r1 = cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta_cupon.id_venta,
            "tipo_origen": "cupon",
            "id_cupon": cupon.id_cupon,
        },
    )
    assert r1.status_code == 201

    # --- redención de oferta de recompra (id_producto = producto_2) ---
    crear_cliente_en_ventana_recompra(
        sesion,
        escenario,
        nombre=f"Marca recompra {datetime.now().timestamp()}",
        id_producto=id_producto_2,
    )
    detectar_ofertas_recompra(sesion, id_sucursal=id_sucursal)
    sesion.commit()
    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto_2)
    ).scalar_one()
    venta_oferta = _venta(
        sesion,
        escenario,
        instante=datetime.now(timezone.utc),
        id_producto=id_producto_2,
    )
    r2 = cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta_oferta.id_venta,
            "tipo_origen": "oferta_recompra",
            "id_oferta_recompra": oferta.id_oferta_recompra,
        },
    )
    assert r2.status_code == 201

    # --- consulta de la marca ---
    respuesta = cliente_http.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": id_sucursal,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    marcas = {(m["id_producto"], m["periodo"]): set(m["tipos"]) for m in respuesta.json()}

    # El cupón (id_producto NULL) se expande al producto_1 de su venta.
    assert (id_producto_1, _HOY.isoformat()) in marcas
    assert "fecha_fija" in marcas[(id_producto_1, _HOY.isoformat())]
    # La oferta de recompra marca el producto_2.
    assert "recompra" in marcas[(id_producto_2, _HOY.isoformat())]
    # Toda fila es de esta sucursal.
    for m in respuesta.json():
        assert m["id_sucursal"] == id_sucursal


def test_producto_sin_redencion_no_aparece_y_sucursal_es_obligatoria(sesion):
    escenario = escenario_dos_productos(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto_2 = escenario["producto_2"].id_producto

    cupon = _cupon_de_cumpleanos(sesion, escenario)
    venta = _venta(
        sesion,
        escenario,
        instante=datetime.now(timezone.utc),
        id_producto=escenario["producto"].id_producto,
    )
    cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta.id_venta,
            "tipo_origen": "cupon",
            "id_cupon": cupon.id_cupon,
        },
    )

    respuesta = cliente_http.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": id_sucursal,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    marcas = {m["id_producto"] for m in respuesta.json()}
    assert id_producto_2 not in marcas  # nadie redimió nada de producto_2

    # id_sucursal es obligatorio.
    sin_sucursal = cliente_http.get(
        "/promociones/marca-activa",
        params={"desde": _HOY.isoformat(), "hasta": _HOY.isoformat()},
    )
    assert sin_sucursal.status_code == 422

    # Sucursal inexistente -> 404 con {codigo, mensaje}.
    inexistente = cliente_http.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": 999999,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    assert inexistente.status_code == 404
    assert set(inexistente.json()) >= {"codigo", "mensaje"}


def test_no_mezcla_dos_sucursales(sesion):
    escenario_a = escenario_dos_productos(sesion)
    escenario_b = escenario_dos_productos(sesion)
    id_producto_a = escenario_a["producto"].id_producto

    cupon = _cupon_de_cumpleanos(sesion, escenario_a)
    venta = _venta(
        sesion,
        escenario_a,
        instante=datetime.now(timezone.utc),
        id_producto=id_producto_a,
    )
    cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta.id_venta,
            "tipo_origen": "cupon",
            "id_cupon": cupon.id_cupon,
        },
    )

    en_b = cliente_http.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": escenario_b["sucursal"].id_sucursal,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    assert en_b.status_code == 200
    assert id_producto_a not in {m["id_producto"] for m in en_b.json()}
