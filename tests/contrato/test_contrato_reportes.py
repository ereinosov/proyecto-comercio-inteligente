"""Prueba obligatoria de contrato de 008-reportes-inteligencia.

Toda la superficie exige rol `encargado`; la forma de cada cuerpo sigue
`specs/008-reportes-inteligencia/contracts/openapi.yaml`.
"""

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.sesion import SesionLocal
from tests.apoyo import crear_escenario_basico, headers_encargado, headers_sesion

_s = SesionLocal()
_CAB_ENC = headers_encargado(_s)
_s.close()
cliente = TestClient(app)


def test_comparativo_sin_token_da_401():
    r = cliente.get("/reportes/comparativo")
    assert r.status_code == 401
    assert r.json()["codigo"] in ("sesion_invalida", "sesion_expirada")


def test_comparativo_con_cajero_da_403(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    cab_cajero = headers_sesion(sesion, escenario["operador"])
    sesion.commit()
    r = cliente.get("/reportes/comparativo", headers=cab_cajero)
    assert r.status_code == 403
    assert r.json()["codigo"] == "rol_insuficiente"


def test_comparativo_con_encargado_devuelve_la_forma_del_contrato():
    r = cliente.get("/reportes/comparativo", headers=_CAB_ENC)
    assert r.status_code == 200
    cuerpo = r.json()
    for clave in ("periodo_inicio", "periodo_fin", "comparable", "sucursales", "indicadores", "instante_calculo"):
        assert clave in cuerpo
    assert isinstance(cuerpo["comparable"], bool)
    for fila in cuerpo["indicadores"]:
        assert {"clave", "etiqueta", "celdas"} <= set(fila)
        for celda in fila["celdas"]:
            assert {"id_sucursal", "valor", "sin_datos", "atencion"} <= set(celda)
