"""Detección de fraude por sub-registro y gestión de anomalías (006-caja-mermas-fraude, US3+US4 —
T035, T036, T045).

- `indicadores_operador` (US3, T035, ✓) — consulta DERIVADA sobre 001 (`venta`, `anulacion_venta`,
  `renglon_venta`; NO hay tabla de indicadores — research.md #2, #7). Por operador: tasa de
  anulaciones (FR-018) y concentración de ventas bajo precio de lista (FR-019). Cada operador se
  compara contra la LÍNEA BASE de sus pares comparables (mediana + razón, sin librería —
  research.md #16). La respuesta NUNCA dice "fraude": dice "se desvía de la línea base de sus
  pares" (FR-023).
- `cruce_inventario_ventas` (US3, T036) — **BLOQUEADA por 001 (User Story 5, T065-T071)**: hoy
  lanza `CajaBloqueadoPor001` -> `409 caja_bloqueado_por_001`. El esquema de `merma.id_conteo_renglon`
  y `anomalia_caja.id_conteo_fisico` ya existe; la lógica que lee `conteo_renglon` no.
- `listar_anomalias` / `obtener_anomalia` / `resolver_anomalia` (US4, T045) — el sistema NUNCA
  fuerza una clasificación ni cierra una anomalía por el paso del tiempo (FR-029); la resolución la
  asigna una persona con texto libre (FR-030, research.md #18).

El servicio NO comitea: deja la transacción al endpoint.
"""

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.config import caja as cfg
from rasero.dominio.indicadores_operador import (
    concentracion_bajo_lista,
    mediana,
    se_desvia,
    tasa_anulaciones,
)
from rasero.errores import CajaBloqueadoPor001, ErrorCaja
from rasero.persistencia.modelos import (
    AnomaliaCaja,
    AnulacionVenta,
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
# US3 — cruce inventario-ventas (BLOQUEADA por 001 User Story 5)
# ==========================================================================


def cruce_inventario_ventas(
    sesion: Session,
    *,
    id_sucursal: int,
    desde,
    hasta,
    id_conteo_fisico: int | None = None,
) -> dict:
    """BLOQUEADA por 001 (User Story 5, T065-T071). El `409 caja_bloqueado_por_001` es
    comportamiento controlado y esperado, no un fallo (tasks.md T037).

    Al implementar `001` User Story 5, esta función:
    1. leerá `conteo_renglon.diferencia` del conteo (o del último resuelto de la sucursal);
    2. descontará la merma clasificada del producto/período (`servicios/mermas`) y las anulaciones
       registradas (`movimiento_inventario` tipo `entrada_anulacion`);
    3. repartirá el `faltante_no_explicado > 0` por turno
       (`dominio/indicadores_operador.reparto_proporcional_faltante`);
    4. creará una `AnomaliaCaja` de `origen = "inventario"` con `magnitud`, `valor_estimado` e
       `indicador_snapshot`; si `faltante_no_explicado <= 0`, no creará nada (FR-025, FR-031).
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
    _sucursal_o_404(sesion, id_sucursal)
    raise CajaBloqueadoPor001()


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
