"""Entradas de inventario, consulta de existencias y capital inmovilizado
(001-core-ventas-inventario, US2 T045 · US2 T047 · US7 T081).

- `registrar_entrada` — compra a proveedor: crea o alimenta un lote en la sucursal receptora con
  su costo y, si el producto lo requiere, su caducidad (FR-012, FR-013). Genera un movimiento
  `entrada_compra`; `existencia` se mueve por delta en la misma transacción. **Solo costo, nunca
  margen** (FR-014).
- `listar_existencias` — saldo por producto y sucursal, agregado sobre `existencia` (derivada de
  `movimiento_inventario`). Puede ser negativo (dato histórico, FR-047 previo); nunca se limita a
  cero.
- `existencia_por_lote` — desglose del saldo de UN producto en UNA sucursal, lote por lote, en el
  mismo orden FEFO que el consumo de 001 (US14). El costo sólo se incluye si se pide
  explícitamente (`incluir_costo=True`): es dato de margen, fuera de la vista de caja.
- `capital_inmovilizado` — lotes cuya última salida excede el umbral de días de su categoría
  (`COALESCE(categoria.dias_umbral_inmovilizado, umbral_global)`); valor = cantidad restante ×
  costo, o "no calculable" si el lote no tiene costo (FR-033 a FR-036). Solo hace visible el dato.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.configuracion import UMBRAL_GLOBAL_DIAS_INMOVILIZADO
from rasero.errores import RecursoNoEncontrado, RenglonInvalido
from rasero.persistencia.modelos import (
    Categoria,
    Existencia,
    Lote,
    MovimientoInventario,
    Producto,
    Sucursal,
)
from rasero.persistencia.movimientos import obtener_existencia, registrar_movimiento


def registrar_entrada(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int,
    cantidad: int,
    costo_unitario: Decimal,
    fecha_caducidad: date | None = None,
) -> Lote:
    if cantidad <= 0:
        raise RenglonInvalido("La cantidad de la entrada debe ser mayor que cero.")

    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")
    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    costo = Decimal(costo_unitario)
    instante = datetime.now(timezone.utc)

    # Crea o alimenta un lote: se reutiliza el que coincida en producto, sucursal, costo y
    # caducidad; si no hay ninguno, se crea uno nuevo (openapi: "crea o alimenta un lote").
    lote = sesion.execute(
        select(Lote)
        .where(
            Lote.id_producto == id_producto,
            Lote.id_sucursal == id_sucursal,
            Lote.costo_unitario == costo,
            Lote.fecha_caducidad.is_(fecha_caducidad)
            if fecha_caducidad is None
            else Lote.fecha_caducidad == fecha_caducidad,
        )
        .order_by(Lote.instante_entrada)
        .limit(1)
    ).scalar_one_or_none()

    if lote is None:
        lote = Lote(
            id_producto=id_producto,
            id_sucursal=id_sucursal,
            costo_unitario=costo,
            fecha_caducidad=fecha_caducidad,
            instante_entrada=instante,
            moneda=producto.moneda,
        )
        sesion.add(lote)
        sesion.flush()

    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(cantidad),
        instante=instante,
    )
    sesion.commit()
    return lote


def cantidad_restante_lote(sesion: Session, id_lote: int) -> Decimal:
    lote = sesion.get(Lote, id_lote)
    if lote is None:
        return Decimal(0)
    return obtener_existencia(
        sesion, id_sucursal=lote.id_sucursal, id_producto=lote.id_producto, id_lote=id_lote
    )


def listar_existencias(
    sesion: Session, *, id_sucursal: int, id_producto: int | None = None
) -> list[dict]:
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")

    consulta = (
        select(
            Existencia.id_producto,
            func.coalesce(func.sum(Existencia.cantidad), 0),
            Producto.es_granel,
        )
        .join(Producto, Producto.id_producto == Existencia.id_producto)
        .where(Existencia.id_sucursal == id_sucursal)
        .group_by(Existencia.id_producto, Producto.es_granel)
        .order_by(Existencia.id_producto)
    )
    if id_producto is not None:
        consulta = consulta.where(Existencia.id_producto == id_producto)

    return [
        {
            "id_sucursal": id_sucursal,
            "id_producto": pid,
            "cantidad": int(cantidad),
            "es_granel": es_granel,
        }
        for pid, cantidad, es_granel in sesion.execute(consulta).all()
    ]


def existencia_por_lote(
    sesion: Session,
    *,
    id_sucursal: int,
    id_producto: int,
    incluir_costo: bool = False,
) -> list[dict]:
    """Saldo de `id_producto` en `id_sucursal`, lote por lote, en orden FEFO (misma clave que el
    consumo de 001: caducidad ascendente con nulos al final, luego entrada, luego id_lote). Sólo
    lotes con saldo distinto de cero. `costo_unitario` se incluye únicamente si `incluir_costo`
    — es dato de margen, no de la pantalla de Venta (US14).
    """
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    filas = sesion.execute(
        select(Lote, Existencia.cantidad)
        .join(
            Existencia,
            (Existencia.id_lote == Lote.id_lote)
            & (Existencia.id_sucursal == Lote.id_sucursal)
            & (Existencia.id_producto == Lote.id_producto),
        )
        .where(
            Lote.id_sucursal == id_sucursal,
            Lote.id_producto == id_producto,
            Existencia.cantidad != 0,
        )
        .order_by(
            Lote.fecha_caducidad.asc().nulls_last(),
            Lote.instante_entrada.asc(),
            Lote.id_lote.asc(),
        )
    ).all()

    resultado: list[dict] = []
    for lote, cantidad in filas:
        fila = {
            "id_lote": lote.id_lote,
            "cantidad": int(cantidad),
            "fecha_caducidad": lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
            "instante_entrada": lote.instante_entrada,
        }
        if incluir_costo:
            # `0.0000` es el centinela de "sin costo registrado" (research.md §11).
            costo = Decimal(lote.costo_unitario)
            fila["costo_unitario"] = None if costo == 0 else f"{costo:.4f}"
        resultado.append(fila)
    return resultado


def _dia_local(instante: datetime, zona_horaria: str) -> date:
    return instante.astimezone(ZoneInfo(zona_horaria)).date()


def capital_inmovilizado(sesion: Session, *, id_sucursal: int | None = None) -> list[dict]:
    """Lotes con existencia positiva cuya última salida (o, si nunca tuvo salida, su entrada)
    lleva más días parada que el umbral de su categoría. Valor = cantidad restante × costo; sin
    costo, `valor_inmovilizado = null` y `valor_calculable = false`, nunca cero (FR-035).
    """
    saldo_por_lote = {
        id_lote: Decimal(saldo)
        for id_lote, saldo in sesion.execute(
            select(Existencia.id_lote, func.sum(Existencia.cantidad))
            .where(Existencia.id_lote.is_not(None))
            .group_by(Existencia.id_lote)
        ).all()
    }
    # Última salida por lote: el movimiento negativo más reciente.
    ultima_salida = {
        id_lote: instante
        for id_lote, instante in sesion.execute(
            select(MovimientoInventario.id_lote, func.max(MovimientoInventario.instante))
            .where(
                MovimientoInventario.id_lote.is_not(None),
                MovimientoInventario.cantidad < 0,
            )
            .group_by(MovimientoInventario.id_lote)
        ).all()
    }

    consulta = (
        select(Lote, Categoria.dias_umbral_inmovilizado, Sucursal.zona_horaria)
        .join(Producto, Producto.id_producto == Lote.id_producto)
        .join(Sucursal, Sucursal.id_sucursal == Lote.id_sucursal)
        .join(Categoria, Categoria.id_categoria == Producto.id_categoria, isouter=True)
    )
    if id_sucursal is not None:
        consulta = consulta.where(Lote.id_sucursal == id_sucursal)

    hoy_por_zona: dict[str, date] = {}
    resultado: list[dict] = []
    for lote, umbral_categoria, zona_horaria in sesion.execute(consulta).all():
        restante = saldo_por_lote.get(lote.id_lote, Decimal(0))
        if restante <= 0:
            continue

        hoy = hoy_por_zona.setdefault(
            zona_horaria, datetime.now(ZoneInfo(zona_horaria)).date()
        )
        referencia = ultima_salida.get(lote.id_lote) or lote.instante_entrada
        dias_sin_salida = (hoy - _dia_local(referencia, zona_horaria)).days

        umbral_heredado = umbral_categoria is None
        umbral = (
            UMBRAL_GLOBAL_DIAS_INMOVILIZADO if umbral_heredado else int(umbral_categoria)
        )
        if dias_sin_salida <= umbral:
            continue

        # research.md §11: `costo_unitario = 0.00` es el centinela de "sin costo registrado"
        # (el campo es NOT NULL). Esos lotes aparecen como no calculables, nunca con valor cero.
        calculable = Decimal(lote.costo_unitario) != 0
        valor = (
            (restante * Decimal(lote.costo_unitario)).quantize(Decimal("0.01"))
            if calculable
            else None
        )
        resultado.append(
            {
                "id_lote": lote.id_lote,
                "id_producto": lote.id_producto,
                "id_sucursal": lote.id_sucursal,
                "cantidad_restante": int(restante),
                "dias_sin_salida": dias_sin_salida,
                "dias_umbral_aplicado": umbral,
                "umbral_heredado_del_global": umbral_heredado,
                "valor_calculable": calculable,
                "valor_inmovilizado": (None if valor is None else f"{valor:.2f}"),
            }
        )

    resultado.sort(key=lambda f: (-f["dias_sin_salida"], f["id_lote"]))
    return resultado
