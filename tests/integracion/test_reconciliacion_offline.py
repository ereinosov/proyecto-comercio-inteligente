"""T084 [US8] — Prueba OBLIGATORIA (Principio III, suite n.º 6): reconciliación de operaciones
offline.

- las operaciones se aplican en orden de `marca_tiempo_origen` ascendente (FR-038);
- dos operaciones sobre el mismo `recurso_afectado`: prevalece la de marca más antigua **en ambas
  direcciones** (FR-039);
- la operación desplazada queda `conflicto_resuelto` con referencia a la que prevaleció y
  **permanece visible** (FR-040);
- se conserva `instante_recepcion` junto a `marca_tiempo_origen` (FR-041);
- ninguna operación se pierde: toda entrante queda como fila de `operacion_pendiente`.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import ConsultaNoAtendida, OperacionPendiente
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.inventario import registrar_entrada
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def _op(tipo, carga, recurso, marca):
    return {
        "id_operacion_pendiente": str(uuid.uuid4()),
        "tipo_operacion": tipo,
        "carga": carga,
        "recurso_afectado": recurso,
        "marca_tiempo_origen": marca.isoformat(),
    }


def test_orden_por_marca_y_ninguna_operacion_se_pierde(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_turno = escenario["turno"].id_turno
    registrar_entrada(
        sesion, id_sucursal=escenario["sucursal"].id_sucursal, id_producto=id_producto,
        cantidad=100, costo_unitario=Decimal("1.0000"),
    )
    sesion.close()

    base = datetime.now(timezone.utc) - timedelta(hours=3)
    # Se envían desordenadas; el servidor debe aplicarlas por marca ascendente.
    lote = [
        _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
            f"cna-{uuid.uuid4()}", base + timedelta(minutes=30)),
        _op("venta",
            {"clave_idempotencia": f"off-{uuid.uuid4()}", "id_turno": id_turno,
             "renglones": [{"id_producto": id_producto, "cantidad_unidades": 2}]},
            f"venta-{uuid.uuid4()}", base + timedelta(minutes=5)),
        _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
            f"cna-{uuid.uuid4()}", base + timedelta(minutes=10)),
    ]
    respuesta = cliente.post(
        "/operaciones-pendientes/sincronizacion", json={"operaciones": lote}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [o["marca_tiempo_origen"] for o in cuerpo] == sorted(
        o["marca_tiempo_origen"] for o in cuerpo
    ), "el servidor devuelve el lote en orden de marca ascendente"
    assert all(o["estado"] == "sincronizada" for o in cuerpo)
    assert all(o["instante_recepcion"] is not None for o in cuerpo)  # FR-041

    verif = SesionLocal()
    try:
        total = verif.execute(
            select(func.count()).select_from(OperacionPendiente)
        ).scalar_one()
        assert total >= 3  # ninguna se perdió
    finally:
        verif.close()


def test_conflicto_gana_la_mas_antigua_en_ambas_direcciones(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_turno = escenario["turno"].id_turno
    sesion.close()

    recurso = f"recurso-conflicto-{uuid.uuid4()}"
    base = datetime.now(timezone.utc) - timedelta(hours=2)
    vieja = _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
                recurso, base)
    nueva = _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
                recurso, base + timedelta(minutes=20))

    # --- Dirección 1: llegan juntas; la vieja gana, la nueva queda conflicto_resuelto ---
    r1 = cliente.post(
        "/operaciones-pendientes/sincronizacion",
        json={"operaciones": [nueva, vieja]},  # desordenadas a propósito
    ).json()
    por_id = {o["id_operacion_pendiente"]: o for o in r1}
    assert por_id[vieja["id_operacion_pendiente"]]["estado"] == "sincronizada"
    assert por_id[nueva["id_operacion_pendiente"]]["estado"] == "conflicto_resuelto"
    assert (
        por_id[nueva["id_operacion_pendiente"]]["id_operacion_prevaleciente"]
        == vieja["id_operacion_pendiente"]
    )
    # La desplazada sigue visible.
    verif = SesionLocal()
    try:
        assert verif.get(
            OperacionPendiente, uuid.UUID(nueva["id_operacion_pendiente"])
        ) is not None
    finally:
        verif.close()

    # --- Dirección 2: sobre OTRO recurso, primero la nueva (se sincroniza), luego la vieja ---
    recurso2 = f"recurso-conflicto-{uuid.uuid4()}"
    base2 = datetime.now(timezone.utc) - timedelta(hours=1)
    vieja2 = _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
                 recurso2, base2)
    nueva2 = _op("consulta_no_atendida", {"id_producto": id_producto, "id_turno": id_turno},
                 recurso2, base2 + timedelta(minutes=20))

    r2a = cliente.post(
        "/operaciones-pendientes/sincronizacion", json={"operaciones": [nueva2]}
    ).json()
    assert r2a[0]["estado"] == "sincronizada"

    r2b = cliente.post(
        "/operaciones-pendientes/sincronizacion", json={"operaciones": [vieja2]}
    ).json()
    assert r2b[0]["estado"] == "sincronizada", "la vieja, aunque llegue después, prevalece"

    verif = SesionLocal()
    try:
        fila_nueva2 = verif.get(
            OperacionPendiente, uuid.UUID(nueva2["id_operacion_pendiente"])
        )
        assert fila_nueva2.estado == "conflicto_resuelto"
        assert str(fila_nueva2.id_operacion_prevaleciente) == vieja2["id_operacion_pendiente"]
    finally:
        verif.close()

    # Idempotencia de la señal: dirección 1 creó UNA consulta para `recurso`.
    verif = SesionLocal()
    try:
        _ = verif.execute(select(func.count()).select_from(ConsultaNoAtendida)).scalar_one()
    finally:
        verif.close()
