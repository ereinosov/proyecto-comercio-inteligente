"""T007 — Prueba obligatoria (Principio III): `reconstruir_serie` materializa `demanda_observada`
y `demanda_corregida` de una ventana, con `dias_en_quiebre` calculado REPLAYANDO
`movimiento_inventario` (nunca leyendo `existencia`, que no es autoritativa — data-model.md de
001), y la corrección por quiebre nunca deja la demanda corregida por debajo de la observada
(FR-006). Contra PostgreSQL real, puerto 5442.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import update

from rasero.dominio.serie_demanda import periodo_local
from rasero.persistencia.modelos import DemandaCorregida, DemandaObservada, Existencia
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.demanda import reconstruir_serie
from tests.apoyo import anulacion_de_prueba, crear_escenario_basico, venta_de_prueba

_ZONA = "America/Guayaquil"
# 12:00 UTC = 07:00 en America/Guayaquil (UTC-5, sin horario de verano): lejos de medianoche
# local, así que el día local de cada instante es estable con independencia de la hora del test.
_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _en(dias_atras: int, horas: int = 0) -> datetime:
    return _BASE - timedelta(days=dias_atras) + timedelta(hours=horas)


def _fecha(atras: int):
    return periodo_local(_en(atras), _ZONA)


def _dia_local(atras: int) -> str:
    return _fecha(atras).isoformat()


def _mov(sesion, escenario, *, tipo, cantidad, instante):
    extra = {}
    if tipo == "salida_venta":
        extra["id_venta"] = venta_de_prueba(
            sesion, id_turno=escenario["turno"].id_turno, instante=instante
        )
    elif tipo == "entrada_anulacion":
        id_venta = venta_de_prueba(sesion, id_turno=escenario["turno"].id_turno, instante=instante)
        extra["id_anulacion_venta"] = anulacion_de_prueba(
            sesion,
            id_venta=id_venta,
            id_operador=escenario["operador"].id_operador,
            instante=instante,
        )
    registrar_movimiento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo=tipo,
        cantidad=Decimal(cantidad),
        instante=instante,
        **extra,
    )


def _escenario_con_quiebre(sesion):
    """30 de existencia el día -10, ventas de 10/día tres días hasta agotar, dos días en quiebre
    total (sin stock, sin ventas), reposición el día -5 y ventas de nuevo.
    """
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    _mov(sesion, escenario, tipo="entrada_compra", cantidad=30, instante=_en(10))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-10, instante=_en(10, horas=1))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-10, instante=_en(9))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-10, instante=_en(8))  # saldo 0
    # días -7 y -6: sin movimientos, saldo 0 -> quiebre total
    _mov(sesion, escenario, tipo="entrada_compra", cantidad=30, instante=_en(5))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-8, instante=_en(5, horas=1))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-9, instante=_en(4))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-7, instante=_en(3))
    sesion.commit()
    return escenario


def test_serie_observada_coincide_con_las_ventas_netas_de_anulaciones(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    _mov(sesion, escenario, tipo="entrada_compra", cantidad=50, instante=_en(6))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-12, instante=_en(6, horas=1))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-3, instante=_en(5))
    # Una anulación el día -5 devuelve 3 unidades: la demanda satisfecha neta de ese día es 0.
    _mov(
        sesion,
        escenario,
        tipo="entrada_anulacion",
        cantidad=3,
        instante=_en(5, horas=2),
    )
    sesion.commit()

    filas = reconstruir_serie(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        desde=_fecha(6),
    )
    sesion.commit()

    por_dia = {f["periodo"]: f for f in filas}
    assert por_dia[_dia_local(6)]["demanda_observada"] == "12"
    assert por_dia[_dia_local(5)]["demanda_observada"] == "0", "venta 3 menos anulación 3"


def test_dias_en_quiebre_se_calculan_replayando_movimientos_no_leyendo_existencia(
    sesion,
):
    escenario = _escenario_con_quiebre(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    # Corrompemos deliberadamente `existencia` a un valor positivo absurdo: si la reconstrucción
    # leyera esta tabla, dejaría de ver el quiebre. Debe seguir viéndolo (replay de movimientos).
    sesion.execute(
        update(Existencia)
        .where(Existencia.id_sucursal == id_sucursal, Existencia.id_producto == id_producto)
        .values(cantidad=Decimal(9999))
    )
    sesion.commit()

    filas = reconstruir_serie(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, desde=_fecha(10)
    )
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    assert por_dia[_dia_local(7)]["dias_en_quiebre"] == "1.000"
    assert por_dia[_dia_local(6)]["dias_en_quiebre"] == "1.000"
    assert por_dia[_dia_local(9)]["dias_en_quiebre"] == "0.000"
    assert por_dia[_dia_local(4)]["dias_en_quiebre"] == "0.000"


def test_demanda_corregida_por_quiebre_nunca_menor_que_la_observada_y_se_materializa(
    sesion,
):
    escenario = _escenario_con_quiebre(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    filas = reconstruir_serie(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, desde=_fecha(10)
    )
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    # Días -7 y -6 en quiebre con demanda observada 0: la corregida sube al máximo de los días
    # recientes sin quiebre (10, 10, 10) -> 10, y nunca por debajo de lo observado (FR-006).
    for atras in (7, 6):
        fila = por_dia[_dia_local(atras)]
        assert fila["demanda_observada"] == "0"
        assert Decimal(fila["demanda_corregida"]) == Decimal("10.0000")
        assert Decimal(fila["demanda_corregida"]) >= Decimal(fila["demanda_observada"])
        assert fila["respaldo_quiebre"] == "metodo_base"
        assert fila["estado"] == "ok"

    # Un día sin quiebre no se toca (FR-011).
    assert por_dia[_dia_local(4)]["demanda_observada"] == "9"
    assert Decimal(por_dia[_dia_local(4)]["demanda_corregida"]) == Decimal("9.0000")
    assert por_dia[_dia_local(4)]["correccion_quiebre"] == "0.0000"

    # Se materializó en ambas tablas.
    obs = sesion.get(DemandaObservada, (id_producto, id_sucursal, _fecha(7)))
    cor = sesion.get(DemandaCorregida, (id_producto, id_sucursal, _fecha(7)))
    assert obs is not None and obs.cantidad == Decimal(0)
    assert cor is not None and cor.valor == Decimal("10.0000")
    assert cor.censura_total is False


def test_censura_total_se_expone_como_no_estimable_no_como_cero(sesion):
    # Producto que tuvo stock hace 40 días pero lleva agotado toda la ventana consultada y sin
    # consultas no atendidas (FR-012): no hay ningún período sin quiebre del cual estimar.
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    _mov(sesion, escenario, tipo="entrada_compra", cantidad=5, instante=_en(40))
    _mov(sesion, escenario, tipo="salida_venta", cantidad=-5, instante=_en(40, horas=1))
    sesion.commit()

    filas = reconstruir_serie(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
        desde=_fecha(10),
    )
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    dia_en_quiebre = por_dia[_dia_local(5)]
    assert dia_en_quiebre["dias_en_quiebre"] == "1.000"
    assert dia_en_quiebre["demanda_corregida"] is None
    assert dia_en_quiebre["estado"] == "no_estimable_censura_total"
