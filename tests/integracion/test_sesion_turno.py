"""User Story 11 (Principio VI, sub-sección "Identidad de sesión", enmienda constitucional
v2.4.0): la identidad del operador se deriva del token de sesión de turno, no del `id_operador`
del cuerpo.

Contra PostgreSQL real, puerto 5442. Prueba obligatoria (Principio III): contrato de
autorización + transición de estado de `turno` sujeta a la sesión.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.configuracion import JWT_ALGORITMO, JWT_SECRET_KEY
from rasero.persistencia.modelos import Operador, Sucursal, Turno
from rasero.seguridad import emitir_token_turno, hashear_pin

cliente = TestClient(app)


def _sucursal(sesion) -> Sucursal:
    s = Sucursal(nombre=f"Suc {uuid.uuid4().hex[:8]}", zona_horaria="America/Guayaquil")
    sesion.add(s)
    sesion.flush()
    return s


def _operador(sesion, rol: str, id_sucursal: int, *, pin: str = "1234", activo: bool = True) -> Operador:
    o = Operador(nombre=f"Op {rol} {uuid.uuid4().hex[:5]}", pin_hash="", rol=rol,
                 id_sucursal=id_sucursal, activo=activo)
    sesion.add(o)
    sesion.flush()
    o.pin_hash = hashear_pin(pin, str(o.id_operador))
    sesion.flush()
    return o


def _turno_abierto(sesion, operador) -> Turno:
    t = Turno(id_operador=operador.id_operador, id_sucursal=operador.id_sucursal,
              caja="caja-1", instante_apertura=datetime.now(timezone.utc))
    sesion.add(t)
    sesion.flush()
    return t


def _cab(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- El hallazgo de la auditoría: la suplantación por cuerpo ya no funciona (SC-015) ---


def test_id_operador_en_el_cuerpo_no_suplanta_al_operador_del_token(sesion):
    suc = _sucursal(sesion)
    cajero = _operador(sesion, "cajero", suc.id_sucursal)
    admin = _operador(sesion, "admin", suc.id_sucursal)
    turno_cajero = _turno_abierto(sesion, cajero)
    sesion.commit()

    token_cajero = emitir_token_turno(
        id_operador=cajero.id_operador, id_turno=turno_cajero.id_turno, rol="cajero"
    )
    # El cajero intenta un alta de operador (acción de admin) inyectando el id del admin.
    r = cliente.post(
        "/operadores",
        json={
            "nombre": "Colado", "rol": "cajero", "id_sucursal": suc.id_sucursal, "pin": "9999",
            "id_operador": admin.id_operador,               # ignorado
            "id_operador_solicitante": admin.id_operador,   # ignorado
        },
        headers=_cab(token_cajero),
    )
    assert r.status_code == 403
    assert r.json()["codigo"] == "rol_insuficiente"


# --- Modos de fallo de la sesión (FR-068, SC-016) ---


def test_sin_header_authorization_es_401_sesion_invalida(sesion):
    r = cliente.post("/administracion/categorias", json={"nombre": "X"})
    assert r.status_code == 401
    cuerpo = r.json()
    assert cuerpo["codigo"] == "sesion_invalida"
    assert "turno" in cuerpo["mensaje"].lower()


def test_token_con_firma_invalida_es_401_sesion_invalida(sesion):
    r = cliente.post(
        "/administracion/categorias", json={"nombre": "X"},
        headers=_cab("no-es-un-jwt"),
    )
    assert r.status_code == 401 and r.json()["codigo"] == "sesion_invalida"


def test_token_expirado_es_401_sesion_expirada(sesion):
    suc = _sucursal(sesion)
    enc = _operador(sesion, "encargado", suc.id_sucursal)
    turno = _turno_abierto(sesion, enc)
    sesion.commit()
    ahora = datetime.now(timezone.utc)
    vencido = jwt.encode(
        {"id_operador": enc.id_operador, "id_turno": turno.id_turno, "rol": "encargado",
         "iat": ahora - timedelta(hours=13), "exp": ahora - timedelta(hours=1)},
        JWT_SECRET_KEY, algorithm=JWT_ALGORITMO,
    )
    r = cliente.post("/administracion/categorias", json={"nombre": "X"}, headers=_cab(vencido))
    assert r.status_code == 401 and r.json()["codigo"] == "sesion_expirada"


def test_token_de_turno_cerrado_es_401_aunque_no_haya_expirado(sesion):
    suc = _sucursal(sesion)
    enc = _operador(sesion, "encargado", suc.id_sucursal)
    turno = _turno_abierto(sesion, enc)
    sesion.commit()
    token = emitir_token_turno(id_operador=enc.id_operador, id_turno=turno.id_turno, rol="encargado")

    turno.instante_cierre = datetime.now(timezone.utc)
    sesion.commit()

    r = cliente.post("/administracion/categorias", json={"nombre": "X"}, headers=_cab(token))
    assert r.status_code == 401 and r.json()["codigo"] == "sesion_invalida"


def test_token_de_operador_desactivado_es_401_inmediato(sesion):
    suc = _sucursal(sesion)
    enc = _operador(sesion, "encargado", suc.id_sucursal)
    turno = _turno_abierto(sesion, enc)
    sesion.commit()
    token = emitir_token_turno(id_operador=enc.id_operador, id_turno=turno.id_turno, rol="encargado")

    enc.activo = False
    sesion.commit()

    r = cliente.post("/administracion/categorias", json={"nombre": "X"}, headers=_cab(token))
    assert r.status_code == 401 and r.json()["codigo"] == "sesion_invalida"


# --- Camino feliz (FR-065, FR-067) ---


def test_abrir_turno_devuelve_token_y_el_token_autoriza(sesion):
    suc = _sucursal(sesion)
    # `admin`: `/administracion/categorias` es admin en exclusiva desde la constitución v2.7.1.
    adm = _operador(sesion, "admin", suc.id_sucursal, pin="4242")
    sesion.commit()

    abierto = cliente.post("/turnos", json={
        "id_operador": adm.id_operador, "id_sucursal": suc.id_sucursal,
        "caja": "caja-1", "pin": "4242",
    })
    assert abierto.status_code == 201, abierto.text
    token = abierto.json()["token"]
    assert isinstance(token, str) and token.count(".") == 2

    claims = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITMO])
    assert claims["id_operador"] == adm.id_operador
    assert claims["id_turno"] == abierto.json()["id_turno"]

    r = cliente.post(
        "/administracion/categorias",
        json={"nombre": f"Cat {uuid.uuid4().hex[:6]}"},
        headers=_cab(token),
    )
    assert r.status_code == 201, r.text


def test_anular_venta_toma_el_operador_del_token(sesion):
    from decimal import Decimal

    from rasero.persistencia.modelos import Venta

    suc = _sucursal(sesion)
    cajero = _operador(sesion, "cajero", suc.id_sucursal)
    turno = _turno_abierto(sesion, cajero)
    venta = Venta(clave_idempotencia=f"anul-{uuid.uuid4()}", id_turno=turno.id_turno,
                  instante=datetime.now(timezone.utc), total=Decimal("0.00"))
    sesion.add(venta)
    sesion.commit()
    token = emitir_token_turno(id_operador=cajero.id_operador, id_turno=turno.id_turno, rol="cajero")

    r = cliente.post(
        f"/ventas/{venta.id_venta}/anulacion",
        json={"motivo": "prueba"},
        headers=_cab(token),
    )
    assert r.status_code == 201, r.text
    assert r.json()["id_operador"] == cajero.id_operador
