"""Validación de la descensura contra series sintéticas con demanda latente CONOCIDA (T024, T025,
T026 de 004-pronostico-demanda, User Story 2).

Es la única forma de comprobar que el método base de descensura de FR-009 (a) funciona mientras
`001` no implemente `consulta_no_atendida` (User Story 3, bloqueo documentado en plan.md): se
genera una serie donde la demanda latente de cada período de quiebre es un valor conocido de
antemano —no observado—, se corre EXACTAMENTE la misma función de dominio que usa producción
(`corregir_serie_por_quiebre`), y se mide cuánto se acerca la demanda corregida a ese valor
verdadero frente a no corregir nada. `reporte_error_descensura` es esa medición: es la prueba de
fondo de que la corrección acerca la serie a la realidad en vez de alejarla (SC-002).

Aislamiento (FR-017): las filas sintéticas viven en las MISMAS tablas (`demanda_observada`,
`demanda_corregida`) para ejercer el mismo código, distinguidas por `es_sintetico = TRUE`. Toda
consulta de pronóstico de producción las excluye: `GET /demanda` se reconstruye desde
`movimiento_inventario` (que un producto sintético no tiene), el upsert de producción lleva
`WHERE es_sintetico = FALSE`, y `generar_pronostico` (User Story 3) rechaza un producto sólo
sintético con `es_producto_solo_sintetico`.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from rasero.config.pronostico import VENTANA_METODO_BASE_DIAS
from rasero.dominio.censura import PeriodoObservado, corregir_serie_por_quiebre
from rasero.errores import RecursoNoEncontrado, SerieSinteticaInvalida
from rasero.persistencia.modelos import (
    DemandaCorregida,
    DemandaObservada,
    MovimientoInventario,
    Producto,
    Sucursal,
)

CAMINO_CON_CONSULTA = "con_consulta_no_atendida"
CAMINO_SOLO_METODO_BASE = "solo_metodo_base"


def _dec(valor) -> Decimal:
    return Decimal(str(valor))


def _fmt4(valor: Decimal) -> str:
    return f"{valor:.4f}"


def _promedio(valores: list[Decimal]) -> Decimal:
    if not valores:
        return Decimal(0)
    return sum(valores, Decimal(0)) / Decimal(len(valores))


def cargar_serie(sesion: Session, carga: dict) -> dict:
    """Inserta una serie histórica sintética (FR-013, FR-016). Idempotente: recargar reemplaza la
    serie sintética previa del mismo producto y sucursal. Deriva `demanda_corregida` con la misma
    función de dominio que producción, para que la validación mida el código real.
    """
    id_producto = int(carga["id_producto"])
    id_sucursal = int(carga["id_sucursal"])
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    consultas: dict[date, int] = {
        date.fromisoformat(c["periodo"]): int(c["conteo"])
        for c in carga.get("consultas_no_atendidas_sinteticas", [])
    }

    filas: list[dict] = []
    for p in carga.get("periodos", []):
        periodo = date.fromisoformat(p["periodo"])
        latente = p.get("demanda_latente_verdadera")
        filas.append(
            {
                "periodo": periodo,
                "cantidad": _dec(p["demanda_observada"]),
                "dias_en_quiebre": _dec(p["dias_en_quiebre"]),
                "demanda_latente_verdadera": _dec(latente) if latente is not None else None,
                "consultas_no_atendidas_sinteticas": consultas.get(periodo),
            }
        )

    _validar_fr016(filas)

    sesion.execute(
        delete(DemandaObservada).where(
            DemandaObservada.id_producto == id_producto,
            DemandaObservada.id_sucursal == id_sucursal,
            DemandaObservada.es_sintetico.is_(True),
        )
    )
    sesion.execute(
        delete(DemandaCorregida).where(
            DemandaCorregida.id_producto == id_producto,
            DemandaCorregida.id_sucursal == id_sucursal,
            DemandaCorregida.es_sintetico.is_(True),
        )
    )

    ahora = datetime.now(timezone.utc)
    sesion.execute(
        insert(DemandaObservada),
        [
            {
                "id_producto": id_producto,
                "id_sucursal": id_sucursal,
                "periodo": f["periodo"],
                "cantidad": f["cantidad"],
                "dias_en_quiebre": f["dias_en_quiebre"],
                "precio_vigente_periodo": None,
                "con_promocion": False,
                "es_sintetico": True,
                "demanda_latente_verdadera": f["demanda_latente_verdadera"],
                "consultas_no_atendidas_sinteticas": f["consultas_no_atendidas_sinteticas"],
                "instante_materializacion": ahora,
            }
            for f in filas
        ],
    )

    corregidos = corregir_serie_por_quiebre(
        [
            PeriodoObservado(
                periodo=f["periodo"], cantidad=f["cantidad"], dias_en_quiebre=f["dias_en_quiebre"]
            )
            for f in filas
        ],
        n=VENTANA_METODO_BASE_DIAS,
    )
    sesion.execute(
        insert(DemandaCorregida),
        [
            {
                "id_producto": id_producto,
                "id_sucursal": id_sucursal,
                "periodo": c.periodo,
                "valor_observado": c.valor_observado,
                "valor": c.valor if c.valor is not None else Decimal(0),
                "correccion_quiebre": c.correccion_quiebre,
                "respaldo_quiebre": c.respaldo_quiebre,
                "ajuste_cruzado_sustituto": Decimal(0),
                "correccion_precio": Decimal(0),
                "elasticidad_usada": None,
                "excluido_por_promocion": False,
                "censura_total": c.censura_total,
                "es_sintetico": True,
                "instante_materializacion": ahora,
            }
            for c in corregidos
        ],
    )
    sesion.flush()
    return {
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "periodos_cargados": len(filas),
    }


def _validar_fr016(filas: list[dict]) -> None:
    hay_sin_quiebre = any(f["dias_en_quiebre"] == 0 for f in filas)
    quiebres = [f for f in filas if f["dias_en_quiebre"] > 0]
    if not hay_sin_quiebre or not quiebres:
        raise SerieSinteticaInvalida(
            "La serie sintética debe incluir períodos con quiebre y sin quiebre (FR-016)."
        )
    if any(f["demanda_latente_verdadera"] is None for f in quiebres):
        raise SerieSinteticaInvalida(
            "Todo período de quiebre sintético debe declarar su demanda_latente_verdadera "
            "(FR-013)."
        )
    con_consulta = [f for f in quiebres if f["consultas_no_atendidas_sinteticas"] is not None]
    sin_consulta = [f for f in quiebres if f["consultas_no_atendidas_sinteticas"] is None]
    if not con_consulta or not sin_consulta:
        raise SerieSinteticaInvalida(
            "La serie sintética debe incluir al menos un período de quiebre CON consultas no "
            "atendidas y uno SIN, para ejercer por separado los caminos de FR-007 y FR-008 "
            "(FR-016)."
        )


def es_producto_solo_sintetico(sesion: Session, *, id_producto: int, id_sucursal: int) -> bool:
    """True si el producto tiene serie sintética en esa sucursal y NINGÚN movimiento de inventario
    real. `generar_pronostico` (User Story 3) lo usa para rechazar con 409 un pronóstico de
    producción sobre datos sólo sintéticos (FR-017).
    """
    tiene_sintetico = (
        sesion.execute(
            select(DemandaObservada.periodo)
            .where(
                DemandaObservada.id_producto == id_producto,
                DemandaObservada.id_sucursal == id_sucursal,
                DemandaObservada.es_sintetico.is_(True),
            )
            .limit(1)
        ).first()
        is not None
    )
    tiene_movimiento = (
        sesion.execute(
            select(MovimientoInventario.id_movimiento_inventario)
            .where(
                MovimientoInventario.id_producto == id_producto,
                MovimientoInventario.id_sucursal == id_sucursal,
            )
            .limit(1)
        ).first()
        is not None
    )
    return tiene_sintetico and not tiene_movimiento


def reporte_error_descensura(sesion: Session, *, id_producto: int, id_sucursal: int) -> dict:
    """Compara, para los períodos de quiebre de la serie sintética, la demanda CORREGIDA contra la
    demanda latente VERDADERA (conocida al generarla) y contra la demanda OBSERVADA sin corregir
    (SC-002, FR-014, FR-015). La descensura es válida si su error medio es MENOR que el de no
    corregir nada: eso demuestra que el método base de FR-009 acerca la serie a la realidad.

    El desglose por camino (`con_consulta_no_atendida` / `solo_metodo_base`) deja medido por
    separado lo que exige FR-016. Hoy ambos caminos usan el método base: la magnitud por evidencia
    real (FR-007 / T014) está bloqueada por `001`, así que los dos números serán parecidos hasta
    que se desbloquee — y eso mismo es información útil.
    """
    observadas = (
        sesion.execute(
            select(DemandaObservada).where(
                DemandaObservada.id_producto == id_producto,
                DemandaObservada.id_sucursal == id_sucursal,
                DemandaObservada.es_sintetico.is_(True),
            )
        )
        .scalars()
        .all()
    )
    if not observadas:
        raise RecursoNoEncontrado(
            f"No hay serie sintética para el producto {id_producto} en la sucursal {id_sucursal}."
        )

    corregidas = {
        c.periodo: c
        for c in sesion.execute(
            select(DemandaCorregida).where(
                DemandaCorregida.id_producto == id_producto,
                DemandaCorregida.id_sucursal == id_sucursal,
                DemandaCorregida.es_sintetico.is_(True),
            )
        ).scalars()
    }

    por_camino: dict[str, list[tuple[Decimal, Decimal]]] = {
        CAMINO_CON_CONSULTA: [],
        CAMINO_SOLO_METODO_BASE: [],
    }
    for o in observadas:
        if o.dias_en_quiebre <= 0 or o.demanda_latente_verdadera is None:
            continue
        c = corregidas.get(o.periodo)
        latente = o.demanda_latente_verdadera
        # Con censura total la "corrección" no produjo un valor: el error es la demanda latente
        # completa, igual que no corregir (se documenta así, no se oculta).
        corregida = c.valor if (c is not None and not c.censura_total) else o.cantidad
        error_descensura = abs(corregida - latente)
        error_sin_corregir = abs(o.cantidad - latente)
        camino = (
            CAMINO_CON_CONSULTA
            if o.consultas_no_atendidas_sinteticas is not None
            else CAMINO_SOLO_METODO_BASE
        )
        por_camino[camino].append((error_descensura, error_sin_corregir))

    todos = por_camino[CAMINO_CON_CONSULTA] + por_camino[CAMINO_SOLO_METODO_BASE]
    error_medio_descensura = _promedio([d for d, _s in todos])
    error_medio_sin_corregir = _promedio([s for _d, s in todos])

    return {
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "periodos_quiebre_evaluados": len(todos),
        "error_medio_descensura": _fmt4(error_medio_descensura),
        "error_medio_sin_corregir": _fmt4(error_medio_sin_corregir),
        "descensura_mejora_sobre_no_corregir": error_medio_descensura < error_medio_sin_corregir,
        "detalle_por_camino": {
            camino: {
                "periodos": len(registros),
                "error_medio_descensura": _fmt4(_promedio([d for d, _s in registros])),
                "error_medio_sin_corregir": _fmt4(_promedio([s for _d, s in registros])),
            }
            for camino, registros in por_camino.items()
        },
    }
