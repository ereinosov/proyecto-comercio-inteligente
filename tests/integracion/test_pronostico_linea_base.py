"""T034 — Prueba obligatoria (Principio III), SC-004: un pronóstico que no supera su línea base
determinista no se presenta como vigente; un producto sin histórico suficiente se marca "datos
insuficientes" en vez de recibir un número; un producto sólo sintético se rechaza con 409.
Contra PostgreSQL real, puerto 5442.
"""

import pytest

from rasero.persistencia.modelos import Producto, Sucursal
from rasero.servicios.demanda_sintetica import cargar_serie
from rasero.servicios.pronostico import (
    MOTIVO_DATOS_INSUFICIENTES,
    MOTIVO_NO_SUPERA_LINEA_BASE,
    PronosticoNoEstimable,
    a_respuesta,
    generar_pronostico,
)
from tests.apoyo import crear_escenario_basico, sembrar_ventas_diarias
from tests.utilidades.generador_sintetico import generar_serie
from decimal import Decimal


def test_pronostico_que_sigue_un_cambio_de_nivel_supera_a_la_linea_base(sesion, capsys):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    # 20 días a 6, luego 20 días a 15: el suavizado se adapta, el promedio móvil de 30 días arrastra
    # el nivel viejo mucho más tiempo.
    sembrar_ventas_diarias(sesion, escenario, dias=40, cantidad=lambda i, _f: 6 if i < 20 else 15)

    fila = generar_pronostico(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
        horizonte="corto",
    )
    sesion.commit()
    r = a_respuesta(fila)

    with capsys.disabled():
        print("\n=== Pronóstico vs línea base (cambio de nivel 6 -> 15) ===")
        print(f"  nivel suavizado      : {r['factores']['nivel_suavizado']}")
        print(f"  valor línea base     : {r['valor_linea_base']}")
        print(f"  error retrospectivo  : {r['error_retrospectivo']}")
        print(f"  error línea base     : {r['error_linea_base']}")
        print(f"  vigente              : {r['vigente']}")
        print(f"  pronóstico día 1     : {r['serie_pronosticada'][0]}")

    assert r["vigente"] is True
    assert r["motivo_no_vigente"] is None
    assert Decimal(r["error_retrospectivo"]) < Decimal(r["error_linea_base"])
    assert r["factores"]["alfa_usado"] == "0.300"
    assert len(r["serie_pronosticada"]) == 14
    # El nivel del suavizado ya siguió al 15, no se quedó en el promedio histórico (~10).
    assert Decimal(r["factores"]["nivel_suavizado"]) > Decimal("12")


def test_pronostico_de_demanda_erratica_no_supera_la_linea_base(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    # Alternancia fuerte 4/20: el suavizado persigue el último valor y se equivoca; el promedio
    # móvil predice la media y acierta más.
    sembrar_ventas_diarias(
        sesion, escenario, dias=40, cantidad=lambda i, _f: 4 if i % 2 == 0 else 20
    )

    fila = generar_pronostico(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
        horizonte="corto",
    )
    sesion.commit()

    assert fila.vigente is False
    assert fila.motivo_no_vigente == MOTIVO_NO_SUPERA_LINEA_BASE
    assert fila.error_retrospectivo >= fila.error_linea_base


def test_producto_nuevo_sin_historico_suficiente_no_recibe_numero(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sembrar_ventas_diarias(sesion, escenario, dias=10, cantidad=8)

    fila = generar_pronostico(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
        horizonte="corto",
    )
    sesion.commit()

    assert fila.vigente is False
    assert fila.motivo_no_vigente == MOTIVO_DATOS_INSUFICIENTES
    assert fila.serie_pronosticada == []


def test_producto_solo_sintetico_rechaza_pronostico_de_produccion_con_409(sesion):
    # Resuelve el 409 diferido de la User Story 2 (T022/T026): FR-017.
    sucursal = Sucursal(nombre="Sólo sintético 409", zona_horaria="America/Guayaquil")
    producto = Producto(
        nombre="Sólo sintético",
        es_granel=False,
        precio_vigente=Decimal("1.0000"),
        lleva_caducidad=False,
    )
    sesion.add_all([sucursal, producto])
    sesion.flush()
    cargar_serie(sesion, generar_serie(producto.id_producto, sucursal.id_sucursal))
    sesion.commit()

    with pytest.raises(PronosticoNoEstimable):
        generar_pronostico(
            sesion,
            id_producto=producto.id_producto,
            id_sucursal=sucursal.id_sucursal,
            horizonte="corto",
        )


def test_horizonte_medio_aplica_multiplicadores_de_tramo_del_mes(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sembrar_ventas_diarias(sesion, escenario, dias=45, cantidad=lambda i, _f: 8 + (i % 7))

    fila = generar_pronostico(
        sesion,
        id_producto=escenario["producto"].id_producto,
        id_sucursal=escenario["sucursal"].id_sucursal,
        horizonte="medio",
    )
    sesion.commit()
    r = a_respuesta(fila)

    assert fila.dias_horizonte == 30
    assert len(r["serie_pronosticada"]) == 30
    assert r["factores"]["multiplicadores_tramo"] is not None
