"""T019 — asignar un rol lo persiste y lo refleja en consultas posteriores (FR-005); cambiar el
rol sobrescribe `instante_asignacion` sin dejar historial (research.md #3); un producto nunca
clasificado queda "sin clasificar" (FR-007). Contra PostgreSQL real.

Nota de alcance (mismo criterio que T006): esta prueba toca la base de datos real
(`rol_producto`), así que vive en `tests/integracion/`, no en `tests/unidad/` — este repo reserva
`tests/unidad/` a funciones puras (ver la corrección ya documentada en tasks.md para T006).
"""

from rasero.persistencia.modelos import RolProducto
from rasero.servicios.precios import asignar_rol_producto
from tests.apoyo import crear_escenario_basico


def test_asignar_rol_lo_persiste_y_lo_refleja(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto

    fila = asignar_rol_producto(sesion, id_producto=id_producto, rol="gancho_trafico")
    sesion.commit()

    assert fila.rol == "gancho_trafico"
    releida = sesion.get(RolProducto, id_producto)
    assert releida.rol == "gancho_trafico"


def test_cambiar_el_rol_sobrescribe_en_vez_de_acumular_historial(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto

    asignar_rol_producto(sesion, id_producto=id_producto, rol="gancho_trafico")
    sesion.commit()
    primer_instante = sesion.get(RolProducto, id_producto).instante_asignacion

    asignar_rol_producto(sesion, id_producto=id_producto, rol="generador_margen")
    sesion.commit()

    filas = list(sesion.query(RolProducto).filter(RolProducto.id_producto == id_producto))
    assert len(filas) == 1, "sobrescribe la fila existente; no acumula historial (research.md #3)"
    assert filas[0].rol == "generador_margen"
    assert filas[0].instante_asignacion >= primer_instante


def test_producto_sin_clasificar_no_tiene_fila(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sesion.commit()

    assert sesion.get(RolProducto, escenario["producto"].id_producto) is None
