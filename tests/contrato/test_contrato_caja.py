"""Prueba obligatoria de contrato (Principio III) de 006-caja-mermas-fraude contra
`specs/006-caja-mermas-fraude/contracts/openapi.yaml`. Contra PostgreSQL real, puerto 5442.

Cubre las cuatro historias (T014 arqueos; T026 mermas + alertas; T038 indicadores + cruce;
T047 anomalías) en su forma feliz y en sus modos de fallo declarados, siempre con el formato de
error unificado `{codigo, mensaje}`.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from decimal import Decimal

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import ConteoFisico, ConteoRenglon
from tests.apoyo_caja import (
    crear_lote,
    crear_operador,
    crear_producto,
    crear_sucursal,
    escenario_arqueo,
)

cliente = TestClient(app)
_MARCA = datetime.now(timezone.utc).isoformat()
_HOY = datetime.now(timezone.utc).date()
_DESDE = (_HOY - timedelta(days=2)).isoformat()
_HASTA = (_HOY + timedelta(days=2)).isoformat()

CLAVES_ARQUEO = (
    "id_arqueo",
    "id_turno",
    "id_operador",
    "id_sucursal",
    "dia_local",
    "monto_esperado",
    "monto_contado",
    "diferencia",
    "genero_anomalia",
    "ajustes",
    "instante_cierre_arqueo",
)
CLAVES_MERMA = (
    "id_merma",
    "id_conteo_renglon",
    "id_producto",
    "id_sucursal",
    "cantidad_faltante",
    "causa",
    "valoracion",
    "periodo_desde",
    "periodo_hasta",
    "estado",
    "conciliar_con_conteo",
    "id_operador_registro",
    "instante_registro",
)
CLAVES_ANOMALIA = (
    "id_anomalia_caja",
    "origen",
    "estado",
    "id_sucursal",
    "dia_local",
    "historial",
    "instante_deteccion",
)


def _error_bien_formado(respuesta, codigo: str):
    assert respuesta.headers["content-type"].startswith("application/json")
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"codigo", "mensaje"}
    assert cuerpo["codigo"] == codigo
    assert isinstance(cuerpo["mensaje"], str) and cuerpo["mensaje"]


# --- Arqueos (T014) ----------------------------------------------------------


def test_contrato_arqueo_feliz_e_idempotencia(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["10.00", "5.00"])
    cuerpo = {"id_turno": turno.id_turno, "monto_contado": "15.00", "marca_tiempo_origen": _MARCA}
    primera = cliente.post("/caja/arqueos", json=cuerpo)
    assert primera.status_code == 201
    assert set(CLAVES_ARQUEO).issubset(primera.json())
    segunda = cliente.post("/caja/arqueos", json=cuerpo)
    assert segunda.status_code == 200
    assert segunda.json()["id_arqueo"] == primera.json()["id_arqueo"]

    detalle = cliente.get(f"/caja/arqueos/{primera.json()['id_arqueo']}")
    assert detalle.status_code == 200
    lista = cliente.get(f"/caja/arqueos?id_sucursal={_s.id_sucursal}")
    assert lista.status_code == 200 and isinstance(lista.json(), list)

    ajuste = cliente.patch(
        f"/caja/arqueos/{primera.json()['id_arqueo']}",
        json={"monto_contado_nuevo": "15.50", "id_operador": turno.id_operador, "nota": "recuento"},
    )
    assert ajuste.status_code == 200
    assert len(ajuste.json()["ajustes"]) == 1


def test_contrato_arqueo_modos_de_fallo(sesion):
    _error_bien_formado(
        cliente.post(
            "/caja/arqueos",
            json={"id_turno": 999999, "monto_contado": "1.00", "marca_tiempo_origen": _MARCA},
        ),
        "caja_turno_no_existe",
    )
    _error_bien_formado(cliente.get("/caja/arqueos"), "caja_sucursal_requerida")
    _error_bien_formado(cliente.get("/caja/arqueos/999999"), "caja_arqueo_no_existe")


# --- Mermas y alertas de caducidad (T026) ----------------------------------


def test_contrato_merma_feliz_y_fallos(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion)
    operador = crear_operador(sesion)
    crear_lote(
        sesion, id_producto=producto.id_producto, id_sucursal=sucursal.id_sucursal, costo="2.0000"
    )
    sesion.commit()

    feliz = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 2,
            "causa": "dano",
            "id_operador_registro": operador.id_operador,
        },
    )
    assert feliz.status_code == 201
    assert set(CLAVES_MERMA).issubset(feliz.json())

    _error_bien_formado(
        cliente.post(
            "/caja/mermas",
            json={
                "id_producto": producto.id_producto,
                "id_sucursal": sucursal.id_sucursal,
                "cantidad_faltante": 0,
                "causa": "dano",
                "id_operador_registro": operador.id_operador,
            },
        ),
        "caja_cantidad_invalida",
    )
    _error_bien_formado(
        cliente.post(
            "/caja/mermas",
            json={
                "id_producto": 999999,
                "id_sucursal": sucursal.id_sucursal,
                "cantidad_faltante": 1,
                "causa": "dano",
                "id_operador_registro": operador.id_operador,
            },
        ),
        "caja_producto_no_existe",
    )
    # Rama con id_conteo_renglon: clasifica la diferencia bruta que 001 expone (201).
    ahora = datetime.now(timezone.utc)
    conteo = ConteoFisico(
        id_sucursal=sucursal.id_sucursal,
        estado="resuelto",
        alcance=None,
        instante_inicio=ahora,
        instante_resolucion=ahora,
    )
    sesion.add(conteo)
    sesion.flush()
    renglon = ConteoRenglon(
        id_conteo_fisico=conteo.id_conteo_fisico,
        id_producto=producto.id_producto,
        id_lote=None,
        cantidad_contada=Decimal("9"),
        cantidad_esperada=Decimal("12"),
        diferencia=Decimal("-3"),
    )
    sesion.add(renglon)
    sesion.commit()
    rama_conteo = cliente.post(
        "/caja/mermas",
        json={
            "id_producto": producto.id_producto,
            "id_sucursal": sucursal.id_sucursal,
            "cantidad_faltante": 1,
            "causa": "dano",
            "id_operador_registro": operador.id_operador,
            "id_conteo_renglon": renglon.id_conteo_renglon,
        },
    )
    assert rama_conteo.status_code == 201
    assert set(CLAVES_MERMA).issubset(rama_conteo.json())
    assert rama_conteo.json()["id_conteo_renglon"] == renglon.id_conteo_renglon

    desglose = cliente.get(f"/caja/mermas?id_sucursal={sucursal.id_sucursal}")
    assert desglose.status_code == 200
    assert {"total_valorado", "con_valor_no_calculable", "mermas"} <= set(desglose.json())

    alertas = cliente.get(f"/caja/alertas-caducidad?id_sucursal={sucursal.id_sucursal}")
    assert alertas.status_code == 200 and isinstance(alertas.json(), list)


# --- Indicadores y cruce (T038) ------------------------------------------


def test_contrato_indicadores_y_cruce(sesion):
    sucursal = crear_sucursal(sesion)
    sesion.commit()
    indic = cliente.get(
        f"/caja/indicadores-operador?id_sucursal={sucursal.id_sucursal}"
        f"&desde={_DESDE}&hasta={_HASTA}"
    )
    assert indic.status_code == 200
    assert {"periodo", "operadores", "factor_desviacion_anulaciones"} <= set(indic.json())

    _error_bien_formado(cliente.get("/caja/indicadores-operador"), "caja_sucursal_requerida")

    cruce = cliente.post(
        "/caja/cruce-operador",
        json={"id_sucursal": sucursal.id_sucursal, "desde": _DESDE, "hasta": _HASTA},
    )
    assert cruce.status_code == 200
    assert {"id_conteo_fisico", "anomalias_creadas", "detalle"} <= set(cruce.json())

    _error_bien_formado(
        cliente.post(
            "/caja/cruce-operador",
            json={"id_sucursal": sucursal.id_sucursal, "desde": _HASTA, "hasta": _DESDE},
        ),
        "caja_rango_invalido",
    )


# --- Anomalías (T047) -------------------------------------------------------


def test_contrato_anomalias(sesion):
    _s, _o, turno, _v = escenario_arqueo(sesion, totales=["50.00"])
    arqueo = cliente.post(
        "/caja/arqueos",
        json={"id_turno": turno.id_turno, "monto_contado": "40.00", "marca_tiempo_origen": _MARCA},
    )
    id_anomalia = arqueo.json()["id_anomalia_caja"]

    lista = cliente.get(f"/caja/anomalias?id_sucursal={_s.id_sucursal}")
    assert lista.status_code == 200 and isinstance(lista.json(), list)

    detalle = cliente.get(f"/caja/anomalias/{id_anomalia}")
    assert detalle.status_code == 200
    assert set(CLAVES_ANOMALIA).issubset(detalle.json())

    _error_bien_formado(cliente.get("/caja/anomalias/999999"), "caja_anomalia_no_existe")
    _error_bien_formado(
        cliente.post(
            f"/caja/anomalias/{id_anomalia}/resolucion",
            json={"resolucion": "x", "id_operador": 999999},
        ),
        "caja_operador_no_existe",
    )

    encargado = crear_operador(sesion)
    sesion.commit()
    resuelta = cliente.post(
        f"/caja/anomalias/{id_anomalia}/resolucion",
        json={"resolucion": "ajuste aceptado", "id_operador": encargado.id_operador},
    )
    assert resuelta.status_code == 200
    assert resuelta.json()["estado"] == "resuelta"
    _error_bien_formado(
        cliente.post(
            f"/caja/anomalias/{id_anomalia}/resolucion",
            json={"resolucion": "otra", "id_operador": encargado.id_operador},
        ),
        "caja_anomalia_ya_resuelta",
    )
