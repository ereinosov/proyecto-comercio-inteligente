"""Administración de datos maestros: alta, edición y desactivación de `sucursal`, `producto`,
`categoria`, `zona_exhibicion` y `medio_pago` desde la interfaz (Parte 3 de la enmienda de
administración). Cierra la brecha entre lo que el modelo promete —N sucursales sin cambios
estructurales (constitución, "Modelo multi-sucursal")— y lo que la interfaz permitía: hasta
ahora estos maestros sólo se creaban editando un script de semilla de Python.

Autorización: crear / editar / desactivar cualquiera de estas cinco entidades requiere
`operador.es_encargado`. Se replica EXACTAMENTE el mecanismo de
`servicios/terminales_pago.py` y `servicios/cobertura_pago.py` (`if not operador.es_encargado:`
-> error 400 con mensaje "Sólo un encargado puede ..."). La edición de `cliente` NO pasa por
aquí: cualquier cajero puede editarlo (ver `servicios/clientes.actualizar_cliente`).

Borrado: nunca físico (Principio IV). "Desactivar" pone `activo = false`. Antes de desactivar,
`contar_dependencias` devuelve el conteo real de lo que quedará colgando (ventas de un producto,
productos de una categoría, …) para que la UI lo muestre y deje continuar de todas formas —
nunca bloquear, sólo informar con datos reales.

Los servicios no comitean: la transacción queda a cargo del endpoint (mismo patrón que
`servicios/terminales_pago.py`).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.errores import ErrorAdministracion
from rasero.persistencia.modelos import (
    BitacoraAuditoria,
    Categoria,
    CoberturaPago,
    Lote,
    MedioPago,
    Operador,
    Producto,
    RenglonVenta,
    RolProducto,
    Sucursal,
    SugerenciaColocacion,
    SustitucionProducto,
    Turno,
    ZonaExhibicion,
)

# --------------------------------------------------------------------------
# Autorización — mismo mecanismo que terminales_pago.py / cobertura_pago.py
# --------------------------------------------------------------------------


def _encargado_o_error(sesion: Session, id_operador: int, entidad: str) -> Operador:
    operador = sesion.get(Operador, id_operador)
    if operador is None:
        raise ErrorAdministracion(
            "admin_operador_no_existe", "Ese operador no existe.", status_code=404
        )
    if not operador.es_encargado:
        raise ErrorAdministracion(
            "admin_operador_no_encargado",
            f"Sólo un encargado puede administrar {entidad}.",
        )
    return operador


def _texto(valor: str, campo: str) -> str:
    limpio = (valor or "").strip()
    if not limpio:
        raise ErrorAdministracion(
            "admin_campo_requerido", f"El campo «{campo}» es obligatorio."
        )
    return limpio


# --------------------------------------------------------------------------
# Sucursal
# --------------------------------------------------------------------------


def crear_sucursal(
    sesion: Session, *, nombre: str, zona_horaria: str, id_operador: int
) -> Sucursal:
    _encargado_o_error(sesion, id_operador, "sucursales")
    nombre = _texto(nombre, "nombre")
    if (
        sesion.execute(
            select(Sucursal).where(func.lower(Sucursal.nombre) == nombre.lower())
        ).scalar_one_or_none()
        is not None
    ):
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay una sucursal con ese nombre."
        )
    sucursal = Sucursal(
        nombre=nombre, zona_horaria=_texto(zona_horaria, "zona horaria")
    )
    sesion.add(sucursal)
    sesion.flush()
    return sucursal


def actualizar_sucursal(
    sesion: Session,
    *,
    id_sucursal: int,
    nombre: str,
    zona_horaria: str,
    id_operador: int,
) -> Sucursal:
    _encargado_o_error(sesion, id_operador, "sucursales")
    sucursal = _o_404(sesion, Sucursal, id_sucursal, "La sucursal")
    nombre = _texto(nombre, "nombre")
    choca = sesion.execute(
        select(Sucursal).where(
            func.lower(Sucursal.nombre) == nombre.lower(),
            Sucursal.id_sucursal != id_sucursal,
        )
    ).scalar_one_or_none()
    if choca is not None:
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay otra sucursal con ese nombre."
        )
    sucursal.nombre = nombre
    sucursal.zona_horaria = _texto(zona_horaria, "zona horaria")
    sesion.flush()
    return sucursal


# --------------------------------------------------------------------------
# Categoria
# --------------------------------------------------------------------------


def crear_categoria(
    sesion: Session,
    *,
    nombre: str,
    dias_umbral_inmovilizado: int | None,
    id_operador: int,
) -> Categoria:
    _encargado_o_error(sesion, id_operador, "categorías")
    nombre = _texto(nombre, "nombre")
    if (
        sesion.execute(
            select(Categoria).where(func.lower(Categoria.nombre) == nombre.lower())
        ).scalar_one_or_none()
        is not None
    ):
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay una categoría con ese nombre."
        )
    categoria = Categoria(
        nombre=nombre, dias_umbral_inmovilizado=_umbral(dias_umbral_inmovilizado)
    )
    sesion.add(categoria)
    sesion.flush()
    return categoria


def actualizar_categoria(
    sesion: Session,
    *,
    id_categoria: int,
    nombre: str,
    dias_umbral_inmovilizado: int | None,
    id_operador: int,
) -> Categoria:
    _encargado_o_error(sesion, id_operador, "categorías")
    categoria = _o_404(sesion, Categoria, id_categoria, "La categoría")
    nombre = _texto(nombre, "nombre")
    choca = sesion.execute(
        select(Categoria).where(
            func.lower(Categoria.nombre) == nombre.lower(),
            Categoria.id_categoria != id_categoria,
        )
    ).scalar_one_or_none()
    if choca is not None:
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay otra categoría con ese nombre."
        )
    categoria.nombre = nombre
    categoria.dias_umbral_inmovilizado = _umbral(dias_umbral_inmovilizado)
    sesion.flush()
    return categoria


def _umbral(valor: int | None) -> int | None:
    if valor is None:
        return None
    if valor <= 0:
        raise ErrorAdministracion(
            "admin_umbral_invalido",
            "El umbral de días de capital inmovilizado debe ser un número positivo, o vacío "
            "para heredar el umbral global.",
        )
    return int(valor)


# --------------------------------------------------------------------------
# Producto
# --------------------------------------------------------------------------


def crear_producto(
    sesion: Session,
    *,
    nombre: str,
    id_categoria: int | None,
    es_granel: bool,
    precio_vigente: Decimal,
    lleva_caducidad: bool,
    id_operador: int,
) -> Producto:
    _encargado_o_error(sesion, id_operador, "productos")
    nombre = _texto(nombre, "nombre")
    _valida_categoria(sesion, id_categoria)
    _valida_precio(precio_vigente)
    producto = Producto(
        nombre=nombre,
        id_categoria=id_categoria,
        es_granel=bool(es_granel),
        precio_vigente=Decimal(precio_vigente),
        lleva_caducidad=bool(lleva_caducidad),
    )
    sesion.add(producto)
    sesion.flush()
    return producto


def actualizar_producto(
    sesion: Session,
    *,
    id_producto: int,
    nombre: str,
    id_categoria: int | None,
    es_granel: bool,
    precio_vigente: Decimal,
    lleva_caducidad: bool,
    id_operador: int,
) -> Producto:
    _encargado_o_error(sesion, id_operador, "productos")
    producto = _o_404(sesion, Producto, id_producto, "El producto")
    _valida_categoria(sesion, id_categoria)
    _valida_precio(precio_vigente)
    producto.nombre = _texto(nombre, "nombre")
    producto.id_categoria = id_categoria
    producto.es_granel = bool(es_granel)
    producto.precio_vigente = Decimal(precio_vigente)
    producto.lleva_caducidad = bool(lleva_caducidad)
    sesion.flush()
    return producto


def _valida_categoria(sesion: Session, id_categoria: int | None) -> None:
    if id_categoria is None:
        return
    if sesion.get(Categoria, id_categoria) is None:
        raise ErrorAdministracion(
            "admin_categoria_no_existe", "Esa categoría no existe."
        )


def _valida_precio(precio: Decimal) -> None:
    if precio is None or Decimal(precio) < 0:
        raise ErrorAdministracion(
            "admin_precio_invalido", "El precio de venta no puede ser negativo."
        )


# --------------------------------------------------------------------------
# ZonaExhibicion
# --------------------------------------------------------------------------


def crear_zona_exhibicion(
    sesion: Session,
    *,
    id_sucursal: int,
    nombre: str,
    grado_privilegio: int,
    id_operador: int,
) -> ZonaExhibicion:
    _encargado_o_error(sesion, id_operador, "zonas de exhibición")
    if sesion.get(Sucursal, id_sucursal) is None:
        raise ErrorAdministracion("admin_sucursal_no_existe", "Esa sucursal no existe.")
    zona = ZonaExhibicion(
        id_sucursal=id_sucursal,
        nombre=_texto(nombre, "nombre"),
        grado_privilegio=_grado(grado_privilegio),
    )
    sesion.add(zona)
    sesion.flush()
    return zona


def actualizar_zona_exhibicion(
    sesion: Session,
    *,
    id_zona_exhibicion: int,
    id_sucursal: int,
    nombre: str,
    grado_privilegio: int,
    id_operador: int,
) -> ZonaExhibicion:
    _encargado_o_error(sesion, id_operador, "zonas de exhibición")
    zona = _o_404(sesion, ZonaExhibicion, id_zona_exhibicion, "La zona de exhibición")
    if sesion.get(Sucursal, id_sucursal) is None:
        raise ErrorAdministracion("admin_sucursal_no_existe", "Esa sucursal no existe.")
    zona.id_sucursal = id_sucursal
    zona.nombre = _texto(nombre, "nombre")
    zona.grado_privilegio = _grado(grado_privilegio)
    sesion.flush()
    return zona


def _grado(valor: int) -> int:
    if valor is None or int(valor) < 1:
        raise ErrorAdministracion(
            "admin_grado_invalido",
            "El grado de privilegio debe ser un entero de 1 en adelante (mayor = mejor ubicación).",
        )
    return int(valor)


# --------------------------------------------------------------------------
# MedioPago
# --------------------------------------------------------------------------


def crear_medio_pago(
    sesion: Session,
    *,
    nombre: str,
    requiere_terminal: bool,
    admite_tokenizacion: bool,
    id_operador: int,
) -> MedioPago:
    _encargado_o_error(sesion, id_operador, "medios de pago")
    nombre = _texto(nombre, "nombre")
    if (
        sesion.execute(
            select(MedioPago).where(func.lower(MedioPago.nombre) == nombre.lower())
        ).scalar_one_or_none()
        is not None
    ):
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay un medio de pago con ese nombre."
        )
    medio = MedioPago(
        nombre=nombre,
        requiere_terminal=bool(requiere_terminal),
        admite_tokenizacion=bool(admite_tokenizacion),
    )
    sesion.add(medio)
    sesion.flush()
    return medio


def actualizar_medio_pago(
    sesion: Session,
    *,
    id_medio_pago: int,
    nombre: str,
    requiere_terminal: bool,
    admite_tokenizacion: bool,
    id_operador: int,
) -> MedioPago:
    _encargado_o_error(sesion, id_operador, "medios de pago")
    medio = _o_404(sesion, MedioPago, id_medio_pago, "El medio de pago")
    nombre = _texto(nombre, "nombre")
    choca = sesion.execute(
        select(MedioPago).where(
            func.lower(MedioPago.nombre) == nombre.lower(),
            MedioPago.id_medio_pago != id_medio_pago,
        )
    ).scalar_one_or_none()
    if choca is not None:
        raise ErrorAdministracion(
            "admin_nombre_duplicado", "Ya hay otro medio de pago con ese nombre."
        )
    medio.nombre = nombre
    medio.requiere_terminal = bool(requiere_terminal)
    medio.admite_tokenizacion = bool(admite_tokenizacion)
    sesion.flush()
    return medio


# --------------------------------------------------------------------------
# Desactivación (nunca borrado físico) + conteo de dependencias
# --------------------------------------------------------------------------

_ENTIDADES = {
    "sucursales": (Sucursal, "id_sucursal", "La sucursal"),
    "categorias": (Categoria, "id_categoria", "La categoría"),
    "productos": (Producto, "id_producto", "El producto"),
    "zonas": (ZonaExhibicion, "id_zona_exhibicion", "La zona de exhibición"),
    "medios": (MedioPago, "id_medio_pago", "El medio de pago"),
}


def _o_404(sesion: Session, modelo, pk, etiqueta: str):
    fila = sesion.get(modelo, pk)
    if fila is None:
        raise ErrorAdministracion(
            "admin_no_encontrado", f"{etiqueta} no existe.", status_code=404
        )
    return fila


def _cuenta(sesion: Session, consulta) -> int:
    return int(sesion.execute(consulta).scalar() or 0)


def contar_dependencias(
    sesion: Session, *, entidad: str, id_entidad: int
) -> list[dict]:
    """Conteo real de lo que quedará referenciando a la entidad tras desactivarla. Nunca
    bloquea: la UI lo muestra y deja continuar (Parte 3). Cada dependencia conserva su
    historial completo — desactivar sólo la oculta de los selectores.
    """
    modelo, _pk, etiqueta = _ENTIDADES[entidad]
    _o_404(sesion, modelo, id_entidad, etiqueta)
    deps: list[dict] = []

    if entidad == "sucursales":
        deps.append(
            {
                "descripcion": "turnos abiertos o cerrados en esta sucursal",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(Turno)
                    .where(Turno.id_sucursal == id_entidad),
                ),
            }
        )
        deps.append(
            {
                "descripcion": "lotes de inventario en esta sucursal",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(Lote)
                    .where(Lote.id_sucursal == id_entidad),
                ),
            }
        )
        deps.append(
            {
                "descripcion": "zonas de exhibición de esta sucursal",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(ZonaExhibicion)
                    .where(ZonaExhibicion.id_sucursal == id_entidad),
                ),
            }
        )
    elif entidad == "categorias":
        deps.append(
            {
                "descripcion": "productos asociados a esta categoría",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(Producto)
                    .where(Producto.id_categoria == id_entidad),
                ),
            }
        )
    elif entidad == "productos":
        deps.append(
            {
                "descripcion": "ventas registradas de este producto",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(RenglonVenta)
                    .where(RenglonVenta.id_producto == id_entidad),
                ),
            }
        )
        deps.append(
            {
                "descripcion": "lotes de este producto",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(Lote)
                    .where(Lote.id_producto == id_entidad),
                ),
            }
        )
        deps.append(
            {
                "descripcion": "relaciones de rol o de sustitución de este producto",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(RolProducto)
                    .where(RolProducto.id_producto == id_entidad),
                )
                + _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(SustitucionProducto)
                    .where(
                        (SustitucionProducto.id_producto == id_entidad)
                        | (SustitucionProducto.id_producto_sustituto == id_entidad)
                    ),
                ),
            }
        )
    elif entidad == "zonas":
        deps.append(
            {
                "descripcion": "sugerencias de colocación hacia esta zona",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(SugerenciaColocacion)
                    .where(SugerenciaColocacion.id_zona_exhibicion == id_entidad),
                ),
            }
        )
    elif entidad == "medios":
        deps.append(
            {
                "descripcion": "tramos de cobertura por sucursal de este medio",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(CoberturaPago)
                    .where(CoberturaPago.id_medio_pago == id_entidad),
                ),
            }
        )
        deps.append(
            {
                "descripcion": "entradas de bitácora que referencian este medio",
                "conteo": _cuenta(
                    sesion,
                    select(func.count())
                    .select_from(BitacoraAuditoria)
                    .where(BitacoraAuditoria.id_medio_pago == id_entidad),
                ),
            }
        )

    return [d for d in deps if d["conteo"] > 0]


def fijar_activo(
    sesion: Session, *, entidad: str, id_entidad: int, activo: bool, id_operador: int
):
    """Desactiva (o reactiva) un maestro. Nunca borra. Reservado al encargado."""
    if entidad not in _ENTIDADES:
        raise ErrorAdministracion(
            "admin_entidad_desconocida", "Ese tipo de maestro no existe."
        )
    _encargado_o_error(sesion, id_operador, "estos datos maestros")
    modelo, _pk, etiqueta = _ENTIDADES[entidad]
    fila = _o_404(sesion, modelo, id_entidad, etiqueta)
    fila.activo = bool(activo)
    sesion.flush()
    return fila


# --------------------------------------------------------------------------
# Listados paginables por la API
# --------------------------------------------------------------------------


def listar(sesion: Session, *, entidad: str, incluir_inactivos: bool) -> list[dict]:
    if entidad not in _ENTIDADES:
        raise ErrorAdministracion(
            "admin_entidad_desconocida", "Ese tipo de maestro no existe."
        )
    modelo, pk, _etiqueta = _ENTIDADES[entidad]
    consulta = select(modelo)
    if not incluir_inactivos:
        consulta = consulta.where(modelo.activo.is_(True))
    consulta = consulta.order_by(getattr(modelo, pk))
    filas = sesion.execute(consulta).scalars().all()
    return [_a_dict(entidad, f) for f in filas]


def _a_dict(entidad: str, f) -> dict:
    if entidad == "sucursales":
        return {
            "id_sucursal": f.id_sucursal,
            "nombre": f.nombre,
            "zona_horaria": f.zona_horaria,
            "activo": f.activo,
        }
    if entidad == "categorias":
        return {
            "id_categoria": f.id_categoria,
            "nombre": f.nombre,
            "dias_umbral_inmovilizado": f.dias_umbral_inmovilizado,
            "activo": f.activo,
        }
    if entidad == "productos":
        return {
            "id_producto": f.id_producto,
            "nombre": f.nombre,
            "id_categoria": f.id_categoria,
            "es_granel": f.es_granel,
            "precio_vigente": f"{f.precio_vigente:.4f}",
            "lleva_caducidad": f.lleva_caducidad,
            "moneda": f.moneda,
            "activo": f.activo,
        }
    if entidad == "zonas":
        return {
            "id_zona_exhibicion": f.id_zona_exhibicion,
            "id_sucursal": f.id_sucursal,
            "nombre": f.nombre,
            "grado_privilegio": f.grado_privilegio,
            "activo": f.activo,
        }
    return {
        "id_medio_pago": f.id_medio_pago,
        "nombre": f.nombre,
        "requiere_terminal": f.requiere_terminal,
        "admite_tokenizacion": f.admite_tokenizacion,
        "activo": f.activo,
    }
