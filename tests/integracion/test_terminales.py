"""Suite obligatoria 5 — integración (007, US2 — T018). Contra PostgreSQL real, puerto 5442.

- señales de firmware con motivo enumerado (FR-010, FR-011, SC-004).
- NINGUNA señal deshabilita la terminal (FR-012, SC-005).
- una terminal movida atribuye su señal a la sucursal del momento evaluado (FR-014).
- `GET /pagos/terminales` exige `id_sucursal` (FR-034).
"""

import pytest
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.config import pagos as cfg
from rasero.persistencia.modelos import TerminalPago
from tests.apoyo_pagos import crear_operador, crear_sucursal, crear_terminal

cliente = TestClient(app)


@pytest.fixture
def firmware_config():
    ultima = dict(cfg.ULTIMA_VERSION_FIRMWARE)
    lista = list(cfg.LISTA_FIRMWARE_VULNERABLE)
    cfg.ULTIMA_VERSION_FIRMWARE.clear()
    cfg.ULTIMA_VERSION_FIRMWARE.update({"P400": "3.2.0"})
    cfg.LISTA_FIRMWARE_VULNERABLE[:] = [
        {"modelo": "P400", "version": "3.0.1", "referencia": "CVE-2025-0001"}
    ]
    yield
    cfg.ULTIMA_VERSION_FIRMWARE.clear()
    cfg.ULTIMA_VERSION_FIRMWARE.update(ultima)
    cfg.LISTA_FIRMWARE_VULNERABLE[:] = lista


def test_indicadores_de_firmware_con_motivo_y_ninguna_deshabilita(sesion, firmware_config):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    for version, modelo in [
        ("3.2.0", "P400"),  # A: al día
        ("3.0.1", "P400"),  # B: expuesta + desactualizada
        ("2.9.0", "P400"),  # C: desactualizada
        ("1.4.0", "Move5000"),  # D: referencia desconocida
    ]:
        crear_terminal(
            sesion,
            id_sucursal=sucursal.id_sucursal,
            id_operador_encargado=encargado.id_operador,
            modelo=modelo,
            version_firmware=version,
        )
    sesion.commit()

    r = cliente.get(f"/pagos/terminales?id_sucursal={sucursal.id_sucursal}")
    assert r.status_code == 200
    por_version = {t["version_firmware"]: t for t in r.json()}

    a = por_version["3.2.0"]
    assert not a["desactualizada"] and not a["expuesta_a_clonacion"]

    b = por_version["3.0.1"]
    assert b["expuesta_a_clonacion"] is True
    assert b["referencias_vulnerabilidad"] == ["CVE-2025-0001"]
    assert b["desactualizada"] is True

    c = por_version["2.9.0"]
    assert c["desactualizada"] is True and c["expuesta_a_clonacion"] is False

    d = por_version["1.4.0"]
    assert d["version_referencia_desconocida"] is True
    assert d["desactualizada"] is False

    # NINGUNA queda inactiva por una señal (FR-012, SC-005)
    assert all(t["activa"] is True for t in r.json())
    for t in sesion.query(TerminalPago).all():
        assert t.activa is True


def test_lista_vulnerable_vacia_deja_solo_desactualizadas(sesion, firmware_config):
    cfg.LISTA_FIRMWARE_VULNERABLE[:] = []
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    crear_terminal(
        sesion,
        id_sucursal=sucursal.id_sucursal,
        id_operador_encargado=encargado.id_operador,
        modelo="P400",
        version_firmware="3.0.1",
    )
    sesion.commit()
    t = cliente.get(f"/pagos/terminales?id_sucursal={sucursal.id_sucursal}").json()[0]
    assert t["expuesta_a_clonacion"] is False
    assert t["desactualizada"] is True


def test_senal_se_atribuye_a_la_sucursal_del_momento(sesion, firmware_config):
    s1 = crear_sucursal(sesion)
    s2 = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    terminal = crear_terminal(
        sesion,
        id_sucursal=s1.id_sucursal,
        id_operador_encargado=encargado.id_operador,
        modelo="P400",
        version_firmware="3.0.1",
    )
    sesion.commit()

    # mover a s2
    r = cliente.patch(
        f"/pagos/terminales/{terminal.id_terminal_pago}",
        json={"id_sucursal_destino": s2.id_sucursal, "id_operador": encargado.id_operador},
    )
    assert r.status_code == 200, r.text

    en_s1 = cliente.get(f"/pagos/terminales?id_sucursal={s1.id_sucursal}").json()
    en_s2 = cliente.get(f"/pagos/terminales?id_sucursal={s2.id_sucursal}").json()
    assert [t["id_terminal_pago"] for t in en_s1] == []
    assert [t["id_terminal_pago"] for t in en_s2] == [terminal.id_terminal_pago]
    hist = en_s2[0]["historial_ubicacion"]
    assert len(hist) == 2 and hist[0]["hasta"] is not None and hist[1]["hasta"] is None


def test_get_terminales_exige_sucursal(sesion):
    assert cliente.get("/pagos/terminales").status_code == 400
    assert cliente.get("/pagos/terminales").json()["codigo"] == "pagos_sucursal_requerida"


def test_actualizar_firmware_reevalua_y_rechaza_retroceso(sesion, firmware_config):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    terminal = crear_terminal(
        sesion,
        id_sucursal=sucursal.id_sucursal,
        id_operador_encargado=encargado.id_operador,
        modelo="P400",
        version_firmware="3.0.1",
    )
    sesion.commit()

    r = cliente.post(
        f"/pagos/terminales/{terminal.id_terminal_pago}/firmware",
        json={"version": "3.2.0", "fecha": "2026-07-01", "id_operador": encargado.id_operador},
    )
    assert r.status_code == 200, r.text
    assert r.json()["desactualizada"] is False
    assert r.json()["expuesta_a_clonacion"] is False

    r = cliente.post(
        f"/pagos/terminales/{terminal.id_terminal_pago}/firmware",
        json={"version": "3.1.0", "fecha": "2026-08-01", "id_operador": encargado.id_operador},
    )
    assert r.status_code == 400 and r.json()["codigo"] == "pagos_version_no_avanza"
