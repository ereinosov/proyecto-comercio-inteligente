"""T055 [US4] — Prueba de integración de precios de competencia (FR-025, FR-026, FR-027, FR-050).

- el catálogo de canales evita duplicados por nombre normalizado;
- la captura rechaza un origen distinto de manual/archivo (FR-026);
- la comparación resuelve el precio propio para la sucursal indicada (override o base, FR-050) y
  normaliza cada observación, con antigüedad y tres portadores;
- una observación no convertible se guarda pero se marca no comparable.
"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.servicios.catalogo import fijar_precio_sucursal
from tests.apoyo import crear_escenario_basico

cliente = TestClient(app)


def _canal(nombre: str) -> dict:
    r = cliente.post("/canales-competencia", json={"nombre": nombre})
    assert r.status_code in (200, 201)
    return r.json()


def test_catalogo_de_canales_no_duplica_por_nombre_normalizado(sesion):
    sesion.close()
    nombre = f"Tienda {uuid.uuid4().hex[:6]}"
    primero = cliente.post("/canales-competencia", json={"nombre": nombre})
    assert primero.status_code == 201
    repetido = cliente.post("/canales-competencia", json={"nombre": f"  {nombre.upper()}  "})
    assert repetido.status_code == 200
    assert repetido.json()["id_canal_competencia"] == primero.json()["id_canal_competencia"]

    listado = cliente.get("/canales-competencia").json()
    coincidencias = [c for c in listado if c["id_canal_competencia"] == primero.json()["id_canal_competencia"]]
    assert len(coincidencias) == 1


def test_captura_rechaza_origen_automatico(sesion):
    escenario = crear_escenario_basico(sesion)
    sesion.close()
    canal = _canal(f"Canal {uuid.uuid4().hex[:6]}")
    r = cliente.post(
        "/observaciones-precio",
        json={
            "id_producto": escenario["producto"].id_producto,
            "id_canal_competencia": canal["id_canal_competencia"],
            "presentacion_cantidad": "1",
            "presentacion_unidad": "unidad",
            "precio_observado": "2.00",
            "fuente": "visita",
            "origen_captura": "scraping",
        },
    )
    assert r.status_code == 422
    assert r.json()["codigo"] == "valor_invalido"


def test_comparacion_normaliza_y_resuelve_precio_propio_por_sucursal(sesion):
    escenario = crear_escenario_basico(sesion, es_granel=True)  # precio propio 2.5000 por kg
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    # Override de sucursal: 2.9000 por kg.
    fijar_precio_sucursal(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("2.9000")
    )
    sesion.commit()
    sesion.close()

    canal_a = _canal(f"Canal A {uuid.uuid4().hex[:6]}")
    canal_b = _canal(f"Canal B {uuid.uuid4().hex[:6]}")

    # Observación comparable: 500 g por 1.30 -> 2.60 por kg.
    cliente.post(
        "/observaciones-precio",
        json={
            "id_producto": id_producto,
            "id_canal_competencia": canal_a["id_canal_competencia"],
            "presentacion_cantidad": "500",
            "presentacion_unidad": "gramo",
            "precio_observado": "1.30",
            "fuente": "visita",
            "origen_captura": "manual",
        },
    )
    # Observación NO comparable: combinado por unidad, sin peso.
    no_comp = cliente.post(
        "/observaciones-precio",
        json={
            "id_producto": id_producto,
            "id_canal_competencia": canal_b["id_canal_competencia"],
            "presentacion_cantidad": "1",
            "presentacion_unidad": "unidad",
            "precio_observado": "3.00",
            "fuente": "archivo",
            "origen_captura": "archivo",
        },
    )
    assert no_comp.status_code == 201
    assert no_comp.json()["comparable"] is False

    comp = cliente.get(
        f"/productos/{id_producto}/comparacion-precios?id_sucursal={id_sucursal}"
    ).json()
    assert comp["precio_propio_por_unidad_medida"] == "2.9000"  # override de la sucursal
    por_canal = {o["canal"]: o for o in comp["observaciones"]}
    assert por_canal[canal_a["nombre"]]["precio_por_unidad_medida"] == "2.6000"
    assert por_canal[canal_a["nombre"]]["indicador_forma"] == "lleno"
    assert por_canal[canal_a["nombre"]]["antiguedad_texto"] == "hoy"
    assert por_canal[canal_b["nombre"]]["precio_por_unidad_medida"] is None
    assert por_canal[canal_b["nombre"]]["comparable"] is False
