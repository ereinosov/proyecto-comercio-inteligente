"""T016 — Prueba obligatoria (Principio III): `GET /demanda` conforme a
`specs/004-pronostico-demanda/contracts/openapi.yaml` (esquema `PuntoSerie`) en su forma feliz y
en su modo de fallo declarado (`404`). Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Producto, Sucursal
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import SesionLocal
from tests.apoyo import crear_escenario_basico, sembrar_ventas_diarias, venta_de_prueba
from tests.utilidades.generador_sintetico import generar_serie

cliente = TestClient(app)

CLAVES_PUNTO_SERIE = (
    "id_producto",
    "id_sucursal",
    "periodo",
    "demanda_observada",
    "demanda_corregida",
    "estado",
    "dias_en_quiebre",
    "correccion_quiebre",
    "respaldo_quiebre",
    "ajuste_cruzado_sustituto",
    "precio_vigente_periodo",
    "correccion_precio",
    "elasticidad_usada",
    "con_promocion",
    "excluido_por_promocion",
    "senal_sustitucion",
)


def _escenario_con_una_venta():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    ahora = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    registrar_movimiento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(20),
        instante=ahora - timedelta(days=5),
    )
    instante_venta = ahora - timedelta(days=4)
    registrar_movimiento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="salida_venta",
        cantidad=Decimal(-6),
        instante=instante_venta,
        id_venta=venta_de_prueba(
            sesion, id_turno=escenario["turno"].id_turno, instante=instante_venta
        ),
    )
    sesion.commit()
    ids = (escenario["producto"].id_producto, escenario["sucursal"].id_sucursal)
    sesion.close()
    return ids


def test_get_demanda_de_un_producto_devuelve_200_con_las_claves_del_contrato():
    id_producto, id_sucursal = _escenario_con_una_venta()

    respuesta = cliente.get(
        "/demanda", params={"id_sucursal": id_sucursal, "id_producto": id_producto}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list) and cuerpo, "serie densa: una fila por día de la ventana"

    for fila in cuerpo:
        for clave in CLAVES_PUNTO_SERIE:
            assert clave in fila, f"falta '{clave}' en un PuntoSerie de GET /demanda"
        assert fila["id_sucursal"] == id_sucursal

    dia_con_venta = next(f for f in cuerpo if f["demanda_observada"] == "6")
    assert dia_con_venta["estado"] == "ok"
    assert dia_con_venta["respaldo_quiebre"] == "no_aplica"
    assert dia_con_venta["con_promocion"] is False


def test_get_demanda_de_sucursal_completa_devuelve_lista():
    _id_producto, id_sucursal = _escenario_con_una_venta()
    respuesta = cliente.get("/demanda", params={"id_sucursal": id_sucursal})
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


def test_get_demanda_sucursal_inexistente_devuelve_404():
    respuesta = cliente.get("/demanda", params={"id_sucursal": 999999})
    assert respuesta.status_code == 404


def test_get_demanda_producto_inexistente_devuelve_404():
    _id_producto, id_sucursal = _escenario_con_una_venta()
    respuesta = cliente.get("/demanda", params={"id_sucursal": id_sucursal, "id_producto": 999999})
    assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# T028 — validación sintética (User Story 2): POST /demanda-sintetica y
# GET /demanda-sintetica/validacion contra contracts/openapi.yaml
# --------------------------------------------------------------------------

CLAVES_REPORTE_VALIDACION = (
    "id_producto",
    "id_sucursal",
    "periodos_quiebre_evaluados",
    "error_medio_descensura",
    "error_medio_sin_corregir",
    "descensura_mejora_sobre_no_corregir",
    "detalle_por_camino",
)


def _producto_sintetico() -> tuple[int, int]:
    sesion = SesionLocal()
    sucursal = Sucursal(
        nombre=f"Contrato sintético {datetime.now(timezone.utc).timestamp()}",
        zona_horaria="America/Guayaquil",
    )
    producto = Producto(
        nombre="Producto contrato sintético",
        es_granel=False,
        precio_vigente=Decimal("1.0000"),
        lleva_caducidad=False,
    )
    sesion.add_all([sucursal, producto])
    sesion.commit()
    ids = (producto.id_producto, sucursal.id_sucursal)
    sesion.close()
    return ids


def test_post_demanda_sintetica_devuelve_201_y_get_validacion_devuelve_reporte():
    id_producto, id_sucursal = _producto_sintetico()

    carga = cliente.post("/demanda-sintetica", json=generar_serie(id_producto, id_sucursal))
    assert carga.status_code == 201
    assert carga.json()["periodos_cargados"] == 56

    reporte = cliente.get(
        "/demanda-sintetica/validacion",
        params={"id_sucursal": id_sucursal, "id_producto": id_producto},
    )
    assert reporte.status_code == 200
    cuerpo = reporte.json()
    for clave in CLAVES_REPORTE_VALIDACION:
        assert clave in cuerpo, f"falta '{clave}' en GET /demanda-sintetica/validacion"
    for camino in ("con_consulta_no_atendida", "solo_metodo_base"):
        assert camino in cuerpo["detalle_por_camino"]
        for clave in ("periodos", "error_medio_descensura", "error_medio_sin_corregir"):
            assert clave in cuerpo["detalle_por_camino"][camino]
    assert cuerpo["descensura_mejora_sobre_no_corregir"] is True


def test_post_demanda_sintetica_sin_ambos_caminos_de_quiebre_devuelve_400():
    id_producto, id_sucursal = _producto_sintetico()
    # Serie con quiebre pero sin ningún período sin quiebre -> viola FR-016.
    carga = {
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "periodos": [
            {
                "periodo": "2026-02-01",
                "demanda_observada": "0",
                "dias_en_quiebre": "1",
                "demanda_latente_verdadera": "10",
            }
        ],
        "consultas_no_atendidas_sinteticas": [],
    }
    respuesta = cliente.post("/demanda-sintetica", json=carga)
    assert respuesta.status_code == 400


def test_get_validacion_sin_serie_sintetica_devuelve_404():
    id_producto, id_sucursal = _producto_sintetico()
    respuesta = cliente.get(
        "/demanda-sintetica/validacion",
        params={"id_sucursal": id_sucursal, "id_producto": id_producto},
    )
    assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# T039 — pronóstico (User Story 3)
# --------------------------------------------------------------------------

CLAVES_PRONOSTICO = (
    "id_pronostico",
    "id_producto",
    "id_sucursal",
    "horizonte",
    "dias_horizonte",
    "serie_pronosticada",
    "factores",
    "periodo_datos_desde",
    "periodo_datos_hasta",
    "valor_linea_base",
    "error_retrospectivo",
    "error_linea_base",
    "vigente",
    "motivo_no_vigente",
    "instante_generacion",
)


def _producto_con_ventas(dias: int) -> tuple[int, int]:
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sembrar_ventas_diarias(sesion, escenario, dias=dias, cantidad=10)
    ids = (escenario["producto"].id_producto, escenario["sucursal"].id_sucursal)
    sesion.close()
    return ids


def test_get_pronostico_devuelve_200_con_las_claves_del_contrato():
    id_producto, id_sucursal = _producto_con_ventas(40)
    respuesta = cliente.get(
        f"/productos/{id_producto}/pronostico",
        params={"id_sucursal": id_sucursal, "horizonte": "corto"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in CLAVES_PRONOSTICO:
        assert clave in cuerpo, f"falta '{clave}' en GET /productos/{{id}}/pronostico"
    for clave in ("nivel_suavizado", "alfa_usado", "multiplicadores_tramo"):
        assert clave in cuerpo["factores"]
    assert cuerpo["horizonte"] == "corto"
    assert cuerpo["dias_horizonte"] == 14


def test_get_pronostico_solo_ultimo_no_crea_uno_nuevo():
    id_producto, id_sucursal = _producto_con_ventas(40)
    primero = cliente.get(
        f"/productos/{id_producto}/pronostico", params={"id_sucursal": id_sucursal}
    ).json()
    ultimo = cliente.get(
        f"/productos/{id_producto}/pronostico",
        params={"id_sucursal": id_sucursal, "solo_ultimo": True},
    ).json()
    assert ultimo["id_pronostico"] == primero["id_pronostico"]


def test_get_pronostico_producto_inexistente_devuelve_404():
    _p, id_sucursal = _producto_con_ventas(5)
    respuesta = cliente.get("/productos/999999/pronostico", params={"id_sucursal": id_sucursal})
    assert respuesta.status_code == 404


def test_get_pronostico_de_producto_solo_sintetico_devuelve_409():
    id_producto, id_sucursal = _producto_sintetico()
    cliente.post("/demanda-sintetica", json=generar_serie(id_producto, id_sucursal))
    respuesta = cliente.get(
        f"/productos/{id_producto}/pronostico", params={"id_sucursal": id_sucursal}
    )
    assert respuesta.status_code == 409


# --------------------------------------------------------------------------
# T064 — relaciones de sustitución (User Story 6)
# --------------------------------------------------------------------------

CLAVES_SUSTITUCION = (
    "id_sustitucion_producto",
    "id_producto",
    "id_producto_sustituto",
    "instante_declaracion",
)


def test_sustituciones_crud_por_contrato():
    id_a, _ = _producto_con_ventas(3)
    id_b, _ = _producto_con_ventas(3)

    creada = cliente.post(
        "/sustituciones", json={"id_producto": id_a, "id_producto_sustituto": id_b}
    )
    assert creada.status_code == 201
    cuerpo = creada.json()
    for clave in CLAVES_SUSTITUCION:
        assert clave in cuerpo

    listado = cliente.get("/sustituciones", params={"id_producto": id_a})
    assert listado.status_code == 200
    assert any(r["id_producto_sustituto"] == id_b for r in listado.json())

    # Re-declarar la misma dirección -> 409.
    assert (
        cliente.post(
            "/sustituciones", json={"id_producto": id_a, "id_producto_sustituto": id_b}
        ).status_code
        == 409
    )
    # id_producto == id_producto_sustituto -> 400.
    assert (
        cliente.post(
            "/sustituciones", json={"id_producto": id_a, "id_producto_sustituto": id_a}
        ).status_code
        == 400
    )

    borrado = cliente.delete(f"/sustituciones/{cuerpo['id_sustitucion_producto']}")
    assert borrado.status_code == 204
    assert cliente.delete(f"/sustituciones/{cuerpo['id_sustitucion_producto']}").status_code == 404
