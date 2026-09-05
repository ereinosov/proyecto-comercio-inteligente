"""T059 — Prueba obligatoria (Principio III): declarar / consultar / retirar una relación de
sustitución (FR-032), y el ajuste cruzado de la descensura por quiebre (FR-009 b) + la señal
cualitativa (FR-033) que esa relación alimenta. Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from rasero.dominio.serie_demanda import periodo_local
from rasero.errores import (
    RecursoNoEncontrado,
    RelacionSustitucionDuplicada,
    RelacionSustitucionInvalida,
)
from rasero.persistencia.modelos import Producto
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios import sustitucion as servicio
from rasero.servicios.demanda import reconstruir_serie
from tests.apoyo import crear_escenario_basico, venta_de_prueba

_ZONA = "America/Guayaquil"
_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _dia(atras: int) -> str:
    return periodo_local(_BASE - timedelta(days=atras), _ZONA).isoformat()


def _otro_producto(sesion, nombre: str) -> int:
    p = Producto(
        nombre=nombre, es_granel=False, precio_vigente=Decimal("2.5000"), lleva_caducidad=False
    )
    sesion.add(p)
    sesion.flush()
    return p.id_producto


def test_declarar_listar_y_retirar_una_relacion_de_sustitucion(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    a = escenario["producto"].id_producto
    b = _otro_producto(sesion, "Sustituto B")
    sesion.commit()

    rel = servicio.declarar(sesion, id_producto=a, id_producto_sustituto=b)
    sesion.commit()
    assert rel.id_producto == a and rel.id_producto_sustituto == b

    assert len(servicio.listar(sesion, id_producto=a)) == 1

    # Relación mutua = dos filas.
    servicio.declarar(sesion, id_producto=b, id_producto_sustituto=a)
    sesion.commit()
    assert len(servicio.listar(sesion)) == 2

    servicio.retirar(sesion, id_sustitucion_producto=rel.id_sustitucion_producto)
    sesion.commit()
    assert len(servicio.listar(sesion, id_producto=a)) == 0


def test_reglas_de_declaracion(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    a = escenario["producto"].id_producto
    b = _otro_producto(sesion, "Sustituto")
    sesion.commit()

    with pytest.raises(RelacionSustitucionInvalida):
        servicio.declarar(sesion, id_producto=a, id_producto_sustituto=a)

    with pytest.raises(RecursoNoEncontrado):
        servicio.declarar(sesion, id_producto=a, id_producto_sustituto=999999)

    servicio.declarar(sesion, id_producto=a, id_producto_sustituto=b)
    sesion.commit()
    with pytest.raises(RelacionSustitucionDuplicada):
        servicio.declarar(sesion, id_producto=a, id_producto_sustituto=b)


def test_ajuste_cruzado_suma_el_exceso_del_sustituto_y_senala_su_serie(sesion, capsys):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_turno = escenario["turno"].id_turno
    id_lote = escenario["lote"].id_lote
    p_original = escenario["producto"].id_producto  # "azúcar morena"
    p_sustituto = _otro_producto(sesion, "azúcar blanca")
    sesion.commit()

    servicio.declarar(sesion, id_producto=p_original, id_producto_sustituto=p_sustituto)
    sesion.commit()

    def _venta(pid, cant, atras):
        registrar_movimiento(
            sesion,
            id_sucursal=id_sucursal,
            id_producto=pid,
            id_lote=id_lote,
            tipo="salida_venta",
            cantidad=Decimal(-cant),
            instante=_BASE - timedelta(days=atras),
            id_venta=venta_de_prueba(
                sesion, id_turno=id_turno, instante=_BASE - timedelta(days=atras)
            ),
        )

    # Original: entrada EXACTA de 300, 10/día 30 días (-34..-5) hasta agotar; luego quiebre -4..-1.
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=p_original,
        id_lote=id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(300),
        instante=_BASE - timedelta(days=35),
    )
    for atras in range(34, 4, -1):
        _venta(p_original, 10, atras)

    # Sustituto: siempre con stock. 8/día su nivel típico; durante el quiebre del original
    # (días -4..-1) vende 15/día -> exceso 7/día.
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=p_sustituto,
        id_lote=id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(1000),
        instante=_BASE - timedelta(days=36),
    )
    for atras in range(34, 4, -1):
        _venta(p_sustituto, 8, atras)
    for atras in (4, 3, 2, 1):
        _venta(p_sustituto, 15, atras)
    sesion.commit()

    filas_original = {
        f["periodo"]: f
        for f in reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=p_original)
    }
    filas_sustituto = {
        f["periodo"]: f
        for f in reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=p_sustituto)
    }
    sesion.commit()

    dia_quiebre = filas_original[_dia(3)]
    with capsys.disabled():
        print("\n=== Ajuste cruzado por sustituto (día en quiebre del original) ===")
        print(f"  demanda observada original : {dia_quiebre['demanda_observada']}")
        print(f"  método base (10) + exceso del sustituto (7)")
        print(f"  demanda corregida original : {dia_quiebre['demanda_corregida']}")
        print(f"  ajuste_cruzado_sustituto   : {dia_quiebre['ajuste_cruzado_sustituto']}")
        print(f"  señal en la serie del sustituto: {filas_sustituto[_dia(3)]['senal_sustitucion']}")

    # Método base (máx de días recientes sin quiebre = 10) + exceso del sustituto (15 - 8 = 7).
    assert Decimal(dia_quiebre["ajuste_cruzado_sustituto"]) == Decimal("7.0000")
    assert Decimal(dia_quiebre["demanda_corregida"]) == Decimal("17.0000")

    # La serie del sustituto lleva la señal cualitativa (FR-033), sin descontarle volumen (FR-034).
    senal = filas_sustituto[_dia(3)]["senal_sustitucion"]
    assert senal is not None
    assert senal["id_producto_en_quiebre"] == p_original
    assert filas_sustituto[_dia(3)]["demanda_observada"] == "15"  # no se le descuenta nada
