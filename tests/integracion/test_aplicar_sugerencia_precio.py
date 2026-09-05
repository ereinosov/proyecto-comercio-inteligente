"""T027 — aplicar una sugerencia de precio crea o actualiza `producto_precio_sucursal` vía
`fijar_precio_sucursal` (T002) y deja registro de qué sugerencia lo originó (FR-013); aplicar la
misma sugerencia dos veces devuelve 409 en la segunda. Contra PostgreSQL real.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from rasero.errores import SugerenciaYaAplicada
from rasero.persistencia.modelos import CanalCompetencia, ObservacionPrecio, ProductoPrecioSucursal
from rasero.servicios.precios import (
    aplicar_sugerencia_precio,
    asignar_rol_producto,
    generar_sugerencia_precio,
)
from tests.apoyo import crear_escenario_basico


def _capturar_observacion(sesion, *, id_producto: int, precio_observado: str) -> None:
    canal = CanalCompetencia(nombre="Canal de prueba", nombre_normalizado="canal-de-prueba")
    sesion.add(canal)
    sesion.flush()
    sesion.add(
        ObservacionPrecio(
            id_producto=id_producto,
            id_canal_competencia=canal.id_canal_competencia,
            presentacion_cantidad="1",
            presentacion_unidad="unidad",
            precio_observado=precio_observado,
            fuente="prueba",
            origen_captura="manual",
            instante_captura=datetime.now(timezone.utc),
            comparable=True,
        )
    )
    sesion.commit()


def test_aplicar_sugerencia_crea_override_con_el_precio_sugerido(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio 2.50
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    asignar_rol_producto(sesion, id_producto=id_producto, rol="gancho_trafico")
    sesion.commit()
    _capturar_observacion(sesion, id_producto=id_producto, precio_observado="2.0000")

    sugerencia = generar_sugerencia_precio(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()
    assert sugerencia.precio_sugerido == Decimal("2.0000")
    assert sugerencia.aplicada is False

    aplicada = aplicar_sugerencia_precio(sesion, id_sugerencia_precio=sugerencia.id_sugerencia_precio)
    sesion.commit()

    assert aplicada.aplicada is True
    assert aplicada.instante_aplicacion is not None

    override = sesion.execute(
        select(ProductoPrecioSucursal).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one()
    assert override.precio_vigente == Decimal("2.0000")


def test_aplicar_la_misma_sugerencia_dos_veces_falla_la_segunda(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    sugerencia = generar_sugerencia_precio(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()

    aplicar_sugerencia_precio(sesion, id_sugerencia_precio=sugerencia.id_sugerencia_precio)
    sesion.commit()

    with pytest.raises(SugerenciaYaAplicada):
        aplicar_sugerencia_precio(sesion, id_sugerencia_precio=sugerencia.id_sugerencia_precio)
