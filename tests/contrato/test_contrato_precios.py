"""T014, T022, T033, T044 — Pruebas obligatorias (Principio III): endpoints de precios y
márgenes conformes a contracts/openapi.yaml (`MargenProducto`, rol de producto, sugerencias de
precio y de colocación).
"""

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import ZonaExhibicion
from rasero.persistencia.sesion import SesionLocal
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)

CLAVES_MARGEN_PRODUCTO = (
    "id_producto",
    "id_sucursal",
    "costo_vigente",
    "precio_vigente",
    "margen",
    "confiable",
    "instante_calculo",
)


def test_get_margen_producto_devuelve_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio 2.50
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.close()

    respuesta = cliente.get(f"/productos/{id_producto}/margen", params={"id_sucursal": id_sucursal})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    for clave in CLAVES_MARGEN_PRODUCTO:
        assert clave in cuerpo, f"falta '{clave}' en la respuesta de GET /productos/{{id}}/margen"

    assert cuerpo["margen"] == 0.6
    assert cuerpo["confiable"] is True
    assert cuerpo["precio_vigente"] == "2.5000"
    assert cuerpo["costo_vigente"] == "1.0000"


def test_get_margen_producto_inexistente_devuelve_404():
    respuesta = cliente.get("/productos/999999/margen", params={"id_sucursal": 1})
    assert respuesta.status_code == 404


def test_get_margenes_devuelve_200_con_lista_de_margen_producto():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    sesion.close()

    respuesta = cliente.get("/margenes", params={"id_sucursal": id_sucursal})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)

    fila = next(f for f in cuerpo if f["id_producto"] == id_producto)
    for clave in CLAVES_MARGEN_PRODUCTO:
        assert clave in fila, f"falta '{clave}' en un elemento de GET /margenes"
    assert fila["margen"] == 0.6


def test_get_margen_producto_sin_costo_vigente_devuelve_margen_nulo():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.close()

    respuesta = cliente.get(f"/productos/{id_producto}/margen", params={"id_sucursal": id_sucursal})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["margen"] is None
    assert cuerpo["costo_vigente"] is None


# --------------------------------------------------------------------------
# T022 — PUT /productos/{id_producto}/rol (User Story 2)
# --------------------------------------------------------------------------


def test_put_rol_producto_devuelve_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    sesion.close()

    respuesta = cliente.put(f"/productos/{id_producto}/rol", json={"rol": "gancho_trafico"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in ("id_producto", "rol", "instante_asignacion"):
        assert clave in cuerpo
    assert cuerpo["rol"] == "gancho_trafico"


def test_get_rol_producto_sin_clasificar_devuelve_rol_nulo():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    sesion.close()

    respuesta = cliente.get(f"/productos/{id_producto}/rol")
    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] is None


# --------------------------------------------------------------------------
# T033 — sugerencia de precio (User Story 3)
# --------------------------------------------------------------------------

CLAVES_SUGERENCIA_PRECIO = (
    "id_sugerencia_precio",
    "id_producto",
    "id_sucursal",
    "precio_sugerido",
    "margen_usado",
    "rol_usado",
    "observacion_competencia_usada",
    "instante_generacion",
    "aplicada",
    "instante_aplicacion",
)


def test_get_sugerencia_precio_devuelve_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.close()

    respuesta = cliente.get(
        f"/productos/{id_producto}/sugerencia-precio", params={"id_sucursal": id_sucursal}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in CLAVES_SUGERENCIA_PRECIO:
        assert clave in cuerpo, f"falta '{clave}' en GET /productos/{{id}}/sugerencia-precio"
    assert cuerpo["aplicada"] is False
    assert cuerpo["observacion_competencia_usada"] is None  # sin observación capturada (FR-010)


def test_post_aplicar_sugerencia_precio_devuelve_200_y_luego_409():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.close()

    generada = cliente.get(
        f"/productos/{id_producto}/sugerencia-precio", params={"id_sucursal": id_sucursal}
    ).json()

    primera = cliente.post(
        f"/productos/{id_producto}/sugerencia-precio/aplicar",
        json={"id_sugerencia_precio": generada["id_sugerencia_precio"]},
    )
    assert primera.status_code == 200
    assert primera.json()["aplicada"] is True

    segunda = cliente.post(
        f"/productos/{id_producto}/sugerencia-precio/aplicar",
        json={"id_sugerencia_precio": generada["id_sugerencia_precio"]},
    )
    assert segunda.status_code == 409


# --------------------------------------------------------------------------
# T044 — sugerencia de colocación (User Story 4)
# --------------------------------------------------------------------------

CLAVES_SUGERENCIA_COLOCACION = (
    "id_sugerencia_colocacion",
    "id_producto",
    "id_sucursal",
    "id_zona_exhibicion",
    "zona_nombre",
    "margen_usado",
    "rol_usado",
    "instante_generacion",
    "aplicada",
    "instante_aplicacion",
)


def test_get_sugerencia_colocacion_devuelve_200_con_las_claves_del_contrato():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.add(ZonaExhibicion(id_sucursal=id_sucursal, nombre="Zona de prueba", grado_privilegio=1))
    sesion.commit()
    sesion.close()

    respuesta = cliente.get(
        f"/productos/{id_producto}/sugerencia-colocacion", params={"id_sucursal": id_sucursal}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in CLAVES_SUGERENCIA_COLOCACION:
        assert clave in cuerpo, f"falta '{clave}' en GET /productos/{{id}}/sugerencia-colocacion"
    assert cuerpo["zona_nombre"] == "Zona de prueba"


def test_get_sugerencia_colocacion_sin_zonas_devuelve_404():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal_sin_zonas = escenario["sucursal"].id_sucursal
    sesion.close()

    respuesta = cliente.get(
        f"/productos/{id_producto}/sugerencia-colocacion", params={"id_sucursal": id_sucursal_sin_zonas}
    )
    assert respuesta.status_code == 404


def test_post_aplicar_sugerencia_colocacion_devuelve_200_y_luego_409():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.add(ZonaExhibicion(id_sucursal=id_sucursal, nombre="Otra zona", grado_privilegio=1))
    sesion.commit()
    sesion.close()

    generada = cliente.get(
        f"/productos/{id_producto}/sugerencia-colocacion", params={"id_sucursal": id_sucursal}
    ).json()

    primera = cliente.post(
        f"/productos/{id_producto}/sugerencia-colocacion/aplicar",
        json={"id_sugerencia_colocacion": generada["id_sugerencia_colocacion"]},
    )
    assert primera.status_code == 200
    assert primera.json()["aplicada"] is True

    segunda = cliente.post(
        f"/productos/{id_producto}/sugerencia-colocacion/aplicar",
        json={"id_sugerencia_colocacion": generada["id_sugerencia_colocacion"]},
    )
    assert segunda.status_code == 409
