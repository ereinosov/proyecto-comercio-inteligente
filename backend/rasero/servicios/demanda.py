"""Reconstrucción de la serie de demanda observada y corregida por producto y sucursal
(User Stories 1, 4, 5 y 6 de 004-pronostico-demanda).

`demanda_observada` y `demanda_corregida` se materializan por upsert sobre la ventana de días
pedida en cada lectura (recompute-on-read, research.md #3) — nunca por disparador ni tarea de
fondo: los insumos (ventas, movimientos de inventario) son eventos de 001, no de 004.

Las correcciones se aplican en ORDEN FIJO (research.md #3), cada una sobre el valor que dejó la
anterior:

  (1) quiebre de stock   — método base (FR-009 a) + ajuste cruzado por sustituto (FR-009 b)
  (2) precio             — normalización al precio de referencia (FR-025, User Story 4)
  (3) promoción          — exclusión de los períodos con promoción activa (FR-029, User Story 5)
  (4) señal de sustitución — marca cualitativa en la serie del sustituto (FR-033, User Story 6)

El paso (1) se subdivide: primero el método base para todos los productos, y luego el ajuste
cruzado por sustituto, que necesita la serie de los sustitutos ya construida.

La reconstrucción se resuelve con un número FIJO de consultas de conjunto, todas independientes
del número de productos (research.md #4). `test_demanda_sucursal.py` (T008) lo verifica.

Frontera de propiedad de datos: `movimiento_inventario`, `venta`, `renglon_venta`, `turno`,
`existencia`, `sucursal`, `producto`, `producto_precio_sucursal` son de 001. Este módulo los
CONSULTA, nunca los posee ni altera su esquema, y NO escribe en ninguna tabla de 001.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from rasero.config.pronostico import (
    ELASTICIDAD_PRECIO,
    VENTANA_MATERIALIZACION_DIAS,
    VENTANA_METODO_BASE_DIAS,
)
from rasero.dominio.censura import (
    PeriodoCorregido,
    PeriodoObservado,
    ajuste_cruzado,
    corregir_serie_por_quiebre,
    estimar_latente_metodo_base,
    exceso_sustituto,
)
from rasero.dominio.serie_demanda import (
    demanda_observada_por_dia,
    dias_del_rango,
    dias_en_quiebre_por_dia,
    inicio_dia_utc,
    marca_promocion_por_dia,
    normalizar_demanda_por_precio,
    periodo_local,
    precio_vigente_por_dia,
)
from rasero.errores import RecursoNoEncontrado
from rasero.persistencia.modelos import (
    DemandaCorregida,
    DemandaObservada,
    MovimientoInventario,
    Producto,
    ProductoPrecioSucursal,
    RenglonVenta,
    Sucursal,
    SustitucionProducto,
    Turno,
    Venta,
)

_TIPOS_DEMANDA = ("salida_venta", "entrada_anulacion")

_CAMPOS_OBSERVADA = (
    "cantidad",
    "dias_en_quiebre",
    "precio_vigente_periodo",
    "con_promocion",
    "instante_materializacion",
)
_CAMPOS_CORREGIDA = (
    "valor_observado",
    "valor",
    "correccion_quiebre",
    "respaldo_quiebre",
    "ajuste_cruzado_sustituto",
    "correccion_precio",
    "elasticidad_usada",
    "excluido_por_promocion",
    "censura_total",
    "instante_materializacion",
)


@dataclass
class _SerieProducto:
    observados: list[PeriodoObservado]
    quiebre: dict[date, PeriodoCorregido]  # resultado del método base, por período

    def cantidad(self, dia: date) -> Decimal:
        for o in self.observados:
            if o.periodo == dia:
                return o.cantidad
        return Decimal(0)

    def en_quiebre(self, dia: date) -> bool:
        for o in self.observados:
            if o.periodo == dia:
                return o.dias_en_quiebre > 0
        return False

    def maximo_n_antes(self, dia: date, n: int) -> Decimal | None:
        previos = [
            o.cantidad for o in self.observados if o.dias_en_quiebre == 0 and o.periodo < dia
        ]
        return estimar_latente_metodo_base(periodos_sin_quiebre_previos=previos, n=n)


def _inicios_de_intervalo_de_quiebre(observados: list[PeriodoObservado]) -> dict[date, date]:
    """Por cada día en quiebre, el primer día del intervalo de quiebre CONTIGUO al que pertenece.
    `observados` viene en orden cronológico."""
    inicios: dict[date, date] = {}
    corrida: date | None = None
    for o in observados:
        if o.dias_en_quiebre > 0:
            corrida = corrida or o.periodo
            inicios[o.periodo] = corrida
        else:
            corrida = None
    return inicios


def _fmt0(valor: Decimal | None) -> str | None:
    return None if valor is None else f"{valor:.0f}"


def _fmt4(valor: Decimal | None) -> str | None:
    return None if valor is None else f"{valor:.4f}"


def _rango_por_defecto(hoy_local: date) -> tuple[date, date]:
    return hoy_local - timedelta(days=VENTANA_MATERIALIZACION_DIAS), hoy_local


def _saldo_arrastrado(
    sesion: Session, *, id_sucursal: int, filtro_productos: set[int] | None, inicio_utc: datetime
) -> dict[int, Decimal]:
    """Consulta: saldo de existencia reconstruido desde `movimiento_inventario` justo antes de la
    ventana, agregado por producto. Una fila por producto, independiente del número de productos.
    """
    consulta = (
        select(
            MovimientoInventario.id_producto,
            func.coalesce(func.sum(MovimientoInventario.cantidad), 0),
        )
        .where(
            MovimientoInventario.id_sucursal == id_sucursal,
            MovimientoInventario.instante < inicio_utc,
        )
        .group_by(MovimientoInventario.id_producto)
    )
    if filtro_productos is not None:
        consulta = consulta.where(MovimientoInventario.id_producto.in_(filtro_productos))
    return {pid: Decimal(saldo) for pid, saldo in sesion.execute(consulta).all()}


def _movimientos_de_la_ventana(
    sesion: Session,
    *,
    id_sucursal: int,
    filtro_productos: set[int] | None,
    inicio_utc: datetime,
    fin_utc: datetime,
) -> dict[int, list[tuple[datetime, Decimal, str]]]:
    """Consulta: todos los movimientos dentro de la ventana, agrupados por producto en Python."""
    consulta = (
        select(
            MovimientoInventario.id_producto,
            MovimientoInventario.instante,
            MovimientoInventario.cantidad,
            MovimientoInventario.tipo,
        )
        .where(
            MovimientoInventario.id_sucursal == id_sucursal,
            MovimientoInventario.instante >= inicio_utc,
            MovimientoInventario.instante < fin_utc,
        )
        .order_by(
            MovimientoInventario.id_producto,
            MovimientoInventario.instante,
            MovimientoInventario.id_movimiento_inventario,
        )
    )
    if filtro_productos is not None:
        consulta = consulta.where(MovimientoInventario.id_producto.in_(filtro_productos))

    por_producto: dict[int, list[tuple[datetime, Decimal, str]]] = {}
    for pid, instante, cantidad, tipo in sesion.execute(consulta).all():
        por_producto.setdefault(pid, []).append((instante, Decimal(cantidad), tipo))
    return por_producto


def _renglones_de_la_ventana(
    sesion: Session,
    *,
    id_sucursal: int,
    filtro_productos: set[int] | None,
    inicio_utc: datetime,
    fin_utc: datetime,
) -> dict[int, list[tuple[datetime, Decimal, Decimal]]]:
    """Consulta: `renglon_venta.precio_aplicado` (precio histórico copiado en cada venta) de la
    ventana, con el instante de la venta y la cantidad. Una sola consulta (research.md #8b)."""
    cantidad = func.coalesce(RenglonVenta.cantidad_unidades, RenglonVenta.cantidad_gramos)
    consulta = (
        select(RenglonVenta.id_producto, Venta.instante, RenglonVenta.precio_aplicado, cantidad)
        .join(Venta, RenglonVenta.id_venta == Venta.id_venta)
        .join(Turno, Venta.id_turno == Turno.id_turno)
        .where(
            Turno.id_sucursal == id_sucursal,
            Venta.instante >= inicio_utc,
            Venta.instante < fin_utc,
        )
    )
    if filtro_productos is not None:
        consulta = consulta.where(RenglonVenta.id_producto.in_(filtro_productos))

    por_producto: dict[int, list[tuple[datetime, Decimal, Decimal]]] = {}
    for pid, instante, precio, cant in sesion.execute(consulta).all():
        por_producto.setdefault(pid, []).append(
            (instante, Decimal(precio), Decimal(cant if cant is not None else 0))
        )
    return por_producto


def _precio_referencia(
    sesion: Session, *, id_sucursal: int, productos: set[int]
) -> dict[int, Decimal]:
    """Precio de referencia ACTUAL de cada producto en la sucursal: el override si existe, si no
    el precio base (misma resolución `COALESCE` que 001 usa al vender). El pronóstico responde a
    "cuánta demanda esperar al precio de hoy" (Assumptions de spec.md)."""
    if not productos:
        return {}
    override = ProductoPrecioSucursal.precio_vigente
    consulta = (
        select(Producto.id_producto, func.coalesce(override, Producto.precio_vigente))
        .outerjoin(
            ProductoPrecioSucursal,
            (ProductoPrecioSucursal.id_producto == Producto.id_producto)
            & (ProductoPrecioSucursal.id_sucursal == id_sucursal),
        )
        .where(Producto.id_producto.in_(productos))
    )
    return {pid: Decimal(precio) for pid, precio in sesion.execute(consulta).all()}


def _relaciones_sustitucion(
    sesion: Session, *, id_producto: int | None
) -> list[SustitucionProducto]:
    """Relaciones de sustitución declaradas que tocan a `id_producto` (por cualquiera de los dos
    lados); todas si `id_producto` es None."""
    consulta = select(SustitucionProducto)
    if id_producto is not None:
        consulta = consulta.where(
            (SustitucionProducto.id_producto == id_producto)
            | (SustitucionProducto.id_producto_sustituto == id_producto)
        )
    return list(sesion.execute(consulta).scalars())


def _upsert(sesion: Session, modelo, filas: list[dict], campos: tuple[str, ...]) -> None:
    """Un único `INSERT ... ON CONFLICT DO UPDATE` con todas las filas (research.md #4). El
    `WHERE es_sintetico = FALSE` protege las series sintéticas de la User Story 2 (FR-017)."""
    if not filas:
        return
    upsert = pg_insert(modelo).values(filas)
    upsert = upsert.on_conflict_do_update(
        index_elements=[modelo.id_producto, modelo.id_sucursal, modelo.periodo],
        set_={campo: getattr(upsert.excluded, campo) for campo in campos},
        where=modelo.es_sintetico.is_(False),
    )
    sesion.execute(upsert)
    sesion.flush()


def reconstruir_serie(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[dict]:
    """Reconstruye y materializa la serie observada y corregida de la ventana pedida y la devuelve
    con las anotaciones que la explican (forma `PuntoSerie` de contracts/openapi.yaml).

    Con `id_producto` da una serie DENSA (una fila por día, incluidos los de demanda cero); sin
    `id_producto` da la serie de los productos con demanda en la ventana, filtrando los días sin
    demanda ni quiebre para no inundar la respuesta.
    """
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")
    if id_producto is not None and sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    zona_horaria = sucursal.zona_horaria
    hoy_local = periodo_local(datetime.now(timezone.utc), zona_horaria)
    if hasta is None:
        hasta = hoy_local
    if desde is None:
        desde = _rango_por_defecto(hasta)[0]

    dias = dias_del_rango(desde, hasta)
    inicio_utc = inicio_dia_utc(desde, zona_horaria)
    fin_utc = inicio_dia_utc(hasta + timedelta(days=1), zona_horaria)

    relaciones = _relaciones_sustitucion(sesion, id_producto=id_producto)

    # Conjunto de productos a traer: los objetivo más los auxiliares que las relaciones de
    # sustitución exigen (los sustitutos de un objetivo, y los productos que tienen un objetivo
    # como sustituto). Para la sucursal completa se traen todos.
    if id_producto is not None:
        objetivo_conocido: set[int] | None = {id_producto}
        auxiliares = {
            r.id_producto_sustituto for r in relaciones if r.id_producto == id_producto
        } | {r.id_producto for r in relaciones if r.id_producto_sustituto == id_producto}
        filtro_productos: set[int] | None = {id_producto} | auxiliares
    else:
        objetivo_conocido = None
        filtro_productos = None

    saldo_arrastrado = _saldo_arrastrado(
        sesion, id_sucursal=id_sucursal, filtro_productos=filtro_productos, inicio_utc=inicio_utc
    )
    movimientos = _movimientos_de_la_ventana(
        sesion,
        id_sucursal=id_sucursal,
        filtro_productos=filtro_productos,
        inicio_utc=inicio_utc,
        fin_utc=fin_utc,
    )
    renglones = _renglones_de_la_ventana(
        sesion,
        id_sucursal=id_sucursal,
        filtro_productos=filtro_productos,
        inicio_utc=inicio_utc,
        fin_utc=fin_utc,
    )

    productos_con_datos = sorted(set(movimientos) | set(renglones) | (objetivo_conocido or set()))
    if objetivo_conocido is not None:
        objetivo = sorted(objetivo_conocido)
    else:
        objetivo = sorted(
            {
                pid
                for pid, movs in movimientos.items()
                if any(tipo in _TIPOS_DEMANDA for _i, _c, tipo in movs)
            }
        )

    # --- Fase 1: serie observada + descensura por MÉTODO BASE, para todo producto con datos ---
    series: dict[int, _SerieProducto] = {}
    for pid in productos_con_datos:
        movs = movimientos.get(pid, [])
        demanda_por_dia = demanda_observada_por_dia(movs, zona_horaria)
        quiebre_por_dia = dias_en_quiebre_por_dia(
            movs,
            saldo_inicial=saldo_arrastrado.get(pid, Decimal(0)),
            zona_horaria=zona_horaria,
            dias=dias,
        )
        observados = [
            PeriodoObservado(
                periodo=dia,
                cantidad=demanda_por_dia.get(dia, Decimal(0)),
                dias_en_quiebre=quiebre_por_dia.get(dia, Decimal(0)),
            )
            for dia in dias
        ]
        quiebre = {
            c.periodo: c for c in corregir_serie_por_quiebre(observados, n=VENTANA_METODO_BASE_DIAS)
        }
        series[pid] = _SerieProducto(observados=observados, quiebre=quiebre)

    inicios_quiebre = {
        pid: _inicios_de_intervalo_de_quiebre(s.observados) for pid, s in series.items()
    }
    precio_ref = _precio_referencia(sesion, id_sucursal=id_sucursal, productos=set(objetivo))

    # --- Fase 2: por cada producto OBJETIVO, ajuste cruzado + precio + promoción + señal ---
    ahora = datetime.now(timezone.utc)
    filas_observada: list[dict] = []
    filas_corregida: list[dict] = []
    respuesta: list[dict] = []

    for pid in objetivo:
        serie = series[pid]
        precio_por_dia = precio_vigente_por_dia(renglones.get(pid, []), zona_horaria)
        promo_por_dia = marca_promocion_por_dia(
            sesion, id_producto=pid, id_sucursal=id_sucursal, dias=dias
        )
        sustitutos = [r for r in relaciones if r.id_producto == pid]
        soy_sustituto_de = [r for r in relaciones if r.id_producto_sustituto == pid]
        inicio_intervalo = inicios_quiebre[pid]

        for obs in serie.observados:
            dia = obs.periodo
            base = serie.quiebre[dia]

            interesante = obs.cantidad > 0 or obs.dias_en_quiebre > 0
            if objetivo_conocido is None and not interesante:
                continue

            # (1b) Ajuste cruzado por sustituto — sólo si el método base produjo un valor.
            # El "nivel típico" del sustituto se mide con sus períodos sin quiebre PREVIOS AL
            # INICIO del intervalo de quiebre del original (research.md #5/#6): así el alza que el
            # propio quiebre provoca en el sustituto no infla su nivel típico.
            ajuste = Decimal(0)
            if base.valor is not None and obs.dias_en_quiebre > 0 and sustitutos:
                inicio = inicio_intervalo.get(dia, dia)
                excesos: list[Decimal] = []
                for r in sustitutos:
                    s = series.get(r.id_producto_sustituto)
                    if s is None or s.en_quiebre(dia):
                        continue  # sustituto también agotado -> sin trasvase observable (FR-036)
                    excesos.append(
                        exceso_sustituto(
                            demanda_sustituto=s.cantidad(dia),
                            maximo_n_sustituto=s.maximo_n_antes(inicio, VENTANA_METODO_BASE_DIAS),
                        )
                    )
                ajuste = ajuste_cruzado(estimado_base=base.valor, excesos=excesos)

            valor_tras_quiebre = (base.valor + ajuste) if base.valor is not None else None
            correccion_quiebre = base.correccion_quiebre + ajuste

            # (2) Precio — normalización al precio de referencia.
            correccion_precio = Decimal(0)
            elasticidad_usada: Decimal | None = None
            precio_periodo = precio_por_dia.get(dia)
            if valor_tras_quiebre is not None and precio_periodo is not None:
                valor_tras_precio, correccion_precio = normalizar_demanda_por_precio(
                    cantidad=valor_tras_quiebre,
                    precio_periodo=precio_periodo,
                    precio_referencia=precio_ref.get(pid),
                    epsilon=ELASTICIDAD_PRECIO,
                )
                if correccion_precio != 0:
                    elasticidad_usada = ELASTICIDAD_PRECIO
                valor_tras_precio = max(Decimal(0), valor_tras_precio)
            else:
                valor_tras_precio = valor_tras_quiebre

            # (3) Promoción — exclusión del período de la serie a precio normal.
            con_promocion = bool(promo_por_dia.get(dia, False))
            excluido_por_promocion = con_promocion  # hoy siempre False (005 no existe, FR-030)

            # (4) Señal de sustitución en MI serie: soy el sustituto de otro producto que se agotó,
            # y este día vendí por encima de mi nivel típico (medido ANTES de que empezara el
            # quiebre del otro). Marca CUALITATIVA para revisión — no descuenta mi volumen (FR-034).
            senal = None
            if obs.dias_en_quiebre == 0 and obs.cantidad > 0 and soy_sustituto_de:
                for r in soy_sustituto_de:
                    original = series.get(r.id_producto)
                    if original is None or not original.en_quiebre(dia):
                        continue
                    inicio_original = inicios_quiebre[r.id_producto].get(dia, dia)
                    tipico = serie.maximo_n_antes(inicio_original, VENTANA_METODO_BASE_DIAS)
                    if tipico is not None and obs.cantidad > tipico:
                        senal = {
                            "id_producto_en_quiebre": r.id_producto,
                            "id_sustitucion_producto": r.id_sustitucion_producto,
                        }
                        break

            valor_final = valor_tras_precio
            censura_total = base.censura_total

            filas_observada.append(
                {
                    "id_producto": pid,
                    "id_sucursal": id_sucursal,
                    "periodo": dia,
                    "cantidad": obs.cantidad,
                    "dias_en_quiebre": obs.dias_en_quiebre,
                    "precio_vigente_periodo": precio_periodo,
                    "con_promocion": con_promocion,
                    "instante_materializacion": ahora,
                }
            )
            filas_corregida.append(
                {
                    "id_producto": pid,
                    "id_sucursal": id_sucursal,
                    "periodo": dia,
                    "valor_observado": base.valor_observado,
                    "valor": valor_final if valor_final is not None else Decimal(0),
                    "correccion_quiebre": correccion_quiebre,
                    "respaldo_quiebre": base.respaldo_quiebre,
                    "ajuste_cruzado_sustituto": ajuste,
                    "correccion_precio": correccion_precio,
                    "elasticidad_usada": elasticidad_usada,
                    "excluido_por_promocion": excluido_por_promocion,
                    "censura_total": censura_total,
                    "instante_materializacion": ahora,
                }
            )
            respuesta.append(
                {
                    "id_producto": pid,
                    "id_sucursal": id_sucursal,
                    "periodo": dia.isoformat(),
                    "demanda_observada": _fmt0(obs.cantidad),
                    "demanda_corregida": _fmt4(valor_final),
                    "estado": base.estado,
                    "dias_en_quiebre": f"{obs.dias_en_quiebre:.3f}",
                    "correccion_quiebre": _fmt4(correccion_quiebre),
                    "respaldo_quiebre": base.respaldo_quiebre,
                    "ajuste_cruzado_sustituto": _fmt4(ajuste),
                    "precio_vigente_periodo": _fmt4(precio_periodo),
                    "correccion_precio": _fmt4(correccion_precio),
                    "elasticidad_usada": _fmt4(elasticidad_usada),
                    "con_promocion": con_promocion,
                    "excluido_por_promocion": excluido_por_promocion,
                    "senal_sustitucion": senal,
                }
            )

    _upsert(sesion, DemandaObservada, filas_observada, _CAMPOS_OBSERVADA)
    _upsert(sesion, DemandaCorregida, filas_corregida, _CAMPOS_CORREGIDA)
    return respuesta


# --------------------------------------------------------------------------------------------
# T014 — BLOQUEADA por 001 (User Story 3 / consulta_no_atendida, tareas T050-T053 sin implementar)
# --------------------------------------------------------------------------------------------
# Cuando 001 implemente su User Story 3, aquí (dentro de la Fase 1, antes del método base) va la
# rama de EVIDENCIA REAL (FR-007): para cada intervalo de quiebre con registros de
# `consulta_no_atendida` de 001 del producto y sucursal, usar `saldo_en_el_instante` y el CONTEO
# de consultas como evidencia directa de la magnitud de la demanda latente en vez del método
# base, y marcar `respaldo_quiebre = 'consulta_no_atendida'`. La prueba
# `tests/integracion/test_descensura_consulta_no_atendida.py` (T009) queda escrita y marcada
# `xfail(strict=True)`: al implementar esta rama, quitar ese marcador. Ver tasks.md, "Bloqueado
# por 001".
