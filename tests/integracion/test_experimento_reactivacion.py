"""Suite obligatoria 3 (US3) — ciclo de vida del experimento de reactivación + frontera con 002.
Contra PostgreSQL real, puerto 5442.

- T037: crear asigna grupos y registra la semilla; parámetros inválidos -> 400; segundo
  experimento con uno `en_curso` -> 409; `n_elegibles < 2*n*` -> 'muestra_insuficiente' sin
  asignaciones (FR-025); cerrar calcula tasas + z + veredicto (FR-019 a FR-024); cerrar dos veces
  = mismo resultado; cierre con ventana no vencida o de un 'muestra_insuficiente' -> 409.
- T038: crear/cerrar NO cambia ninguna `senal_fuga` de 002 (FR-028); `id_senal_fuga` inmutable;
  `POST /promociones/redenciones` de reactivación: grupo control -> 400, tratamiento -> 201/200.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.apoyo import crear_escenario_basico
from tests.apoyo_promociones import (
    _venta,
    crear_cliente_churned,
    limpiar_experimentos,
    marcar_fugas,
)

from rasero.api.aplicacion import app
from rasero.errores import (
    CierreExperimentoNoAplicable,
    ExperimentoEnCurso,
    ParametrosExperimentoInvalidos,
)
from rasero.persistencia.modelos import (
    AsignacionExperimento,
    ExperimentoReactivacion,
    SenalFuga,
)
from rasero.servicios.clientes import registrar_visita
from rasero.servicios.experimentos import cerrar_experimento, crear_experimento

cliente_http = TestClient(app)

# MDE alto -> tamaño mínimo de muestra pequeño, para no crear cientos de clientes en la prueba.
# n*(p_c=0.15, MDE=50, alfa=0.05, poder=0.80) = 14; se necesitan >= 28 elegibles.
_MDE_PRUEBA = 50


def _poblar_churned(sesion, escenario, *, n: int, prefijo: str, dias_desde_ultima: int = 150):
    # `dias_desde_ultima` alto: toda visita previa queda ANTES de cualquier `instante_asignacion`
    # que la prueba fije en el pasado, para que no se cuente como retorno espurio.
    for i in range(n):
        crear_cliente_churned(
            sesion,
            escenario,
            nombre=f"{prefijo}-{i}-{datetime.now().timestamp()}",
            dias_desde_ultima=dias_desde_ultima,
        )
    marcar_fugas(sesion)


# --- T037 -------------------------------------------------------------------------


def test_parametros_invalidos_es_400(sesion):
    limpiar_experimentos(sesion)
    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    with pytest.raises(ParametrosExperimentoInvalidos):
        crear_experimento(
            sesion,
            id_sucursal=escenario["sucursal"].id_sucursal,
            ventana_medicion_dias=0,
        )
    with pytest.raises(ParametrosExperimentoInvalidos):
        crear_experimento(
            sesion,
            id_sucursal=escenario["sucursal"].id_sucursal,
            mde_puntos_porcentuales=150,
        )


def test_muestra_insuficiente_sin_asignaciones(sesion):
    limpiar_experimentos(sesion)
    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    _poblar_churned(sesion, escenario, n=5, prefijo="MI")  # 5 << 2*121 con MDE por defecto

    experimento = crear_experimento(sesion, id_sucursal=escenario["sucursal"].id_sucursal)
    sesion.commit()

    assert experimento.veredicto == "muestra_insuficiente"
    assert experimento.n_tratamiento is None
    assert experimento.n_control is None
    n_asignaciones = sesion.execute(
        select(AsignacionExperimento).where(
            AsignacionExperimento.id_experimento_reactivacion
            == experimento.id_experimento_reactivacion
        )
    ).all()
    assert n_asignaciones == []

    with pytest.raises(CierreExperimentoNoAplicable):
        cerrar_experimento(
            sesion, id_experimento_reactivacion=experimento.id_experimento_reactivacion
        )


def test_ciclo_completo_asignacion_cierre_y_veredicto(sesion):
    limpiar_experimentos(sesion)
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000000)
    _poblar_churned(sesion, escenario, n=40, prefijo="CC")

    experimento = crear_experimento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        mde_puntos_porcentuales=_MDE_PRUEBA,
        semilla=20260905,
    )
    sesion.commit()

    assert experimento.veredicto == "en_curso"
    assert experimento.semilla == 20260905
    assert experimento.n_tratamiento + experimento.n_control == 40
    asignaciones = list(
        sesion.execute(
            select(AsignacionExperimento).where(
                AsignacionExperimento.id_experimento_reactivacion
                == experimento.id_experimento_reactivacion
            )
        ).scalars()
    )
    assert len(asignaciones) == 40
    assert {a.grupo for a in asignaciones} == {"tratamiento", "control"}

    # Segundo experimento con uno en curso -> 409.
    with pytest.raises(ExperimentoEnCurso):
        crear_experimento(sesion, id_sucursal=escenario["sucursal"].id_sucursal)

    # Cierre con la ventana no vencida -> 409.
    with pytest.raises(CierreExperimentoNoAplicable):
        cerrar_experimento(
            sesion, id_experimento_reactivacion=experimento.id_experimento_reactivacion
        )

    # Simular retornos: 60% del tratamiento vuelve, 20% del control (incrementalidad grande y
    # significativa a este tamaño). Backdatear `instante_asignacion` para que la ventana venza.
    experimento.instante_asignacion = datetime.now(timezone.utc) - timedelta(days=60)
    sesion.commit()
    tratamiento = [a for a in asignaciones if a.grupo == "tratamiento"]
    control = [a for a in asignaciones if a.grupo == "control"]
    for a in tratamiento[: int(len(tratamiento) * 0.6)]:
        v = _venta(
            sesion,
            escenario,
            instante=experimento.instante_asignacion + timedelta(days=5),
        )
        registrar_visita(sesion, id_cliente=a.id_cliente, id_venta=v.id_venta)
    for a in control[: max(1, int(len(control) * 0.2))]:
        v = _venta(
            sesion,
            escenario,
            instante=experimento.instante_asignacion + timedelta(days=5),
        )
        registrar_visita(sesion, id_cliente=a.id_cliente, id_venta=v.id_venta)

    cerrado = cerrar_experimento(
        sesion, id_experimento_reactivacion=experimento.id_experimento_reactivacion
    )
    sesion.commit()

    assert cerrado.retorno_tratamiento > cerrado.retorno_control
    assert cerrado.incrementalidad > 0
    assert cerrado.veredicto == "efectivo"
    assert cerrado.instante_cierre is not None

    # Idempotente: cerrar de nuevo -> mismo resultado.
    z_1, p_1 = cerrado.estadistico_z, cerrado.valor_p
    otra_vez = cerrar_experimento(
        sesion, id_experimento_reactivacion=experimento.id_experimento_reactivacion
    )
    assert (otra_vez.estadistico_z, otra_vez.valor_p) == (z_1, p_1)


# --- T038 --------------------------------------------------------------------------


def test_frontera_con_002_y_redencion_de_reactivacion(sesion):
    limpiar_experimentos(sesion)
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000000)
    _poblar_churned(sesion, escenario, n=30, prefijo="FR")

    senales_antes = {
        s.id_senal_fuga: (s.estado, s.instante_deteccion)
        for s in sesion.execute(select(SenalFuga)).scalars()
    }

    experimento = crear_experimento(
        sesion,
        id_sucursal=escenario["sucursal"].id_sucursal,
        mde_puntos_porcentuales=_MDE_PRUEBA,
    )
    sesion.commit()

    asignaciones = list(
        sesion.execute(
            select(AsignacionExperimento).where(
                AsignacionExperimento.id_experimento_reactivacion
                == experimento.id_experimento_reactivacion
            )
        ).scalars()
    )
    id_senal_por_asignacion = {a.id_asignacion_experimento: a.id_senal_fuga for a in asignaciones}

    # FR-028: crear el experimento no tocó ninguna senal_fuga.
    senales_despues = {
        s.id_senal_fuga: (s.estado, s.instante_deteccion)
        for s in sesion.execute(select(SenalFuga)).scalars()
    }
    for id_senal, antes in senales_antes.items():
        assert senales_despues[id_senal] == antes

    control = next(a for a in asignaciones if a.grupo == "control")
    tratamiento = next(a for a in asignaciones if a.grupo == "tratamiento")

    venta_c = _venta(sesion, escenario, instante=datetime.now(timezone.utc))
    r_control = cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta_c.id_venta,
            "tipo_origen": "reactivacion",
            "id_asignacion_experimento": control.id_asignacion_experimento,
        },
    )
    assert r_control.status_code == 400
    assert r_control.json()["codigo"] == "redencion_de_grupo_control"

    venta_t = _venta(sesion, escenario, instante=datetime.now(timezone.utc))
    r_trat = cliente_http.post(
        "/promociones/redenciones",
        json={
            "id_venta": venta_t.id_venta,
            "tipo_origen": "reactivacion",
            "id_asignacion_experimento": tratamiento.id_asignacion_experimento,
        },
    )
    assert r_trat.status_code == 201

    # La redención no alteró la asignación (el retorno se computa al cerrar, no aquí).
    sesion.expire_all()
    trat_despues = sesion.get(AsignacionExperimento, tratamiento.id_asignacion_experimento)
    assert trat_despues.retorno is False
    assert (
        id_senal_por_asignacion[trat_despues.id_asignacion_experimento]
        == trat_despues.id_senal_fuga
    )
    _ = Decimal
