"""T038 — dos sugerencias de colocación distintas pueden apuntar a la misma zona para productos
distintos sin bloquearse (FR-019); aplicar una sugerencia de colocación solo la marca `aplicada`,
nunca reubica nada físico ni escribe en `zona_exhibicion` (FR-017). Contra PostgreSQL real.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from rasero.errores import SugerenciaYaAplicada, RecursoNoEncontrado
from rasero.persistencia.modelos import Lote, Producto, ZonaExhibicion
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.precios import (
    aplicar_sugerencia_colocacion,
    generar_sugerencia_colocacion,
)
from tests.apoyo import crear_escenario_basico


def _agregar_producto_con_costo(sesion, *, id_sucursal: int, costo: str, precio: str) -> int:
    producto = Producto(nombre="Producto colocación", es_granel=False, precio_vigente=Decimal(precio), lleva_caducidad=False)
    sesion.add(producto)
    sesion.flush()
    lote = Lote(
        id_producto=producto.id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal(costo),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=producto.id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(10),
        instante=datetime.now(timezone.utc) - timedelta(days=1),
    )
    return producto.id_producto


def test_dos_sugerencias_pueden_apuntar_a_la_misma_zona_sin_bloquearse(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal

    zona = ZonaExhibicion(id_sucursal=id_sucursal, nombre="Vitrina", grado_privilegio=5)
    sesion.add(zona)
    sesion.commit()

    id_producto_a = _agregar_producto_con_costo(sesion, id_sucursal=id_sucursal, costo="1.0000", precio="2.0000")
    id_producto_b = _agregar_producto_con_costo(sesion, id_sucursal=id_sucursal, costo="1.0000", precio="3.0000")
    sesion.commit()

    sugerencia_a = generar_sugerencia_colocacion(sesion, id_producto=id_producto_a, id_sucursal=id_sucursal)
    sesion.commit()
    sugerencia_b = generar_sugerencia_colocacion(sesion, id_producto=id_producto_b, id_sucursal=id_sucursal)
    sesion.commit()

    assert sugerencia_a.id_zona_exhibicion == zona.id_zona_exhibicion
    assert sugerencia_b.id_zona_exhibicion == zona.id_zona_exhibicion  # única zona: ambas caen ahí


def test_aplicar_sugerencia_de_colocacion_solo_marca_aplicada_no_reubica_nada(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)  # costo 1.00, precio 2.50
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    zona = ZonaExhibicion(id_sucursal=id_sucursal, nombre="Estante frontal", grado_privilegio=10)
    sesion.add(zona)
    sesion.commit()

    sugerencia = generar_sugerencia_colocacion(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()
    assert sugerencia.aplicada is False

    aplicada = aplicar_sugerencia_colocacion(sesion, id_sugerencia_colocacion=sugerencia.id_sugerencia_colocacion)
    sesion.commit()

    assert aplicada.aplicada is True
    assert aplicada.instante_aplicacion is not None

    # No se escribió nada en zona_exhibicion: sigue existiendo una sola zona, sin cambios.
    zonas = list(sesion.query(ZonaExhibicion).filter(ZonaExhibicion.id_sucursal == id_sucursal))
    assert len(zonas) == 1
    assert zonas[0].nombre == "Estante frontal"

    with pytest.raises(SugerenciaYaAplicada):
        aplicar_sugerencia_colocacion(sesion, id_sugerencia_colocacion=sugerencia.id_sugerencia_colocacion)


def test_sin_zonas_catalogadas_no_genera_sugerencia(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=10)
    with pytest.raises(RecursoNoEncontrado):
        generar_sugerencia_colocacion(
            sesion, id_producto=escenario["producto"].id_producto, id_sucursal=escenario["sucursal"].id_sucursal
        )
