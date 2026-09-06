"""Suite obligatoria 6 (007, US4 — T039). Bitácora de solo anexado, sin datos sensibles.
Contra PostgreSQL real, puerto 5442.

- append-only forzado por el MOTOR: un UPDATE / DELETE directo (rol de aplicación) es rechazado
  por el TRIGGER de la migración 0007 (FR-025, SC-012).

  DESVIACIÓN DOCUMENTADA de tasks.md T001: se usa un TRIGGER `BEFORE UPDATE OR DELETE` en vez de
  `REVOKE ... FROM rasero_app` porque en este entorno el rol de BD es `rasero` (dueño y
  superusuario en desarrollo), sobre el que un REVOKE no surte efecto. El trigger cumple la misma
  intención ("rechazo del motor") y la prueba de abajo lo verifica igual.

- cada hecho de pago genera una entrada con tipo/día local/sucursal/iniciador/resultado (SC-011).
- ninguna entrada contiene un PAN ni un CVV (FR-026).
- filtros por sucursal / terminal / tipo (FR-027).
"""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from rasero.api.aplicacion import app
from rasero.config import pagos as cfg
from rasero.dominio.token import es_luhn_valido
from tests.apoyo_pagos import (
    TARJETA_VISA,
    crear_operador,
    crear_sucursal,
    crear_terminal,
    crear_turno,
    crear_venta,
    escenario_cobro_con_tarjeta,
)

cliente = TestClient(app)
_MARCA = "2026-09-05T12:00:00+00:00"


@pytest.fixture
def firmware_config():
    ultima = dict(cfg.ULTIMA_VERSION_FIRMWARE)
    lista = list(cfg.LISTA_FIRMWARE_VULNERABLE)
    cfg.ULTIMA_VERSION_FIRMWARE.clear()
    cfg.ULTIMA_VERSION_FIRMWARE.update({"P400": "3.5.0"})
    yield
    cfg.ULTIMA_VERSION_FIRMWARE.clear()
    cfg.ULTIMA_VERSION_FIRMWARE.update(ultima)
    cfg.LISTA_FIRMWARE_VULNERABLE[:] = lista


def _tiene_pan(texto) -> bool:
    return texto is not None and any(
        es_luhn_valido(s) for s in re.findall(r"\d{13,19}", str(texto))
    )


def _id_medio(nombre: str) -> int:
    return next(m["id_medio_pago"] for m in cliente.get("/pagos/medios").json() if m["nombre"] == nombre)


def test_bitacora_es_solo_anexado_forzado_por_el_motor(sesion):
    sucursal = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    sesion.commit()
    cliente.post(
        "/pagos/intencion-no-atendida",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago_deseado": _id_medio("efectivo"),
            "id_operador": operador.id_operador,
            "clave_idempotencia": f"ap-{sucursal.id_sucursal}",
        },
    )

    with pytest.raises(DBAPIError):
        sesion.execute(
            text("UPDATE bitacora_auditoria SET resultado = 'alterado' WHERE id_sucursal = :s"),
            {"s": sucursal.id_sucursal},
        )
        sesion.flush()
    sesion.rollback()

    with pytest.raises(DBAPIError):
        sesion.execute(
            text("DELETE FROM bitacora_auditoria WHERE id_sucursal = :s"),
            {"s": sucursal.id_sucursal},
        )
        sesion.flush()
    sesion.rollback()

    # la entrada sigue ahí, intacta
    fila = sesion.execute(
        text("SELECT resultado FROM bitacora_auditoria WHERE id_sucursal = :s"),
        {"s": sucursal.id_sucursal},
    ).scalar_one()
    assert "alterado" not in fila


def test_cada_hecho_de_pago_genera_una_entrada_sin_datos_sensibles(sesion, firmware_config):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal, encargado, sucursal = esc["terminal"], esc["encargado"], esc["sucursal"]

    # emitir token
    turno = crear_turno(sesion, id_operador=encargado.id_operador, id_sucursal=sucursal.id_sucursal)
    venta = crear_venta(sesion, id_turno=turno.id_turno)
    sesion.commit()
    cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "clave_idempotencia": f"b-tok-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    # rechazar un PAN
    venta2 = crear_venta(sesion, id_turno=turno.id_turno)
    sesion.commit()
    cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta2.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "tipo": TARJETA_VISA,
            "clave_idempotencia": f"b-pan-{venta2.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    # actualizar firmware
    cliente.post(
        f"/pagos/terminales/{terminal.id_terminal_pago}/firmware",
        json={"version": "3.6.0", "fecha": "2026-09-05", "id_operador": encargado.id_operador},
    )
    # cambiar cobertura
    cliente.put(
        "/pagos/cobertura",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago": _id_medio("tarjeta_debito"),
            "acepta": True,
            "fecha_desde": "2026-01-01",
            "id_operador": encargado.id_operador,
        },
    )
    # intención no atendida
    cliente.post(
        "/pagos/intencion-no-atendida",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago_deseado": _id_medio("transferencia"),
            "id_operador": encargado.id_operador,
            "clave_idempotencia": f"b-ina-{sucursal.id_sucursal}",
        },
    )

    entradas = cliente.get(f"/pagos/bitacora?id_sucursal={sucursal.id_sucursal}").json()
    tipos = {e["tipo_evento"] for e in entradas}
    assert {
        "token_emitido",
        "pan_rechazado",
        "firmware_actualizado",
        "cobertura_declarada",
        "intencion_no_atendida",
        "terminal_registrada",
    } <= tipos
    for e in entradas:
        assert e["tipo_evento"] and e["dia_local"] and e["id_sucursal"] == sucursal.id_sucursal
        assert e["iniciador_tipo"] in ("operador", "proceso")
        assert e["resultado"]
        assert not _tiene_pan(e["resultado"]) and not _tiene_pan(e["referencia_recurso_id"])

    # barrido directo de toda la tabla
    for fila in sesion.execute(text("SELECT * FROM bitacora_auditoria")).mappings():
        assert not any(_tiene_pan(v) for v in fila.values())

    # filtros
    solo_token = cliente.get(
        f"/pagos/bitacora?id_sucursal={sucursal.id_sucursal}&tipo_evento=token_emitido"
    ).json()
    assert solo_token and all(e["tipo_evento"] == "token_emitido" for e in solo_token)
    por_terminal = cliente.get(
        f"/pagos/bitacora?id_sucursal={sucursal.id_sucursal}&id_terminal_pago={terminal.id_terminal_pago}"
    ).json()
    assert por_terminal and all(e["id_terminal_pago"] == terminal.id_terminal_pago for e in por_terminal)


def test_bitacora_exige_sucursal(sesion):
    assert cliente.get("/pagos/bitacora").status_code == 400
    assert cliente.get("/pagos/bitacora").json()["codigo"] == "pagos_sucursal_requerida"
