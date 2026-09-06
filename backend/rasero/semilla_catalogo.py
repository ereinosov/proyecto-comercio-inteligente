"""Datos de demostración del catálogo (001-core-ventas-inventario).

    python -m rasero.semilla_catalogo

Sirve para que **Venta.tsx** y **Precios.tsx** no se vean vacíos al abrir el sistema en el
examen: crea ~30 productos variados (abarrotes y frescos/deli por peso) con costo y precio base
realistas, tres zonas de exhibición por sucursal, y existencia inicial amplia en **Quevedo
Centro** y **Buena Fe** — de modo que el margen real sea *calculable* en casi todo el catálogo
(no el estado dominante "Margen no calculable" de una demo sin lotes).

Frontera de propiedad de datos: este módulo pertenece a 001 y sólo escribe en tablas de 001
(`sucursal`, `categoria`, `producto`, `zona_exhibicion`, `lote`) y en `movimiento_inventario`
vía `registrar_movimiento` — nunca por asignación directa a `existencia` (mismo criterio que
`rasero/semilla.py`). `rasero/semilla_clientes.py` (002) y `rasero/semilla_movimientos.py`
(001) consumen este catálogo por los servicios/consultas públicos, sin recrearlo.

Idempotente: re-ejecutarlo no duplica sucursales, categorías, productos, zonas ni lotes, y no
vuelve a inyectar existencia sobre un lote que ya la recibió.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import (
    Base,
    Categoria,
    Lote,
    Producto,
    Sucursal,
    ZonaExhibicion,
)
from rasero.persistencia.movimientos import obtener_existencia, registrar_movimiento
from rasero.persistencia.sesion import SesionLocal, engine

# Las dos sucursales de "Despensa Los Ríos" (nombre de comercio ficticio: valor de fila, nunca
# identificador técnico — constitución, Identidad del Proyecto). Coinciden con `rasero/semilla.py`.
SUCURSALES_DEMO: tuple[str, ...] = ("Quevedo Centro", "Buena Fe")

# Categorías: se reutilizan las de `rasero/semilla.py` si ya existen, y se añaden dos más para
# dar variedad de umbral de inmovilizado.
_CATEGORIAS: dict[str, int | None] = {
    "Abarrotes": 60,
    "Frescos": 7,
    "Bebidas": 45,
    "Limpieza": 90,
}

# Producto que `rasero/semilla_movimientos.py` lleva a un quiebre de stock documentado en
# Quevedo Centro: entra con existencia deliberadamente ajustada para que un pico de demanda la
# agote y la serie de 004 tenga un intervalo de quiebre real que descensurar.
NOMBRE_PRODUCTO_QUIEBRE = "Aceite girasol 1 L"

# (nombre, categoría, es_granel, costo_unitario, precio_vigente). Para los productos a peso el
# costo y el precio son por kilogramo; la venta a granel se registra en gramos.
_PRODUCTOS: tuple[tuple[str, str, bool, str, str], ...] = (
    ("Arroz flor 1 kg", "Abarrotes", False, "0.9500", "1.2500"),
    ("Azúcar blanca 1 kg", "Abarrotes", False, "0.8200", "1.0500"),
    ("Fideo tallarín 400 g", "Abarrotes", False, "0.5200", "0.7500"),
    ("Lenteja 500 g", "Abarrotes", False, "0.7800", "1.1000"),
    ("Atún en aceite lata", "Abarrotes", False, "1.0500", "1.5000"),
    ("Sardina en tomate lata", "Abarrotes", False, "0.8800", "1.2000"),
    ("Sal yodada 1 kg", "Abarrotes", False, "0.3500", "0.5500"),
    ("Harina de trigo 1 kg", "Abarrotes", False, "0.7000", "0.9500"),
    ("Avena en hojuelas 400 g", "Abarrotes", False, "0.9000", "1.3500"),
    ("Café soluble 50 g", "Abarrotes", False, "1.8000", "2.6000"),
    ("Chocolate en polvo 400 g", "Abarrotes", False, "2.1000", "2.9500"),
    ("Mayonesa 400 g", "Abarrotes", False, "1.4000", "1.9500"),
    (NOMBRE_PRODUCTO_QUIEBRE, "Abarrotes", False, "1.9000", "2.7500"),
    ("Manteca vegetal 1 kg", "Abarrotes", False, "1.6000", "2.2000"),
    ("Leche entera 1 L", "Bebidas", False, "0.7500", "1.0000"),
    ("Yogur natural 1 L", "Bebidas", False, "1.3000", "1.8500"),
    ("Gaseosa cola 3 L", "Bebidas", False, "1.5500", "2.2500"),
    ("Agua sin gas 3 L", "Bebidas", False, "0.7000", "1.1000"),
    ("Jugo de naranja 1 L", "Bebidas", False, "0.9500", "1.4500"),
    ("Detergente en polvo 1 kg", "Limpieza", False, "1.7000", "2.4000"),
    ("Jabón de barra ropa", "Limpieza", False, "0.4500", "0.7000"),
    ("Papel higiénico 4 rollos", "Limpieza", False, "1.1000", "1.6500"),
    ("Cloro 1 L", "Limpieza", False, "0.6000", "0.9500"),
    ("Lavavajilla crema 250 g", "Limpieza", False, "0.8000", "1.2500"),
    ("Queso fresco tajado", "Frescos", True, "6.5000", "9.5000"),
    ("Jamón de pierna", "Frescos", True, "7.8000", "11.5000"),
    ("Mortadela especial", "Frescos", True, "3.9000", "6.2000"),
    ("Pollo entero fresco", "Frescos", True, "2.6000", "3.6000"),
    ("Carne molida de res", "Frescos", True, "4.8000", "6.9000"),
    ("Tomate riñón", "Frescos", True, "0.9000", "1.4000"),
    ("Cebolla paiteña", "Frescos", True, "0.8500", "1.3000"),
    ("Papa chola", "Frescos", True, "0.5500", "0.9000"),
    # Casos de margen fuera del rango saludable, para la demo de Precios.tsx:
    ("Aceite de oliva importado", "Abarrotes", False, "5.2000", "5.6500"),  # ~8% -> margen bajo
    ("Pan de molde (liquidación)", "Abarrotes", False, "1.3000", "1.2000"),  # negativo -> pérdida
)

# Zonas de exhibición por sucursal (grado_privilegio: mayor = mejor ubicación de góndola). Las
# sugerencias de colocación de 003 eligen entre estas; el esquema de `producto` no guarda una
# zona asignada (es tabla de 001, no ampliable desde 003), así que aquí sólo se catalogan.
_ZONAS: tuple[tuple[str, int], ...] = (
    ("Cabecera de góndola", 3),
    ("Góndola central", 2),
    ("Estante bajo / fondo", 1),
)

# Existencia inicial por producto (unidades para no-granel, gramos para granel). El producto de
# quiebre entra ajustado a propósito.
_STOCK_NO_GRANEL = 900
_STOCK_GRANEL_GRAMOS = 120_000
_STOCK_QUIEBRE = 70


def _asegurar_sucursales(sesion: Session) -> dict[str, Sucursal]:
    existentes = {
        s.nombre: s
        for s in sesion.execute(select(Sucursal)).scalars()
        if s.nombre in SUCURSALES_DEMO
    }
    for nombre in SUCURSALES_DEMO:
        if nombre not in existentes:
            s = Sucursal(nombre=nombre, zona_horaria="America/Guayaquil")
            sesion.add(s)
            sesion.flush()
            existentes[nombre] = s
    return existentes


def _asegurar_categorias(sesion: Session) -> dict[str, Categoria]:
    existentes = {c.nombre: c for c in sesion.execute(select(Categoria)).scalars()}
    for nombre, umbral in _CATEGORIAS.items():
        if nombre not in existentes:
            c = Categoria(nombre=nombre, dias_umbral_inmovilizado=umbral)
            sesion.add(c)
            sesion.flush()
            existentes[nombre] = c
    return existentes


def _asegurar_zonas(sesion: Session, sucursales: dict[str, Sucursal]) -> int:
    creadas = 0
    for suc in sucursales.values():
        ya = {
            z.nombre
            for z in sesion.execute(
                select(ZonaExhibicion).where(ZonaExhibicion.id_sucursal == suc.id_sucursal)
            ).scalars()
        }
        for nombre, grado in _ZONAS:
            if nombre not in ya:
                sesion.add(
                    ZonaExhibicion(
                        id_sucursal=suc.id_sucursal, nombre=nombre, grado_privilegio=grado
                    )
                )
                creadas += 1
    sesion.flush()
    return creadas


def _asegurar_productos(sesion: Session, categorias: dict[str, Categoria]) -> dict[str, Producto]:
    existentes = {p.nombre: p for p in sesion.execute(select(Producto)).scalars()}
    for nombre, cat, es_granel, costo, precio in _PRODUCTOS:
        if nombre in existentes:
            continue
        p = Producto(
            id_categoria=categorias[cat].id_categoria,
            nombre=nombre,
            es_granel=es_granel,
            precio_vigente=Decimal(precio),
            lleva_caducidad=(cat == "Frescos"),
        )
        sesion.add(p)
        sesion.flush()
        existentes[nombre] = p
    return existentes


def _asegurar_existencia(
    sesion: Session, productos: dict[str, Producto], sucursales: dict[str, Sucursal]
) -> tuple[int, int]:
    """Un lote por producto y sucursal, con su entrada de compra. Idempotente: si el lote ya
    existe con existencia positiva, no se vuelve a inyectar stock."""
    instante = datetime.now(timezone.utc) - timedelta(days=95)
    lotes_creados = 0
    entradas = 0
    for nombre, cat, es_granel, costo, _precio in _PRODUCTOS:
        producto = productos[nombre]
        for suc_nombre, suc in sucursales.items():
            lote = (
                sesion.execute(
                    select(Lote).where(
                        Lote.id_producto == producto.id_producto,
                        Lote.id_sucursal == suc.id_sucursal,
                    )
                )
                .scalars()
                .first()
            )
            if lote is not None:
                existencia = obtener_existencia(
                    sesion,
                    id_sucursal=suc.id_sucursal,
                    id_producto=producto.id_producto,
                    id_lote=lote.id_lote,
                )
                if existencia > 0:
                    continue  # ya sembrado
            else:
                lote = Lote(
                    id_producto=producto.id_producto,
                    id_sucursal=suc.id_sucursal,
                    costo_unitario=Decimal(costo),
                    fecha_caducidad=None,
                    instante_entrada=instante,
                )
                sesion.add(lote)
                sesion.flush()
                lotes_creados += 1

            if nombre == NOMBRE_PRODUCTO_QUIEBRE and suc_nombre == "Quevedo Centro":
                cantidad = _STOCK_QUIEBRE
            elif es_granel:
                cantidad = _STOCK_GRANEL_GRAMOS
            else:
                cantidad = _STOCK_NO_GRANEL

            registrar_movimiento(
                sesion,
                id_sucursal=suc.id_sucursal,
                id_producto=producto.id_producto,
                id_lote=lote.id_lote,
                tipo="entrada_compra",
                cantidad=Decimal(cantidad),
                instante=instante,
            )
            entradas += 1
    return lotes_creados, entradas


def sembrar() -> dict:
    Base.metadata.create_all(engine)  # no-op si Alembic ya aplicó el esquema
    sesion = SesionLocal()
    try:
        sucursales = _asegurar_sucursales(sesion)
        categorias = _asegurar_categorias(sesion)
        productos = _asegurar_productos(sesion, categorias)
        zonas_creadas = _asegurar_zonas(sesion, sucursales)
        lotes, entradas = _asegurar_existencia(sesion, productos, sucursales)
        sesion.commit()

        print(
            f"Catálogo sembrado: {len(_PRODUCTOS)} productos en {len(sucursales)} sucursales; "
            f"{zonas_creadas} zonas nuevas; {lotes} lotes nuevos; {entradas} entradas de compra."
        )
        for nombre, suc in sucursales.items():
            print(f"  Sucursal {nombre}: id={suc.id_sucursal}")
        print(f"  Producto de quiebre (para 004): «{NOMBRE_PRODUCTO_QUIEBRE}» en Quevedo Centro.")
        return {
            "sucursales": {n: s.id_sucursal for n, s in sucursales.items()},
            "productos": len(_PRODUCTOS),
        }
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
