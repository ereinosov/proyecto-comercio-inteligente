"""T009 — Prueba del camino de EVIDENCIA REAL de la descensura (FR-007): cuando existen registros
de `consulta_no_atendida` (de 001) para el intervalo de quiebre de un producto, la corrección
debe apoyarse en ese conteo como evidencia directa de la magnitud de la demanda latente y marcar
`respaldo_quiebre = 'consulta_no_atendida'`, en vez del método base.

001 implementó su User Story 3 (`consulta_no_atendida`, T050-T053) y 004 implementó T014 (rama
de evidencia real, paso (1c) de `reconstruir_serie`). El `xfail` se retiró: la prueba está en
verde.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import ConsultaNoAtendida
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.demanda import reconstruir_serie
from rasero.dominio.serie_demanda import periodo_local
from tests.apoyo import crear_escenario_basico, venta_de_prueba

_ZONA = "America/Guayaquil"
_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _en(dias_atras: int, horas: int = 0) -> datetime:
    return _BASE - timedelta(days=dias_atras) + timedelta(hours=horas)


def test_intervalo_de_quiebre_con_consultas_no_atendidas_usa_ese_conteo_como_evidencia(
    sesion,
):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto"].id_producto

    def _mov(tipo, cantidad, instante):
        extra = {}
        if tipo == "salida_venta":
            extra["id_venta"] = venta_de_prueba(
                sesion, id_turno=escenario["turno"].id_turno, instante=instante
            )
        registrar_movimiento(
            sesion,
            id_sucursal=id_sucursal,
            id_producto=id_producto,
            id_lote=escenario["lote"].id_lote,
            tipo=tipo,
            cantidad=Decimal(cantidad),
            instante=instante,
            **extra,
        )

    # Ventas bajas (2/día) tres días, agota; luego dos días en quiebre.
    _mov("entrada_compra", 6, _en(10))
    _mov("salida_venta", -2, _en(10, horas=1))
    _mov("salida_venta", -2, _en(9))
    _mov("salida_venta", -2, _en(8))  # saldo 0
    sesion.commit()

    # Durante el quiebre (días -7 y -6) se registraron MUCHAS consultas no atendidas: la demanda
    # latente real fue muy superior a las 2/día observadas antes del quiebre.
    for _ in range(15):
        sesion.add(
            ConsultaNoAtendida(
                id_producto=id_producto,
                id_sucursal=id_sucursal,
                id_turno=escenario["turno"].id_turno,
                instante=_en(7, horas=3),
                saldo_en_el_instante=Decimal(0),
            )
        )
    sesion.commit()

    filas = reconstruir_serie(
        sesion, id_sucursal=id_sucursal, id_producto=id_producto, desde=_en(10).date()
    )
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}
    dia_quiebre = por_dia[periodo_local(_en(7), _ZONA).isoformat()]

    assert dia_quiebre["respaldo_quiebre"] == "consulta_no_atendida"
    # El conteo real de consultas (15) debe empujar la corrección MUY por encima del método base
    # (que sólo vería las 2/día previas).
    assert Decimal(dia_quiebre["demanda_corregida"]) >= Decimal(10)
