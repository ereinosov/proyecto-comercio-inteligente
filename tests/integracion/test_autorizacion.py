"""User Story 10 (Principio VI, enmienda v2.3.0): autorización centralizada por rol.

Contra PostgreSQL real, puerto 5442. Verifica el mecanismo único `requiere_rol` y la gestión
de operadores admin-only. Prueba obligatoria (Principio III): contrato de autorización sobre
`operador`.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from rasero.api.aplicacion import app
from rasero.errores import OperadorInvalido
from rasero.persistencia.modelos import Operador, Sucursal
from rasero.seguridad import RolInsuficiente, requiere_rol

cliente = TestClient(app)


def _sucursal(sesion) -> Sucursal:
    s = Sucursal(nombre=f"Suc {uuid.uuid4().hex[:8]}", zona_horaria="America/Guayaquil")
    sesion.add(s)
    sesion.flush()
    return s


def _operador(sesion, rol: str, id_sucursal: int) -> Operador:
    o = Operador(nombre=f"Op {rol} {uuid.uuid4().hex[:5]}", pin_hash="", rol=rol,
                 id_sucursal=id_sucursal, activo=True)
    sesion.add(o)
    sesion.flush()
    return o


def test_requiere_rol_respeta_la_jerarquia(sesion):
    suc = _sucursal(sesion)
    cajero = _operador(sesion, "cajero", suc.id_sucursal)
    encargado = _operador(sesion, "encargado", suc.id_sucursal)
    admin = _operador(sesion, "admin", suc.id_sucursal)
    sesion.commit()

    # cajero: sólo alcanza "cajero"
    assert requiere_rol(sesion, cajero.id_operador, "cajero").id_operador == cajero.id_operador
    with pytest.raises(RolInsuficiente):
        requiere_rol(sesion, cajero.id_operador, "encargado")
    with pytest.raises(RolInsuficiente):
        requiere_rol(sesion, cajero.id_operador, "admin")

    # encargado: alcanza cajero y encargado, no admin
    assert requiere_rol(sesion, encargado.id_operador, "encargado")
    with pytest.raises(RolInsuficiente):
        requiere_rol(sesion, encargado.id_operador, "admin")

    # admin: alcanza todo
    assert requiere_rol(sesion, admin.id_operador, "admin")
    assert requiere_rol(sesion, admin.id_operador, "cajero")


def test_operador_inactivo_o_inexistente_es_rechazado(sesion):
    suc = _sucursal(sesion)
    inactivo = _operador(sesion, "encargado", suc.id_sucursal)
    inactivo.activo = False
    sesion.commit()
    with pytest.raises(OperadorInvalido):
        requiere_rol(sesion, inactivo.id_operador, "cajero")
    with pytest.raises(OperadorInvalido):
        requiere_rol(sesion, 999_999, "cajero")


def test_encargado_puede_administrar_maestros_pero_no_operadores(sesion):
    suc = _sucursal(sesion)
    encargado = _operador(sesion, "encargado", suc.id_sucursal)
    sesion.commit()

    ok = cliente.post("/administracion/categorias",
                      json={"nombre": f"Cat {uuid.uuid4().hex[:6]}", "id_operador": encargado.id_operador})
    assert ok.status_code == 201, ok.text

    r = cliente.post("/operadores", json={
        "nombre": "Nuevo Cajero", "rol": "cajero", "id_sucursal": suc.id_sucursal,
        "pin": "4321", "id_operador_solicitante": encargado.id_operador,
    })
    assert r.status_code == 403 and r.json()["codigo"] == "rol_insuficiente"


def test_admin_crea_operador_y_encargado_no_puede_ascender(sesion):
    suc = _sucursal(sesion)
    admin = _operador(sesion, "admin", suc.id_sucursal)
    encargado = _operador(sesion, "encargado", suc.id_sucursal)
    sesion.commit()

    creado = cliente.post("/operadores", json={
        "nombre": "Cajero Nuevo", "rol": "cajero", "id_sucursal": suc.id_sucursal,
        "pin": "1111", "id_operador_solicitante": admin.id_operador,
    })
    assert creado.status_code == 201, creado.text
    id_nuevo = creado.json()["id_operador"]
    assert creado.json()["rol"] == "cajero"

    # el encargado no puede ascenderlo
    r = cliente.put(f"/operadores/{id_nuevo}", json={
        "nombre": "Cajero Nuevo", "rol": "encargado", "id_sucursal": suc.id_sucursal,
        "id_operador_solicitante": encargado.id_operador,
    })
    assert r.status_code == 403

    # el admin sí
    ok = cliente.put(f"/operadores/{id_nuevo}", json={
        "nombre": "Cajero Nuevo", "rol": "encargado", "id_sucursal": suc.id_sucursal,
        "id_operador_solicitante": admin.id_operador,
    })
    assert ok.status_code == 200 and ok.json()["rol"] == "encargado"
