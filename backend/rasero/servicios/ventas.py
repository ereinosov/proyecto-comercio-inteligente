"""Registro y anulación de venta (T026, T027).

El eje: `movimiento_inventario` es la única fuente de verdad; `existencia` se actualiza por
delta en la misma transacción (persistencia/movimientos.py). La venta es idempotente por
`clave_idempotencia` — la restricción UNIQUE de base de datos es lo que hace que la unicidad
de la venta implique unicidad de sus movimientos, incluso bajo reintentos concurrentes
(research.md, decisión 2).

Existencia insuficiente: **bloqueo duro** (spec 001, Corrección 2026-09-07). Antes de escribir
ningún movimiento se valida cada renglón contra la existencia disponible del producto en la
sucursal; si alguno no alcanza, la venta COMPLETA se rechaza con `ExistenciaInsuficiente` (409)
y no queda ningún movimiento a medias. La cita previa del Principio II ("ninguna validación
bloquea el cobro") estaba mal aplicada: el Principio II protege contra la caída de servicios
externos, no contra una consulta determinista a la propia base. El saldo negativo histórico
anterior a esta corrección sigue siendo válido y visible.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.dominio.seleccion_lote import ordenar_fefo
from rasero.dominio.totales import calcular_importe_renglon, calcular_total_venta
from rasero.errores import (
    AnulacionNoAutorizada,
    ExistenciaInsuficiente,
    RecursoNoEncontrado,
    RenglonInvalido,
    TurnoInvalido,
    VentaYaAnulada,
)
from rasero.persistencia.modelos import (
    AnulacionVenta,
    Lote,
    MedioPago,
    MovimientoInventario,
    Operador,
    Producto,
    ProductoPrecioSucursal,
    RenglonVenta,
    Turno,
    Venta,
)
from rasero.persistencia.movimientos import (
    obtener_existencia,
    obtener_existencia_total,
    registrar_movimiento,
)
from rasero.seguridad import RANGO_ROL


@dataclass
class RenglonEntrada:
    id_producto: int
    cantidad_unidades: int | None
    cantidad_gramos: int | None


def _resolver_precio(sesion: Session, *, id_producto: int, id_sucursal: int, precio_base: Decimal) -> Decimal:
    override = sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()
    return resolver_precio_efectivo(precio_base=precio_base, override_sucursal=override)


def _cantidad_base_renglon(producto: Producto, entrada: RenglonEntrada) -> Decimal:
    """Valida la forma del renglón (granel vs. unidad, positivo) y devuelve la cantidad en la
    unidad base del producto (gramos si es granel, unidades si no). Único lugar donde vive esta
    regla — la usan la pre-validación de existencia y el consumo FEFO.
    """
    if producto.es_granel:
        if entrada.cantidad_gramos is None or entrada.cantidad_unidades is not None:
            raise RenglonInvalido(
                f"El producto {producto.nombre} se vende a peso: envía cantidad_gramos."
            )
        if entrada.cantidad_gramos <= 0:
            raise RenglonInvalido("El peso leído en báscula debe ser mayor que cero.")
        return Decimal(entrada.cantidad_gramos)
    if entrada.cantidad_unidades is None or entrada.cantidad_gramos is not None:
        raise RenglonInvalido(
            f"El producto {producto.nombre} se vende por unidad: envía cantidad_unidades."
        )
    if entrada.cantidad_unidades <= 0:
        raise RenglonInvalido("La cantidad debe ser mayor que cero.")
    return Decimal(entrada.cantidad_unidades)


def _consumir_fefo(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int,
    nombre_producto: str,
    cantidad_requerida: Decimal,
    instante: datetime,
    id_venta: int,
) -> tuple[list[dict], list[dict]]:
    """Consume existencia en orden FEFO. Devuelve (lotes_consumidos, advertencias); la lista de
    advertencias hoy siempre es vacía — se conserva por compatibilidad del contrato de venta.
    """
    lotes = sesion.execute(
        select(Lote)
        .where(Lote.id_producto == id_producto, Lote.id_sucursal == id_sucursal)
        .with_for_update()
    ).scalars().all()
    lotes_ordenados = ordenar_fefo(lotes)

    restante = cantidad_requerida
    lotes_consumidos: list[dict] = []

    for lote in lotes_ordenados:
        if restante <= 0:
            break
        disponible = obtener_existencia(
            sesion, id_sucursal=id_sucursal, id_producto=id_producto, id_lote=lote.id_lote
        )
        tomar = min(restante, disponible) if disponible > 0 else Decimal(0)
        if tomar > 0:
            registrar_movimiento(
                sesion,
                id_sucursal=id_sucursal,
                id_producto=id_producto,
                id_lote=lote.id_lote,
                tipo="salida_venta",
                cantidad=-tomar,
                instante=instante,
                id_venta=id_venta,
            )
            lotes_consumidos.append({"id_lote": lote.id_lote, "cantidad": tomar})
            restante -= tomar

    if restante > 0:
        # Inalcanzable en el flujo normal: `registrar_venta` ya validó la existencia total del
        # producto antes de tocar ningún movimiento. Queda como defensa por si la existencia
        # disponible está atrapada en una fila sin lote que FEFO no puede consumir — bloqueo
        # duro, nunca un saldo negativo silencioso.
        disponible = obtener_existencia_total(
            sesion, id_sucursal=id_sucursal, id_producto=id_producto
        )
        raise ExistenciaInsuficiente(nombre_producto, disponible, cantidad_requerida)

    return lotes_consumidos, []


def registrar_venta(
    sesion: Session,
    *,
    clave_idempotencia: str,
    id_turno: int,
    referencia_terminal_pago: str | None,
    instante_origen: datetime | None,
    renglones: list[RenglonEntrada],
    id_medio_pago: int | None = None,
) -> tuple[Venta, bool, list[dict], dict[int, list[dict]]]:
    """Devuelve (venta, creada_ahora, advertencias, lotes_consumidos_por_renglon)."""

    existente = sesion.execute(
        select(Venta).where(Venta.clave_idempotencia == clave_idempotencia)
    ).scalar_one_or_none()
    if existente is not None:
        return existente, False, [], {}

    if not renglones:
        raise RenglonInvalido("La venta debe tener al menos un renglón.")

    turno = sesion.get(Turno, id_turno)
    if turno is None:
        raise TurnoInvalido("El turno indicado no existe.")

    # Bloqueo duro por existencia insuficiente (Corrección 2026-09-07): se valida la venta
    # COMPLETA contra la existencia disponible ANTES de escribir ningún movimiento. Si un solo
    # renglón no alcanza, se rechaza la venta entera — nunca un consumo parcial silencioso.
    requerido_por_producto: dict[int, tuple[str, Decimal]] = {}
    for entrada in renglones:
        producto = sesion.get(Producto, entrada.id_producto)
        if producto is None:
            raise RecursoNoEncontrado(f"El producto {entrada.id_producto} no existe.")
        cantidad_base = _cantidad_base_renglon(producto, entrada)
        nombre, acumulado = requerido_por_producto.get(
            producto.id_producto, (producto.nombre, Decimal(0))
        )
        requerido_por_producto[producto.id_producto] = (nombre, acumulado + cantidad_base)
    for id_producto, (nombre, requerido) in requerido_por_producto.items():
        disponible = obtener_existencia_total(
            sesion, id_sucursal=turno.id_sucursal, id_producto=id_producto
        )
        if disponible < requerido:
            raise ExistenciaInsuficiente(nombre, disponible, requerido)

    instante = instante_origen or datetime.now(timezone.utc)

    # El medio de pago es opcional y de sólo lectura sobre el catálogo de 007. Si llega un id
    # que no existe o está inactivo, se rechaza el cobro con un mensaje de acción correctiva
    # (consulta determinista a la propia base, no un servicio externo — no la protege el
    # Principio II, igual que la validación de existencia).
    if id_medio_pago is not None:
        medio = sesion.get(MedioPago, id_medio_pago)
        if medio is None or not medio.activo:
            raise RenglonInvalido(
                "El medio de pago seleccionado no está disponible. Elige otro y vuelve a cobrar."
            )

    venta = Venta(
        clave_idempotencia=clave_idempotencia,
        id_turno=id_turno,
        referencia_terminal_pago=referencia_terminal_pago,
        id_medio_pago=id_medio_pago,
        instante=instante,
        total=Decimal("0.00"),
    )
    sesion.add(venta)
    sesion.flush()

    importes: list[Decimal] = []
    advertencias: list[dict] = []
    lotes_consumidos_por_renglon: dict[int, list[dict]] = {}

    for entrada in renglones:
        producto = sesion.get(Producto, entrada.id_producto)
        if producto is None:
            raise RecursoNoEncontrado(f"El producto {entrada.id_producto} no existe.")

        cantidad_base = _cantidad_base_renglon(producto, entrada)

        precio = _resolver_precio(
            sesion,
            id_producto=producto.id_producto,
            id_sucursal=turno.id_sucursal,
            precio_base=producto.precio_vigente,
        )
        importe = calcular_importe_renglon(
            cantidad_unidades=entrada.cantidad_unidades,
            cantidad_gramos=entrada.cantidad_gramos,
            precio_por_unidad_o_kg=precio,
        )

        renglon = RenglonVenta(
            id_venta=venta.id_venta,
            id_producto=producto.id_producto,
            cantidad_unidades=entrada.cantidad_unidades,
            cantidad_gramos=entrada.cantidad_gramos,
            precio_aplicado=precio,
            importe=importe,
            moneda=producto.moneda,
        )
        sesion.add(renglon)
        sesion.flush()
        importes.append(importe)

        lotes_consumidos, advertencias_renglon = _consumir_fefo(
            sesion,
            id_sucursal=turno.id_sucursal,
            id_producto=producto.id_producto,
            nombre_producto=producto.nombre,
            cantidad_requerida=cantidad_base,
            instante=instante,
            id_venta=venta.id_venta,
        )
        lotes_consumidos_por_renglon[renglon.id_renglon_venta] = lotes_consumidos
        advertencias.extend(advertencias_renglon)

    venta.total = calcular_total_venta(importes)
    sesion.flush()

    try:
        sesion.commit()
    except IntegrityError:
        # Reintento concurrente con la misma clave: gana quien insertó primero.
        sesion.rollback()
        existente = sesion.execute(
            select(Venta).where(Venta.clave_idempotencia == clave_idempotencia)
        ).scalar_one()
        return existente, False, [], {}

    return venta, True, advertencias, lotes_consumidos_por_renglon


def anular_venta(
    sesion: Session, *, id_venta: int, id_operador_ejecuta: int, motivo: str | None
) -> AnulacionVenta:
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")

    ya_anulada = sesion.execute(
        select(AnulacionVenta).where(AnulacionVenta.id_venta == id_venta)
    ).scalar_one_or_none()
    if ya_anulada is not None:
        raise VentaYaAnulada()

    operador = sesion.get(Operador, id_operador_ejecuta)
    if operador is None or not operador.activo:
        raise RecursoNoEncontrado("El operador que anula no existe o está inactivo.")

    turno_venta = sesion.get(Turno, venta.id_turno)
    turno_en_curso = turno_venta.instante_cierre is None
    es_su_propio_turno = turno_venta.id_operador == id_operador_ejecuta

    # Enmienda v2.3.0: el rango de rol se lee de RANGO_ROL (jerarquía central), no de un
    # booleano por operador. Anular una venta de turno cerrado exige rol `encargado` o más.
    tiene_rango_encargado = RANGO_ROL.get(operador.rol, 0) >= RANGO_ROL["encargado"]
    autorizado = (turno_en_curso and es_su_propio_turno) or tiene_rango_encargado
    if not autorizado:
        raise AnulacionNoAutorizada()

    instante = datetime.now(timezone.utc)
    anulacion = AnulacionVenta(
        id_venta=id_venta, id_operador=id_operador_ejecuta, instante=instante, motivo=motivo
    )
    sesion.add(anulacion)
    sesion.flush()

    movimientos_originales = sesion.execute(
        select(MovimientoInventario).where(
            MovimientoInventario.id_venta == id_venta,
            MovimientoInventario.tipo == "salida_venta",
        )
    ).scalars().all()

    for mov in movimientos_originales:
        registrar_movimiento(
            sesion,
            id_sucursal=mov.id_sucursal,
            id_producto=mov.id_producto,
            id_lote=mov.id_lote,
            tipo="entrada_anulacion",
            cantidad=-mov.cantidad,
            instante=instante,
            id_anulacion_venta=anulacion.id_anulacion_venta,
        )

    sesion.commit()
    return anulacion
