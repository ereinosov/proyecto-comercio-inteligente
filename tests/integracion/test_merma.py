"""Suite obligatoria 3 y 4 (006-caja-mermas-fraude, US2 — T019/T020/T021). Contra PostgreSQL real,
puerto 5442.

- T019 (rama libre ✓): `POST /caja/mermas` sin `id_conteo_renglon` registra la merma valorada al
  costo del lote FEFO, con `conciliar_con_conteo=true`, sin escribir en `existencia` (FR-012,
  FR-034); nunca lleva `id_operador` de imputación (FR-011); `GET /caja/mermas` desglosa y exige
  `id_sucursal` (FR-016, FR-038).
- T020: `GET /caja/alertas-caducidad` lista lotes de 001 en la ventana, marca los ya caducados,
  sin escribir nada (FR-014).
- T021 (rama de conteo): PRUEBA EN VERDE del `409 caja_bloqueado_por_001` (comportamiento
  controlado y esperado, tasks.md T023) + PRUEBA XFAIL del comportamiento eventual (201 clasificado)
  hasta que 001 implemente su User Story 5.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import (
    ConteoFisico,
    ConteoRenglon,
    Existencia,
    Merma,
    MovimientoInventario,
)
from tests.apoyo_caja import (
    crear_lote,
    crear_operador,
    crear_producto,
    crear_sucursal,
)

cliente = TestClient(app)


def _base(sesion, *, es_granel=False, costo="2.0000"):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion, es_granel=es_granel)
    operador = crear_operador(sesion)
    lote = crear_lote(
        sesion,
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo=costo,
    )
    sesion.commit()
    return sucursal, producto, operador, lote


# --- T019 ---------------------------------------------------------------------


def test_merma_libre_se_registra_valorada_y_no_toca_existencia(sesion):
    sucursal, producto, operador, lote = _base(sesion, costo="2.0000")
    exist_antes = sesion.execute(select(func.count()).select_from(Existencia)).scalar_one()
    mov_antes = sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()

    respuesta = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 3,
            "causa": "dano",
            "id_operador_registro": operador.id_operador,
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["valoracion"] == "6.00"
    assert cuerpo["conciliar_con_conteo"] is True
    assert cuerpo["estado"] == "clasificada"
    assert "id_operador" not in cuerpo  # FR-011: sin imputación a un operador
    assert cuerpo["id_operador_registro"] == operador.id_operador

    assert sesion.execute(select(func.count()).select_from(Existencia)).scalar_one() == exist_antes
    assert (
        sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
        == mov_antes
    )


def test_merma_sin_costo_de_lote_es_no_calculable_nunca_cero(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion)
    operador = crear_operador(sesion)
    sesion.commit()  # sin lote -> sin costo

    respuesta = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 4,
            "causa": "vencimiento",
            "id_operador_registro": operador.id_operador,
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["valoracion"] is None


def test_desglose_de_mermas_exige_sucursal(sesion):
    respuesta = cliente.get("/caja/mermas")
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "caja_sucursal_requerida"


def test_desglose_de_mermas_por_causa_y_sucursal(sesion):
    sucursal, producto, operador, lote = _base(sesion)
    for causa in ("dano", "vencimiento", "dano"):
        cliente.post(
            "/caja/mermas",
            json={
                "id_producto": producto.id_producto,
                "id_sucursal": sucursal.id_sucursal,
                "cantidad_faltante": 1,
                "causa": causa,
                "id_operador_registro": operador.id_operador,
            },
        )
    todas = cliente.get(f"/caja/mermas?id_sucursal={sucursal.id_sucursal}").json()
    assert len(todas["mermas"]) == 3
    solo_dano = cliente.get(
        f"/caja/mermas?id_sucursal={sucursal.id_sucursal}&causa=dano"
    ).json()
    assert len(solo_dano["mermas"]) == 2


# --- T020 -------------------------------------------------------------------


def test_alertas_de_caducidad_marca_los_ya_caducados_sin_escribir(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion)
    hoy = datetime.now(timezone.utc).date()
    lote_pronto = crear_lote(
        sesion,
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo="2.0000",
        fecha_caducidad=hoy + timedelta(days=3),
    )
    lote_caducado = crear_lote(
        sesion,
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo="2.0000",
        fecha_caducidad=hoy - timedelta(days=2),
    )
    lote_lejano = crear_lote(
        sesion,
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo="2.0000",
        fecha_caducidad=hoy + timedelta(days=90),
    )
    for lote in (lote_pronto, lote_caducado, lote_lejano):
        sesion.add(
            Existencia(
                id_sucursal=sucursal.id_sucursal,
                id_producto=producto.id_producto,
                id_lote=lote.id_lote,
                cantidad=Decimal("10"),
            )
        )
    sesion.commit()

    lotes_antes = sesion.execute(
        select(func.count()).select_from(Existencia).where(
            Existencia.id_sucursal == sucursal.id_sucursal
        )
    ).scalar_one()

    alertas = cliente.get(
        f"/caja/alertas-caducidad?id_sucursal={sucursal.id_sucursal}&dentro_de_dias=14"
    ).json()
    por_lote = {a["id_lote"]: a for a in alertas}
    assert lote_pronto.id_lote in por_lote
    assert lote_caducado.id_lote in por_lote
    assert lote_lejano.id_lote not in por_lote
    assert por_lote[lote_caducado.id_lote]["ya_caducado"] is True
    assert por_lote[lote_pronto.id_lote]["ya_caducado"] is False
    assert por_lote[lote_pronto.id_lote]["valor_en_riesgo"] == "20.00"

    assert (
        sesion.execute(
            select(func.count()).select_from(Existencia).where(
                Existencia.id_sucursal == sucursal.id_sucursal
            )
        ).scalar_one()
        == lotes_antes
    )


# --- T021 -----------------------------------------------------------------------


def _conteo_renglon(sesion, *, id_sucursal, id_producto, id_lote):
    conteo = ConteoFisico(
        id_sucursal=id_sucursal,
        estado="resuelto",
        alcance=None,
        instante_inicio=datetime.now(timezone.utc) - timedelta(days=1),
        instante_resolucion=datetime.now(timezone.utc),
    )
    sesion.add(conteo)
    sesion.flush()
    renglon = ConteoRenglon(
        id_conteo_fisico=conteo.id_conteo_fisico,
        id_producto=id_producto,
        id_lote=id_lote,
        cantidad_contada=Decimal("37"),
        cantidad_esperada=Decimal("40"),
        diferencia=Decimal("-3"),
    )
    sesion.add(renglon)
    sesion.commit()
    return renglon


def test_clasificar_diferencia_de_conteo_devuelve_409_bloqueado(sesion):
    """PRUEBA EN VERDE (T023): la rama con `id_conteo_renglon` está bloqueada por 001 User Story 5
    y devuelve `409 caja_bloqueado_por_001` — comportamiento controlado y esperado, NO un fallo.
    """
    sucursal, producto, operador, lote = _base(sesion)
    renglon = _conteo_renglon(sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto, id_lote=lote.id_lote)
    respuesta = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 3,
            "causa": "vencimiento",
            "id_operador_registro": operador.id_operador,
            "id_conteo_renglon": renglon.id_conteo_renglon,
        },
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "caja_bloqueado_por_001"


@pytest.mark.xfail(reason="bloqueado por 001 US5 T065-T071", strict=True)
def test_clasificar_diferencia_de_conteo_clasifica_la_merma(sesion):
    """XFAIL hasta que 001 implemente su User Story 5: entonces `POST /caja/mermas` con
    `id_conteo_renglon` debe clasificar la `diferencia` que 001 expone (201), sin recalcularla.
    """
    sucursal, producto, operador, lote = _base(sesion)
    renglon = _conteo_renglon(sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto, id_lote=lote.id_lote)
    respuesta = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 3,
            "causa": "vencimiento",
            "id_operador_registro": operador.id_operador,
            "id_conteo_renglon": renglon.id_conteo_renglon,
        },
    )
    assert respuesta.status_code == 201
    assert sesion.execute(
        select(Merma.id_conteo_renglon).where(
            Merma.id_conteo_renglon == renglon.id_conteo_renglon
        )
    ).scalar_one() == renglon.id_conteo_renglon
