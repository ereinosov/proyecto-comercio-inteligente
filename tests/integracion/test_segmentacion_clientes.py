"""Prueba obligatoria (Principio III) de la segmentación de clientes — 008, User Story 4.

- tres patrones de compra deliberadamente separados caen juntos ≥ 80 %;
- dos recálculos sobre los mismos datos → asignación idéntica (FR-019, SC-003);
- clientes de 1 visita → `sin_clasificar` (FR-021);
- sin base clasificable → 409;
- estado vacío antes del primer recálculo.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from rasero.errores import SinBaseParaSegmentar
from rasero.persistencia.modelos import AsignacionSegmento, SegmentoCliente, Visita
from rasero.servicios.clientes import registrar_cliente
from rasero.servicios.segmentacion_clientes import leer, recalcular
from tests.apoyo import crear_escenario_basico, venta_de_prueba

_AHORA = datetime.now(timezone.utc)


def _asignacion(sesion) -> dict[int, str]:
    return dict(
        sesion.execute(
            select(AsignacionSegmento.id_cliente, AsignacionSegmento.etiqueta_grupo)
        ).all()
    )


def _cliente_con_visitas(sesion, id_turno, nombre, *, n, cada_dias, ultima_hace_dias, margen):
    c = registrar_cliente(sesion, nombre=nombre, fecha_nacimiento=None)
    for i in range(n):
        offset = ultima_hace_dias + (n - 1 - i) * cada_dias
        inst = _AHORA - timedelta(days=offset)
        id_venta = venta_de_prueba(sesion, id_turno=id_turno, instante=inst)
        sesion.add(
            Visita(
                id_cliente=c.id_cliente,
                id_venta=id_venta,
                instante=inst,
                monto_total=Decimal("10.00"),
                margen_relativo=Decimal(str(margen)),
            )
        )
    return c.id_cliente


def test_segmentacion_separa_patrones_y_es_determinista(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    t = esc["turno"].id_turno
    m = uuid.uuid4().hex[:6]

    frecuentes, dormidos, esporadicos = [], [], []
    for k in range(10):
        frecuentes.append(_cliente_con_visitas(sesion, t, f"F{m}{k}", n=8, cada_dias=4, ultima_hace_dias=3, margen="0.45"))
        dormidos.append(_cliente_con_visitas(sesion, t, f"D{m}{k}", n=6, cada_dias=10, ultima_hace_dias=90, margen="0.30"))
        esporadicos.append(_cliente_con_visitas(sesion, t, f"E{m}{k}", n=3, cada_dias=40, ultima_hace_dias=30, margen="0.10"))
    unicos = [_cliente_con_visitas(sesion, t, f"U{m}{k}", n=1, cada_dias=1, ultima_hace_dias=5, margen="0.2") for k in range(4)]
    sesion.commit()

    r1 = recalcular(sesion)
    assert r1["calculado"] is True

    a1 = _asignacion(sesion)
    for u in unicos:
        assert a1[u] == "sin_clasificar"

    for grupo_ids in (frecuentes, dormidos, esporadicos):
        etiquetas = [a1[i] for i in grupo_ids]
        dominante = max(set(etiquetas), key=etiquetas.count)
        assert dominante != "sin_clasificar"
        assert etiquetas.count(dominante) / len(grupo_ids) >= 0.8

    recalcular(sesion)  # determinismo
    assert a1 == _asignacion(sesion)

    for g in r1["grupos"]:
        assert g["descripcion"]


def test_estado_vacio_antes_del_primer_recalculo(sesion):
    sesion.execute(delete(AsignacionSegmento))
    sesion.execute(delete(SegmentoCliente))
    sesion.commit()

    r = leer(sesion)
    assert r["calculado"] is False
    assert r["grupos"] == []


def test_sin_base_para_segmentar_da_409(sesion):
    sesion.execute(delete(AsignacionSegmento))
    sesion.execute(delete(SegmentoCliente))
    sesion.commit()
    if sesion.execute(select(func.count()).select_from(Visita)).scalar_one() > 0:
        pytest.skip("la base compartida ya tiene visitas de otros tests")
    with pytest.raises(SinBaseParaSegmentar):
        recalcular(sesion)
