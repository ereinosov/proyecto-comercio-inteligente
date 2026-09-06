"""User Story 10 (Principio VI, enmienda v2.3.0): restricción de sucursal en apertura de turno.

`cajero`/`encargado` sólo abren turno en `operador.id_sucursal`; `admin` en cualquiera.
Contra PostgreSQL real, puerto 5442. Prueba obligatoria (Principio III): transición de estado
de `turno` sujeta a autorización.
"""

import uuid

from fastapi.testclient import TestClient
from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Operador, Sucursal
from rasero.seguridad import hashear_pin

cliente = TestClient(app)


def _sucursal(sesion, nombre) -> Sucursal:
    s = Sucursal(nombre=f"{nombre} {uuid.uuid4().hex[:6]}", zona_horaria="America/Guayaquil")
    sesion.add(s)
    sesion.flush()
    return s


def _operador(sesion, rol, id_sucursal) -> Operador:
    o = Operador(nombre=f"Op {rol} {uuid.uuid4().hex[:5]}", pin_hash="", rol=rol,
                 id_sucursal=id_sucursal, activo=True)
    sesion.add(o)
    sesion.flush()
    o.pin_hash = hashear_pin("1234", str(o.id_operador))
    sesion.flush()
    return o


def _abrir(id_operador, id_sucursal):
    return cliente.post("/turnos", json={
        "id_operador": id_operador, "id_sucursal": id_sucursal, "caja": "caja-1", "pin": "1234",
    })


def test_cajero_solo_abre_en_su_sucursal(sesion):
    asignada = _sucursal(sesion, "Quevedo Centro")
    otra = _sucursal(sesion, "Buena Fe")
    cajero = _operador(sesion, "cajero", asignada.id_sucursal)
    sesion.commit()

    ok = _abrir(cajero.id_operador, asignada.id_sucursal)
    assert ok.status_code == 201, ok.text

    mal = _abrir(cajero.id_operador, otra.id_sucursal)
    assert mal.status_code == 422
    cuerpo = mal.json()
    assert cuerpo["codigo"] == "turno_sucursal_no_asignada"
    assert "no puede abrir turno en otra sucursal" in cuerpo["mensaje"]


def test_encargado_tambien_esta_atado_a_su_sucursal(sesion):
    asignada = _sucursal(sesion, "Quevedo Centro")
    otra = _sucursal(sesion, "Buena Fe")
    encargado = _operador(sesion, "encargado", asignada.id_sucursal)
    sesion.commit()

    assert _abrir(encargado.id_operador, otra.id_sucursal).status_code == 422
    assert _abrir(encargado.id_operador, asignada.id_sucursal).status_code == 201


def test_admin_abre_turno_en_cualquier_sucursal(sesion):
    registro = _sucursal(sesion, "Quevedo Centro")
    otra = _sucursal(sesion, "Buena Fe")
    admin = _operador(sesion, "admin", registro.id_sucursal)
    sesion.commit()

    assert _abrir(admin.id_operador, registro.id_sucursal).status_code == 201
    assert _abrir(admin.id_operador, otra.id_sucursal).status_code == 201
