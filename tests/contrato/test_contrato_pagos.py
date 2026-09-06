"""Prueba obligatoria de contrato (Principio III) de 007-pagos-seguridad contra
`specs/007-pagos-seguridad/contracts/openapi.yaml`. Contra PostgreSQL real, puerto 5442.

Cubre las cuatro historias (T013 cobertura; T024 terminales; T037 tokenización; T043 bitácora) en
su forma feliz y en sus modos de fallo declarados, siempre con el formato de error unificado
`{codigo, mensaje}`. Verifica además que:
  - la respuesta de `POST /pagos/tokens` NO contiene `numero_tarjeta` (writeOnly, FR-017).
  - NO existe ningún endpoint que modifique o borre la bitácora (FR-025).
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.config import pagos as cfg
from tests.apoyo_pagos import (
    TARJETA_VISA,
    crear_operador,
    crear_sucursal,
    crear_terminal,
    crear_turno,
    crear_venta,
)

cliente = TestClient(app)
_MARCA = datetime.now(timezone.utc).isoformat()


def _error(r):
    assert r.headers["content-type"].startswith("application/json")
    cuerpo = r.json()
    assert set(cuerpo) == {"codigo", "mensaje"}
    assert isinstance(cuerpo["codigo"], str) and isinstance(cuerpo["mensaje"], str)
    return cuerpo["codigo"]


def _id_medio(nombre):
    return next(m["id_medio_pago"] for m in cliente.get("/pagos/medios").json() if m["nombre"] == nombre)


# --- Cobertura (T013) ------------------------------------------------------


def test_contrato_cobertura(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    no_encargado = crear_operador(sesion, es_encargado=False)
    sesion.commit()
    debito = _id_medio("tarjeta_debito")

    medios = cliente.get("/pagos/medios")
    assert medios.status_code == 200
    assert {"id_medio_pago", "nombre", "requiere_terminal", "admite_tokenizacion", "activo"} <= set(
        medios.json()[0]
    )

    r = cliente.put(
        "/pagos/cobertura",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago": debito,
            "acepta": True,
            "fecha_desde": "2026-02-01",
            "id_operador": encargado.id_operador,
        },
    )
    assert r.status_code == 200
    assert {"id_cobertura_pago", "id_medio_pago", "id_sucursal", "fecha_desde", "fecha_hasta"} <= set(
        r.json()
    )

    assert _error(cliente.get("/pagos/cobertura")) == "pagos_sucursal_requerida"
    assert (
        _error(
            cliente.put(
                "/pagos/cobertura",
                json={
                    "id_sucursal": sucursal.id_sucursal,
                    "id_medio_pago": debito,
                    "acepta": True,
                    "fecha_desde": "2026-03-01",
                    "id_operador": no_encargado.id_operador,
                },
            )
        )
        == "pagos_operador_no_encargado"
    )
    assert (
        _error(
            cliente.put(
                "/pagos/cobertura",
                json={
                    "id_sucursal": sucursal.id_sucursal,
                    "id_medio_pago": 999999,
                    "acepta": True,
                    "fecha_desde": "2026-03-01",
                    "id_operador": encargado.id_operador,
                },
            )
        )
        == "pagos_medio_no_existe"
    )

    ok = cliente.post(
        "/pagos/intencion-no-atendida",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago_deseado": debito,
            "id_operador": encargado.id_operador,
            "clave_idempotencia": f"c-ina-{sucursal.id_sucursal}",
        },
    )
    assert ok.status_code == 201
    r2 = cliente.post(
        "/pagos/intencion-no-atendida",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago_deseado": debito,
            "id_operador": encargado.id_operador,
            "clave_idempotencia": f"c-ina-{sucursal.id_sucursal}",
        },
    )
    assert r2.status_code == 200


# --- Terminales (T024) ---------------------------------------------------


def test_contrato_terminales(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    no_encargado = crear_operador(sesion, es_encargado=False)
    sesion.commit()

    r = cliente.post(
        "/pagos/terminales",
        json={
            "identificador": "CONTRATO-1",
            "modelo": "P400",
            "id_sucursal": sucursal.id_sucursal,
            "version_firmware": "3.2.0",
            "id_operador": encargado.id_operador,
        },
    )
    assert r.status_code == 201
    campos = {
        "id_terminal_pago",
        "identificador",
        "modelo",
        "id_sucursal",
        "version_firmware",
        "desactualizada",
        "expuesta_a_clonacion",
        "version_referencia_desconocida",
        "referencias_vulnerabilidad",
        "activa",
    }
    assert campos <= set(r.json())
    id_terminal = r.json()["id_terminal_pago"]

    assert (
        _error(
            cliente.post(
                "/pagos/terminales",
                json={
                    "identificador": "CONTRATO-2",
                    "modelo": "P400",
                    "id_sucursal": sucursal.id_sucursal,
                    "version_firmware": "3-2-0",
                    "id_operador": encargado.id_operador,
                },
            )
        )
        == "pagos_version_firmware_invalida"
    )
    assert (
        _error(
            cliente.post(
                "/pagos/terminales",
                json={
                    "identificador": "CONTRATO-1",
                    "modelo": "P400",
                    "id_sucursal": sucursal.id_sucursal,
                    "version_firmware": "3.2.0",
                    "id_operador": encargado.id_operador,
                },
            )
        )
        == "pagos_identificador_duplicado"
    )
    assert (
        _error(
            cliente.post(
                "/pagos/terminales",
                json={
                    "identificador": "CONTRATO-3",
                    "modelo": "P400",
                    "id_sucursal": sucursal.id_sucursal,
                    "version_firmware": "3.2.0",
                    "id_operador": no_encargado.id_operador,
                },
            )
        )
        == "pagos_operador_no_encargado"
    )

    assert _error(cliente.get("/pagos/terminales")) == "pagos_sucursal_requerida"
    assert cliente.get(f"/pagos/terminales?id_sucursal={sucursal.id_sucursal}").status_code == 200

    assert (
        _error(
            cliente.post(
                f"/pagos/terminales/{id_terminal}/firmware",
                json={"version": "3.1.0", "fecha": "2026-07-01", "id_operador": encargado.id_operador},
            )
        )
        == "pagos_version_no_avanza"
    )
    assert cliente.patch("/pagos/terminales/999999", json={"id_operador": encargado.id_operador}).status_code == 404


# --- Tokenización (T037) -----------------------------------------------


def test_contrato_tokens(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    terminal = crear_terminal(
        sesion, id_sucursal=sucursal.id_sucursal, id_operador_encargado=encargado.id_operador
    )
    turno = crear_turno(sesion, id_operador=encargado.id_operador, id_sucursal=sucursal.id_sucursal)
    venta = crear_venta(sesion, id_turno=turno.id_turno)
    sesion.commit()

    r = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "tipo": "credito",
            "clave_idempotencia": f"ct-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert r.status_code == 201
    cuerpo = r.json()
    # writeOnly: la respuesta NO contiene numero_tarjeta ni ningún campo de PAN (FR-017)
    assert "numero_tarjeta" not in cuerpo
    assert set(cuerpo) == {
        "token",
        "id_venta",
        "ultimos_digitos",
        "marca",
        "tipo",
        "id_terminal_pago",
        "id_sucursal",
        "instante",
        "dia_local",
    }

    r2 = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "clave_idempotencia": f"ct-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert r2.status_code == 200

    v2 = crear_venta(sesion, id_turno=turno.id_turno)
    sesion.commit()
    assert (
        _error(
            cliente.post(
                "/pagos/tokens",
                json={
                    "id_venta": v2.id_venta,
                    "id_terminal_pago": terminal.id_terminal_pago,
                    "numero_tarjeta": TARJETA_VISA,
                    "clave_idempotencia": f"ct-{venta.id_venta}",
                    "marca_tiempo_origen": _MARCA,
                },
            )
        )
        == "pagos_clave_idempotencia_reusada"
    )
    assert (
        _error(
            cliente.post(
                "/pagos/tokens",
                json={
                    "id_venta": 999999,
                    "id_terminal_pago": terminal.id_terminal_pago,
                    "numero_tarjeta": TARJETA_VISA,
                    "clave_idempotencia": f"ct-missing-{venta.id_venta}",
                    "marca_tiempo_origen": _MARCA,
                },
            )
        )
        == "pagos_venta_no_existe"
    )

    assert cliente.get(f"/pagos/ventas/{venta.id_venta}/pago").status_code == 200
    assert _error(cliente.get("/pagos/ventas/999999/pago")) == "pagos_venta_no_existe"
    assert _error(cliente.get(f"/pagos/ventas/{v2.id_venta}/pago")) == "pagos_venta_sin_tokenizacion"


# --- Bitácora (T043) --------------------------------------------------


def test_contrato_bitacora(sesion):
    assert _error(cliente.get("/pagos/bitacora")) == "pagos_sucursal_requerida"
    sucursal = crear_sucursal(sesion)
    sesion.commit()
    r = cliente.get(f"/pagos/bitacora?id_sucursal={sucursal.id_sucursal}")
    # Listado paginado: { items, total } (schema RespuestaPaginada).
    assert r.status_code == 200 and isinstance(r.json()["items"], list)
    assert (
        _error(
            cliente.get(
                f"/pagos/bitacora?id_sucursal={sucursal.id_sucursal}&desde=2026-06-01&hasta=2026-01-01"
            )
        )
        == "pagos_rango_invalido"
    )


def test_no_hay_endpoint_de_edicion_ni_borrado_de_bitacora():
    esquema = cliente.get("/openapi.json").json()
    rutas_bitacora = {
        ruta: list(metodos)
        for ruta, metodos in esquema["paths"].items()
        if "/pagos/bitacora" in ruta
    }
    for metodos in rutas_bitacora.values():
        assert set(m.lower() for m in metodos) <= {"get"}


def test_openapi_yaml_del_contrato_coincide_en_rutas():
    """Las rutas de `contracts/openapi.yaml` existen en la app."""
    import pathlib

    import yaml

    ruta = (
        pathlib.Path(__file__).resolve().parents[2]
        / "specs"
        / "007-pagos-seguridad"
        / "contracts"
        / "openapi.yaml"
    )
    contrato = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    app_paths = set(cliente.get("/openapi.json").json()["paths"])
    for p in contrato["paths"]:
        assert p in app_paths, p
