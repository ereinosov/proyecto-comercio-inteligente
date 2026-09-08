"""Servicios de 005-promociones-inteligentes.

- `generar_cupones` (US1, T011) — mecanismo 1: fecha llega -> cupón. Idempotente por
  `UNIQUE (id_cliente, fecha_objetivo)` (FR-007). Consulta la lista de cumpleañeros que 002 ya
  expone (FR-002); nunca lee `cliente.fecha_nacimiento`.
- `registrar_redencion` (US1 base, T013 + rama oferta T027) — la ÚNICA vía por la que 005 se
  entera de que una promoción se usó en una venta de 001. Se llama DESPUÉS de la venta, nunca
  dentro de `POST /ventas` (Principio II). Idempotente por el índice único parcial sobre el
  `id_*` de origen. Marca `cupon.estado='redimido'` / `oferta_recompra.desenlace='comprado'`.
- `detectar_ofertas_recompra` (US2, T025) — mecanismo 2: reserva de PRECIO, no de inventario
  (FR-010, FR-011). NO escribe ni lee `existencia` / `movimiento_inventario` de 001.
- `consultar_marca_activa` (US4, T050) — la marca agregada de "promoción activa" que 004 consume
  (FR-031 a FR-034). Sólo lectura sobre `redencion_promocion`.

Frontera de propiedad de datos: `cliente`/`visita`/`intervalo_compra` son de 002;
`venta`/`renglon_venta`/`producto`/`producto_precio_sucursal`/`sucursal`/`turno` son de 001. Este
módulo los CONSULTA, nunca los escribe ni redefine. No toca `existencia`, `movimiento_inventario`
ni `senal_fuga`.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config import promociones as cfg
from rasero.dominio.promociones import (
    cliente_en_ventana_recompra,
    contar_compras_por_producto,
    justificacion_recompra,
    periodo_local_venta,
    seleccionar_producto_recompra,
    ventana_validez_cupon,
)
from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.errores import (
    CuponFueraDeVentana,
    RecursoNoEncontrado,
    RedencionDeGrupoControl,
    RedencionInvalida,
)
from rasero.persistencia.modelos import (
    AsignacionExperimento,
    Campania,
    Cliente,
    Cupon,
    IntervaloCompra,
    OfertaRecompra,
    Producto,
    ProductoPrecioSucursal,
    RedencionPromocion,
    RenglonVenta,
    Sucursal,
    Turno,
    Venta,
    Visita,
)
from rasero.servicios import clientes as servicio_clientes

_CIEN = Decimal("100")
_CUATRO_DECIMALES = Decimal("0.0001")

# `redencion_promocion.tipo_origen` -> el `tipo` que 004 espera en la marca de promoción activa.
_TIPO_MARCA = {
    "cupon": "fecha_fija",
    "oferta_recompra": "recompra",
    "reactivacion": "reactivacion",
}


# ==========================================================================
# Mecanismo 1 — cupón por fecha fija (US1)
# ==========================================================================


def _cumpleanos_en_rango(fecha_nacimiento: date, desde: date, hasta: date) -> date:
    """El (mes, día) de nacimiento cae exactamente una vez en `[desde, hasta]` (rango <= 1 año).
    Devuelve esa fecha concreta (con el año que corresponde), incluso si el rango cruza el 1 ene.
    """
    for anio in (desde.year, hasta.year, desde.year + 1):
        try:
            candidato = fecha_nacimiento.replace(year=anio)
        except ValueError:  # 29 de febrero en un año no bisiesto -> se trata como 1 de marzo
            candidato = date(anio, 3, 1)
        if desde <= candidato <= hasta:
            return candidato
    # Cae fuera del rango por un desajuste de bordes; usa el año de `desde` como aproximación.
    try:
        return fecha_nacimiento.replace(year=desde.year)
    except ValueError:
        return date(desde.year, 3, 1)


def _marcar_cupones_vencidos(sesion: Session) -> None:
    """Un cupón `generado` cuya ventana de validez ya pasó, sin redención, queda `vencido`."""
    hoy = date.today()
    for cupon in sesion.execute(
        select(Cupon).where(Cupon.estado == "generado", Cupon.valido_hasta < hoy)
    ).scalars():
        cupon.estado = "vencido"
    sesion.flush()


def generar_cupones(
    sesion: Session,
    *,
    desde: date,
    hasta: date,
    nombre_campania: str | None = None,
    porcentaje_descuento: Decimal | str | float | None = None,
) -> dict:
    """FR-001 a FR-007. Crea una `campania` de tipo 'fecha_fija' y, para cada cliente que 002
    devuelve en `clientes_con_cumpleanos`, un `cupon` con su ventana de validez. Idempotente: la
    segunda corrida reporta `cupones_generados: 0`.

    `porcentaje_descuento` deja fijar el valor del cupón por campaña; si es `None` se usa
    `cfg.DESCUENTO_CUPON_CUMPLEANOS_PCT`.
    """
    if porcentaje_descuento is None:
        pct = cfg.DESCUENTO_CUPON_CUMPLEANOS_PCT
    else:
        pct = Decimal(str(porcentaje_descuento))
        if pct <= 0 or pct > 100:
            from rasero.errores import ValorInvalido

            raise ValorInvalido("El descuento del cupón debe estar entre 0 y 100 %.")
    if hasta < desde:
        from rasero.errores import RangoFechasInvalido

        raise RangoFechasInvalido()
    if (hasta - desde).days > 366:
        from rasero.errores import RangoFechasInvalido

        raise RangoFechasInvalido("El rango de generación no puede exceder un año.")

    ahora = datetime.now(timezone.utc)
    nombre = nombre_campania or f"Cumpleaños {desde.isoformat()} a {hasta.isoformat()}"
    campania = Campania(
        tipo="fecha_fija",
        id_sucursal=None,
        nombre=nombre,
        ventana_desde=desde,
        ventana_hasta=hasta,
        instante_creacion=ahora,
    )
    sesion.add(campania)
    sesion.flush()

    generados = 0
    ya_existentes = 0
    for cliente in servicio_clientes.clientes_con_cumpleanos(sesion, desde=desde, hasta=hasta):
        fecha_objetivo = _cumpleanos_en_rango(cliente.fecha_nacimiento, desde, hasta)
        existente = sesion.execute(
            select(Cupon.id_cupon).where(
                Cupon.id_cliente == cliente.id_cliente,
                Cupon.fecha_objetivo == fecha_objetivo,
            )
        ).scalar_one_or_none()
        if existente is not None:
            ya_existentes += 1
            continue

        valido_desde, valido_hasta = ventana_validez_cupon(
            fecha_objetivo,
            antelacion_dias=cfg.ANTELACION_GENERACION_CUPON_DIAS,
            validez_dias=cfg.VALIDEZ_CUPON_DIAS,
        )
        sesion.add(
            Cupon(
                id_campania=campania.id_campania,
                id_cliente=cliente.id_cliente,
                motivo="fecha_fija_cumpleanos",
                fecha_objetivo=fecha_objetivo,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                porcentaje_descuento=pct,
                estado="generado",
                instante_generacion=ahora,
            )
        )
        sesion.flush()
        generados += 1

    _marcar_cupones_vencidos(sesion)
    return {
        "id_campania": campania.id_campania,
        "cupones_generados": generados,
        "cupones_ya_existentes": ya_existentes,
    }


def _cupon_a_respuesta(c: Cupon, *, nombre_cliente: str | None = None) -> dict:
    return {
        "id_cupon": c.id_cupon,
        "id_campania": c.id_campania,
        "id_cliente": c.id_cliente,
        # Nombre resuelto por JOIN en el listado (US1 de este bloque). Aditivo: los consumidores
        # que sólo leían id_cliente lo ignoran. `None` si el cliente no tiene nombre registrado.
        "nombre_cliente": nombre_cliente,
        "motivo": c.motivo,
        "fecha_objetivo": c.fecha_objetivo,
        "valido_desde": c.valido_desde,
        "valido_hasta": c.valido_hasta,
        "porcentaje_descuento": f"{c.porcentaje_descuento:.2f}",
        "estado": c.estado,
        "instante_generacion": c.instante_generacion,
    }


def listar_cupones(
    sesion: Session,
    *,
    id_cliente: int | None = None,
    estado: str | None = None,
    vigentes: bool = False,
) -> list[dict]:
    _marcar_cupones_vencidos(sesion)
    stmt = select(Cupon).order_by(Cupon.id_cupon.desc())
    if id_cliente is not None:
        stmt = stmt.where(Cupon.id_cliente == id_cliente)
    if estado is not None:
        stmt = stmt.where(Cupon.estado == estado)
    if vigentes:
        hoy = date.today()
        stmt = stmt.where(
            Cupon.estado == "generado",
            Cupon.valido_desde <= hoy,
            Cupon.valido_hasta >= hoy,
        )
    cupones = list(sesion.execute(stmt).scalars())
    ids = {c.id_cliente for c in cupones}
    nombres: dict[int, str | None] = (
        {
            fila.id_cliente: fila.nombre
            for fila in sesion.execute(
                select(Cliente.id_cliente, Cliente.nombre).where(Cliente.id_cliente.in_(ids))
            )
        }
        if ids
        else {}
    )
    return [_cupon_a_respuesta(c, nombre_cliente=nombres.get(c.id_cliente)) for c in cupones]


def anular_cupon(sesion: Session, *, id_cupon: int) -> Cupon:
    """Anula un cupón todavía sin redimir (arrepentimiento del encargado). Un cupón `redimido`
    no se anula: ya afectó una venta. Un `vencido` tampoco tiene sentido anularlo.
    """
    cupon = sesion.get(Cupon, id_cupon)
    if cupon is None:
        raise RecursoNoEncontrado(f"El cupón {id_cupon} no existe.")
    if cupon.estado != "generado":
        raise RedencionInvalida(
            f"El cupón {id_cupon} está '{cupon.estado}'; sólo se anula un cupón generado."
        )
    cupon.estado = "anulado"
    sesion.flush()
    return cupon


def cancelar_oferta_recompra(sesion: Session, *, id_oferta_recompra: int) -> OfertaRecompra:
    """Cancela una oferta de recompra pendiente. La reserva de precio deja de estar disponible."""
    oferta = sesion.get(OfertaRecompra, id_oferta_recompra)
    if oferta is None:
        raise RecursoNoEncontrado(f"La oferta de recompra {id_oferta_recompra} no existe.")
    if oferta.desenlace != "pendiente":
        raise RedencionInvalida(
            f"La oferta {id_oferta_recompra} ya no está pendiente ('{oferta.desenlace}')."
        )
    oferta.desenlace = "no_comprado"
    oferta.estado_reserva = "vencida"
    sesion.flush()
    return oferta


# ==========================================================================
# Redención transversal (US1 base + rama oferta de US2)
# ==========================================================================


def _resolver_sucursal_y_periodo(sesion: Session, venta: Venta) -> tuple[int, date]:
    """`venta -> turno -> sucursal`, y el día local de la sucursal (research.md #4)."""
    turno = sesion.get(Turno, venta.id_turno)
    if turno is None:  # no debería ocurrir: toda venta tiene turno
        raise RecursoNoEncontrado(f"La venta {venta.id_venta} no tiene turno.")
    sucursal = sesion.get(Sucursal, turno.id_sucursal)
    periodo = periodo_local_venta(venta.instante, sucursal.zona_horaria)
    return sucursal.id_sucursal, periodo


def _descuento_de_producto(
    sesion: Session, *, id_venta: int, id_producto: int | None, id_sucursal: int
) -> Decimal | None:
    """Monto del descuento efectivamente aplicado a `id_producto` en la venta = suma de
    `(precio_lista - precio_aplicado) * cantidad` sobre sus renglones. `None` si no hay
    `id_producto` (cupón de canasta) o no se puede determinar / no hubo descuento.
    """
    if id_producto is None:
        return None
    producto = sesion.get(Producto, id_producto)
    if producto is None:
        return None
    override = sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()
    precio_lista = resolver_precio_efectivo(
        precio_base=producto.precio_vigente, override_sucursal=override
    )
    total = Decimal(0)
    hubo = False
    for r in sesion.execute(
        select(RenglonVenta).where(
            RenglonVenta.id_venta == id_venta, RenglonVenta.id_producto == id_producto
        )
    ).scalars():
        cantidad = Decimal(r.cantidad_unidades or 0) + Decimal(r.cantidad_gramos or 0)
        delta = (precio_lista - r.precio_aplicado) * cantidad
        if delta > 0:
            total += delta
            hubo = True
    return total.quantize(_CUATRO_DECIMALES) if hubo else None


def registrar_redencion(
    sesion: Session,
    *,
    id_venta: int,
    tipo_origen: str,
    id_cupon: int | None = None,
    id_oferta_recompra: int | None = None,
    id_asignacion_experimento: int | None = None,
    id_producto: int | None = None,
) -> tuple[RedencionPromocion, bool]:
    """Devuelve `(redencion, creada_ahora)`. `creada_ahora=False` en un segundo POST sobre el
    mismo origen (idempotencia, mismo patrón que `registrar_visita` de 002).
    """
    origenes = {
        "cupon": id_cupon,
        "oferta_recompra": id_oferta_recompra,
        "reactivacion": id_asignacion_experimento,
    }
    if tipo_origen not in origenes:
        raise RedencionInvalida(f"tipo_origen '{tipo_origen}' no es válido.")
    if origenes[tipo_origen] is None or sum(1 for v in origenes.values() if v is not None) != 1:
        raise RedencionInvalida(
            "Debes indicar exactamente el id de origen que corresponde a tipo_origen."
        )

    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")
    id_sucursal, periodo = _resolver_sucursal_y_periodo(sesion, venta)

    columna_origen = {
        "cupon": RedencionPromocion.id_cupon,
        "oferta_recompra": RedencionPromocion.id_oferta_recompra,
        "reactivacion": RedencionPromocion.id_asignacion_experimento,
    }[tipo_origen]
    id_origen = origenes[tipo_origen]

    # Idempotencia: una redención por origen (índice único parcial).
    existente = sesion.execute(
        select(RedencionPromocion).where(columna_origen == id_origen)
    ).scalar_one_or_none()
    if existente is not None:
        return existente, False

    cupon = oferta = asignacion = None
    if tipo_origen == "cupon":
        cupon = sesion.get(Cupon, id_cupon)
        if cupon is None:
            raise RecursoNoEncontrado(f"El cupón {id_cupon} no existe.")
        if not (cupon.valido_desde <= periodo <= cupon.valido_hasta):
            raise CuponFueraDeVentana()
    elif tipo_origen == "oferta_recompra":
        oferta = sesion.get(OfertaRecompra, id_oferta_recompra)
        if oferta is None:
            raise RecursoNoEncontrado(f"La oferta de recompra {id_oferta_recompra} no existe.")
        if id_producto is None:
            id_producto = oferta.id_producto
    else:  # reactivacion
        asignacion = sesion.get(AsignacionExperimento, id_asignacion_experimento)
        if asignacion is None:
            raise RecursoNoEncontrado(
                f"La asignación de experimento {id_asignacion_experimento} no existe."
            )
        if asignacion.grupo == "control":
            raise RedencionDeGrupoControl()

    redencion = RedencionPromocion(
        tipo_origen=tipo_origen,
        id_cupon=id_cupon,
        id_oferta_recompra=id_oferta_recompra,
        id_asignacion_experimento=id_asignacion_experimento,
        id_venta=id_venta,
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        periodo=periodo,
        descuento_aplicado=_descuento_de_producto(
            sesion, id_venta=id_venta, id_producto=id_producto, id_sucursal=id_sucursal
        ),
        instante_redencion=datetime.now(timezone.utc),
    )
    sesion.add(redencion)

    # Efecto sobre el origen (T013 cupón; T027 oferta). La reactivación no cambia su asignación:
    # el `retorno` se computa al cerrar el experimento mirando `visita` de 002 (research.md #11).
    if cupon is not None:
        cupon.estado = "redimido"
    if oferta is not None and oferta.desenlace == "pendiente":
        oferta.desenlace = "comprado"

    sesion.flush()
    return redencion, True


def redencion_a_respuesta(r: RedencionPromocion) -> dict:
    return {
        "id_redencion_promocion": r.id_redencion_promocion,
        "tipo_origen": r.tipo_origen,
        "id_cupon": r.id_cupon,
        "id_oferta_recompra": r.id_oferta_recompra,
        "id_asignacion_experimento": r.id_asignacion_experimento,
        "id_venta": r.id_venta,
        "id_producto": r.id_producto,
        "id_sucursal": r.id_sucursal,
        "periodo": r.periodo,
        "descuento_aplicado": (
            f"{r.descuento_aplicado:.4f}" if r.descuento_aplicado is not None else None
        ),
        "instante_redencion": r.instante_redencion,
    }


# ==========================================================================
# Mecanismo 2 — empuje por recompra con reserva de precio (US2)
# ==========================================================================


def _marcar_reservas_vencidas(sesion: Session) -> None:
    hoy = date.today()
    for oferta in sesion.execute(
        select(OfertaRecompra).where(
            OfertaRecompra.desenlace == "pendiente", OfertaRecompra.reserva_hasta < hoy
        )
    ).scalars():
        oferta.estado_reserva = "vencida"
        oferta.desenlace = "reserva_vencida"
    sesion.flush()


def detectar_ofertas_recompra(sesion: Session, *, id_sucursal: int) -> dict:
    """FR-008 a FR-014. Para cada cliente con `intervalo_compra.estado='calculado'` que se acerca
    a su intervalo esperado sin superarlo, propone una oferta de un producto que suele recomprar,
    con una RESERVA DE PRECIO. **No consulta ni escribe `existencia` / `movimiento_inventario`.**
    """
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    _marcar_reservas_vencidas(sesion)

    ahora = datetime.now(timezone.utc)
    reserva_hasta = date.today() + timedelta(days=cfg.VENTANA_RESERVA_RECOMPRA_DIAS)
    campania = Campania(
        tipo="recompra",
        id_sucursal=id_sucursal,
        nombre=f"Recompra {sucursal.nombre} {date.today().isoformat()}",
        ventana_desde=date.today(),
        ventana_hasta=reserva_hasta,
        instante_creacion=ahora,
    )
    sesion.add(campania)
    sesion.flush()

    corte_historial = ahora - timedelta(days=cfg.VENTANA_HISTORIAL_RECOMPRA_DIAS)
    candidatos = sesion.execute(
        select(
            IntervaloCompra.id_cliente,
            IntervaloCompra.intervalo_esperado_dias,
            func.max(Visita.instante),
        )
        .join(Visita, Visita.id_cliente == IntervaloCompra.id_cliente)
        .where(IntervaloCompra.estado == "calculado")
        .group_by(IntervaloCompra.id_cliente, IntervaloCompra.intervalo_esperado_dias)
    ).all()

    propuestas = 0
    ya_activas = 0
    for id_cliente, intervalo_esperado_dias, ultima_visita in candidatos:
        dias_sin_compra = (ahora - ultima_visita).total_seconds() / 86400
        if not cliente_en_ventana_recompra(
            dias_sin_compra,
            intervalo_esperado_dias,
            margen=cfg.MARGEN_ANTICIPACION_RECOMPRA,
        ):
            continue

        # El historial que sustenta la oferta se limita a las compras de este cliente EN ESTA
        # sucursal (`venta -> turno -> sucursal`): la reserva de precio se redime aquí (FR-035),
        # así que "el producto que suele recomprar" es el que suele recomprar en esta sucursal.
        renglones = sesion.execute(
            select(RenglonVenta.id_venta, RenglonVenta.id_producto, Venta.instante)
            .join(Venta, Venta.id_venta == RenglonVenta.id_venta)
            .join(Turno, Turno.id_turno == Venta.id_turno)
            .join(Visita, Visita.id_venta == Venta.id_venta)
            .where(
                Visita.id_cliente == id_cliente,
                Venta.instante >= corte_historial,
                Turno.id_sucursal == id_sucursal,
            )
        ).all()
        compras_por_producto = contar_compras_por_producto([(v, p, i) for v, p, i in renglones])
        id_producto = seleccionar_producto_recompra(
            compras_por_producto, minimo_compras=cfg.MIN_COMPRAS_PRODUCTO_RECOMPRA
        )
        if id_producto is None:
            continue

        existe_pendiente = sesion.execute(
            select(OfertaRecompra.id_oferta_recompra).where(
                OfertaRecompra.id_cliente == id_cliente,
                OfertaRecompra.id_producto == id_producto,
                OfertaRecompra.desenlace == "pendiente",
            )
        ).scalar_one_or_none()
        if existe_pendiente is not None:
            ya_activas += 1
            continue

        producto = sesion.get(Producto, id_producto)
        override = sesion.execute(
            select(ProductoPrecioSucursal.precio_vigente).where(
                ProductoPrecioSucursal.id_producto == id_producto,
                ProductoPrecioSucursal.id_sucursal == id_sucursal,
            )
        ).scalar_one_or_none()
        precio_resuelto = resolver_precio_efectivo(
            precio_base=producto.precio_vigente, override_sucursal=override
        )
        precio_garantizado = (
            precio_resuelto * (_CIEN - cfg.DESCUENTO_RECOMPRA_PCT) / _CIEN
        ).quantize(_CUATRO_DECIMALES, rounding=ROUND_HALF_UP)

        instantes_por_venta = {v: i for v, p, i in renglones if p == id_producto}
        sesion.add(
            OfertaRecompra(
                id_campania=campania.id_campania,
                id_cliente=id_cliente,
                id_producto=id_producto,
                id_sucursal=id_sucursal,
                intervalo_esperado_dias_disparo=intervalo_esperado_dias,
                justificacion=justificacion_recompra(
                    instantes_por_venta,
                    ventana_dias=cfg.VENTANA_HISTORIAL_RECOMPRA_DIAS,
                ),
                precio_garantizado=precio_garantizado,
                reserva_desde=date.today(),
                reserva_hasta=reserva_hasta,
                estado_reserva="vigente",
                desenlace="pendiente",
                instante_generacion=ahora,
            )
        )
        sesion.flush()
        propuestas += 1

    return {
        "id_campania": campania.id_campania,
        "ofertas_propuestas": propuestas,
        "ofertas_ya_activas": ya_activas,
    }


def _oferta_a_respuesta(o: OfertaRecompra) -> dict:
    return {
        "id_oferta_recompra": o.id_oferta_recompra,
        "id_campania": o.id_campania,
        "id_cliente": o.id_cliente,
        "id_producto": o.id_producto,
        "id_sucursal": o.id_sucursal,
        "intervalo_esperado_dias_disparo": f"{o.intervalo_esperado_dias_disparo:.2f}",
        "justificacion": o.justificacion,
        "precio_garantizado": f"{o.precio_garantizado:.4f}",
        "reserva_desde": o.reserva_desde,
        "reserva_hasta": o.reserva_hasta,
        "estado_reserva": o.estado_reserva,
        "desenlace": o.desenlace,
        "instante_generacion": o.instante_generacion,
    }


def listar_ofertas_recompra(
    sesion: Session, *, id_cliente: int | None = None, desenlace: str | None = None
) -> list[dict]:
    _marcar_reservas_vencidas(sesion)
    stmt = select(OfertaRecompra).order_by(OfertaRecompra.id_oferta_recompra.desc())
    if id_cliente is not None:
        stmt = stmt.where(OfertaRecompra.id_cliente == id_cliente)
    if desenlace is not None:
        stmt = stmt.where(OfertaRecompra.desenlace == desenlace)
    return [_oferta_a_respuesta(o) for o in sesion.execute(stmt).scalars()]


# ==========================================================================
# Rendimiento de campañas — "¿sirvió la promo?"
# ==========================================================================


def rendimiento_campanias(
    sesion: Session, *, id_sucursal: int, desde: date, hasta: date
) -> dict:
    """Cierra el ciclo de la pantalla de Promociones: hoy se generan cupones y se detectan
    ofertas, pero nunca se ve si funcionaron. Agrega, para la sucursal y la ventana:

    - Cupones: emitidos / redimidos / vencidos / anulados y tasa de redención.
    - Ofertas de recompra: propuestas / compradas / reserva vencida.
    - Descuento total efectivamente otorgado (`SUM(redencion_promocion.descuento_aplicado)`),
      por tipo de mecanismo, y nº de ventas influidas.

    Sólo lectura. `redencion_promocion` ya trae `id_sucursal` y `periodo` denormalizados.
    """
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    _marcar_cupones_vencidos(sesion)
    _marcar_reservas_vencidas(sesion)

    # Cupones emitidos en la ventana (por fecha objetivo, que es cuando "cuenta" la campaña).
    cupones = list(
        sesion.execute(
            select(Cupon).where(
                Cupon.fecha_objetivo >= desde, Cupon.fecha_objetivo <= hasta
            )
        ).scalars()
    )
    por_estado: dict[str, int] = {}
    for c in cupones:
        por_estado[c.estado] = por_estado.get(c.estado, 0) + 1
    emitidos = len(cupones)
    redimidos = por_estado.get("redimido", 0)

    ofertas = list(
        sesion.execute(
            select(OfertaRecompra).where(
                OfertaRecompra.id_sucursal == id_sucursal,
                OfertaRecompra.reserva_desde >= desde,
                OfertaRecompra.reserva_desde <= hasta,
            )
        ).scalars()
    )
    ofertas_por_desenlace: dict[str, int] = {}
    for o in ofertas:
        ofertas_por_desenlace[o.desenlace] = ofertas_por_desenlace.get(o.desenlace, 0) + 1

    # Redenciones (descuento otorgado + ventas influidas) por tipo, en la sucursal y ventana.
    redenciones = sesion.execute(
        select(
            RedencionPromocion.tipo_origen,
            RedencionPromocion.descuento_aplicado,
            RedencionPromocion.id_venta,
        ).where(
            RedencionPromocion.id_sucursal == id_sucursal,
            RedencionPromocion.periodo >= desde,
            RedencionPromocion.periodo <= hasta,
        )
    ).all()
    descuento_por_tipo: dict[str, Decimal] = {}
    ventas_por_tipo: dict[str, set[int]] = {}
    for tipo_origen, descuento, id_venta in redenciones:
        if descuento is not None:
            descuento_por_tipo[tipo_origen] = descuento_por_tipo.get(
                tipo_origen, Decimal(0)
            ) + Decimal(descuento)
        ventas_por_tipo.setdefault(tipo_origen, set()).add(id_venta)

    return {
        "id_sucursal": id_sucursal,
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "cupones": {
            "emitidos": emitidos,
            "redimidos": redimidos,
            "vencidos": por_estado.get("vencido", 0),
            "anulados": por_estado.get("anulado", 0),
            "tasa_redencion": (
                f"{(Decimal(redimidos) / Decimal(emitidos)):.4f}" if emitidos else "0.0000"
            ),
        },
        "ofertas_recompra": {
            "propuestas": len(ofertas),
            "compradas": ofertas_por_desenlace.get("comprado", 0),
            "reserva_vencida": ofertas_por_desenlace.get("reserva_vencida", 0),
        },
        "por_mecanismo": [
            {
                "tipo_origen": tipo,
                "descuento_otorgado": f"{descuento_por_tipo.get(tipo, Decimal(0)):.2f}",
                "ventas_influidas": len(ventas_por_tipo.get(tipo, set())),
            }
            for tipo in sorted(set(descuento_por_tipo) | set(ventas_por_tipo))
        ],
    }


# ==========================================================================
# Marca agregada de "promoción activa" para 004 (US4)
# ==========================================================================


def consultar_marca_activa(
    sesion: Session, *, id_sucursal: int, desde: date, hasta: date
) -> list[dict]:
    """FR-031 a FR-035, SC-009. Agrega `redencion_promocion` por `(id_producto, id_sucursal,
    periodo)` en la ventana y lista los tipos de promoción. Las filas con `id_producto = NULL`
    (cupón/reactivación de canasta) se **expanden** a todos los productos de su venta vía
    `renglon_venta` de 001. Exige `id_sucursal`; nunca mezcla dos sucursales.
    """
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    filas = sesion.execute(
        select(
            RedencionPromocion.id_producto,
            RedencionPromocion.periodo,
            RedencionPromocion.tipo_origen,
            RedencionPromocion.id_venta,
        ).where(
            RedencionPromocion.id_sucursal == id_sucursal,
            RedencionPromocion.periodo >= desde,
            RedencionPromocion.periodo <= hasta,
        )
    ).all()

    marca: dict[tuple[int, date], set[str]] = {}
    for id_producto, periodo, tipo_origen, id_venta in filas:
        tipo_marca = _TIPO_MARCA[tipo_origen]
        if id_producto is not None:
            marca.setdefault((id_producto, periodo), set()).add(tipo_marca)
            continue
        for (id_prod_renglon,) in sesion.execute(
            select(RenglonVenta.id_producto).where(RenglonVenta.id_venta == id_venta).distinct()
        ).all():
            marca.setdefault((id_prod_renglon, periodo), set()).add(tipo_marca)

    return [
        {
            "id_producto": id_producto,
            "id_sucursal": id_sucursal,
            "periodo": periodo,
            "tipos": sorted(tipos),
        }
        for (id_producto, periodo), tipos in sorted(marca.items())
    ]
