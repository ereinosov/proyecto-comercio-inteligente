"""T012 — Prueba obligatoria (Principio III): POST /clientes y POST /clientes/{id_cliente}/visitas
conformes a contracts/openapi.yaml de 002-clientes-fidelizacion. Se amplía en User Story 2 (T023)
y User Story 3 (T037) con los endpoints de lectura que esas historias añaden.
"""

import uuid

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico

cliente_http = TestClient(app)


def test_post_clientes_devuelve_201_con_las_claves_del_contrato():
    respuesta = cliente_http.post(
        "/clientes",
        json={"nombre": "María Torres", "fecha_nacimiento": "1992-07-15"},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    for clave in ("id_cliente", "nombre", "fecha_nacimiento", "contacto", "fecha_alta", "anonimizado"):
        assert clave in cuerpo, f"falta '{clave}' en la respuesta de POST /clientes"
    assert cuerpo["nombre"] == "María Torres"
    assert cuerpo["anonimizado"] is False


def test_post_clientes_sin_fecha_nacimiento_devuelve_422():
    respuesta = cliente_http.post("/clientes", json={"nombre": "Sin fecha"})
    assert respuesta.status_code == 422


def test_post_visitas_devuelve_201_y_luego_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=20)
    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=f"contrato-clientes-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(
                id_producto=escenario["producto"].id_producto,
                cantidad_unidades=1,
                cantidad_gramos=None,
            )
        ],
    )
    sesion.close()

    cliente_creado = cliente_http.post(
        "/clientes", json={"nombre": "Contrato Visita", "fecha_nacimiento": "1980-01-01"}
    ).json()

    primera = cliente_http.post(
        f"/clientes/{cliente_creado['id_cliente']}/visitas", json={"id_venta": venta.id_venta}
    )
    assert primera.status_code == 201
    cuerpo = primera.json()
    for clave in ("id_visita", "id_cliente", "id_venta", "instante", "monto_total", "margen_relativo"):
        assert clave in cuerpo, f"falta '{clave}' en la respuesta de POST .../visitas"
    assert cuerpo["monto_total"] == "2.50"

    segunda = cliente_http.post(
        f"/clientes/{cliente_creado['id_cliente']}/visitas", json={"id_venta": venta.id_venta}
    )
    assert segunda.status_code == 200
    assert segunda.json()["id_visita"] == cuerpo["id_visita"]


def test_post_visitas_con_venta_de_otro_cliente_devuelve_409():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=20)
    venta, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=f"contrato-conflicto-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(
                id_producto=escenario["producto"].id_producto,
                cantidad_unidades=1,
                cantidad_gramos=None,
            )
        ],
    )
    sesion.close()

    cliente_a = cliente_http.post(
        "/clientes", json={"nombre": "Cliente A", "fecha_nacimiento": "1980-01-01"}
    ).json()
    cliente_b = cliente_http.post(
        "/clientes", json={"nombre": "Cliente B", "fecha_nacimiento": "1980-01-01"}
    ).json()

    primera = cliente_http.post(
        f"/clientes/{cliente_a['id_cliente']}/visitas", json={"id_venta": venta.id_venta}
    )
    assert primera.status_code == 201

    conflicto = cliente_http.post(
        f"/clientes/{cliente_b['id_cliente']}/visitas", json={"id_venta": venta.id_venta}
    )
    assert conflicto.status_code == 409
    assert "codigo" in conflicto.json()


def test_post_visitas_con_cliente_inexistente_devuelve_404():
    respuesta = cliente_http.post("/clientes/999999/visitas", json={"id_venta": 1})
    assert respuesta.status_code == 404


def test_get_clientes_devuelve_lista_con_las_claves_del_contrato():
    cliente_http.post("/clientes", json={"nombre": "Listado A", "fecha_nacimiento": "1980-01-01"})

    respuesta = cliente_http.get("/clientes")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    assert len(cuerpo) >= 1
    for clave in ("id_cliente", "nombre", "valor", "monto_total"):
        assert clave in cuerpo[0], f"falta '{clave}' en la respuesta de GET /clientes"


def test_get_cliente_por_id_devuelve_detalle_con_desglose():
    creado = cliente_http.post(
        "/clientes", json={"nombre": "Detalle Contrato", "fecha_nacimiento": "1980-01-01"}
    ).json()

    respuesta = cliente_http.get(f"/clientes/{creado['id_cliente']}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in ("id_cliente", "nombre", "fecha_nacimiento", "contacto", "anonimizado", "valor"):
        assert clave in cuerpo, f"falta '{clave}' en el detalle de GET /clientes/{{id_cliente}}"
    # Un cliente recién creado, sin visitas, no tiene valor calculado (FR-007): null, no 0.
    assert cuerpo["valor"] is None


def test_get_cliente_inexistente_devuelve_404():
    respuesta = cliente_http.get("/clientes/999999")
    assert respuesta.status_code == 404


def test_ruta_busqueda_no_es_capturada_por_la_ruta_dinamica_de_id_cliente():
    """Regresión de enrutado: `/clientes/busqueda` debe resolver a la búsqueda, nunca intentar
    interpretarse como `/clientes/{id_cliente}` con id_cliente="busqueda".
    """
    respuesta = cliente_http.get("/clientes/busqueda", params={"q": "Detalle"})
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


def test_get_cumpleanos_devuelve_clientes_en_el_rango_con_las_claves_del_contrato():
    cliente_http.post(
        "/clientes", json={"nombre": "Cumpleañero", "fecha_nacimiento": "1990-06-15"}
    )

    respuesta = cliente_http.get(
        "/clientes/cumpleanos", params={"desde": "2026-06-10", "hasta": "2026-06-20"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert any(c["nombre"] == "Cumpleañero" for c in cuerpo)
    for clave in ("id_cliente", "nombre", "fecha_nacimiento"):
        assert clave in cuerpo[0], f"falta '{clave}' en GET /clientes/cumpleanos"


def test_get_cumpleanos_no_incluye_a_quien_no_cumple_en_el_rango():
    cliente_http.post(
        "/clientes", json={"nombre": "Fuera De Rango", "fecha_nacimiento": "1990-12-25"}
    )

    respuesta = cliente_http.get(
        "/clientes/cumpleanos", params={"desde": "2026-06-10", "hasta": "2026-06-20"}
    )
    assert respuesta.status_code == 200
    assert not any(c["nombre"] == "Fuera De Rango" for c in respuesta.json())


def test_ruta_cumpleanos_no_es_capturada_por_la_ruta_dinamica_de_id_cliente():
    respuesta = cliente_http.get(
        "/clientes/cumpleanos", params={"desde": "2026-01-01", "hasta": "2026-12-31"}
    )
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)
