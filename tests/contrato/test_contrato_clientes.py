"""T012 — Prueba obligatoria (Principio III): POST /clientes y POST /clientes/{id_cliente}/visitas
conformes a contracts/openapi.yaml de 002-clientes-fidelizacion. Se amplía en User Story 2 (T023)
y User Story 3 (T037) con los endpoints de lectura que esas historias añaden.
"""

import datetime as dt
import uuid

from sqlalchemy import delete, event
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Cliente, IntervaloCompra, SenalFuga
from rasero.persistencia.sesion import SesionLocal, engine
from rasero.servicios import clientes as servicio_clientes
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
    for clave in (
        "id_cliente",
        "nombre",
        "fecha_nacimiento",
        "contacto",
        "identificador",
        "fecha_alta",
        "anonimizado",
    ):
        assert clave in cuerpo, f"falta '{clave}' en la respuesta de POST /clientes"
    assert cuerpo["nombre"] == "María Torres"
    assert cuerpo["anonimizado"] is False


def test_post_clientes_sin_datos_personales_se_acepta():
    """`nombre` y `fecha_nacimiento` son opcionales (contrato v1.1): un cliente puede quedar
    registrado sólo por su identificador, o sin ningún dato ("consumidor final" anotado).
    """
    respuesta = cliente_http.post("/clientes", json={})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] is None
    assert cuerpo["fecha_nacimiento"] is None
    assert cuerpo["identificador"] is None


def test_post_clientes_con_identificador_invalido_devuelve_422():
    respuesta = cliente_http.post(
        "/clientes", json={"nombre": "Cédula mala", "identificador": "1714035200"}
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "identificador_invalido"


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
    # Listado paginado: { items, total } (schema RespuestaPaginada).
    assert isinstance(cuerpo["items"], list)
    assert cuerpo["total"] >= 1 and len(cuerpo["items"]) >= 1
    for clave in ("id_cliente", "nombre", "valor", "monto_total"):
        assert clave in cuerpo["items"][0], f"falta '{clave}' en la respuesta de GET /clientes"


def test_get_clientes_filtra_por_busqueda_de_nombre_y_conserva_la_paginacion():
    import uuid as _uuid

    marca = _uuid.uuid4().hex[:8]
    cliente_http.post("/clientes", json={"nombre": f"Zoraida {marca}"})
    cliente_http.post("/clientes", json={"nombre": f"Bruno {marca}"})

    r = cliente_http.get(f"/clientes?busqueda=zoraida {marca}&tamano_pagina=50")
    assert r.status_code == 200
    cuerpo = r.json()
    nombres = [c["nombre"] for c in cuerpo["items"]]
    assert nombres == [f"Zoraida {marca}"]
    assert cuerpo["total"] == 1


_AHORA_FUGA = dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc)


def _crear_cliente_con_fuga(
    sesion, nombre: str, intervalo_estado: str, senal_estado: str | None
) -> int:
    c = Cliente(nombre=nombre, fecha_alta=_AHORA_FUGA)
    sesion.add(c)
    sesion.flush()
    sesion.add(
        IntervaloCompra(
            id_cliente=c.id_cliente,
            intervalo_esperado_dias=None if intervalo_estado == "datos_insuficientes" else 10,
            visitas_consideradas=1 if intervalo_estado == "datos_insuficientes" else 4,
            estado=intervalo_estado,
            instante_calculo=_AHORA_FUGA,
        )
    )
    if senal_estado is not None:
        sesion.add(
            SenalFuga(
                id_cliente=c.id_cliente,
                estado=senal_estado,
                instante_deteccion=_AHORA_FUGA,
                instante_confirmacion=_AHORA_FUGA if senal_estado == "confirmada" else None,
                instante_resolucion=_AHORA_FUGA if senal_estado == "resuelta" else None,
                instante_purga_programada=(
                    _AHORA_FUGA + dt.timedelta(days=90) if senal_estado == "confirmada" else None
                ),
            )
        )
    return c.id_cliente


def _limpiar(ids: list[int]) -> None:
    sesion = SesionLocal()
    try:
        sesion.execute(delete(SenalFuga).where(SenalFuga.id_cliente.in_(ids)))
        sesion.execute(delete(IntervaloCompra).where(IntervaloCompra.id_cliente.in_(ids)))
        sesion.execute(delete(Cliente).where(Cliente.id_cliente.in_(ids)))
        sesion.commit()
    finally:
        sesion.close()


def test_get_clientes_expone_estado_fuga_consistente_con_el_detalle():
    """El listado (`GET /clientes`) devuelve `estado_fuga` en cada fila, con EXACTAMENTE el
    mismo valor que `fuga.estado` del detalle (`GET /clientes/{id}`) para ese cliente.
    """
    marca = uuid.uuid4().hex[:8]
    sesion = SesionLocal()
    ids: list[int] = []
    try:
        casos = [
            ("calculado", None),
            ("datos_insuficientes", None),
            ("calculado", "activa"),
            ("calculado", "confirmada"),
            ("calculado", "resuelta"),
        ]
        for i, (intervalo_estado, senal_estado) in enumerate(casos):
            ids.append(
                _crear_cliente_con_fuga(
                    sesion, f"Fuga {marca} {i}", intervalo_estado, senal_estado
                )
            )
        sesion.commit()
    finally:
        sesion.close()

    try:
        listado = cliente_http.get(f"/clientes?busqueda=Fuga {marca}&tamano_pagina=50")
        assert listado.status_code == 200
        filas = {f["id_cliente"]: f for f in listado.json()["items"]}
        assert set(ids) <= set(filas), "el listado no trajo todos los clientes de prueba"

        for id_cliente in ids:
            fila = filas[id_cliente]
            assert "estado_fuga" in fila, "falta 'estado_fuga' en la fila del listado"
            detalle = cliente_http.get(f"/clientes/{id_cliente}").json()
            assert fila["estado_fuga"] == detalle["fuga"]["estado"], (
                f"cliente {id_cliente}: listado dice {fila['estado_fuga']!r} pero el detalle "
                f"dice {detalle['fuga']['estado']!r}"
            )
    finally:
        _limpiar(ids)


def test_listar_valor_clientes_no_escala_queries_con_el_numero_de_clientes():
    """El `estado_fuga` del listado se resuelve con una única query adicional por página, nunca
    una por cliente: el conteo de SELECTs no debe crecer al duplicar la población.
    """
    marca = uuid.uuid4().hex[:8]
    ids: list[int] = []

    def contar_selects(busqueda: str) -> int:
        conteo = 0

        def _al_ejecutar(_conn, _cursor, statement, *_a, **_k):
            nonlocal conteo
            if statement.lstrip().upper().startswith("SELECT"):
                conteo += 1

        event.listen(engine, "before_cursor_execute", _al_ejecutar)
        try:
            sesion = SesionLocal()
            try:
                servicio_clientes.listar_valor_clientes(sesion, busqueda=busqueda)
            finally:
                sesion.close()
        finally:
            event.remove(engine, "before_cursor_execute", _al_ejecutar)
        return conteo

    try:
        sesion = SesionLocal()
        try:
            for i in range(3):
                ids.append(
                    _crear_cliente_con_fuga(sesion, f"NmasUno {marca} {i}", "calculado", "activa")
                )
            sesion.commit()
        finally:
            sesion.close()
        q_pocos = contar_selects(f"NmasUno {marca}")

        sesion = SesionLocal()
        try:
            for i in range(3, 9):
                ids.append(
                    _crear_cliente_con_fuga(sesion, f"NmasUno {marca} {i}", "calculado", "activa")
                )
            sesion.commit()
        finally:
            sesion.close()
        q_muchos = contar_selects(f"NmasUno {marca}")

        assert q_muchos == q_pocos, (
            f"el conteo de SELECTs escaló con la población ({q_pocos} -> {q_muchos}): "
            "hay un N+1 en el cálculo de estado_fuga del listado"
        )
    finally:
        _limpiar(ids)


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
