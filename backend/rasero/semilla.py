"""Datos de demostración de "Despensa Los Ríos" (T012). El nombre del comercio ficticio y
sus sucursales viven solo como valor de fila — nunca como identificador técnico (constitución,
Identidad del Proyecto).

Las existencias iniciales se crean vía `registrar_movimiento` (entrada_compra), nunca por
asignación directa a `existencia`, para que el invariante de agregación derivada se cumpla
desde el primer dato.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from rasero.persistencia.modelos import Base, Categoria, Lote, Operador, Producto, Sucursal, Turno
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import SesionLocal, engine
from rasero.seguridad import hashear_pin


def sembrar() -> None:
    Base.metadata.create_all(engine)  # no-op si Alembic ya aplicó el esquema
    sesion = SesionLocal()
    try:
        if sesion.query(Sucursal).count() > 0:
            print("La base ya tiene datos; nada que sembrar.")
            return

        quevedo = Sucursal(nombre="Quevedo Centro", zona_horaria="America/Guayaquil")
        buena_fe = Sucursal(nombre="Buena Fe", zona_horaria="America/Guayaquil")
        sesion.add_all([quevedo, buena_fe])
        sesion.flush()

        abarrotes = Categoria(nombre="Abarrotes", dias_umbral_inmovilizado=60)
        frescos = Categoria(nombre="Frescos", dias_umbral_inmovilizado=7)
        sesion.add_all([abarrotes, frescos])
        sesion.flush()

        atun = Producto(
            id_categoria=abarrotes.id_categoria,
            nombre="Atún en lata",
            es_granel=False,
            precio_vigente=Decimal("1.5000"),
            lleva_caducidad=False,
        )
        queso = Producto(
            id_categoria=frescos.id_categoria,
            nombre="Queso fresco",
            es_granel=True,
            precio_vigente=Decimal("4.7500"),
            lleva_caducidad=True,
        )
        sesion.add_all([atun, queso])
        sesion.flush()

        cajera = Operador(
            nombre="Ana Cajera", pin_hash="", rol="cajero",
            id_sucursal=quevedo.id_sucursal, activo=True,
        )
        encargado = Operador(
            nombre="Luis Encargado", pin_hash="", rol="encargado",
            id_sucursal=quevedo.id_sucursal, activo=True,
        )
        # Enmienda v2.3.0 (Principio VI): el rol `admin` se crea SIEMPRE de forma explícita,
        # nunca por migración. "Marta Administradora" sigue el estilo de nombres de la semilla.
        admin = Operador(
            nombre="Marta Administradora", pin_hash="", rol="admin",
            id_sucursal=quevedo.id_sucursal, activo=True,
        )
        sesion.add_all([cajera, encargado, admin])
        sesion.flush()
        cajera.pin_hash = hashear_pin("1234", str(cajera.id_operador))
        encargado.pin_hash = hashear_pin("9999", str(encargado.id_operador))
        admin.pin_hash = hashear_pin("0000", str(admin.id_operador))
        sesion.flush()

        ahora = datetime.now(timezone.utc)

        lote_atun = Lote(
            id_producto=atun.id_producto,
            id_sucursal=quevedo.id_sucursal,
            costo_unitario=Decimal("1.0000"),
            fecha_caducidad=None,
            instante_entrada=ahora - timedelta(days=10),
        )
        lote_queso = Lote(
            id_producto=queso.id_producto,
            id_sucursal=quevedo.id_sucursal,
            costo_unitario=Decimal("3.0000"),
            fecha_caducidad=date.today() + timedelta(days=5),
            instante_entrada=ahora - timedelta(days=1),
        )
        sesion.add_all([lote_atun, lote_queso])
        sesion.flush()

        registrar_movimiento(
            sesion,
            id_sucursal=quevedo.id_sucursal,
            id_producto=atun.id_producto,
            id_lote=lote_atun.id_lote,
            tipo="entrada_compra",
            cantidad=Decimal(50),
            instante=lote_atun.instante_entrada,
        )
        registrar_movimiento(
            sesion,
            id_sucursal=quevedo.id_sucursal,
            id_producto=queso.id_producto,
            id_lote=lote_queso.id_lote,
            tipo="entrada_compra",
            cantidad=Decimal(5000),  # 5 kg en gramos
            instante=lote_queso.instante_entrada,
        )

        sesion.commit()
        print("Semilla cargada: Despensa Los Ríos (Quevedo Centro, Buena Fe).")
        print(f"  Operador cajera (rol cajero): id={cajera.id_operador} PIN=1234")
        print(f"  Operador encargado (rol encargado): id={encargado.id_operador} PIN=9999")
        print(f"  Operador admin (rol admin): id={admin.id_operador} PIN=0000")
        print(f"  Sucursal Quevedo Centro: id={quevedo.id_sucursal}")
        print(f"  Sucursal Buena Fe: id={buena_fe.id_sucursal}")
        print(f"  Producto Atún en lata: id={atun.id_producto} (50 u en Quevedo Centro)")
        print(f"  Producto Queso fresco: id={queso.id_producto} (5000 g en Quevedo Centro)")
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
