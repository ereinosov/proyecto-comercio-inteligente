"""Helpers de datos para pruebas de integración y contrato. No es un archivo de pruebas."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import Lote, Operador, Producto, Sucursal, Turno
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.seguridad import hashear_pin


def crear_escenario_basico(sesion, *, existencia_inicial: int = 10, es_granel: bool = False):
    sucursal = Sucursal(nombre=f"Sucursal de prueba {datetime.now().timestamp()}", zona_horaria="America/Guayaquil")
    sesion.add(sucursal)
    sesion.flush()

    producto = Producto(
        nombre="Producto de prueba",
        es_granel=es_granel,
        precio_vigente=Decimal("2.5000"),
        lleva_caducidad=False,
    )
    sesion.add(producto)
    sesion.flush()

    operador = Operador(nombre="Operador de prueba", pin_hash="", es_encargado=False, activo=True)
    sesion.add(operador)
    sesion.flush()
    operador.pin_hash = hashear_pin("1234", str(operador.id_operador))
    sesion.flush()

    turno = Turno(
        id_operador=operador.id_operador,
        id_sucursal=sucursal.id_sucursal,
        caja="caja-1",
        instante_apertura=datetime.now(timezone.utc),
    )
    sesion.add(turno)
    sesion.flush()

    lote = Lote(
        id_producto=producto.id_producto,
        id_sucursal=sucursal.id_sucursal,
        costo_unitario=Decimal("1.0000"),
        fecha_caducidad=None,
        instante_entrada=datetime.now(timezone.utc) - timedelta(days=1),
    )
    sesion.add(lote)
    sesion.flush()

    if existencia_inicial:
        registrar_movimiento(
            sesion,
            id_sucursal=sucursal.id_sucursal,
            id_producto=producto.id_producto,
            id_lote=lote.id_lote,
            tipo="entrada_compra",
            cantidad=Decimal(existencia_inicial),
            instante=datetime.now(timezone.utc) - timedelta(days=1),
        )

    sesion.commit()

    return {
        "sucursal": sucursal,
        "producto": producto,
        "operador": operador,
        "turno": turno,
        "lote": lote,
        "pin": "1234",
    }
