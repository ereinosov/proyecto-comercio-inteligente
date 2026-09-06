"""Suite obligatoria 6 (006-caja-mermas-fraude, US4 — T042/T043/T044). Contra PostgreSQL real,
puerto 5442.

- T042: una anomalía de origen efectivo (de US1) aparece en `GET /caja/anomalias?estado=
  sin_explicacion`; una diferencia con motivo conocido -> 0 anomalías (FR-031, SC-010); el sistema
  NUNCA cierra una anomalía por el paso del tiempo (FR-029, SC-009).
- T043: `POST /caja/anomalias/{id}/resolucion` exige `id_operador`, registra el estado anterior en
  `historial` y pasa a `resuelta` (FR-030); un segundo POST -> `400 caja_anomalia_ya_resuelta`.
- T044: la anomalía de origen inventario (001 User Story 5 ya implementada): tras
  `POST /caja/cruce-operador`, aparece con su `magnitud` e `indicador_snapshot`.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import AnomaliaCaja, ConteoFisico, ConteoRenglon
from tests.apoyo_caja import crear_operador, crear_producto, crear_sucursal, escenario_arqueo

cliente = TestClient(app)
_MARCA = datetime.now(timezone.utc).isoformat()


def _anomalia_de_efectivo(sesion):
    sucursal, operador, turno, _v = escenario_arqueo(sesion, totales=["100.00"])
    respuesta = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "88.00", "marca_tiempo_origen": _MARCA},
    )
    assert respuesta.status_code == 201
    return sucursal, operador, respuesta.json()["id_anomalia_caja"]


# --- T042 ---------------------------------------------------------------------


def test_anomalia_de_efectivo_aparece_en_la_cola_sin_explicacion(sesion):
    sucursal, _op, id_anomalia = _anomalia_de_efectivo(sesion)
    cola = cliente.get(
        f"/caja/anomalias?id_sucursal={sucursal.id_sucursal}&estado=sin_explicacion"
    ).json()
    ids = {a["id_anomalia_caja"] for a in cola}
    assert id_anomalia in ids
    detalle = next(a for a in cola if a["id_anomalia_caja"] == id_anomalia)
    assert detalle["origen"] == "efectivo"
    assert detalle["monto"] == "-12.00"


def test_diferencia_con_motivo_no_genera_anomalia(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["100.00"])
    antes = sesion.execute(select(func.count()).select_from(AnomaliaCaja)).scalar_one()
    respuesta = cliente.post(
        "/caja/arqueos",
        json={
            "id_turno": turno.id_turno,
            "monto_contado": "97.00",
            "motivo_conocido": "pago no registrado",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert respuesta.status_code == 201
    despues = sesion.execute(select(func.count()).select_from(AnomaliaCaja)).scalar_one()
    assert despues == antes


def test_el_sistema_nunca_cierra_una_anomalia_por_el_paso_del_tiempo(sesion):
    _s, _op, id_anomalia = _anomalia_de_efectivo(sesion)
    # No existe ninguna tarea, disparador ni consulta de 006 que cierre una anomalía (FR-029).
    # Consultarla y listarla no la altera.
    for _ in range(3):
        cliente.get(f"/caja/anomalias/{id_anomalia}")
        cliente.get("/caja/anomalias?id_sucursal=1")
    anomalia = sesion.get(AnomaliaCaja, id_anomalia)
    sesion.refresh(anomalia)
    assert anomalia.estado == "sin_explicacion"
    assert anomalia.id_operador_resolucion is None
    assert anomalia.instante_resolucion is None


# --- T043 -------------------------------------------------------------------


def test_resolucion_por_una_persona_registra_historial_y_estado(sesion):
    _s, _op, id_anomalia = _anomalia_de_efectivo(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()

    respuesta = cliente.post(
        f"/caja/anomalias/{id_anomalia}/resolucion",
        json={
            "resolucion": "error operativo confirmado",
            "id_operador": encargado.id_operador,
            "nota": "faltó registrar un cambio",
        },
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "resuelta"
    assert cuerpo["resolucion"] == "error operativo confirmado"
    assert cuerpo["id_operador_resolucion"] == encargado.id_operador
    assert cuerpo["instante_resolucion"] is not None
    # El historial conserva el estado anterior (FR-030).
    ultima = cuerpo["historial"][-1]
    assert ultima["estado"] == "resuelta"
    assert ultima["estado_anterior"] == "sin_explicacion"
    assert ultima["id_operador"] == encargado.id_operador

    # Segundo POST -> 400.
    otra = cliente.post(
        f"/caja/anomalias/{id_anomalia}/resolucion",
        json={"resolucion": "otra cosa", "id_operador": encargado.id_operador},
    )
    assert otra.status_code == 400
    assert otra.json()["codigo"] == "caja_anomalia_ya_resuelta"


def test_resolucion_vacia_es_400(sesion):
    _s, _op, id_anomalia = _anomalia_de_efectivo(sesion)
    encargado = crear_operador(sesion)
    sesion.commit()
    respuesta = cliente.post(
        f"/caja/anomalias/{id_anomalia}/resolucion",
        json={"resolucion": "   ", "id_operador": encargado.id_operador},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "caja_resolucion_vacia"


# --- T044 -----------------------------------------------------------------------


def test_anomalia_de_inventario_tras_el_cruce(sesion):
    """Tras `POST /caja/cruce-operador`, una anomalía de origen inventario aparece con su
    `magnitud` e `indicador_snapshot`, en estado `sin_explicacion` (001 User Story 5).
    """
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion)
    conteo = ConteoFisico(
        id_sucursal=sucursal.id_sucursal,
        estado="resuelto",
        alcance=None,
        instante_inicio=datetime.now(timezone.utc) - timedelta(days=1),
        instante_resolucion=datetime.now(timezone.utc),
    )
    sesion.add(conteo)
    sesion.flush()
    sesion.add(
        ConteoRenglon(
            id_conteo_fisico=conteo.id_conteo_fisico,
            id_producto=producto.id_producto,
            id_lote=None,
            cantidad_contada=Decimal("18"),
            cantidad_esperada=Decimal("25"),
            diferencia=Decimal("-7"),
        )
    )
    sesion.commit()

    respuesta = cliente.post(
        "/caja/cruce-operador",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
        },
    )
    assert respuesta.status_code == 200

    anomalias = cliente.get(
        f"/caja/anomalias?id_sucursal={sucursal.id_sucursal}&origen=inventario"
    ).json()
    assert len(anomalias) == 1
    assert anomalias[0]["magnitud"] == 7
    assert anomalias[0]["estado"] == "sin_explicacion"
    assert anomalias[0]["indicador_snapshot"] is not None
    assert anomalias[0]["historial"][0]["estado"] == "sin_explicacion"
