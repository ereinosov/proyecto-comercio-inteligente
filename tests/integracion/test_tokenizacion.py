"""Suites obligatorias 1–4 (007, US3 — T029/T030/T031/T032). Contra PostgreSQL real, puerto 5442.

- #1 (T029): el PAN nunca se persiste ni se expone — barrido de Luhn sobre columnas, bitácora y
  respuestas; `token_pago` guarda exactamente los campos mínimos; sin estabilidad entre ventas.
- #2 (T030): rechazo de PAN completo -> 400 + evento `pan_rechazado` SIN el número.
- #3 (T031): idempotencia con los 3 casos de research #15.
- #4 (T032): la tokenización no es camino crítico — 0 escrituras en `venta`/`turno`/`operador`.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from rasero.api.aplicacion import app
from rasero.dominio.token import es_luhn_valido
from rasero.persistencia.modelos import BitacoraAuditoria, Operador, TokenPago, Turno, Venta
from tests.apoyo_pagos import (
    TARJETA_INVALIDA_LUHN,
    TARJETA_MASTERCARD,
    TARJETA_VISA,
    crear_terminal,
    crear_operador,
    crear_sucursal,
    crear_turno,
    crear_venta,
    escenario_cobro_con_tarjeta,
)

cliente = TestClient(app)
_MARCA = datetime.now(timezone.utc).isoformat()


def _tiene_pan(texto) -> bool:
    if texto is None:
        return False
    import re

    return any(es_luhn_valido(s) for s in re.findall(r"\d{13,19}", str(texto)))


def _cobro(sesion, terminal):
    turno = crear_turno(
        sesion, id_operador=terminal.id_operador_registro, id_sucursal=terminal.id_sucursal
    )
    venta = crear_venta(sesion, id_turno=turno.id_turno)
    sesion.commit()
    return venta


# --- Suite obligatoria #1 (T029) --------------------------------------------


def test_el_pan_nunca_se_persiste_ni_se_expone(sesion):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal = esc["terminal"]
    respuestas = []
    for i in range(20):
        venta = _cobro(sesion, terminal)
        r = cliente.post(
            "/pagos/tokens",
            json={
                "id_venta": venta.id_venta,
                "id_terminal_pago": terminal.id_terminal_pago,
                "numero_tarjeta": TARJETA_VISA if i % 2 else TARJETA_MASTERCARD,
                "tipo": "credito",
                "clave_idempotencia": f"tok-{venta.id_venta}",
                "marca_tiempo_origen": _MARCA,
            },
        )
        assert r.status_code == 201, r.text
        respuestas.append(r.json())

    # barrido de las respuestas
    for cuerpo in respuestas:
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
        assert len(cuerpo["ultimos_digitos"]) == 4
        assert not any(_tiene_pan(v) for v in cuerpo.values())

    # barrido de TODAS las columnas de token_pago y bitacora_auditoria
    for fila in sesion.execute(text("SELECT * FROM token_pago")).mappings():
        assert not any(_tiene_pan(v) for v in fila.values()), fila
    for fila in sesion.execute(text("SELECT * FROM bitacora_auditoria")).mappings():
        assert not any(_tiene_pan(v) for v in fila.values()), fila

    # sin estabilidad entre ventas: misma tarjeta -> tokens distintos
    tokens_visa = [c["token"] for c, i in zip(respuestas, range(20)) if i % 2]
    assert len(set(tokens_visa)) == len(tokens_visa)

    # GET del pago nunca devuelve el número
    r = cliente.get(f"/pagos/ventas/{respuestas[0]['id_venta']}/pago")
    assert r.status_code == 200
    assert not any(_tiene_pan(v) for v in r.json().values())


# --- Suite obligatoria #2 (T030) -------------------------------------------


def test_rechazo_de_pan_en_un_campo_indebido_sin_registrar_el_numero(sesion):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal = esc["terminal"]
    venta = _cobro(sesion, terminal)

    r = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "tipo": TARJETA_MASTERCARD,  # un PAN en un campo que no corresponde
            "clave_idempotencia": f"tok-pan-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert r.status_code == 400
    assert r.json()["codigo"] == "pagos_pan_detectado"

    entradas = cliente.get(
        f"/pagos/bitacora?id_sucursal={terminal.id_sucursal}&tipo_evento=pan_rechazado"
    ).json()
    assert len(entradas) == 1
    assert not _tiene_pan(entradas[0]["resultado"])
    assert not _tiene_pan(entradas[0]["referencia_recurso_id"])
    # no se creó token
    assert sesion.execute(
        select(func.count()).select_from(TokenPago).where(TokenPago.id_venta == venta.id_venta)
    ).scalar() == 0


def test_numero_de_tarjeta_invalido_luhn(sesion):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal = esc["terminal"]
    venta = _cobro(sesion, terminal)
    r = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_INVALIDA_LUHN,
            "clave_idempotencia": f"tok-luhn-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert r.status_code == 400 and r.json()["codigo"] == "pagos_numero_tarjeta_invalido"


# --- Suite obligatoria #3 (T031) — los 3 casos de research #15 ------------


def test_idempotencia_tres_casos(sesion):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal = esc["terminal"]
    venta_a = _cobro(sesion, terminal)
    venta_b = _cobro(sesion, terminal)

    base = {
        "id_terminal_pago": terminal.id_terminal_pago,
        "numero_tarjeta": TARJETA_VISA,
        "marca_tiempo_origen": _MARCA,
    }

    # (a) misma id_venta + misma clave -> primer 201, luego 200 mismo token, una sola fila
    r1 = cliente.post("/pagos/tokens", json={**base, "id_venta": venta_a.id_venta, "clave_idempotencia": "k1"})
    assert r1.status_code == 201
    token = r1.json()["token"]
    for _ in range(9):
        rr = cliente.post("/pagos/tokens", json={**base, "id_venta": venta_a.id_venta, "clave_idempotencia": "k1"})
        assert rr.status_code == 200 and rr.json()["token"] == token
    assert sesion.execute(
        select(func.count()).select_from(TokenPago).where(TokenPago.id_venta == venta_a.id_venta)
    ).scalar() == 1

    # (b) misma id_venta + clave distinta -> 200 mismo token + token_idempotencia_divergente
    rb = cliente.post("/pagos/tokens", json={**base, "id_venta": venta_a.id_venta, "clave_idempotencia": "k2"})
    assert rb.status_code == 200 and rb.json()["token"] == token
    divergentes = cliente.get(
        f"/pagos/bitacora?id_sucursal={terminal.id_sucursal}&tipo_evento=token_idempotencia_divergente"
    ).json()
    assert len(divergentes) == 1

    # (c) clave reusada + otra id_venta -> 409
    rc = cliente.post("/pagos/tokens", json={**base, "id_venta": venta_b.id_venta, "clave_idempotencia": "k1"})
    assert rc.status_code == 409 and rc.json()["codigo"] == "pagos_clave_idempotencia_reusada"


# --- Suite obligatoria #4 (T032) — no camino crítico ---------------------


def test_tokenizacion_no_es_camino_critico_y_no_toca_001(sesion):
    esc = escenario_cobro_con_tarjeta(sesion)
    terminal = esc["terminal"]
    venta = _cobro(sesion, terminal)

    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar()
    turnos_antes = sesion.execute(select(func.count()).select_from(Turno)).scalar()
    operadores_antes = sesion.execute(select(func.count()).select_from(Operador)).scalar()

    # simular falla de tokenización: número inválido -> la venta de 001 no se toca
    r = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_INVALIDA_LUHN,
            "clave_idempotencia": f"tok-fail-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert r.status_code == 400

    # la venta existe y NO tiene tokenización
    g = cliente.get(f"/pagos/ventas/{venta.id_venta}/pago")
    assert g.status_code == 404 and g.json()["codigo"] == "pagos_venta_sin_tokenizacion"
    sesion.execute(select(Venta)).all()  # refresca
    assert sesion.get(Venta, venta.id_venta).referencia_terminal_pago is None

    # 0 escrituras en 001 (SC-013)
    assert sesion.execute(select(func.count()).select_from(Venta)).scalar() == ventas_antes
    assert sesion.execute(select(func.count()).select_from(Turno)).scalar() == turnos_antes
    assert sesion.execute(select(func.count()).select_from(Operador)).scalar() == operadores_antes

    # más tarde el cobro se procesa OK y la consulta pasa a 200
    ok = cliente.post(
        "/pagos/tokens",
        json={
            "id_venta": venta.id_venta,
            "id_terminal_pago": terminal.id_terminal_pago,
            "numero_tarjeta": TARJETA_VISA,
            "clave_idempotencia": f"tok-ok-{venta.id_venta}",
            "marca_tiempo_origen": _MARCA,
        },
    )
    assert ok.status_code == 201
    assert cliente.get(f"/pagos/ventas/{venta.id_venta}/pago").status_code == 200
