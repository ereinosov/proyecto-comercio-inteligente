"""Suite obligatoria 5 (US2) — empuje por recompra con RESERVA DE PRECIO. Contra PostgreSQL real.

- T021: `detectar_ofertas_recompra` no crea `movimiento_inventario` ni cambia `existencia`;
  `precio_garantizado` = precio resuelto - DESCUENTO_RECOMPRA_PCT (FR-010, FR-011).
- T022: a lo sumo una oferta `pendiente` por (cliente, producto) (FR-014); una reserva vencida
  pasa a `reserva_vencida` sin liberar stock.
- T023: redimir una oferta `pendiente` la deja `comprado` (mismo `POST /promociones/redenciones`
  de US1, no una tabla ni una ruta nueva).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from rasero.config import promociones as cfg
from rasero.persistencia.modelos import Existencia, MovimientoInventario, OfertaRecompra
from rasero.servicios.promociones import (
    detectar_ofertas_recompra,
    listar_ofertas_recompra,
    registrar_redencion,
)
from tests.apoyo_promociones import (
    _venta,
    crear_cliente_en_ventana_recompra,
    escenario_dos_productos,
)

# --- T021 --------------------------------------------------------------------------


def test_deteccion_no_toca_inventario_y_calcula_el_precio_garantizado(sesion):
    escenario = escenario_dos_productos(sesion)
    id_producto = escenario["producto_2"].id_producto  # precio_vigente 4.0000
    crear_cliente_en_ventana_recompra(
        sesion, escenario, nombre="Recompra T021", id_producto=id_producto
    )

    mov_antes = sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
    exist_antes = sesion.execute(select(func.sum(Existencia.cantidad))).scalar_one()

    resultado = detectar_ofertas_recompra(sesion, id_sucursal=escenario["sucursal"].id_sucursal)
    sesion.commit()

    assert resultado["ofertas_propuestas"] == 1
    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto)
    ).scalar_one()
    # 4.0000 * (100 - 8) / 100 = 3.6800
    assert oferta.precio_garantizado == Decimal("3.6800")
    assert oferta.desenlace == "pendiente"
    assert oferta.estado_reserva == "vigente"
    assert oferta.justificacion["compras_del_producto"] == 4

    # Frontera con el inventario de 001: cero escrituras.
    assert (
        sesion.execute(select(func.count()).select_from(MovimientoInventario)).scalar_one()
        == mov_antes
    )
    assert sesion.execute(select(func.sum(Existencia.cantidad))).scalar_one() == exist_antes


# --- T022 -----------------------------------------------------------------------------


def test_una_oferta_activa_por_par_y_vencimiento_de_reserva(sesion):
    escenario = escenario_dos_productos(sesion)
    id_producto = escenario["producto_2"].id_producto
    crear_cliente_en_ventana_recompra(
        sesion, escenario, nombre="Recompra T022", id_producto=id_producto
    )
    id_sucursal = escenario["sucursal"].id_sucursal

    primera = detectar_ofertas_recompra(sesion, id_sucursal=id_sucursal)
    sesion.commit()
    segunda = detectar_ofertas_recompra(sesion, id_sucursal=id_sucursal)
    sesion.commit()

    assert primera["ofertas_propuestas"] == 1
    assert segunda["ofertas_propuestas"] == 0
    assert segunda["ofertas_ya_activas"] == 1

    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto)
    ).scalar_one()

    # Adelantar la fecha de vencimiento de la reserva y volver a barrer.
    oferta.reserva_hasta = date.today() - timedelta(days=1)
    sesion.commit()
    listar_ofertas_recompra(sesion)
    sesion.commit()
    sesion.refresh(oferta)
    assert oferta.estado_reserva == "vencida"
    assert oferta.desenlace == "reserva_vencida"


# --- T023 -------------------------------------------------------------------------------


def test_redencion_de_oferta_pendiente_la_deja_comprado(sesion):
    escenario = escenario_dos_productos(sesion)
    id_producto = escenario["producto_2"].id_producto
    crear_cliente_en_ventana_recompra(
        sesion, escenario, nombre="Recompra T023", id_producto=id_producto
    )
    detectar_ofertas_recompra(sesion, id_sucursal=escenario["sucursal"].id_sucursal)
    sesion.commit()
    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto)
    ).scalar_one()

    venta = _venta(
        sesion,
        escenario,
        instante=datetime.now(timezone.utc),
        id_producto=id_producto,
    )
    redencion, creada = registrar_redencion(
        sesion,
        id_venta=venta.id_venta,
        tipo_origen="oferta_recompra",
        id_oferta_recompra=oferta.id_oferta_recompra,
    )
    sesion.commit()

    assert creada is True
    sesion.refresh(oferta)
    assert oferta.desenlace == "comprado"
    assert redencion.id_producto == id_producto


def test_reserva_vencida_no_puede_quedar_comprado(sesion):
    escenario = escenario_dos_productos(sesion)
    id_producto = escenario["producto_2"].id_producto
    crear_cliente_en_ventana_recompra(
        sesion, escenario, nombre="Recompra T023b", id_producto=id_producto
    )
    detectar_ofertas_recompra(sesion, id_sucursal=escenario["sucursal"].id_sucursal)
    sesion.commit()
    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto)
    ).scalar_one()
    oferta.reserva_hasta = date.today() - timedelta(days=1)
    sesion.commit()
    listar_ofertas_recompra(sesion)  # dispara el barrido de vencimiento
    sesion.commit()
    sesion.refresh(oferta)
    assert oferta.desenlace == "reserva_vencida"

    venta = _venta(sesion, escenario, instante=datetime.now(timezone.utc), id_producto=id_producto)
    registrar_redencion(
        sesion,
        id_venta=venta.id_venta,
        tipo_origen="oferta_recompra",
        id_oferta_recompra=oferta.id_oferta_recompra,
    )
    sesion.commit()
    sesion.refresh(oferta)
    assert oferta.desenlace == "reserva_vencida"  # no cambió a 'comprado'
    _ = cfg
