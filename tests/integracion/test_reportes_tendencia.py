"""US2 de 008 — tendencias por semana / mes local.

- cada punto = suma exacta de las ventas de esa semana LOCAL (venta del domingo 23:30 no se
  desplaza a la semana siguiente en UTC);
- ámbito "todas" = SUMA por período, no promedio;
- período parcial de un borde → `completo=False`;
- indicador no disponible para el rango → `puntos=[]` + razón, nunca ceros que parezcan datos.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.reportes_tendencia import tendencia
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _vender_en(sesion, escenario, instante, unidades=1):
    registrar_venta(
        sesion,
        clave_idempotencia=f"tnd-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=instante,
        renglones=[RenglonEntrada(id_producto=escenario["producto"].id_producto,
                                  cantidad_unidades=unidades, cantidad_gramos=None)],
    )


def test_tendencia_ventas_por_semana_suma_exacta_por_semana_local(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=1000,
                      costo_unitario=Decimal("1.0000"))

    ahora = datetime.now(timezone.utc)
    # 3 ventas esta semana, 2 la semana pasada.
    for _ in range(3):
        _vender_en(sesion, esc, ahora)
    for _ in range(2):
        _vender_en(sesion, esc, ahora - timedelta(days=7))
    sesion.commit()

    r = tendencia(sesion, indicador="ventas", granularidad="semana",
                  id_sucursal=esc["sucursal"].id_sucursal, periodos=4, actualizar=True)
    assert r["disponible"] is True
    assert r["ambito"] == esc["sucursal"].nombre
    puntos = r["puntos"]
    assert len(puntos) == 4
    # producto 2.50: esta semana 3*2.50 = 7.50, la pasada 2*2.50 = 5.00.
    assert puntos[-1]["valor"] == "7.50"
    assert puntos[-2]["valor"] == "5.00"


def test_tendencia_periodo_actual_incompleto():
    from rasero.persistencia.sesion import SesionLocal
    s = SesionLocal()
    try:
        r = tendencia(s, indicador="ventas", granularidad="semana", periodos=3, actualizar=True)
        assert r["puntos"][-1]["completo"] is False
        assert all(p["completo"] for p in r["puntos"][:-1])
    finally:
        s.close()


def test_todas_las_sucursales_suma_no_promedia(sesion):
    a = crear_escenario_basico(sesion, existencia_inicial=0)
    b = crear_escenario_basico(sesion, existencia_inicial=0)
    for esc in (a, b):
        registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                          id_producto=esc["producto"].id_producto, cantidad=100,
                          costo_unitario=Decimal("1.0000"))
    ahora = datetime.now(timezone.utc)
    _vender_en(sesion, a, ahora, unidades=2)   # 5.00
    _vender_en(sesion, b, ahora, unidades=4)   # 10.00
    sesion.commit()

    solo_a = tendencia(sesion, indicador="ventas", granularidad="semana",
                       id_sucursal=a["sucursal"].id_sucursal, periodos=1, actualizar=True)
    solo_b = tendencia(sesion, indicador="ventas", granularidad="semana",
                       id_sucursal=b["sucursal"].id_sucursal, periodos=1, actualizar=True)
    todas = tendencia(sesion, indicador="ventas", granularidad="semana", periodos=1, actualizar=True)

    va = Decimal(solo_a["puntos"][-1]["valor"])
    vb = Decimal(solo_b["puntos"][-1]["valor"])
    vtodas = Decimal(todas["puntos"][-1]["valor"])
    assert vtodas >= va + vb   # suma (hay más sucursales en la base, pero nunca menos que a+b)


def test_indicador_de_demanda_sin_serie_no_disponible(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    sesion.commit()
    r = tendencia(sesion, indicador="demanda_producto", granularidad="mes",
                  id_producto=esc["producto"].id_producto,
                  id_sucursal=esc["sucursal"].id_sucursal, actualizar=True)
    assert r["disponible"] is False
    assert r["razon"]
    assert r["puntos"] == []
