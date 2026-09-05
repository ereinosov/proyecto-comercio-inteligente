"""Relaciones de sustitución entre productos (T061 de 004-pronostico-demanda, User Story 6).

Declaración MANUAL y dirigida (FR-032): `id_producto` es el que, al quedar en quiebre, puede
empujar demanda hacia `id_producto_sustituto`. No se infiere de correlación de ventas. Tabla
propia de 004 (`sustitucion_producto`), con FK hacia `producto` de 001 — mismo patrón que
`rol_producto` de 003; no altera el esquema de `producto`.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.errores import (
    RecursoNoEncontrado,
    RelacionSustitucionDuplicada,
    RelacionSustitucionInvalida,
)
from rasero.persistencia.modelos import Producto, SustitucionProducto


def declarar(
    sesion: Session, *, id_producto: int, id_producto_sustituto: int
) -> SustitucionProducto:
    if id_producto == id_producto_sustituto:
        raise RelacionSustitucionInvalida(
            "Un producto no puede declararse como sustituto de sí mismo."
        )
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")
    if sesion.get(Producto, id_producto_sustituto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto_sustituto} no existe.")

    ya_existe = sesion.execute(
        select(SustitucionProducto).where(
            SustitucionProducto.id_producto == id_producto,
            SustitucionProducto.id_producto_sustituto == id_producto_sustituto,
        )
    ).scalar_one_or_none()
    if ya_existe is not None:
        raise RelacionSustitucionDuplicada()

    fila = SustitucionProducto(
        id_producto=id_producto,
        id_producto_sustituto=id_producto_sustituto,
        instante_declaracion=datetime.now(timezone.utc),
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def listar(sesion: Session, *, id_producto: int | None = None) -> list[SustitucionProducto]:
    consulta = select(SustitucionProducto).order_by(SustitucionProducto.id_sustitucion_producto)
    if id_producto is not None:
        consulta = consulta.where(SustitucionProducto.id_producto == id_producto)
    return list(sesion.execute(consulta).scalars())


def retirar(sesion: Session, *, id_sustitucion_producto: int) -> None:
    fila = sesion.get(SustitucionProducto, id_sustitucion_producto)
    if fila is None:
        raise RecursoNoEncontrado(
            f"La relación de sustitución {id_sustitucion_producto} no existe."
        )
    sesion.delete(fila)
    sesion.flush()


def a_respuesta(fila: SustitucionProducto) -> dict:
    return {
        "id_sustitucion_producto": fila.id_sustitucion_producto,
        "id_producto": fila.id_producto,
        "id_producto_sustituto": fila.id_producto_sustituto,
        "instante_declaracion": fila.instante_declaracion,
    }
