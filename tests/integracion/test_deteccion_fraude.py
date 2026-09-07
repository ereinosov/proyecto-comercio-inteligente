"""Suite obligatoria 5 y 2 (006-caja-mermas-fraude, US3 — T031/T032/T033). Contra PostgreSQL real,
puerto 5442.

- T031: `GET /caja/indicadores-operador` calcula tasa de anulaciones y concentración bajo precio de
  lista por operador; señala sólo al que se desvía de la mediana de pares; NUNCA dice "fraude"
  (FR-018, FR-019, FR-023, SC-007, SC-008). Un operador con pocas ventas -> `comparable=false`.
- T032: un arqueo con `diferencia = "0.00"` NO descarta el sub-registro: el indicador sigue
  señalando al operador (FR-008, FR-026, SC-004).
- T033: 001 implementó su User Story 5, así que `POST /caja/cruce-operador` ya ejerce la lógica
  real (200): reparte el faltante no explicado por turno y crea una `anomalia_caja` de origen
  inventario cuando queda faltante sin explicar; ya no devuelve `409 caja_bloqueado_por_001`.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from tests.apoyo import headers_encargado
from rasero.persistencia.sesion import SesionLocal
from rasero.persistencia.modelos import ConteoFisico, ConteoRenglon
from tests.apoyo_caja import (
    anular_venta,
    crear_operador,
    crear_producto,
    crear_sucursal,
    crear_turno,
    crear_venta,
)


# Rol de pantalla `encargado` (constitución v2.5.0): estas pantallas quedaron tras
# `exige_rol('encargado')`. Header por defecto del cliente; una llamada puntual puede
# sobreescribirlo con `headers=`.
_s_cab = SesionLocal()
_CAB_ENCARGADO = headers_encargado(_s_cab)
_s_cab.close()
cliente = TestClient(app, headers=_CAB_ENCARGADO)

_HOY = datetime.now(timezone.utc).date()
_DESDE = (_HOY - timedelta(days=2)).isoformat()
_HASTA = (_HOY + timedelta(days=2)).isoformat()


def _operador_con_actividad(
    sesion,
    *,
    id_sucursal: int,
    id_producto: int,
    nombre: str,
    n_ventas: int,
    n_anulaciones: int,
    n_bajo_lista: int = 0,
):
    operador = crear_operador(sesion, nombre=nombre)
    turno = crear_turno(
        sesion, id_operador=operador.id_operador, id_sucursal=id_sucursal
    )
    ventas = []
    for i in range(n_ventas):
        precio = "1.00" if i < n_bajo_lista else "3.00"
        ventas.append(
            crear_venta(
                sesion,
                id_turno=turno.id_turno,
                total=precio,
                instante=datetime.now(timezone.utc) - timedelta(hours=2),
                id_producto=id_producto,
                precio_aplicado=precio,
            )
        )
    for v in ventas[:n_anulaciones]:
        anular_venta(sesion, id_venta=v.id_venta, id_operador=operador.id_operador)
    sesion.commit()
    return operador, turno


# --- T031 ---------------------------------------------------------------------


def test_indicadores_senalan_al_operador_que_se_desvia_sin_decir_fraude(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion, precio="3.0000")
    op_a, _ = _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="A normal", n_ventas=40, n_anulaciones=1,
    )
    op_b, _ = _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="B atipico", n_ventas=40, n_anulaciones=8,
    )
    op_c, _ = _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="C normal", n_ventas=40, n_anulaciones=1,
    )
    op_d, _ = _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="D pocas ventas", n_ventas=8, n_anulaciones=2,
    )

    respuesta = cliente.get(
        f"/caja/indicadores-operador?id_sucursal={sucursal.id_sucursal}"
        f"&desde={_DESDE}&hasta={_HASTA}"
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    por_id = {o["id_operador"]: o for o in cuerpo["operadores"]}

    assert por_id[op_b.id_operador]["se_desvia"] is True
    assert por_id[op_b.id_operador]["detalle_desviacion"]
    assert por_id[op_a.id_operador]["se_desvia"] is False
    assert por_id[op_c.id_operador]["se_desvia"] is False

    # D no entra en la comparación por volumen insuficiente (UMBRAL_MINIMO_VENTAS_INDICADOR).
    assert por_id[op_d.id_operador]["comparable"] is False
    assert por_id[op_d.id_operador]["se_desvia"] is False

    # En NINGÚN campo de la respuesta aparece la palabra "fraude" (FR-023).
    assert "fraude" not in json.dumps(cuerpo, ensure_ascii=False).lower()


def test_indicadores_exigen_sucursal_y_rango_valido(sesion):
    assert cliente.get("/caja/indicadores-operador").status_code == 400
    r = cliente.get(
        f"/caja/indicadores-operador?id_sucursal=1&desde={_HASTA}&hasta={_DESDE}"
    )
    assert r.status_code == 400
    assert r.json()["codigo"] == "caja_rango_invalido"


# --- T032 -------------------------------------------------------------------


def test_arqueo_cuadrado_no_descarta_el_sub_registro(sesion):
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion, precio="3.0000")
    _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="Par normal 1", n_ventas=40, n_anulaciones=1,
    )
    _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="Par normal 2", n_ventas=40, n_anulaciones=1,
    )
    op_b, turno_b = _operador_con_actividad(
        sesion, id_sucursal=sucursal.id_sucursal, id_producto=producto.id_producto,
        nombre="B con arqueo cuadrado", n_ventas=40, n_anulaciones=9,
    )
    # Su arqueo cuadra exactamente: monto contado = SUM(venta.total) del turno = 40 × 3.00.
    arqueo = cliente.post(
        "/caja/arqueos",
        json={
            "id_turno": turno_b.id_turno,
            "monto_contado": "120.00",
            "marca_tiempo_origen": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert arqueo.status_code == 201
    assert arqueo.json()["diferencia"] == "0.00"
    assert arqueo.json()["genero_anomalia"] is False

    indicadores = cliente.get(
        f"/caja/indicadores-operador?id_sucursal={sucursal.id_sucursal}"
        f"&desde={_DESDE}&hasta={_HASTA}"
    ).json()
    por_id = {o["id_operador"]: o for o in indicadores["operadores"]}
    # El arqueo cuadró, pero el indicador sigue señalando a B.
    assert por_id[op_b.id_operador]["se_desvia"] is True


# --- T033 -----------------------------------------------------------------------


def test_cruce_operador_sin_conteo_resuelto_no_crea_nada(sesion):
    """`POST /caja/cruce-operador` ya no está bloqueado (001 User Story 5): si no hay ningún
    conteo físico resuelto en la sucursal, responde 200 sin crear ninguna anomalía.
    """
    sucursal = crear_sucursal(sesion)
    sesion.commit()
    respuesta = cliente.post(
        "/caja/cruce-operador",
        json={"id_sucursal": sucursal.id_sucursal, "desde": _DESDE, "hasta": _HASTA},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["anomalias_creadas"] == []
    assert cuerpo["id_conteo_fisico"] is None


def test_cruce_operador_crea_anomalia_de_inventario(sesion):
    """El cruce reparte el faltante no explicado por turno y crea una `anomalia_caja` de origen
    inventario (FR-020, FR-025). Un faltante que la merma clasificada explica por completo NO
    genera anomalía.
    """
    sucursal = crear_sucursal(sesion)
    producto = crear_producto(sesion, precio="3.0000")
    sesion.commit()

    # Conteo resuelto con un faltante bruto de 5 unidades, sin merma ni anulaciones que lo expliquen.
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
            cantidad_contada=Decimal("35"),
            cantidad_esperada=Decimal("40"),
            diferencia=Decimal("-5"),
        )
    )
    sesion.commit()

    respuesta = cliente.post(
        "/caja/cruce-operador",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "desde": _DESDE,
            "hasta": _HASTA,
            "id_conteo_fisico": conteo.id_conteo_fisico,
        },
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["anomalias_creadas"]) == 1

    anomalias = cliente.get(
        f"/caja/anomalias?id_sucursal={sucursal.id_sucursal}&origen=inventario"
    ).json()
    assert len(anomalias) == 1
    assert anomalias[0]["magnitud"] == 5
    assert anomalias[0]["origen"] == "inventario"
    assert anomalias[0]["indicador_snapshot"]["faltante_no_explicado"] == "5"
