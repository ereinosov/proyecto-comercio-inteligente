"""Servicio del experimento de reactivación (005-promociones-inteligentes, US3).

- `crear_experimento` (T040) — toma los clientes con `senal_fuga` ACTIVA de 002 (reutiliza la
  detección de fuga silenciosa; no crea un criterio nuevo — FR-015), calcula el tamaño mínimo de
  muestra y, si alcanza, reparte por aleatorización real con semilla fija en tratamiento/control
  (sólo el tratamiento con derecho al descuento — FR-018). Si no alcanza, crea el experimento con
  `veredicto='muestra_insuficiente'` sin asignaciones (FR-025). `400` por parámetros inválidos,
  `409` si ya hay uno `en_curso`. NUNCA modifica `senal_fuga` (FR-028): lee su estado y su id.
- `cerrar_experimento` (T041) — al vencer la ventana, fija `retorno` de cada asignación mirando
  `visita` de 002 (research.md #11), calcula tasas por grupo, la prueba z de dos proporciones y
  el veredicto (FR-019 a FR-024). Idempotente.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.config import promociones as cfg
from rasero.dominio.experimento import (
    asignar_grupos,
    prueba_z_dos_proporciones,
    tamano_minimo_muestra,
)
from rasero.dominio.experimento import (
    veredicto as calcular_veredicto,
)
from rasero.errores import (
    CierreExperimentoNoAplicable,
    ExperimentoEnCurso,
    ParametrosExperimentoInvalidos,
    RecursoNoEncontrado,
)
from rasero.persistencia.modelos import (
    AsignacionExperimento,
    Campania,
    ExperimentoReactivacion,
    SenalFuga,
    Sucursal,
    Turno,
    Venta,
    Visita,
)

_CIEN = Decimal("100")


def _a_decimal(valor, defecto: Decimal) -> Decimal:
    if valor is None:
        return defecto
    return Decimal(str(valor))


def crear_experimento(
    sesion: Session,
    *,
    id_sucursal: int | None = None,
    semilla: int | None = None,
    ventana_medicion_dias: int | None = None,
    porcentaje_descuento=None,
    mde_puntos_porcentuales=None,
    nombre_campania: str | None = None,
) -> ExperimentoReactivacion:
    semilla = cfg.SEMILLA_ALEATORIZACION if semilla is None else int(semilla)
    ventana = (
        cfg.VENTANA_MEDICION_REACTIVACION_DIAS
        if ventana_medicion_dias is None
        else int(ventana_medicion_dias)
    )
    pct_descuento = _a_decimal(porcentaje_descuento, cfg.DESCUENTO_REACTIVACION_PCT)
    mde = _a_decimal(mde_puntos_porcentuales, cfg.MDE_REACTIVACION_PP)

    if ventana <= 0:
        raise ParametrosExperimentoInvalidos("La ventana de medición debe ser de al menos 1 día.")
    if not (Decimal(0) < mde < _CIEN):
        raise ParametrosExperimentoInvalidos(
            "El efecto mínimo detectable debe estar entre 0 y 100 puntos porcentuales."
        )
    if not (Decimal(0) < pct_descuento < _CIEN):
        raise ParametrosExperimentoInvalidos("El porcentaje de descuento debe estar entre 0 y 100.")

    if id_sucursal is not None and sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    en_curso = sesion.execute(
        select(ExperimentoReactivacion.id_experimento_reactivacion).where(
            ExperimentoReactivacion.veredicto == "en_curso"
        )
    ).scalar_one_or_none()
    if en_curso is not None:
        raise ExperimentoEnCurso()

    ahora = datetime.now(timezone.utc)
    elegibles = _elegibles(sesion, id_sucursal=id_sucursal)

    n_star = tamano_minimo_muestra(
        p_control=cfg.TASA_RETORNO_BASE_ESPERADA,
        mde_puntos_porcentuales=mde,
        z_alfa_medios=cfg.Z_ALFA_MEDIOS,
        z_beta=cfg.Z_BETA,
    )

    campania = Campania(
        tipo="reactivacion",
        id_sucursal=id_sucursal,
        nombre=nombre_campania or f"Reactivación {date.today().isoformat()}",
        ventana_desde=date.today(),
        ventana_hasta=date.today() + timedelta(days=ventana),
        instante_creacion=ahora,
    )
    sesion.add(campania)
    sesion.flush()

    experimento = ExperimentoReactivacion(
        id_campania=campania.id_campania,
        id_sucursal=id_sucursal,
        semilla=semilla,
        algoritmo=cfg.ALGORITMO_ALEATORIZACION,
        proporcion_tratamiento=cfg.PROPORCION_TRATAMIENTO,
        ventana_medicion_dias=ventana,
        porcentaje_descuento=pct_descuento,
        tasa_retorno_base_esperada=cfg.TASA_RETORNO_BASE_ESPERADA,
        mde_puntos_porcentuales=mde,
        alfa=cfg.ALFA_SIGNIFICANCIA,
        poder=cfg.PODER_ESTADISTICO,
        tamano_minimo_muestra=n_star,
        n_elegibles=len(elegibles),
        instante_asignacion=ahora,
    )

    if len(elegibles) < 2 * n_star:
        experimento.veredicto = "muestra_insuficiente"
        sesion.add(experimento)
        sesion.flush()
        return experimento

    experimento.veredicto = "en_curso"
    sesion.add(experimento)
    sesion.flush()

    grupos = asignar_grupos(
        [id_cliente for id_cliente, _ in elegibles],
        semilla=semilla,
        proporcion_tratamiento=cfg.PROPORCION_TRATAMIENTO,
    )
    n_t = n_c = 0
    for id_cliente, id_senal_fuga in elegibles:
        grupo = grupos[id_cliente]
        n_t += grupo == "tratamiento"
        n_c += grupo == "control"
        sesion.add(
            AsignacionExperimento(
                id_experimento_reactivacion=experimento.id_experimento_reactivacion,
                id_cliente=id_cliente,
                id_senal_fuga=id_senal_fuga,
                grupo=grupo,
                retorno=False,
            )
        )
    experimento.n_tratamiento = n_t
    experimento.n_control = n_c
    sesion.flush()
    return experimento


def _elegibles(sesion: Session, *, id_sucursal: int | None) -> list[tuple[int, int]]:
    """`(id_cliente, id_senal_fuga)` de los clientes con `senal_fuga.estado = 'activa'` en 002.
    Con `id_sucursal`, sólo los cuya ÚLTIMA visita fue en esa sucursal (data-model.md).
    """
    filas = sesion.execute(
        select(SenalFuga.id_cliente, SenalFuga.id_senal_fuga).where(SenalFuga.estado == "activa")
    ).all()
    if id_sucursal is None:
        return [(c, s) for c, s in filas]

    elegibles = []
    for id_cliente, id_senal_fuga in filas:
        sucursal_ultima = sesion.execute(
            select(Turno.id_sucursal)
            .join(Venta, Venta.id_turno == Turno.id_turno)
            .join(Visita, Visita.id_venta == Venta.id_venta)
            .where(Visita.id_cliente == id_cliente)
            .order_by(Visita.instante.desc())
            .limit(1)
        ).scalar_one_or_none()
        if sucursal_ultima == id_sucursal:
            elegibles.append((id_cliente, id_senal_fuga))
    return elegibles


def cerrar_experimento(
    sesion: Session, *, id_experimento_reactivacion: int
) -> ExperimentoReactivacion:
    experimento = sesion.get(ExperimentoReactivacion, id_experimento_reactivacion)
    if experimento is None:
        raise RecursoNoEncontrado(f"El experimento {id_experimento_reactivacion} no existe.")
    if experimento.veredicto == "muestra_insuficiente":
        raise CierreExperimentoNoAplicable(
            "Este experimento se marcó 'muestra insuficiente': no hay grupos que medir."
        )
    if experimento.instante_cierre is not None:
        return experimento  # idempotente: ya cerrado, mismo resultado

    fin_ventana = experimento.instante_asignacion + timedelta(
        days=experimento.ventana_medicion_dias
    )
    if datetime.now(timezone.utc) < fin_ventana:
        raise CierreExperimentoNoAplicable("La ventana de medición todavía no ha vencido.")

    asignaciones = list(
        sesion.execute(
            select(AsignacionExperimento).where(
                AsignacionExperimento.id_experimento_reactivacion == id_experimento_reactivacion
            )
        ).scalars()
    )

    retornos = {"tratamiento": 0, "control": 0}
    totales = {"tratamiento": 0, "control": 0}
    for asignacion in asignaciones:
        totales[asignacion.grupo] += 1
        primera = sesion.execute(
            select(Visita.id_venta, Visita.instante)
            .where(
                Visita.id_cliente == asignacion.id_cliente,
                Visita.instante >= experimento.instante_asignacion,
                Visita.instante <= fin_ventana,
            )
            .order_by(Visita.instante.asc())
            .limit(1)
        ).first()
        if primera is not None:
            asignacion.retorno = True
            asignacion.id_venta_retorno = primera[0]
            asignacion.instante_retorno = primera[1]
            retornos[asignacion.grupo] += 1

    resultado = prueba_z_dos_proporciones(
        retornos["tratamiento"],
        totales["tratamiento"],
        retornos["control"],
        totales["control"],
    )
    experimento.retorno_tratamiento = resultado.retorno_tratamiento
    experimento.retorno_control = resultado.retorno_control
    experimento.incrementalidad = resultado.incrementalidad
    experimento.estadistico_z = resultado.estadistico_z
    experimento.valor_p = resultado.valor_p
    experimento.veredicto = calcular_veredicto(
        resultado.incrementalidad, resultado.valor_p, experimento.alfa
    )
    experimento.instante_cierre = datetime.now(timezone.utc)
    sesion.flush()
    return experimento


def obtener_experimento(
    sesion: Session, *, id_experimento_reactivacion: int
) -> ExperimentoReactivacion:
    experimento = sesion.get(ExperimentoReactivacion, id_experimento_reactivacion)
    if experimento is None:
        raise RecursoNoEncontrado(f"El experimento {id_experimento_reactivacion} no existe.")
    return experimento


def listar_asignaciones(
    sesion: Session, *, id_experimento_reactivacion: int, grupo: str | None = None
) -> list[dict]:
    obtener_experimento(sesion, id_experimento_reactivacion=id_experimento_reactivacion)
    stmt = (
        select(AsignacionExperimento)
        .where(AsignacionExperimento.id_experimento_reactivacion == id_experimento_reactivacion)
        .order_by(AsignacionExperimento.id_asignacion_experimento)
    )
    if grupo is not None:
        stmt = stmt.where(AsignacionExperimento.grupo == grupo)
    return [
        {
            "id_asignacion_experimento": a.id_asignacion_experimento,
            "id_experimento_reactivacion": a.id_experimento_reactivacion,
            "id_cliente": a.id_cliente,
            "id_senal_fuga": a.id_senal_fuga,
            "grupo": a.grupo,
            "retorno": a.retorno,
            "id_venta_retorno": a.id_venta_retorno,
            "instante_retorno": a.instante_retorno,
        }
        for a in sesion.execute(stmt).scalars()
    ]


def _motivo_muestra_insuficiente(e: ExperimentoReactivacion) -> str | None:
    if e.veredicto != "muestra_insuficiente":
        return None
    return (
        f"{e.n_elegibles} elegibles, mínimo {2 * e.tamano_minimo_muestra} "
        f"(MDE {e.mde_puntos_porcentuales:.0f} pp, poder {e.poder:.2f})"
    )


def experimento_a_respuesta(e: ExperimentoReactivacion) -> dict:
    def dec(v, fmt):
        return format(v, fmt) if v is not None else None

    return {
        "id_experimento_reactivacion": e.id_experimento_reactivacion,
        "id_campania": e.id_campania,
        "id_sucursal": e.id_sucursal,
        "semilla": e.semilla,
        "algoritmo": e.algoritmo,
        "proporcion_tratamiento": f"{e.proporcion_tratamiento:.3f}",
        "ventana_medicion_dias": e.ventana_medicion_dias,
        "porcentaje_descuento": f"{e.porcentaje_descuento:.2f}",
        "parametros_muestra": {
            "tasa_retorno_base_esperada": f"{e.tasa_retorno_base_esperada:.4f}",
            "mde_puntos_porcentuales": f"{e.mde_puntos_porcentuales:.2f}",
            "alfa": f"{e.alfa:.3f}",
            "poder": f"{e.poder:.3f}",
            "tamano_minimo_muestra": e.tamano_minimo_muestra,
        },
        "n_elegibles": e.n_elegibles,
        "n_tratamiento": e.n_tratamiento,
        "n_control": e.n_control,
        "retorno_tratamiento": dec(e.retorno_tratamiento, ".4f"),
        "retorno_control": dec(e.retorno_control, ".4f"),
        "incrementalidad": dec(e.incrementalidad, ".4f"),
        "estadistico_z": dec(e.estadistico_z, ".5f"),
        "valor_p": dec(e.valor_p, ".6f"),
        "veredicto": e.veredicto,
        "motivo_muestra_insuficiente": _motivo_muestra_insuficiente(e),
        "instante_asignacion": e.instante_asignacion,
        "instante_cierre": e.instante_cierre,
    }
