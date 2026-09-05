"""T021 — Prueba obligatoria (Principio III), SC-002: sobre una serie sintética con demanda
latente VERDADERA conocida, la demanda corregida por el método base de FR-009 queda más cerca de
esa verdad que no corregir nada. Es la prueba de fondo de que la descensura acerca la serie a la
realidad en vez de alejarla — la única posible mientras 001 no implemente `consulta_no_atendida`.
Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timezone
from decimal import Decimal

from rasero.persistencia.modelos import Producto, Sucursal
from rasero.servicios.demanda_sintetica import cargar_serie, reporte_error_descensura
from tests.utilidades.generador_sintetico import generar_serie


def _producto_y_sucursal(sesion) -> tuple[int, int]:
    sucursal = Sucursal(
        nombre=f"Sintética {datetime.now(timezone.utc).timestamp()}",
        zona_horaria="America/Guayaquil",
    )
    producto = Producto(
        nombre="Producto sintético",
        es_granel=False,
        precio_vigente=Decimal("1.0000"),
        lleva_caducidad=False,
    )
    sesion.add_all([sucursal, producto])
    sesion.flush()
    return producto.id_producto, sucursal.id_sucursal


def test_la_descensura_acerca_la_serie_a_la_demanda_latente_verdadera_mas_que_no_corregir(
    sesion, capsys
):
    id_producto, id_sucursal = _producto_y_sucursal(sesion)
    carga = generar_serie(id_producto, id_sucursal)

    resultado = cargar_serie(sesion, carga)
    sesion.commit()
    assert resultado["periodos_cargados"] == len(carga["periodos"])

    reporte = reporte_error_descensura(sesion, id_producto=id_producto, id_sucursal=id_sucursal)

    # Número defendible en examen: se imprime siempre (pytest -s lo muestra).
    with capsys.disabled():
        print("\n=== Reporte de error de descensura (serie sintética) ===")
        print(f"  periodos de quiebre evaluados : {reporte['periodos_quiebre_evaluados']}")
        print(f"  error medio DESCENSURA         : {reporte['error_medio_descensura']}")
        print(f"  error medio SIN CORREGIR       : {reporte['error_medio_sin_corregir']}")
        print(
            f"  descensura mejora              : {reporte['descensura_mejora_sobre_no_corregir']}"
        )
        for camino, det in reporte["detalle_por_camino"].items():
            print(
                f"  [{camino}] periodos={det['periodos']} "
                f"err_descensura={det['error_medio_descensura']} "
                f"err_sin_corregir={det['error_medio_sin_corregir']}"
            )

    assert reporte["descensura_mejora_sobre_no_corregir"] is True, "SC-002"
    err_desc = Decimal(reporte["error_medio_descensura"])
    err_sin = Decimal(reporte["error_medio_sin_corregir"])
    assert err_desc < err_sin * Decimal("0.6"), (
        "la descensura debe reducir el error de forma sustancial, no marginal: "
        f"{err_desc} vs {err_sin}"
    )

    # FR-016: los dos caminos quedan medidos por separado.
    for camino in ("con_consulta_no_atendida", "solo_metodo_base"):
        assert reporte["detalle_por_camino"][camino]["periodos"] > 0
        assert Decimal(reporte["detalle_por_camino"][camino]["error_medio_descensura"]) < Decimal(
            reporte["detalle_por_camino"][camino]["error_medio_sin_corregir"]
        )


def test_recargar_la_serie_sintetica_es_idempotente(sesion):
    id_producto, id_sucursal = _producto_y_sucursal(sesion)
    carga = generar_serie(id_producto, id_sucursal)

    cargar_serie(sesion, carga)
    cargar_serie(sesion, carga)  # segunda carga: reemplaza, no duplica
    sesion.commit()

    reporte = reporte_error_descensura(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    # 6 días de quiebre en el intervalo A + 3 en el B = 9.
    assert reporte["periodos_quiebre_evaluados"] == 9
