"""T052 — Prueba obligatoria (Principio III), FR-029 a FR-031: un período con promoción activa
(marca inyectada manualmente, simulando la futura entrada de 005) queda EXCLUIDO/marcado en la
serie corregida sin borrar el hecho de `demanda_observada`; la serie no tiene un hueco silencioso.
Contra PostgreSQL real, puerto 5442.

`005-promociones-inteligentes` no existe todavía (FR-030): `marca_promocion_por_dia` devuelve `{}`
en producción. Aquí se parchea para simular que 005 marca un período — ejercita el gancho de
integración de la User Story 5.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from rasero.dominio.serie_demanda import periodo_local
from rasero.persistencia.modelos import DemandaCorregida, DemandaObservada
from rasero.servicios import demanda as servicio_demanda
from rasero.servicios.demanda import reconstruir_serie
from tests.apoyo import crear_escenario_basico, sembrar_ventas_diarias

_ZONA = "America/Guayaquil"
_BASE = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)


def _dia(atras: int):
    return periodo_local(_BASE - timedelta(days=atras), _ZONA)


def test_periodo_promocional_se_marca_excluido_sin_borrar_la_demanda_observada(sesion, monkeypatch):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    sembrar_ventas_diarias(sesion, escenario, dias=20, cantidad=12)

    dia_promo = _dia(10)

    def _promo_simulada(sesion, *, id_producto, id_sucursal, dias):  # noqa: ARG001
        return {dia_promo: True}

    monkeypatch.setattr(servicio_demanda, "marca_promocion_por_dia", _promo_simulada)

    filas = reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    sesion.commit()
    por_dia = {f["periodo"]: f for f in filas}

    fila = por_dia[dia_promo.isoformat()]
    assert fila["con_promocion"] is True
    assert fila["excluido_por_promocion"] is True
    # El período SIGUE presente en la serie — no es un hueco silencioso (FR-031).
    assert fila["demanda_observada"] == "12"

    # demanda_observada no cambia; la exclusión queda registrada en demanda_corregida.
    obs = sesion.get(DemandaObservada, (id_producto, id_sucursal, dia_promo))
    cor = sesion.get(DemandaCorregida, (id_producto, id_sucursal, dia_promo))
    assert obs.cantidad == Decimal(12)
    assert obs.con_promocion is True
    assert cor.excluido_por_promocion is True

    # Un día NO promocional no se marca.
    assert por_dia[_dia(9).isoformat()]["excluido_por_promocion"] is False


def test_sin_005_ningun_periodo_se_marca_como_promocional(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    sembrar_ventas_diarias(sesion, escenario, dias=15, cantidad=10)

    filas = reconstruir_serie(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        id_producto=escenario["producto"].id_producto,
    )
    sesion.commit()

    assert all(f["con_promocion"] is False for f in filas)
    assert all(f["excluido_por_promocion"] is False for f in filas)
