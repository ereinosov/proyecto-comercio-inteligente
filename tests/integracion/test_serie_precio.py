"""T045 — Prueba obligatoria (Principio III), FR-025 a FR-028: `precio_vigente_periodo` se
reconstruye de `renglon_venta.precio_aplicado` de 001 (sin depender de ningún histórico de precio
que 001 no conserva); un período sin ventas queda sin corrección de precio (FR-027); un cambio de
precio se atribuye al eje de precio y no a la demanda base. Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.serie_demanda import periodo_local
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.demanda import reconstruir_serie
from tests.apoyo import crear_escenario_basico, sembrar_ventas_diarias

_ZONA = "America/Guayaquil"
_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _dia(atras: int) -> str:
    return periodo_local(_BASE - timedelta(days=atras), _ZONA).isoformat()


def test_precio_por_periodo_reconstruido_de_renglon_venta_y_correccion_al_precio_de_referencia(
    sesion,
):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    # producto.precio_vigente = 2.5000 (precio de referencia). 20 días vendidos a 2.00, 20 a 2.40.
    sembrar_ventas_diarias(
        sesion,
        escenario,
        dias=40,
        cantidad=10,
        precio=lambda i, _f: "2.0000" if i < 20 else "2.4000",
    )

    filas = reconstruir_serie(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
    )
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    dia_barato = por_dia[_dia(40)]
    assert dia_barato["precio_vigente_periodo"] == "2.0000"
    # factor (2.00 / 2.50)^1 = 0.8 -> 10 unidades observadas se normalizan a 8 al precio de hoy.
    assert Decimal(dia_barato["demanda_corregida"]) == Decimal("8.0000")
    assert dia_barato["correccion_precio"] == "-2.0000"
    assert dia_barato["elasticidad_usada"] == "1.0000"

    dia_caro = por_dia[_dia(20)]
    assert dia_caro["precio_vigente_periodo"] == "2.4000"
    # (2.40 / 2.50)^1 = 0.96 -> 10 -> 9.6
    assert Decimal(dia_caro["demanda_corregida"]) == Decimal("9.6000")


def test_periodo_sin_ventas_queda_sin_correccion_de_precio(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto
    # Stock para que NO haya quiebre, pero sin ninguna venta el día -3.
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(100),
        instante=_BASE - timedelta(days=10),
    )
    sesion.commit()

    filas = reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    dia_sin_ventas = por_dia[_dia(3)]
    assert dia_sin_ventas["demanda_observada"] == "0"
    assert dia_sin_ventas["precio_vigente_periodo"] is None
    assert dia_sin_ventas["correccion_precio"] == "0.0000"
    assert dia_sin_ventas["elasticidad_usada"] is None
