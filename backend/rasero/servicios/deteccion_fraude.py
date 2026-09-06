"""Detección de fraude por sub-registro y gestión de anomalías (006-caja-mermas-fraude, US3+US4 —
T035, T036, T045).

- `indicadores_operador` (US3, T035, ✓) — consulta DERIVADA sobre 001 (`venta`, `anulacion_venta`,
  `renglon_venta`; NO hay tabla de indicadores — research.md #2, #7). Por operador: tasa de
  anulaciones (FR-018) y concentración de ventas bajo precio de lista (FR-019). Cada operador se
  compara contra la LÍNEA BASE de sus pares comparables (mediana + razón, sin librería —
  research.md #16). La respuesta NUNCA dice "fraude": dice "se desvía de la línea base de sus
  pares" (FR-023).
- `cruce_inventario_ventas` (US3, T036) — 001 User Story 5 (T065-T071) ya implementada: cruza el
  faltante bruto de `conteo_renglon.diferencia` contra las mermas ya clasificadas y las
  anulaciones registradas del período; el `faltante_no_explicado > 0` se reparte por turno y crea
  una `anomalia_caja` de `origen = "inventario"` (FR-020, FR-025). Nunca escribe en `001`.
- `listar_anomalias` / `obtener_anomalia` / `resolver_anomalia` (US4, T045) — el sistema NUNCA
  fuerza una clasificación ni cierra una anomalía por el paso del tiempo (FR-029); la resolución la
  asigna una persona con texto libre (FR-030, research.md #18).

El servicio NO comitea: deja la transacción al endpoint.
"""

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config import caja as cfg
from rasero.dominio.indicadores_operador import (
    concentracion_bajo_lista,
    mediana,
    reparto_proporcional_faltante,
    se_desvia,
    tasa_anulaciones,
)
from rasero.dominio.seleccion_lote import ordenar_fefo
from rasero.errores import ErrorCaja
from rasero.persistencia.modelos import (
    AnomaliaCaja,
    AnulacionVenta,
    ConteoFisico,
    ConteoRenglon,
    Lote,
    Merma,
    MovimientoInventario,
    Operador,
    Producto,
    ProductoPrecioSucursal,
    RenglonVenta,
    Sucursal,
    Turno,
    Venta,
)


def _sucursal_o_404(sesion: Session, id_sucursal: int) -> Sucursal:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_no_existe", "Esa sucursal no existe.", status_code=404
        )
    return sucursal


# ==========================================================================
# US3 — indicadores por operador (consulta derivada, ✓)
# ==========================================================================


def indicadores_operador(
    sesion: Session, *, id_sucursal: int, desde, hasta
) -> dict:
    if id_sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_requerida",
            "Indica una sucursal para consultar sus indicadores por operador.",
        )
    if desde is None or hasta is None or hasta < desde:
        raise ErrorCaja(
            "caja_rango_invalido",
            "El rango de fechas no es válido: revisa que 'hasta' no sea anterior a 'desde'.",
        )
    sucursal = _sucursal_o_404(sesion, id_sucursal)
    zona = ZoneInfo(sucursal.zona_horaria)

    def dia(instante: datetime):
        return instante.astimezone(zona).date()

    # Precio efectivo por producto (COALESCE override, precio base) — FR-050 de 001.
    precios: dict[int, tuple[Decimal, Decimal | None]] = {}
    for id_producto, precio_base, override in sesion.execute(
        select(
            Producto.id_producto,
            Producto.precio_vigente,
            ProductoPrecioSucursal.precio_vigente,
        ).outerjoin(
            ProductoPrecioSucursal,
            (ProductoPrecioSucursal.id_producto == Producto.id_producto)
            & (ProductoPrecioSucursal.id_sucursal == id_sucursal),
        )
    ).all():
        precios[id_producto] = (Decimal(precio_base), override)

    def precio_efectivo(id_producto: int) -> Decimal:
        base, override = precios.get(id_producto, (Decimal("0"), None))
        return Decimal(override) if override is not None else base

    # Ventas del período, atribuidas al operador del turno.
    ventas = sesion.execute(
        select(Venta.id_venta, Venta.instante, Turno.id_operador)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .where(Turno.id_sucursal == id_sucursal)
    ).all()
    ventas_por_operador: dict[int, int] = {}
    for _id_venta, instante, id_operador in ventas:
        if desde <= dia(instante) <= hasta:
            ventas_por_operador[id_operador] = ventas_por_operador.get(id_operador, 0) + 1

    # Anulaciones del período, atribuidas a quien las ejecutó (FR-049 de 001).
    anulaciones = sesion.execute(
        select(AnulacionVenta.id_operador, AnulacionVenta.instante)
        .join(Venta, Venta.id_venta == AnulacionVenta.id_venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .where(Turno.id_sucursal == id_sucursal)
    ).all()
    anulaciones_por_operador: dict[int, int] = {}
    for id_operador, instante in anulaciones:
        if desde <= dia(instante) <= hasta:
            anulaciones_por_operador[id_operador] = (
                anulaciones_por_operador.get(id_operador, 0) + 1
            )

    # Renglones del período, atribuidos al operador del turno; cuántos por debajo del precio de
    # lista.
    renglones = sesion.execute(
        select(
            RenglonVenta.id_producto,
            RenglonVenta.precio_aplicado,
            Venta.instante,
            Turno.id_operador,
        )
        .join(Venta, Venta.id_venta == RenglonVenta.id_venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .where(Turno.id_sucursal == id_sucursal)
    ).all()
    renglones_por_operador: dict[int, int] = {}
    bajo_lista_por_operador: dict[int, int] = {}
    for id_producto, precio_aplicado, instante, id_operador in renglones:
        if not (desde <= dia(instante) <= hasta):
            continue
        renglones_por_operador[id_operador] = renglones_por_operador.get(id_operador, 0) + 1
        if Decimal(precio_aplicado) < precio_efectivo(id_producto):
            bajo_lista_por_operador[id_operador] = (
                bajo_lista_por_operador.get(id_operador, 0) + 1
            )

    ids_operadores = (
        set(ventas_por_operador)
        | set(anulaciones_por_operador)
        | set(renglones_por_operador)
    )
    nombres = dict(
        sesion.execute(
            select(Operador.id_operador, Operador.nombre).where(
                Operador.id_operador.in_(ids_operadores or {0})
            )
        ).all()
    )

    parciales: list[dict] = []
    for id_operador in sorted(ids_operadores):
        n_ventas = ventas_por_operador.get(id_operador, 0)
        n_anul = anulaciones_por_operador.get(id_operador, 0)
        n_renglones = renglones_por_operador.get(id_operador, 0)
        n_bajo = bajo_lista_por_operador.get(id_operador, 0)
        comparable = n_ventas >= cfg.UMBRAL_MINIMO_VENTAS_INDICADOR
        parciales.append(
            {
                "id_operador": id_operador,
                "nombre": nombres.get(id_operador, f"Operador {id_operador}"),
                "ventas_periodo": n_ventas,
                "comparable": comparable,
                "tasa_anulaciones": tasa_anulaciones(n_anul, n_ventas),
                "concentracion_bajo_lista": concentracion_bajo_lista(n_bajo, n_renglones),
            }
        )

    comparables = [p for p in parciales if p["comparable"]]
    mediana_tasa = mediana([p["tasa_anulaciones"] for p in comparables])
    mediana_conc = mediana([p["concentracion_bajo_lista"] for p in comparables])

    operadores: list[dict] = []
    for p in parciales:
        detalle: list[str] = []
        desviacion = False
        if p["comparable"]:
            if se_desvia(p["tasa_anulaciones"], mediana_tasa, cfg.RAZON_DESVIACION_ANULACIONES):
                desviacion = True
                detalle.append(
                    f"tasa de anulaciones {p['tasa_anulaciones']} vs mediana de pares "
                    f"{mediana_tasa}"
                )
            if se_desvia(
                p["concentracion_bajo_lista"],
                mediana_conc,
                cfg.RAZON_DESVIACION_PRECIO_BAJO_LISTA,
            ):
                desviacion = True
                detalle.append(
                    f"ventas bajo precio de lista {p['concentracion_bajo_lista']} vs mediana de "
                    f"pares {mediana_conc}"
                )
        operadores.append(
            {
                "id_operador": p["id_operador"],
                "nombre": p["nombre"],
                "ventas_periodo": p["ventas_periodo"],
                "comparable": p["comparable"],
                "tasa_anulaciones": str(p["tasa_anulaciones"]),
                "concentracion_bajo_lista": str(p["concentracion_bajo_lista"]),
                "se_desvia": desviacion,
                "detalle_desviacion": detalle or None,
            }
        )

    return {
        "periodo": f"{desde.isoformat()} a {hasta.isoformat()}",
        "mediana_pares_tasa_anulaciones": (
            str(mediana_tasa) if mediana_tasa is not None else None
        ),
        "mediana_pares_concentracion_bajo_lista": (
            str(mediana_conc) if mediana_conc is not None else None
        ),
        "factor_desviacion_anulaciones": str(cfg.RAZON_DESVIACION_ANULACIONES),
        "factor_desviacion_precio_bajo_lista": str(cfg.RAZON_DESVIACION_PRECIO_BAJO_LISTA),
        "operadores": operadores,
    }


# ==========================================================================
# US3 — cruce inventario-ventas (FR-020, FR-025)
# ==========================================================================


def cruce_inventario_ventas(
    sesion: Session,
    *,
    id_sucursal: int,
    desde,
    hasta,
    id_conteo_fisico: int | None = None,
) -> dict:
    """Cruza el faltante bruto de un conteo físico de `001` (`conteo_renglon.diferencia < 0`)
    contra lo que ya está explicado —mermas clasificadas del período (FR-009) y anulaciones
    registradas (`movimiento_inventario` de tipo `entrada_anulacion`)— y, por cada producto cuyo
    `faltante_no_explicado > 0`, reparte ese faltante entre los turnos que movieron el producto y
    crea una `anomalia_caja` de `origen = "inventario"` (FR-020). Si la merma y las anulaciones lo
    explican por completo, no crea nada (FR-025, FR-031, SC-012). NO escribe en `001`.

    `id_conteo_fisico` fija el conteo a cruzar; si se omite, el último conteo resuelto de la
    sucursal. El servicio NO comitea (lo hace el endpoint).
    """
    if id_sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_requerida", "Indica una sucursal para ejecutar el cruce."
        )
    if desde is None or hasta is None or hasta < desde:
        raise ErrorCaja(
            "caja_rango_invalido",
            "El rango de fechas no es válido: revisa que 'hasta' no sea anterior a 'desde'.",
        )
    sucursal = _sucursal_o_404(sesion, id_sucursal)
    zona = ZoneInfo(sucursal.zona_horaria)

    if id_conteo_fisico is not None:
        conteo = sesion.get(ConteoFisico, id_conteo_fisico)
        if conteo is None or conteo.id_sucursal != id_sucursal:
            raise ErrorCaja(
                "caja_conteo_no_existe",
                "Ese conteo físico no existe en esta sucursal.",
                status_code=404,
            )
        if conteo.estado != "resuelto":
            raise ErrorCaja(
                "caja_conteo_no_resuelto",
                "Ese conteo todavía no está resuelto; no hay diferencia que cruzar.",
            )
    else:
        conteo = sesion.execute(
            select(ConteoFisico)
            .where(
                ConteoFisico.id_sucursal == id_sucursal,
                ConteoFisico.estado == "resuelto",
            )
            .order_by(ConteoFisico.instante_resolucion.desc())
            .limit(1)
        ).scalar_one_or_none()

    if conteo is None:
        return {
            "id_conteo_fisico": None,
            "anomalias_creadas": [],
            "detalle": "No hay ningún conteo físico resuelto en esta sucursal para cruzar.",
        }

    renglones = list(
        sesion.execute(
            select(ConteoRenglon).where(
                ConteoRenglon.id_conteo_fisico == conteo.id_conteo_fisico
            )
        ).scalars()
    )
    faltante_por_producto: dict[int, Decimal] = {}
    for r in renglones:
        if r.diferencia < 0:
            faltante_por_producto[r.id_producto] = faltante_por_producto.get(
                r.id_producto, Decimal(0)
            ) + (-Decimal(r.diferencia))

    inicio_utc = datetime.combine(desde, time.min, tzinfo=zona).astimezone(timezone.utc)
    fin_utc = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=zona).astimezone(
        timezone.utc
    )
    hoy_local = datetime.now(zona).date()
    ahora = datetime.now(timezone.utc)

    indicadores = indicadores_operador(
        sesion, id_sucursal=id_sucursal, desde=desde, hasta=hasta
    )
    ind_por_operador = {o["id_operador"]: o for o in indicadores["operadores"]}

    anomalias_creadas: list[int] = []
    detalle: list[dict] = []

    for id_producto, faltante_bruto in sorted(faltante_por_producto.items()):
        merma_descontada = Decimal(
            sesion.execute(
                select(func.coalesce(func.sum(Merma.cantidad_faltante), 0)).where(
                    Merma.id_sucursal == id_sucursal,
                    Merma.id_producto == id_producto,
                    Merma.estado == "clasificada",
                    Merma.periodo_hasta >= desde,
                    Merma.periodo_desde <= hasta,
                )
            ).scalar_one()
        )
        anulaciones_descontadas = Decimal(
            sesion.execute(
                select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
                    MovimientoInventario.id_sucursal == id_sucursal,
                    MovimientoInventario.id_producto == id_producto,
                    MovimientoInventario.tipo == "entrada_anulacion",
                    MovimientoInventario.instante >= inicio_utc,
                    MovimientoInventario.instante < fin_utc,
                )
            ).scalar_one()
        )

        faltante_no_explicado = faltante_bruto - merma_descontada - anulaciones_descontadas
        if faltante_no_explicado <= 0:
            detalle.append(
                {
                    "id_producto": id_producto,
                    "faltante_bruto": str(faltante_bruto),
                    "merma_descontada": str(merma_descontada),
                    "anulaciones_descontadas": str(anulaciones_descontadas),
                    "faltante_no_explicado": str(faltante_no_explicado),
                    "anomalia": None,
                }
            )
            continue

        unidades_por_turno = {
            id_turno: Decimal(unidades)
            for id_turno, unidades in sesion.execute(
                select(
                    Turno.id_turno,
                    func.coalesce(func.sum(func.abs(MovimientoInventario.cantidad)), 0),
                )
                .join(Venta, Venta.id_venta == MovimientoInventario.id_venta)
                .join(Turno, Turno.id_turno == Venta.id_turno)
                .where(
                    MovimientoInventario.id_sucursal == id_sucursal,
                    MovimientoInventario.id_producto == id_producto,
                    MovimientoInventario.tipo == "salida_venta",
                    MovimientoInventario.instante >= inicio_utc,
                    MovimientoInventario.instante < fin_utc,
                )
                .group_by(Turno.id_turno)
            ).all()
        }
        reparto = reparto_proporcional_faltante(faltante_no_explicado, unidades_por_turno)

        id_turno_top = (
            max(reparto, key=lambda t: reparto[t]) if any(reparto.values()) else None
        )
        id_operador_top = None
        if id_turno_top is not None:
            turno_top = sesion.get(Turno, id_turno_top)
            id_operador_top = turno_top.id_operador if turno_top is not None else None

        lotes = list(
            sesion.execute(
                select(Lote).where(
                    Lote.id_producto == id_producto, Lote.id_sucursal == id_sucursal
                )
            ).scalars()
        )
        costo = Decimal(ordenar_fefo(lotes)[0].costo_unitario) if lotes else None
        valor_estimado = (
            (faltante_no_explicado * costo).quantize(Decimal("0.01"))
            if costo is not None
            else None
        )

        ind_top = ind_por_operador.get(id_operador_top, {})
        snapshot = {
            "faltante_bruto": str(faltante_bruto),
            "merma_descontada": str(merma_descontada),
            "anulaciones_descontadas": str(anulaciones_descontadas),
            "faltante_no_explicado": str(faltante_no_explicado),
            "tasa_anulaciones": ind_top.get("tasa_anulaciones"),
            "concentracion_bajo_lista": ind_top.get("concentracion_bajo_lista"),
            "reparto_por_turno": [
                {"id_turno": t, "cantidad_atribuida": str(c)} for t, c in reparto.items()
            ],
        }

        anomalia = AnomaliaCaja(
            origen="inventario",
            estado="sin_explicacion",
            id_sucursal=id_sucursal,
            id_turno=id_turno_top,
            id_operador=id_operador_top,
            id_producto=id_producto,
            id_conteo_fisico=conteo.id_conteo_fisico,
            magnitud=faltante_no_explicado,
            valor_estimado=valor_estimado,
            periodo_desde=desde,
            periodo_hasta=hasta,
            dia_local=hoy_local,
            indicador_snapshot=snapshot,
            historial=[
                {
                    "estado": "sin_explicacion",
                    "instante": ahora.isoformat(),
                    "id_operador": None,
                    "nota": (
                        "Creada automáticamente: faltante de inventario que ni la merma "
                        "clasificada ni las anulaciones registradas explican."
                    ),
                }
            ],
            instante_deteccion=ahora,
        )
        sesion.add(anomalia)
        sesion.flush()
        anomalias_creadas.append(anomalia.id_anomalia_caja)
        detalle.append(
            {
                "id_producto": id_producto,
                "faltante_bruto": str(faltante_bruto),
                "merma_descontada": str(merma_descontada),
                "anulaciones_descontadas": str(anulaciones_descontadas),
                "faltante_no_explicado": str(faltante_no_explicado),
                "anomalia": anomalia.id_anomalia_caja,
            }
        )

    return {
        "id_conteo_fisico": conteo.id_conteo_fisico,
        "anomalias_creadas": anomalias_creadas,
        "detalle": detalle,
    }


# ==========================================================================
# US4 — gestión de anomalías sin explicación
# ==========================================================================


def listar_anomalias(
    sesion: Session,
    *,
    id_sucursal: int,
    estado: str | None = None,
    origen: str | None = None,
    desde=None,
    hasta=None,
) -> list[AnomaliaCaja]:
    if id_sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_requerida",
            "Indica una sucursal para consultar sus anomalías (no se mezclan sucursales).",
        )
    consulta = select(AnomaliaCaja).where(AnomaliaCaja.id_sucursal == id_sucursal)
    if estado is not None:
        consulta = consulta.where(AnomaliaCaja.estado == estado)
    if origen is not None:
        consulta = consulta.where(AnomaliaCaja.origen == origen)
    if desde is not None:
        consulta = consulta.where(AnomaliaCaja.dia_local >= desde)
    if hasta is not None:
        consulta = consulta.where(AnomaliaCaja.dia_local <= hasta)
    consulta = consulta.order_by(
        AnomaliaCaja.estado, AnomaliaCaja.dia_local.desc(), AnomaliaCaja.id_anomalia_caja.desc()
    )
    return list(sesion.execute(consulta).scalars())


def obtener_anomalia(sesion: Session, *, id_anomalia_caja: int) -> AnomaliaCaja:
    anomalia = sesion.get(AnomaliaCaja, id_anomalia_caja)
    if anomalia is None:
        raise ErrorCaja(
            "caja_anomalia_no_existe", "Esa anomalía no existe.", status_code=404
        )
    return anomalia


def resolver_anomalia(
    sesion: Session,
    *,
    id_anomalia_caja: int,
    resolucion: str,
    id_operador: int,
    nota: str | None = None,
) -> AnomaliaCaja:
    anomalia = obtener_anomalia(sesion, id_anomalia_caja=id_anomalia_caja)
    if anomalia.estado == "resuelta":
        raise ErrorCaja(
            "caja_anomalia_ya_resuelta", "Esta anomalía ya estaba resuelta."
        )
    if not resolucion or not resolucion.strip():
        raise ErrorCaja(
            "caja_resolucion_vacia",
            "Escribe una resolución para la anomalía (por ejemplo, 'error operativo confirmado').",
        )
    if sesion.get(Operador, id_operador) is None:
        raise ErrorCaja(
            "caja_operador_no_existe", "Ese operador no existe.", status_code=404
        )
    ahora = datetime.now(timezone.utc)
    anomalia.historial = list(anomalia.historial) + [
        {
            "estado": "resuelta",
            "instante": ahora.isoformat(),
            "id_operador": id_operador,
            "nota": nota,
            "estado_anterior": "sin_explicacion",
        }
    ]
    anomalia.estado = "resuelta"
    anomalia.resolucion = resolucion.strip()
    anomalia.id_operador_resolucion = id_operador
    anomalia.instante_resolucion = ahora
    sesion.flush()
    return anomalia


def anomalia_a_respuesta(anomalia: AnomaliaCaja) -> dict:
    return {
        "id_anomalia_caja": anomalia.id_anomalia_caja,
        "origen": anomalia.origen,
        "estado": anomalia.estado,
        "id_sucursal": anomalia.id_sucursal,
        "id_arqueo": anomalia.id_arqueo,
        "id_turno": anomalia.id_turno,
        "id_operador": anomalia.id_operador,
        "id_producto": anomalia.id_producto,
        "id_conteo_fisico": anomalia.id_conteo_fisico,
        "monto": str(anomalia.monto) if anomalia.monto is not None else None,
        "magnitud": int(anomalia.magnitud) if anomalia.magnitud is not None else None,
        "valor_estimado": (
            str(anomalia.valor_estimado) if anomalia.valor_estimado is not None else None
        ),
        "periodo_desde": (
            anomalia.periodo_desde.isoformat() if anomalia.periodo_desde is not None else None
        ),
        "periodo_hasta": (
            anomalia.periodo_hasta.isoformat() if anomalia.periodo_hasta is not None else None
        ),
        "dia_local": anomalia.dia_local.isoformat(),
        "indicador_snapshot": anomalia.indicador_snapshot,
        "historial": anomalia.historial,
        "resolucion": anomalia.resolucion,
        "id_operador_resolucion": anomalia.id_operador_resolucion,
        "instante_resolucion": (
            anomalia.instante_resolucion.isoformat()
            if anomalia.instante_resolucion is not None
            else None
        ),
        "instante_deteccion": anomalia.instante_deteccion.isoformat(),
    }
