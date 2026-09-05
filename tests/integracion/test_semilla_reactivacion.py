"""T048 / quickstart escenario 7 — la utilidad de datos de demostración `rasero.semilla_reactivacion`
crea 325 clientes con `senal_fuga` activa vía los servicios públicos de 001/002 y, con
`simular_retornos`, hace que el experimento cierre en `veredicto = 'efectivo'` de forma
REPRODUCIBLE con `SEMILLA_ALEATORIZACION = 20260905`. Contra PostgreSQL real, puerto 5442.

Lento a propósito (crea ~1000 ventas reales): es la prueba de que el atrezo de la defensa oral
produce un veredicto real, no inventado. `n* = 242` sigue siendo el mínimo de diseño.
"""

from sqlalchemy import select
from tests.apoyo_promociones import limpiar_experimentos

from rasero.persistencia.modelos import ExperimentoReactivacion
from rasero.persistencia.sesion import SesionLocal
from rasero.semilla_reactivacion import N_CLIENTES, sembrar, simular_retornos
from rasero.servicios.experimentos import cerrar_experimento, crear_experimento


def test_demostracion_325_clientes_cierra_en_efectivo(sesion):
    limpiar_experimentos(sesion)

    resumen = sembrar()
    assert resumen["clientes_creados"] == N_CLIENTES
    assert resumen["senales_activas"] >= 242  # margen sobre n* = 242 (research.md #10c)

    experimento = crear_experimento(sesion, id_sucursal=resumen["id_sucursal"])
    sesion.commit()
    assert experimento.veredicto == "en_curso"
    assert experimento.tamano_minimo_muestra == 121  # n* por grupo con la config de arranque
    id_exp = experimento.id_experimento_reactivacion

    retornos = simular_retornos(id_exp, tasa_control=0.15, tasa_tratamiento=0.29)
    assert retornos["tratamiento"]["retornaron"] > retornos["control"]["retornaron"]

    sesion.expire_all()  # `simular_retornos` adelantó instante_asignacion en otra sesión
    cerrado = cerrar_experimento(sesion, id_experimento_reactivacion=id_exp)
    sesion.commit()

    assert cerrado.retorno_tratamiento > cerrado.retorno_control
    assert cerrado.incrementalidad > 0
    assert cerrado.valor_p < cerrado.alfa
    assert cerrado.veredicto == "efectivo"

    # Reproducibilidad: los mismos ids elegibles + la misma semilla dan el mismo reparto.
    guardado = sesion.execute(
        select(ExperimentoReactivacion).where(
            ExperimentoReactivacion.id_experimento_reactivacion == id_exp
        )
    ).scalar_one()
    assert guardado.semilla == 20260905

    print(
        f"\n325 clientes · retorno tratamiento {cerrado.retorno_tratamiento} vs control "
        f"{cerrado.retorno_control} · incrementalidad {cerrado.incrementalidad} · "
        f"z {cerrado.estadistico_z} · p {cerrado.valor_p} · veredicto {cerrado.veredicto}"
    )

    _ = SesionLocal
