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


def test_tendencia_sin_token_da_401():
    r = cliente.get("/reportes/tendencia", params={"indicador": "ventas", "granularidad": "semana"})
    assert r.status_code == 401


def test_tendencia_forma_del_contrato():
    r = cliente.get(
        "/reportes/tendencia",
        params={"indicador": "ventas", "granularidad": "semana", "periodos": 4},
        headers=_CAB_ENC,
    )
    assert r.status_code == 200
    cuerpo = r.json()
    for clave in ("indicador", "granularidad", "ambito", "disponible", "puntos"):
        assert clave in cuerpo
    for punto in cuerpo["puntos"]:
        assert {"periodo", "etiqueta", "valor", "completo"} <= set(punto)


def test_tendencia_indicador_desconocido_no_500():
    r = cliente.get(
        "/reportes/tendencia",
        params={"indicador": "inventado", "granularidad": "semana"},
        headers=_CAB_ENC,
    )
    assert r.status_code == 200
    assert r.json()["disponible"] is False


def test_tablero_sin_token_da_401():
    assert cliente.get("/reportes/tablero").status_code == 401


def test_tablero_forma_del_contrato():
    r = cliente.get("/reportes/tablero", headers=_CAB_ENC)
    assert r.status_code == 200
    cuerpo = r.json()
    assert "tarjetas" in cuerpo and "instante_calculo" in cuerpo
    for t in cuerpo["tarjetas"]:
        assert {"modulo", "titulo", "periodo_referencia", "cifras", "sin_datos"} <= set(t)
        for c in t["cifras"]:
            assert {"etiqueta", "valor", "atencion"} <= set(c)


def test_segmentos_sin_token_da_401():
    assert cliente.get("/reportes/segmentos").status_code == 401
    assert cliente.post("/reportes/segmentos/recalculo").status_code == 401


def test_segmentos_get_forma_del_contrato():
    r = cliente.get("/reportes/segmentos", headers=_CAB_ENC)
    assert r.status_code == 200
    cuerpo = r.json()
    assert "calculado" in cuerpo and "grupos" in cuerpo


def test_segmento_de_cliente_no_toca_el_detalle_de_002(sesion):
    from rasero.servicios.clientes import registrar_cliente

    c = registrar_cliente(sesion, nombre="Segmentable", fecha_nacimiento=None)
    cab_enc = headers_encargado(sesion)  # crea encargado + turno + commitea

    r = cliente.get(f"/reportes/segmentos/cliente/{c.id_cliente}", headers=cab_enc)
    assert r.status_code == 200
    assert {"id_cliente", "etiqueta_grupo", "descripcion", "corrida"} <= set(r.json())

    detalle = cliente.get(f"/clientes/{c.id_cliente}", headers=cab_enc).json()
    assert "segmento" not in detalle and "etiqueta_grupo" not in detalle
