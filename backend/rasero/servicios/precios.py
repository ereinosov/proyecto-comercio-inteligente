"""Rol de producto y sugerencias de precio/colocación (T020, T029, T030, T040, T041 de
003-precios-margenes).

Frontera de propiedad de datos: `producto`, `observacion_precio`, `canal_competencia` y
`zona_exhibicion` son de `001` — se consultan, nunca se poseen. `fijar_precio_sucursal` (T002,
también de `001`) es la única vía de escritura sobre `producto_precio_sucursal` (research.md #7).
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.dominio.sugerencias import normalizar_precio_observado, sugerir_colocacion, sugerir_precio
from rasero.errores import RecursoNoEncontrado, SugerenciaYaAplicada
from rasero.persistencia.modelos import (
    MargenCalculado,
    ObservacionPrecio,
    Producto,
    RolProducto,
    SugerenciaColocacion,
    SugerenciaPrecio,
    ZonaExhibicion,
)
from rasero.servicios.catalogo import fijar_precio_sucursal
from rasero.servicios.margenes import listar_margenes_sucursal, resolver_margen_producto

ROLES_VALIDOS = ("gancho_trafico", "generador_margen")


def asignar_rol_producto(sesion: Session, *, id_producto: int, rol: str) -> RolProducto:
    """Crea o sobrescribe la clasificación de un producto (FR-005, FR-006). No lleva historial
    de asignaciones previas — research.md #3, decisión deliberada por falta de necesidad
    demostrada de ese historial.
    """
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    fila = sesion.get(RolProducto, id_producto)
    ahora = datetime.now(timezone.utc)
    if fila is None:
        fila = RolProducto(id_producto=id_producto, rol=rol, instante_asignacion=ahora)
        sesion.add(fila)
    else:
        fila.rol = rol
        fila.instante_asignacion = ahora
    sesion.flush()
    return fila


def _rol_de(sesion: Session, *, id_producto: int) -> str | None:
    fila = sesion.get(RolProducto, id_producto)
    return fila.rol if fila is not None else None


def _observacion_vigente_comparable(sesion: Session, *, id_producto: int) -> ObservacionPrecio | None:
    """La observación de competencia comparable más reciente de este producto (FR-009, FR-011).
    "Vigente" es la más reciente disponible — el spec no define una ventana de frescura que la
    excluya por antigüedad; la antigüedad se muestra, nunca se usa para descartar la observación.
    """
    return sesion.execute(
        select(ObservacionPrecio)
        .where(ObservacionPrecio.id_producto == id_producto, ObservacionPrecio.comparable.is_(True))
        .order_by(ObservacionPrecio.instante_captura.desc())
        .limit(1)
    ).scalar_one_or_none()


def generar_sugerencia_precio(sesion: Session, *, id_producto: int, id_sucursal: int) -> SugerenciaPrecio:
    """FR-008 a FR-011, FR-014: genera y persiste (append-only) una sugerencia de precio, con
    los insumos que la originaron congelados como snapshot.
    """
    margen = resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    fila_margen = sesion.get(MargenCalculado, (id_producto, id_sucursal))

    rol = _rol_de(sesion, id_producto=id_producto)

    observacion = _observacion_vigente_comparable(sesion, id_producto=id_producto)
    observacion_normalizada = (
        normalizar_precio_observado(
            precio_observado=observacion.precio_observado,
            presentacion_cantidad=observacion.presentacion_cantidad,
            presentacion_unidad=observacion.presentacion_unidad,
            comparable=observacion.comparable,
        )
        if observacion is not None
        else None
    )

    precio_sugerido = sugerir_precio(
        precio_vigente=fila_margen.precio_vigente,
        costo_vigente=fila_margen.costo_vigente,
        rol=rol,
        observacion_normalizada=observacion_normalizada,
    )

    sugerencia = SugerenciaPrecio(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        precio_sugerido=precio_sugerido,
        margen_usado=margen,
        rol_usado=rol,
        id_observacion_precio_usada=observacion.id_observacion_precio if observacion is not None else None,
        instante_generacion=datetime.now(timezone.utc),
    )
    sesion.add(sugerencia)
    sesion.flush()
    return sugerencia


def aplicar_sugerencia_precio(sesion: Session, *, id_sugerencia_precio: int) -> SugerenciaPrecio:
    """FR-012, FR-013: crea o actualiza el override de `001` vía `fijar_precio_sucursal` en la
    misma transacción en que se marca la sugerencia como aplicada.
    """
    sugerencia = sesion.get(SugerenciaPrecio, id_sugerencia_precio)
    if sugerencia is None:
        raise RecursoNoEncontrado(f"La sugerencia de precio {id_sugerencia_precio} no existe.")
    if sugerencia.aplicada:
        raise SugerenciaYaAplicada()

    fijar_precio_sucursal(
        sesion,
        id_producto=sugerencia.id_producto,
        id_sucursal=sugerencia.id_sucursal,
        precio_vigente=sugerencia.precio_sugerido,
    )
    sugerencia.aplicada = True
    sugerencia.instante_aplicacion = datetime.now(timezone.utc)
    sesion.flush()
    return sugerencia


def _zonas_por_privilegio(sesion: Session, *, id_sucursal: int) -> list[int]:
    return list(
        sesion.execute(
            select(ZonaExhibicion.id_zona_exhibicion)
            .where(ZonaExhibicion.id_sucursal == id_sucursal)
            .order_by(ZonaExhibicion.grado_privilegio.desc(), ZonaExhibicion.id_zona_exhibicion.asc())
        ).scalars()
    )


def generar_sugerencia_colocacion(
    sesion: Session, *, id_producto: int, id_sucursal: int
) -> SugerenciaColocacion:
    """FR-015 a FR-019: ranking por margen real contra `grado_privilegio` (Lectura Crítica n.º 3,
    research.md #6) — nunca por `rol_producto`, que solo se snapshot-ea como explicación.

    Reutiliza `listar_margenes_sucursal` (el resolver de lote, ya libre de N+1) para conocer el
    margen de **todos** los productos de la sucursal: el ranking es intrínsecamente relativo, así
    que no hay forma de responder "¿qué zona le toca a este producto?" sin conocer dónde queda
    frente a los demás — decisión explícita, no un descuido de rendimiento (research.md #4 ya
    demostró que esa consulta de conjunto es barata a esta escala).
    """
    if sesion.get(Producto, id_producto) is None:
        raise RecursoNoEncontrado(f"El producto {id_producto} no existe.")

    zonas = _zonas_por_privilegio(sesion, id_sucursal=id_sucursal)
    if not zonas:
        raise RecursoNoEncontrado(
            f"La sucursal {id_sucursal} no tiene ninguna zona de exhibición catalogada."
        )

    margenes = listar_margenes_sucursal(sesion, id_sucursal=id_sucursal)
    con_margen = sorted(
        (fila for fila in margenes if fila["margen"] is not None),
        key=lambda fila: fila["margen"],
        reverse=True,
    )
    rango_por_producto = {fila["id_producto"]: i + 1 for i, fila in enumerate(con_margen)}
    rango = rango_por_producto.get(id_producto)
    if rango is None:
        # Edge case sin cubrir explícitamente por el spec: un producto sin margen calculable no
        # tiene con qué rankear. Se decide aquí, no implícito: sin base para el ranking, no se
        # genera sugerencia — el mismo criterio que FR-018 ya aplica a la ausencia de zonas.
        raise RecursoNoEncontrado(
            f"El producto {id_producto} no tiene margen calculable; no hay base para sugerir colocación."
        )

    id_zona = sugerir_colocacion(rango=rango, total_con_margen=len(con_margen), zonas_ordenadas=zonas)

    margen_usado = next(fila["margen"] for fila in margenes if fila["id_producto"] == id_producto)
    rol = _rol_de(sesion, id_producto=id_producto)

    sugerencia = SugerenciaColocacion(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        id_zona_exhibicion=id_zona,
        margen_usado=margen_usado,
        rol_usado=rol,
        instante_generacion=datetime.now(timezone.utc),
    )
    sesion.add(sugerencia)
    sesion.flush()
    return sugerencia


def aplicar_sugerencia_colocacion(
    sesion: Session, *, id_sugerencia_colocacion: int
) -> SugerenciaColocacion:
    """FR-017: solo confirma que el encargado ya ejecutó la reubicación física — nunca escribe
    en `zona_exhibicion` ni en ninguna otra tabla de `001`.
    """
    sugerencia = sesion.get(SugerenciaColocacion, id_sugerencia_colocacion)
    if sugerencia is None:
        raise RecursoNoEncontrado(f"La sugerencia de colocación {id_sugerencia_colocacion} no existe.")
    if sugerencia.aplicada:
        raise SugerenciaYaAplicada()

    sugerencia.aplicada = True
    sugerencia.instante_aplicacion = datetime.now(timezone.utc)
    sesion.flush()
    return sugerencia
