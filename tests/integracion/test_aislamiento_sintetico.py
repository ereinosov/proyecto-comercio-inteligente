"""T022 — Prueba obligatoria (Principio III), FR-017: los datos sintéticos nunca se mezclan con
datos reales en una consulta de producción. `GET /demanda` se reconstruye desde
`movimiento_inventario` (que un producto sintético no tiene), así que ninguna cantidad sintética
aparece ahí; y `es_producto_solo_sintetico` distingue un producto sólo sintético de uno real.
Contra PostgreSQL real, puerto 5442.

Nota de alcance (misma decisión que el par T009/T014): el rechazo `409` de `generar_pronostico`
para un producto sólo sintético se verifica en User Story 3, donde se crea esa función (T036/T037).
Esta fase entrega el mecanismo de aislamiento (`es_producto_solo_sintetico` + guarda
`es_sintetico = FALSE` en el upsert de producción) y la parte medible ahora.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Producto, Sucursal
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.servicios.demanda import reconstruir_serie
from rasero.servicios.demanda_sintetica import cargar_serie, es_producto_solo_sintetico
from tests.apoyo import crear_escenario_basico, venta_de_prueba
from tests.utilidades.generador_sintetico import generar_serie

cliente = TestClient(app)


def _sucursal_y_producto(sesion) -> tuple[int, int]:
    sucursal = Sucursal(
        nombre=f"Aislamiento {datetime.now(timezone.utc).timestamp()}",
        zona_horaria="America/Guayaquil",
    )
    producto = Producto(
        nombre="Producto sólo sintético",
        es_granel=False,
        precio_vigente=Decimal("1.0000"),
        lleva_caducidad=False,
    )
    sesion.add_all([sucursal, producto])
    sesion.flush()
    return sucursal.id_sucursal, producto.id_producto


def test_get_demanda_de_un_producto_sintetico_no_expone_ninguna_cantidad_sintetica(sesion):
    id_sucursal, id_producto = _sucursal_y_producto(sesion)
    cargar_serie(sesion, generar_serie(id_producto, id_sucursal))
    sesion.commit()

    respuesta = cliente.get(
        "/demanda", params={"id_sucursal": id_sucursal, "id_producto": id_producto}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    # La serie sintética tiene días con demanda 10, 12, 15 y latente hasta 15. Nada de eso puede
    # aparecer: GET /demanda se reconstruye desde movimientos reales, que este producto no tiene.
    for fila in cuerpo:
        assert fila["demanda_observada"] == "0"
        assert fila["demanda_corregida"] is None or fila["demanda_corregida"] == "0.0000"


def test_es_producto_solo_sintetico_distingue_sintetico_de_real(sesion):
    id_sucursal, id_producto_sintetico = _sucursal_y_producto(sesion)
    cargar_serie(sesion, generar_serie(id_producto_sintetico, id_sucursal))
    sesion.commit()

    assert (
        es_producto_solo_sintetico(
            sesion, id_producto=id_producto_sintetico, id_sucursal=id_sucursal
        )
        is True
    )

    # Un producto real (con movimientos) en la misma sucursal no es "sólo sintético".
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_real = escenario["producto"].id_producto
    id_suc_real = escenario["sucursal"].id_sucursal
    ahora = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    registrar_movimiento(
        sesion,
        id_sucursal=id_suc_real,
        id_producto=id_real,
        id_lote=escenario["lote"].id_lote,
        tipo="salida_venta",
        cantidad=Decimal(-3),
        instante=ahora - timedelta(days=2),
        id_venta=venta_de_prueba(
            sesion, id_turno=escenario["turno"].id_turno, instante=ahora - timedelta(days=2)
        ),
    )
    sesion.commit()

    assert es_producto_solo_sintetico(sesion, id_producto=id_real, id_sucursal=id_suc_real) is False


def test_el_upsert_de_produccion_no_toca_las_filas_sinteticas(sesion):
    """Un producto REAL que además tiene serie sintética cargada (caso raro pero posible):
    reconstruir_serie de datos reales no debe sobrescribir las filas `es_sintetico = TRUE`.
    """
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    ahora = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=escenario["lote"].id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(20),
        instante=ahora - timedelta(days=5),
    )
    sesion.commit()

    cargar_serie(sesion, generar_serie(id_producto, id_sucursal))
    sesion.commit()

    # Reconstrucción de datos reales sobre la misma ventana.
    reconstruir_serie(sesion, id_sucursal=id_sucursal, id_producto=id_producto)
    sesion.commit()

    from rasero.persistencia.modelos import DemandaObservada

    sinteticas = (
        sesion.query(DemandaObservada)
        .filter(
            DemandaObservada.id_producto == id_producto,
            DemandaObservada.id_sucursal == id_sucursal,
            DemandaObservada.es_sintetico.is_(True),
        )
        .all()
    )
    assert len(sinteticas) == 56, "las filas sintéticas siguen intactas tras el upsert real"
    assert any(s.demanda_latente_verdadera is not None for s in sinteticas)
