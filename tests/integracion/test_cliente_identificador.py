"""User Story 4 de 002-clientes-fidelizacion (FR-017): identificar a un cliente por cédula o
RUC de persona natural para no duplicarlo entre visitas. El identificador es SIEMPRE opcional
y nunca bloquea una venta (FR-003, Principio II).
"""

import datetime as dt

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Cliente, SenalFuga
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.anonimizacion import anonimizar_clientes_vencidos

cliente_http = TestClient(app)

CEDULA_VALIDA = "1714035209"
RUC_NATURAL_VALIDO = "0912345675001"


def _crear(**cuerpo):
    return cliente_http.post("/clientes", json=cuerpo)


def test_cedula_valida_se_acepta_y_se_devuelve():
    r = _crear(nombre="Con Cédula", fecha_nacimiento="1990-01-01", identificador=CEDULA_VALIDA)
    assert r.status_code == 201
    assert r.json()["identificador"] == CEDULA_VALIDA


def test_ruc_natural_valido_se_acepta():
    r = _crear(nombre="Con RUC", fecha_nacimiento="1988-02-02", identificador=RUC_NATURAL_VALIDO)
    assert r.status_code == 201
    assert r.json()["identificador"] == RUC_NATURAL_VALIDO


def test_cedula_con_verificador_incorrecto_se_rechaza_422():
    r = _crear(nombre="Mala Cédula", identificador="1714035200")
    assert r.status_code == 422
    assert r.json()["codigo"] == "identificador_invalido"


def test_ruc_con_primeros_10_digitos_invalidos_se_rechaza_422():
    r = _crear(nombre="Mal RUC", identificador="1714035200001")
    assert r.status_code == 422


def test_ruc_que_no_termina_en_001_se_rechaza_422():
    r = _crear(nombre="RUC sin sufijo", identificador="1714035209002")
    assert r.status_code == 422


def test_identificador_duplicado_entre_dos_clientes_activos_se_rechaza_409():
    ced = "2410090878"
    primero = _crear(nombre="Primero", identificador=ced)
    assert primero.status_code == 201
    segundo = _crear(nombre="Segundo", identificador=ced)
    assert segundo.status_code == 409
    assert segundo.json()["codigo"] == "identificador_duplicado"


def test_cliente_sin_identificador_se_crea_sin_error():
    # "Consumidor final" / cajero que no lo pidió: ni nombre ni fecha ni identificador.
    r = _crear()
    assert r.status_code == 201
    assert r.json()["identificador"] is None


def test_identificador_de_un_cliente_anonimizado_se_puede_reasignar():
    """Decisión del índice parcial (migración 0009): excluye a los anonimizados, así que la
    cédula queda libre después de anonimizar a quien la tenía.
    """
    ced = "1311223349"
    creado = _crear(nombre="Se irá", fecha_nacimiento="1970-03-03", identificador=ced).json()

    pasado = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
    sesion = SesionLocal()
    try:
        sesion.add(
            SenalFuga(
                id_cliente=creado["id_cliente"],
                estado="confirmada",
                instante_deteccion=pasado,
                instante_confirmacion=pasado,
                instante_purga_programada=pasado,
            )
        )
        sesion.commit()
        assert anonimizar_clientes_vencidos(sesion) >= 1
        anon = sesion.get(Cliente, creado["id_cliente"])
        assert anon.anonimizado is True
        assert anon.identificador is None
    finally:
        sesion.close()

    reasignado = _crear(nombre="Nueva persona", identificador=ced)
    assert reasignado.status_code == 201


def test_anonimizar_borra_el_identificador():
    ced = "0123456782"
    creado = _crear(nombre="Anon", fecha_nacimiento="1965-05-05", identificador=ced).json()

    sesion = SesionLocal()
    try:
        pasado = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc)
        sesion.add(
            SenalFuga(
                id_cliente=creado["id_cliente"],
                estado="confirmada",
                instante_deteccion=pasado,
                instante_confirmacion=pasado,
                instante_purga_programada=pasado,
            )
        )
        sesion.commit()
        anonimizar_clientes_vencidos(sesion)
        assert sesion.get(Cliente, creado["id_cliente"]).identificador is None
    finally:
        sesion.close()


def test_editar_cliente_puede_fijar_identificador_y_valida():
    creado = _crear(nombre="Editable", fecha_nacimiento="1991-09-09").json()
    ok = cliente_http.put(
        f"/clientes/{creado['id_cliente']}",
        json={"nombre": "Editable", "fecha_nacimiento": "1991-09-09", "identificador": "3001122336"},
    )
    assert ok.status_code == 200
    assert ok.json()["identificador"] == "3001122336"

    malo = cliente_http.put(
        f"/clientes/{creado['id_cliente']}",
        json={"nombre": "Editable", "fecha_nacimiento": "1991-09-09", "identificador": "9999999999"},
    )
    assert malo.status_code == 422
