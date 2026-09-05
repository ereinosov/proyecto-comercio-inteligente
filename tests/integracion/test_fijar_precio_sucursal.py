"""T001 de 003-precios-margenes (prerrequisito sobre 001): `fijar_precio_sucursal`
(`backend/rasero/servicios/catalogo.py`) crea o actualiza el override de precio por sucursal
(FR-050 de 001). Verifica el upsert en sí y que la lectura ya establecida (`listar_catalogo`,
T034 de 001, que usa `resolver_precio_efectivo`, T021/T022) refleje el cambio sin tocar ninguno
de esos dos archivos.
"""

from decimal import Decimal

from sqlalchemy import select

from rasero.persistencia.modelos import ProductoPrecioSucursal
from rasero.servicios.catalogo import fijar_precio_sucursal, listar_catalogo
from tests.apoyo import crear_escenario_basico


def _obtener_override(sesion, *, id_producto: int, id_sucursal: int) -> Decimal | None:
    return sesion.execute(
        select(ProductoPrecioSucursal.precio_vigente).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalar_one_or_none()


def test_crea_override_nuevo_cuando_no_existia(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    assert _obtener_override(sesion, id_producto=id_producto, id_sucursal=id_sucursal) is None

    fila = fijar_precio_sucursal(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("9.0000")
    )
    sesion.commit()

    assert fila.precio_vigente == Decimal("9.0000")
    assert _obtener_override(sesion, id_producto=id_producto, id_sucursal=id_sucursal) == Decimal(
        "9.0000"
    )


def test_actualiza_override_existente_en_vez_de_duplicar(sesion):
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal

    fijar_precio_sucursal(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("9.0000")
    )
    sesion.commit()

    fila_actualizada = fijar_precio_sucursal(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("7.5000")
    )
    sesion.commit()

    assert fila_actualizada.precio_vigente == Decimal("7.5000")

    filas = sesion.execute(
        select(ProductoPrecioSucursal).where(
            ProductoPrecioSucursal.id_producto == id_producto,
            ProductoPrecioSucursal.id_sucursal == id_sucursal,
        )
    ).scalars().all()
    assert len(filas) == 1, "El upsert actualiza la fila existente; no crea una segunda"
    assert filas[0].precio_vigente == Decimal("7.5000")


def test_listar_catalogo_refleja_el_precio_fijado(sesion):
    # Escenario 5 de User Story 4 de 001: mismo producto, precio distinto por sucursal, pero
    # aquí el override lo crea fijar_precio_sucursal en vez de venir precargado en el escenario.
    escenario = crear_escenario_basico(sesion, existencia_inicial=0)
    id_producto = escenario["producto"].id_producto
    id_sucursal = escenario["sucursal"].id_sucursal
    precio_base = escenario["producto"].precio_vigente

    antes = next(p for p in listar_catalogo(sesion, id_sucursal=id_sucursal) if p["id_producto"] == id_producto)
    assert antes["precio_efectivo"] == precio_base, "Sin override, listar_catalogo usa el precio base"

    fijar_precio_sucursal(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal, precio_vigente=Decimal("1.5000")
    )
    sesion.commit()

    despues = next(
        p for p in listar_catalogo(sesion, id_sucursal=id_sucursal) if p["id_producto"] == id_producto
    )
    assert despues["precio_efectivo"] == Decimal(
        "1.5000"
    ), "Tras el upsert, resolver_precio_efectivo (vía listar_catalogo) ya ve el override nuevo"
