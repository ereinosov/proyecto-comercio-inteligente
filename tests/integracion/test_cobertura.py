"""Suite obligatoria 7 (007, US1 — T008). Cobertura por sucursal, nunca faltante de inventario.
Contra PostgreSQL real, puerto 5442.

- un evento de intención no atendida NO crea `venta` ni `consulta_no_atendida` de 001 (FR-005).
- `GET /pagos/cobertura` exige `id_sucursal` y nunca mezcla dos sucursales (FR-006).
- la cobertura de un período pasado refleja el estado de entonces (FR-002, SC-001).
"""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import CoberturaPago, ConsultaNoAtendida, MedioPago, Venta
from tests.apoyo_pagos import crear_operador, crear_sucursal

cliente = TestClient(app)


def _id_medio(nombre: str) -> int:
    for m in cliente.get("/pagos/medios").json():
        if m["nombre"] == nombre:
            return m["id_medio_pago"]
    raise AssertionError(nombre)


def test_intencion_no_atendida_no_crea_venta_ni_consulta_no_atendida(sesion):
    sucursal = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    sesion.commit()

    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar()
    cna_antes = sesion.execute(select(func.count()).select_from(ConsultaNoAtendida)).scalar()

    for i in range(3):
        r = cliente.post(
            "/pagos/intencion-no-atendida",
            json={
                "id_sucursal": sucursal.id_sucursal,
                "id_medio_pago_deseado": _id_medio("transferencia"),
                "id_operador": operador.id_operador,
                "clave_idempotencia": f"ina-{sucursal.id_sucursal}-{i}",
            },
        )
        assert r.status_code == 201, r.text

    assert sesion.execute(select(func.count()).select_from(Venta)).scalar() == ventas_antes
    assert (
        sesion.execute(select(func.count()).select_from(ConsultaNoAtendida)).scalar() == cna_antes
    )

    resumen = cliente.get(f"/pagos/cobertura?id_sucursal={sucursal.id_sucursal}").json()
    medio = next(m for m in resumen["medios"] if m["nombre"] == "transferencia")
    assert medio["intencion_no_atendida"] == 3
    assert resumen["total_intencion_no_atendida"] == 3
    # cuota sobre el total del período
    assert medio["cuota_no_atendida"] == "1.0000"


def test_intencion_no_atendida_es_idempotente_por_clave(sesion):
    sucursal = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    sesion.commit()
    cuerpo = {
        "id_sucursal": sucursal.id_sucursal,
        "id_medio_pago_deseado": _id_medio("tarjeta_credito"),
        "id_operador": operador.id_operador,
        "clave_idempotencia": f"ina-idem-{sucursal.id_sucursal}",
    }
    r1 = cliente.post("/pagos/intencion-no-atendida", json=cuerpo)
    r2 = cliente.post("/pagos/intencion-no-atendida", json=cuerpo)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["id_bitacora_auditoria"] == r2.json()["id_bitacora_auditoria"]


def test_cobertura_exige_sucursal_y_no_mezcla(sesion):
    s1 = crear_sucursal(sesion)
    s2 = crear_sucursal(sesion)
    operador = crear_operador(sesion)
    sesion.commit()
    cliente.post(
        "/pagos/intencion-no-atendida",
        json={
            "id_sucursal": s1.id_sucursal,
            "id_medio_pago_deseado": _id_medio("tarjeta_debito"),
            "id_operador": operador.id_operador,
            "clave_idempotencia": f"ina-mix-{s1.id_sucursal}",
        },
    )

    assert cliente.get("/pagos/cobertura").status_code == 400
    assert cliente.get("/pagos/cobertura").json()["codigo"] == "pagos_sucursal_requerida"

    r1 = cliente.get(f"/pagos/cobertura?id_sucursal={s1.id_sucursal}").json()
    r2 = cliente.get(f"/pagos/cobertura?id_sucursal={s2.id_sucursal}").json()
    assert r1["total_intencion_no_atendida"] == 1
    assert r2["total_intencion_no_atendida"] == 0


def test_cobertura_historica_refleja_el_estado_de_entonces(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    credito = _id_medio("tarjeta_credito")

    r = cliente.put(
        "/pagos/cobertura",
        json={
            "id_sucursal": sucursal.id_sucursal,
            "id_medio_pago": credito,
            "acepta": True,
            "fecha_desde": "2026-03-01",
            "id_operador": encargado.id_operador,
        },
    )
    assert r.status_code == 200, r.text

    antes = cliente.get(
        f"/pagos/cobertura?id_sucursal={sucursal.id_sucursal}&desde=2026-01-01&hasta=2026-02-28"
    ).json()
    despues = cliente.get(
        f"/pagos/cobertura?id_sucursal={sucursal.id_sucursal}&desde=2026-04-01&hasta=2026-04-30"
    ).json()
    assert next(m for m in antes["medios"] if m["id_medio_pago"] == credito)["cubierto"] is False
    assert next(m for m in despues["medios"] if m["id_medio_pago"] == credito)["cubierto"] is True


def test_cobertura_tramos_encadenados_y_reserva_al_encargado(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    no_encargado = crear_operador(sesion, es_encargado=False)
    sesion.commit()
    debito = _id_medio("tarjeta_debito")
    base = {
        "id_sucursal": sucursal.id_sucursal,
        "id_medio_pago": debito,
        "acepta": True,
        "id_operador": encargado.id_operador,
    }
    assert cliente.put("/pagos/cobertura", json={**base, "fecha_desde": "2026-01-01"}).status_code == 200
    # un segundo tramo posterior cierra el anterior automáticamente (sin solape)
    assert cliente.put("/pagos/cobertura", json={**base, "fecha_desde": "2026-06-01"}).status_code == 200
    # operador no encargado -> 400
    r = cliente.put(
        "/pagos/cobertura",
        json={**base, "fecha_desde": "2026-09-01", "id_operador": no_encargado.id_operador},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "rol_insuficiente"  # enmienda v2.3.0


def test_la_restriccion_de_exclusion_gist_rechaza_un_solape_de_vigencia(sesion):
    """El solape de tramos lo impide el MOTOR (restricción de exclusión GiST de la migración 0007),
    no sólo la lógica del servicio: una inserción directa de dos tramos solapados para el mismo
    (medio, sucursal) es rechazada por PostgreSQL (research.md #5)."""
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    debito = sesion.execute(
        select(MedioPago.id_medio_pago).where(MedioPago.nombre == "tarjeta_debito")
    ).scalar_one()

    def tramo(desde, hasta):
        return CoberturaPago(
            id_medio_pago=debito,
            id_sucursal=sucursal.id_sucursal,
            fecha_desde=date.fromisoformat(desde),
            fecha_hasta=date.fromisoformat(hasta) if hasta else None,
            id_operador=encargado.id_operador,
            instante_registro=datetime.now(timezone.utc),
        )

    sesion.add(tramo("2026-01-01", "2026-06-30"))
    sesion.flush()
    sesion.add(tramo("2026-05-01", None))  # solapa con el tramo anterior
    with pytest.raises(IntegrityError) as exc:
        sesion.flush()
    assert "ex_cobertura_pago_sin_solape" in str(exc.value)
    sesion.rollback()
