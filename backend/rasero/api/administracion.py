"""Router de administración de datos maestros (Parte 3): alta, edición y desactivación de
`sucursal`, `producto`, `categoria`, `zona_exhibicion` y `medio_pago` desde la interfaz.

Prefijo `/administracion`. Cada endpoint hace su propio `commit`; el servicio
(`servicios/administracion.py`) no comitea — mismo patrón que `api/pagos.py` frente a
`servicios/terminales_pago.py`.

Autorización de escritura: rol `encargado` o superior, verificado por el mecanismo central
`requiere_rol` (Principio VI). La **identidad** del operador se deriva del token de sesión de
turno (`Authorization: Bearer <token>`), no del cuerpo — enmienda v2.4.0, User Story 11: la
dependency `exige_rol("encargado")` la resuelve y valida el rol de una vez. El `id_operador` se
retiró de los cuerpos.

Estructura de respuesta y forma del error `{codigo, mensaje}`: unificadas con `api/clientes.py`
y `api/pagos.py`.

Paginación de los listados: array en el cuerpo + total en `X-Total-Count` (ver
`api/paginacion.py`).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.api.paginacion import paginar
from rasero.persistencia.modelos import Operador
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import administracion as servicio

router = APIRouter(tags=["administracion"], prefix="/administracion")

_ENTIDADES = ("sucursales", "categorias", "productos", "zonas", "medios")

# La identidad del operador de escritura sale del token de sesión de turno (User Story 11).
_Encargado = Depends(exige_rol("encargado"))


# --------------------------------------------------------------------------
# Cuerpos de alta / edición
# --------------------------------------------------------------------------


class SucursalCuerpo(BaseModel):
    nombre: str
    zona_horaria: str


class CategoriaCuerpo(BaseModel):
    nombre: str
    dias_umbral_inmovilizado: int | None = None


class ProductoCuerpo(BaseModel):
    nombre: str
    id_categoria: int | None = None
    es_granel: bool = False
    precio_vigente: Decimal
    lleva_caducidad: bool = False
    # US12: URL externa de imagen del producto para el catálogo de Venta. Opcional.
    url_imagen: str | None = None


class ZonaCuerpo(BaseModel):
    id_sucursal: int
    nombre: str
    grado_privilegio: int


class MedioCuerpo(BaseModel):
    nombre: str
    requiere_terminal: bool = False
    admite_tokenizacion: bool = False


class Desactivacion(BaseModel):
    activo: bool = False


# --------------------------------------------------------------------------
# Listados
# --------------------------------------------------------------------------


@router.get("/{entidad}")
def listar(
    entidad: str,
    incluir_inactivos: bool = False,
    busqueda: str | None = None,
    pagina: int | None = None,
    tamano_pagina: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    filas = servicio.listar(
        sesion, entidad=entidad, incluir_inactivos=incluir_inactivos, busqueda=busqueda
    )
    return paginar(filas, pagina=pagina, tamano_pagina=tamano_pagina)


@router.get("/{entidad}/{id_entidad:int}/dependencias")
def dependencias(
    entidad: str, id_entidad: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    deps = servicio.contar_dependencias(sesion, entidad=entidad, id_entidad=id_entidad)
    return {"dependencias": deps, "tiene_dependencias": bool(deps)}


@router.post("/{entidad}/{id_entidad:int}/desactivacion")
def cambiar_activo(
    entidad: str,
    id_entidad: int,
    cuerpo: Desactivacion,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.fijar_activo(
        sesion,
        entidad=entidad,
        id_entidad=id_entidad,
        activo=cuerpo.activo,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict(entidad, fila)


# --------------------------------------------------------------------------
# Alta
# --------------------------------------------------------------------------


@router.post("/sucursales", status_code=status.HTTP_201_CREATED)
def crear_sucursal(
    cuerpo: SucursalCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.crear_sucursal(
        sesion,
        nombre=cuerpo.nombre,
        zona_horaria=cuerpo.zona_horaria,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("sucursales", fila)


@router.post("/categorias", status_code=status.HTTP_201_CREATED)
def crear_categoria(
    cuerpo: CategoriaCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.crear_categoria(
        sesion,
        nombre=cuerpo.nombre,
        dias_umbral_inmovilizado=cuerpo.dias_umbral_inmovilizado,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("categorias", fila)


@router.post("/productos", status_code=status.HTTP_201_CREATED)
def crear_producto(
    cuerpo: ProductoCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.crear_producto(
        sesion,
        nombre=cuerpo.nombre,
        id_categoria=cuerpo.id_categoria,
        es_granel=cuerpo.es_granel,
        precio_vigente=cuerpo.precio_vigente,
        lleva_caducidad=cuerpo.lleva_caducidad,
        url_imagen=cuerpo.url_imagen,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("productos", fila)


@router.post("/zonas", status_code=status.HTTP_201_CREATED)
def crear_zona(
    cuerpo: ZonaCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.crear_zona_exhibicion(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        nombre=cuerpo.nombre,
        grado_privilegio=cuerpo.grado_privilegio,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("zonas", fila)


@router.post("/medios", status_code=status.HTTP_201_CREATED)
def crear_medio(
    cuerpo: MedioCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.crear_medio_pago(
        sesion,
        nombre=cuerpo.nombre,
        requiere_terminal=cuerpo.requiere_terminal,
        admite_tokenizacion=cuerpo.admite_tokenizacion,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("medios", fila)


# --------------------------------------------------------------------------
# Edición
# --------------------------------------------------------------------------


@router.put("/sucursales/{id_entidad:int}")
def editar_sucursal(
    id_entidad: int,
    cuerpo: SucursalCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.actualizar_sucursal(
        sesion,
        id_sucursal=id_entidad,
        nombre=cuerpo.nombre,
        zona_horaria=cuerpo.zona_horaria,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("sucursales", fila)


@router.put("/categorias/{id_entidad:int}")
def editar_categoria(
    id_entidad: int,
    cuerpo: CategoriaCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.actualizar_categoria(
        sesion,
        id_categoria=id_entidad,
        nombre=cuerpo.nombre,
        dias_umbral_inmovilizado=cuerpo.dias_umbral_inmovilizado,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("categorias", fila)


@router.put("/productos/{id_entidad:int}")
def editar_producto(
    id_entidad: int,
    cuerpo: ProductoCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.actualizar_producto(
        sesion,
        id_producto=id_entidad,
        nombre=cuerpo.nombre,
        id_categoria=cuerpo.id_categoria,
        es_granel=cuerpo.es_granel,
        precio_vigente=cuerpo.precio_vigente,
        lleva_caducidad=cuerpo.lleva_caducidad,
        url_imagen=cuerpo.url_imagen,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("productos", fila)


@router.put("/zonas/{id_entidad:int}")
def editar_zona(
    id_entidad: int,
    cuerpo: ZonaCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.actualizar_zona_exhibicion(
        sesion,
        id_zona_exhibicion=id_entidad,
        id_sucursal=cuerpo.id_sucursal,
        nombre=cuerpo.nombre,
        grado_privilegio=cuerpo.grado_privilegio,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("zonas", fila)


@router.put("/medios/{id_entidad:int}")
def editar_medio(
    id_entidad: int,
    cuerpo: MedioCuerpo,
    sesion: Session = Depends(obtener_sesion),
    operador: Operador = _Encargado,
) -> dict:
    fila = servicio.actualizar_medio_pago(
        sesion,
        id_medio_pago=id_entidad,
        nombre=cuerpo.nombre,
        requiere_terminal=cuerpo.requiere_terminal,
        admite_tokenizacion=cuerpo.admite_tokenizacion,
        operador=operador,
    )
    sesion.commit()
    return servicio._a_dict("medios", fila)
