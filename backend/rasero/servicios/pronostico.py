"""Generación del pronóstico de demanda a partir de la serie corregida (T036, T037 de
004-pronostico-demanda, User Story 3).

El pronóstico se deriva SIEMPRE de `demanda_corregida`, nunca de `demanda_observada` cruda
(FR-018). Método: suavizado exponencial simple (FR-020, research.md #7) — funciones puras en
`dominio/pronostico.py`. Cada generación es una fila nueva de `pronostico` (append-only,
Principio IV) con sus factores, su período de datos y el valor de la línea base determinista
(FR-021, FR-022).

`vigente = False` cuando el pronóstico no supera su línea base retrospectiva (SC-004) o cuando no
hay histórico suficiente (FR-023). Un producto cuya serie corregida no tiene ningún valor usable
(censura total en toda la ventana) se rechaza con `409` (contracts/openapi.yaml).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.config.pronostico import (
    ALFA_SUAVIZADO,
    DIAS_HORIZONTE_CORTO,
    DIAS_HORIZONTE_MEDIO,
    MINIMO_PERIODOS_POR_TRAMO,
    MINIMO_PERIODOS_SIN_QUIEBRE,
    TRAMOS_MES,
    VENTANA_METODO_BASE_DIAS,
    VENTANA_VALIDACION_RETROSPECTIVA,
)
from rasero.dominio import pronostico as dominio
from rasero.dominio.serie_demanda import periodo_local
from rasero.errores import ErrorDominio, RecursoNoEncontrado
from rasero.persistencia.modelos import (
    DemandaCorregida,
    DemandaObservada,
    Pronostico,
    Producto,
    Sucursal,
)
from rasero.servicios.demanda import reconstruir_serie
from rasero.servicios.demanda_sintetica import es_producto_solo_sintetico

_HORIZONTES = {"corto": DIAS_HORIZONTE_CORTO, "medio": DIAS_HORIZONTE_MEDIO}

MOTIVO_DATOS_INSUFICIENTES = "datos insuficientes"
MOTIVO_NO_SUPERA_LINEA_BASE = "no supera la linea base"
MOTIVO_SIN_VALIDACION = "historia insuficiente para validar contra la linea base"


class PronosticoNoEstimable(ErrorDominio):
    codigo = "pronostico_no_estimable"
    status_code = 409


class HorizonteInvalido(ErrorDominio):
    codigo = "horizonte_invalido"
    status_code = 422


def _serie_activa(
    corregidas: list[DemandaCorregida], observadas_por_dia: dict[date, Decimal]
) -> tuple[list[Decimal], list[Decimal], list[tuple[date, Decimal]], date | None, date | None]:
    """Recorta la serie densa al tramo activo del producto (del primer al último día con demanda
    observada o quiebre) y, dentro de él, descarta los días con censura total o excluidos por
    promoción. Devuelve `(serie_ses, serie_observada, historicos_para_tramo, desde, hasta)`.
    """
    activos = [
        c
        for c in corregidas
        if observadas_por_dia.get(c.periodo, Decimal(0)) > 0 or c.correccion_quiebre > 0
    ]
    if not activos:
        return [], [], [], None, None
    desde, hasta = activos[0].periodo, activos[-1].periodo

    serie_ses: list[Decimal] = []
    serie_obs: list[Decimal] = []
    historicos: list[tuple[date, Decimal]] = []
    for c in corregidas:
        if c.periodo < desde or c.periodo > hasta:
            continue
        if c.censura_total or c.excluido_por_promocion:
            continue
        serie_ses.append(Decimal(c.valor))
        serie_obs.append(observadas_por_dia.get(c.periodo, Decimal(0)))
        historicos.append((c.periodo, Decimal(c.valor)))
    return serie_ses, serie_obs, historicos, desde, hasta


def generar_pronostico(
    sesion: Session, *, id_producto: int, id_sucursal: int, horizonte: str
) -> Pronostico:
    if horizonte not in _HORIZONTES:
        raise HorizonteInvalido("El horizonte debe ser 'corto' o 'medio'.")
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")
    if es_producto_solo_sintetico(sesion, id_producto=id_producto, id_sucursal=id_sucursal):
        raise PronosticoNoEstimable(
            "Ese producto sólo tiene datos sintéticos de validación; no se genera un pronóstico "
            "de producción sobre ellos (FR-017)."
        )

    zona_horaria = sesion.get(Sucursal, id_sucursal).zona_horaria
    hoy_local = periodo_local(datetime.now(timezone.utc), zona_horaria)

    # Materializa la ventana (recompute-on-read) y lee la serie corregida real (no sintética).
    reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    corregidas = list(
        sesion.execute(
            select(DemandaCorregida)
            .where(
                DemandaCorregida.id_producto == id_producto,
                DemandaCorregida.id_sucursal == id_sucursal,
                DemandaCorregida.es_sintetico.is_(False),
            )
            .order_by(DemandaCorregida.periodo)
        ).scalars()
    )
    observadas_por_dia = {
        o.periodo: Decimal(o.cantidad)
        for o in sesion.execute(
            select(DemandaObservada).where(
                DemandaObservada.id_producto == id_producto,
                DemandaObservada.id_sucursal == id_sucursal,
                DemandaObservada.es_sintetico.is_(False),
            )
        ).scalars()
    }

    serie_ses, serie_obs, historicos, datos_desde, datos_hasta = _serie_activa(
        corregidas, observadas_por_dia
    )

    dias_futuros = [hoy_local + timedelta(days=k) for k in range(1, _HORIZONTES[horizonte] + 1)]

    if not serie_ses:
        # Toda la ventana en censura total (o sin actividad): no hay nada de qué partir.
        raise PronosticoNoEstimable(
            "La serie corregida de ese producto no tiene ningún valor estimable "
            "(censura total en toda la ventana); no se puede pronosticar."
        )

    dias_con_demanda = sum(1 for v in serie_obs if v > 0)
    dias_sin_quiebre = sum(
        1
        for c in corregidas
        if datos_desde
        and datos_desde <= c.periodo <= datos_hasta
        and c.correccion_quiebre == 0
        and not c.excluido_por_promocion
    )

    linea_base = dominio.linea_base_promedio_movil(serie_obs, VENTANA_METODO_BASE_DIAS)

    if (
        dias_con_demanda < VENTANA_METODO_BASE_DIAS
        or dias_sin_quiebre < MINIMO_PERIODOS_SIN_QUIEBRE
    ):
        return _persistir(
            sesion,
            id_producto=id_producto,
            id_sucursal=id_sucursal,
            horizonte=horizonte,
            serie_pronosticada=[],
            nivel=Decimal(0),
            multiplicadores=None,
            datos_desde=datos_desde,
            datos_hasta=datos_hasta,
            linea_base=linea_base,
            error_ses=None,
            error_base=None,
            vigente=False,
            motivo=MOTIVO_DATOS_INSUFICIENTES,
        )

    nivel = dominio.suavizado_exponencial_simple(serie_ses, ALFA_SUAVIZADO)
    multiplicadores = (
        dominio.multiplicadores_tramo_mes(
            historicos, TRAMOS_MES, minimo_por_tramo=MINIMO_PERIODOS_POR_TRAMO
        )
        if horizonte == "medio"
        else None
    )
    proyeccion = dominio.proyectar(
        nivel=nivel,
        dias_futuros=dias_futuros,
        multiplicadores=multiplicadores,
        tramos=TRAMOS_MES,
    )
    serie_pronosticada = [{"periodo": d.isoformat(), "valor": f"{v:.4f}"} for d, v in proyeccion]

    error_ses, error_base = dominio.comparar_contra_linea_base(
        corregida=serie_ses,
        observada=serie_obs,
        alfa=ALFA_SUAVIZADO,
        n_linea_base=VENTANA_METODO_BASE_DIAS,
        cola=VENTANA_VALIDACION_RETROSPECTIVA,
    )
    if error_ses is None or error_base is None:
        vigente, motivo = False, MOTIVO_SIN_VALIDACION
    elif error_ses < error_base:
        vigente, motivo = True, None
    else:
        vigente, motivo = False, MOTIVO_NO_SUPERA_LINEA_BASE

    return _persistir(
        sesion,
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        horizonte=horizonte,
        serie_pronosticada=serie_pronosticada,
        nivel=nivel,
        multiplicadores=multiplicadores,
        datos_desde=datos_desde,
        datos_hasta=datos_hasta,
        linea_base=linea_base,
        error_ses=error_ses,
        error_base=error_base,
        vigente=vigente,
        motivo=motivo,
    )


def _persistir(
    sesion: Session,
    *,
    id_producto: int,
    id_sucursal: int,
    horizonte: str,
    serie_pronosticada: list[dict],
    nivel: Decimal,
    multiplicadores: dict[str, str] | None,
    datos_desde: date | None,
    datos_hasta: date | None,
    linea_base: Decimal,
    error_ses: Decimal | None,
    error_base: Decimal | None,
    vigente: bool,
    motivo: str | None,
) -> Pronostico:
    hoy = datetime.now(timezone.utc).date()
    fila = Pronostico(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        horizonte=horizonte,
        dias_horizonte=_HORIZONTES[horizonte],
        serie_pronosticada=serie_pronosticada,
        nivel_suavizado=nivel.quantize(Decimal("0.0001")),
        alfa_usado=ALFA_SUAVIZADO,
        multiplicadores_tramo=multiplicadores,
        periodo_datos_desde=datos_desde or hoy,
        periodo_datos_hasta=datos_hasta or hoy,
        valor_linea_base=linea_base.quantize(Decimal("0.0001")),
        error_retrospectivo=(
            error_ses.quantize(Decimal("0.0001")) if error_ses is not None else None
        ),
        error_linea_base=error_base.quantize(Decimal("0.0001")) if error_base is not None else None,
        vigente=vigente,
        motivo_no_vigente=motivo,
        instante_generacion=datetime.now(timezone.utc),
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def ultimo_pronostico(
    sesion: Session, *, id_producto: int, id_sucursal: int, horizonte: str
) -> Pronostico | None:
    return sesion.execute(
        select(Pronostico)
        .where(
            Pronostico.id_producto == id_producto,
            Pronostico.id_sucursal == id_sucursal,
            Pronostico.horizonte == horizonte,
            Pronostico.es_sintetico.is_(False),
        )
        .order_by(Pronostico.instante_generacion.desc())
        .limit(1)
    ).scalar_one_or_none()


def a_respuesta(fila: Pronostico) -> dict:
    return {
        "id_pronostico": fila.id_pronostico,
        "id_producto": fila.id_producto,
        "id_sucursal": fila.id_sucursal,
        "horizonte": fila.horizonte,
        "dias_horizonte": fila.dias_horizonte,
        "serie_pronosticada": fila.serie_pronosticada,
        "factores": {
            "nivel_suavizado": f"{fila.nivel_suavizado:.4f}",
            "alfa_usado": f"{fila.alfa_usado:.3f}",
            "multiplicadores_tramo": fila.multiplicadores_tramo,
        },
        "periodo_datos_desde": fila.periodo_datos_desde.isoformat(),
        "periodo_datos_hasta": fila.periodo_datos_hasta.isoformat(),
        "valor_linea_base": f"{fila.valor_linea_base:.4f}",
        "error_retrospectivo": (
            f"{fila.error_retrospectivo:.4f}" if fila.error_retrospectivo is not None else None
        ),
        "error_linea_base": (
            f"{fila.error_linea_base:.4f}" if fila.error_linea_base is not None else None
        ),
        "vigente": fila.vigente,
        "motivo_no_vigente": fila.motivo_no_vigente,
        "instante_generacion": fila.instante_generacion,
    }
