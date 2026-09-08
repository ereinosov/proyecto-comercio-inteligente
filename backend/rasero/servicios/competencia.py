"""Precios de competencia (001-core-ventas-inventario, US4 — T056, T057, T061).

- `crear_o_devolver_canal` — catálogo ABIERTO de canales (FR-025): el operador lo alimenta al
  capturar; un nombre con el mismo `nombre_normalizado` devuelve el canal existente, sin duplicar.
- `capturar_observacion` — registra una observación fechada (FR-022). `origen_captura` limitado a
  `manual` / `archivo`: la obtención automática desde sitios de terceros está PROHIBIDA (FR-026).
  La presentación observada se guarda tal cual; `comparable` se congela según si admite
  normalización.
- `comparar_precios` — precio propio (resuelto para la sucursal, FR-050) contra las observaciones,
  cada una normalizada a precio por unidad de medida y con su antigüedad calculada al leer
  (FR-023, FR-024, FR-027). El sistema NO ajusta ningún precio (FR-028).

El servicio comitea las escrituras; `comparar_precios` es solo lectura.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.dominio.comparacion_precios import (
    dias_de_antiguedad,
    indicador_forma,
    normalizar_nombre_canal,
    precio_por_unidad_de_medida,
    texto_antiguedad,
)
from rasero.dominio.resolucion_precio import resolver_precio_efectivo
from rasero.errores import RecursoNoEncontrado, ValorInvalido
from rasero.persistencia.modelos import (
    CanalCompetencia,
    ObservacionPrecio,
    Producto,
    ProductoPrecioSucursal,
    Sucursal,
)

_UNIDADES = {"unidad", "gramo", "mililitro"}
_ORIGENES = {"manual", "archivo"}


def crear_o_devolver_canal(sesion: Session, *, nombre: str) -> tuple[CanalCompetencia, bool]:
    limpio = nombre.strip()
    if not limpio:
        raise ValorInvalido("El nombre del canal de competencia no puede estar vacío.")
    normalizado = normalizar_nombre_canal(limpio)

    existente = sesion.execute(
        select(CanalCompetencia).where(CanalCompetencia.nombre_normalizado == normalizado)
    ).scalar_one_or_none()
    if existente is not None:
        return existente, False

    canal = CanalCompetencia(nombre=limpio, nombre_normalizado=normalizado)
    sesion.add(canal)
    sesion.commit()
    return canal, True


def capturar_observacion(
    sesion: Session,
    *,
    id_producto: int,
    id_canal_competencia: int,
    presentacion_cantidad: Decimal,
    presentacion_unidad: str,
    precio_observado: Decimal,
    fuente: str,
    origen_captura: str,
    moneda: str = "USD",
    id_turno: int | None = None,
) -> ObservacionPrecio:
    if origen_captura not in _ORIGENES:
        raise ValorInvalido(
            "El origen de la captura solo puede ser manual o por archivo; la obtención "
            "automática desde sitios de terceros está prohibida."
        )
    if presentacion_unidad not in _UNIDADES:
        raise ValorInvalido("La unidad de la presentación debe ser unidad, gramo o mililitro.")

    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")
    if sesion.get(CanalCompetencia, id_canal_competencia) is None:
        raise RecursoNoEncontrado(f"El canal de competencia {id_canal_competencia} no existe.")

    cantidad = Decimal(str(presentacion_cantidad))
    if cantidad <= 0:
        raise ValorInvalido("La cantidad de la presentación observada debe ser mayor que cero.")
    precio = Decimal(str(precio_observado))

    normalizado = precio_por_unidad_de_medida(
        precio_observado=precio,
        presentacion_cantidad=cantidad,
        presentacion_unidad=presentacion_unidad,
        producto_es_granel=producto.es_granel,
    )

    observacion = ObservacionPrecio(
        id_producto=id_producto,
        id_canal_competencia=id_canal_competencia,
        presentacion_cantidad=cantidad,
        presentacion_unidad=presentacion_unidad,
        precio_observado=precio,
        moneda=moneda,
        fuente=fuente,
        origen_captura=origen_captura,
        instante_captura=datetime.now(timezone.utc),
        id_turno=id_turno,
        comparable=normalizado is not None,
    )
    sesion.add(observacion)
    sesion.commit()
    return observacion


def listar_observaciones(sesion: Session, *, id_producto: int | None = None) -> list[dict]:
    """Observaciones de competencia capturadas, más recientes primero. Para el historial de la
    pantalla de captura (revisar y corregir lo que se registró mal).
    """
    ahora = datetime.now(timezone.utc)
    stmt = (
        select(ObservacionPrecio, CanalCompetencia.nombre)
        .join(
            CanalCompetencia,
            CanalCompetencia.id_canal_competencia == ObservacionPrecio.id_canal_competencia,
        )
        .order_by(ObservacionPrecio.instante_captura.desc())
    )
    if id_producto is not None:
        stmt = stmt.where(ObservacionPrecio.id_producto == id_producto)
    filas = sesion.execute(stmt).all()
    return [
        {
            "id_observacion_precio": obs.id_observacion_precio,
            "id_producto": obs.id_producto,
            "canal": canal,
            "presentacion": f"{Decimal(obs.presentacion_cantidad):g} {obs.presentacion_unidad}",
            "precio_observado": f"{Decimal(obs.precio_observado):.2f}",
            "fuente": obs.fuente,
            "origen_captura": obs.origen_captura,
            "comparable": obs.comparable,
            "instante_captura": obs.instante_captura.isoformat(),
            "dias_de_antiguedad": dias_de_antiguedad(obs.instante_captura, ahora),
        }
        for obs, canal in filas
    ]


def eliminar_observacion(sesion: Session, *, id_observacion_precio: int) -> None:
    """Borra una observación mal capturada. `observacion_precio` es un dato de APOYO a la
    decisión de precio (no un asiento contable ni una tabla de sólo-anexado como
    `bitacora_auditoria`): corregir "registré mal algo" es rehacerlo, así que se admite el
    borrado. El sistema NUNCA ajustó ningún precio a partir de ella (FR-028).
    """
    obs = sesion.get(ObservacionPrecio, id_observacion_precio)
    if obs is None:
        raise RecursoNoEncontrado(f"La observación {id_observacion_precio} no existe.")
    sesion.delete(obs)
    sesion.commit()


def _precio_propio(sesion: Session, *, id_producto: int, id_sucursal: int) -> Decimal:
    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")
    override = sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()
    return resolver_precio_efectivo(
        precio_base=Decimal(producto.precio_vigente), override_sucursal=override
    )


def comparar_precios(sesion: Session, *, id_producto: int, id_sucursal: int) -> dict:
    if sesion.get(Sucursal, id_sucursal) is None:
        raise RecursoNoEncontrado(f"La sucursal {id_sucursal} no existe.")
    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    precio_propio = _precio_propio(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    ahora = datetime.now(timezone.utc)

    filas = sesion.execute(
        select(ObservacionPrecio, CanalCompetencia.nombre)
        .join(
            CanalCompetencia,
            CanalCompetencia.id_canal_competencia == ObservacionPrecio.id_canal_competencia,
        )
        .where(ObservacionPrecio.id_producto == id_producto)
        .order_by(ObservacionPrecio.instante_captura.desc())
    ).all()

    observaciones: list[dict] = []
    for obs, canal in filas:
        normalizado = precio_por_unidad_de_medida(
            precio_observado=Decimal(obs.precio_observado),
            presentacion_cantidad=Decimal(obs.presentacion_cantidad),
            presentacion_unidad=obs.presentacion_unidad,
            producto_es_granel=producto.es_granel,
        )
        dias = dias_de_antiguedad(obs.instante_captura, ahora)
        observaciones.append(
            {
                "id_observacion_precio": obs.id_observacion_precio,
                "canal": canal,
                "presentacion": f"{Decimal(obs.presentacion_cantidad):g} {obs.presentacion_unidad}",
                "precio_observado": f"{Decimal(obs.precio_observado):.2f}",
                "precio_por_unidad_medida": (
                    None if normalizado is None else f"{normalizado:.4f}"
                ),
                "comparable": normalizado is not None,
                "dias_de_antiguedad": dias,
                "antiguedad_texto": texto_antiguedad(dias),
                "indicador_forma": indicador_forma(dias),
            }
        )

    return {
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "precio_propio_por_unidad_medida": f"{precio_propio:.4f}",
        "observaciones": observaciones,
    }
