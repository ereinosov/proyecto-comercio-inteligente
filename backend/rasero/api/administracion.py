"""Router de administración de datos maestros (Parte 3): alta, edición y desactivación de
`sucursal`, `producto`, `categoria`, `zona_exhibicion` y `medio_pago` desde la interfaz.

Prefijo `/administracion`. Cada endpoint hace su propio `commit`; el servicio
(`servicios/administracion.py`) no comitea — mismo patrón que `api/pagos.py` frente a
`servicios/terminales_pago.py`.

Autorización de escritura: `operador.es_encargado`, verificado en el servicio con el mismo
mecanismo que `terminales_pago.py` / `cobertura_pago.py`. El `id_operador` viaja en el cuerpo,
igual que en `POST /pagos/terminales`.

Estructura de respuesta y forma del error `{codigo, mensaje}`: unificadas con `api/clientes.py`
y `api/pagos.py`.

Paginación de los listados: array en el cuerpo + total en `X-Total-Count` (ver
`api/paginacion.py`).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.api.paginacion import paginar
from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import administracion as servicio

router = APIRouter(tags=["administracion"], prefix="/administracion")

_ENTIDADES = ("sucursales", "categorias", "productos", "zonas", "medios")


# --------------------------------------------------------------------------
# Cuerpos de alta / edición
# --------------------------------------------------------------------------


class SucursalCuerpo(BaseModel):
    nombre: str
    zona_horaria: str
    id_operador: int


class CategoriaCuerpo(BaseModel):
    nombre: str
    dias_umbral_inmovilizado: int | None = None
    id_operador: int


class ProductoCuerpo(BaseModel):
    nombre: str
    id_categoria: int | None = None
    es_granel: bool = False
    precio_vigente: Decimal
    lleva_caducidad: bool = False
    id_operador: int


class ZonaCuerpo(BaseModel):
    id_sucursal: int
    nombre: str
    grado_privilegio: int
    id_operador: int


class MedioCuerpo(BaseModel):
    nombre: str
    requiere_terminal: bool = False
    admite_tokenizacion: bool = False
    id_operador: int


class Desactivacion(BaseModel):
    activo: bool = False
    id_operador: int


# --------------------------------------------------------------------------
# Listados
# --------------------------------------------------------------------------


@router.get("/{entidad}")
def listar(
    entidad: str,
    response: Response,
    incluir_inactivos: bool = False,
    pagina: int | None = None,
    tamano_pagina: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> list[dict]:
    filas = servicio.listar(
        sesion, entidad=entidad, incluir_inactivos=incluir_inactivos
    )
    return paginar(filas, pagina=pagina, tamano_pagina=tamano_pagina, response=response)


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
) -> dict:
    fila = servicio.fijar_activo(
        sesion,
        entidad=entidad,
        id_entidad=id_entidad,
        activo=cuerpo.activo,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict(entidad, fila)


# --------------------------------------------------------------------------
# Alta
# --------------------------------------------------------------------------


@router.post("/sucursales", status_code=status.HTTP_201_CREATED)
def crear_sucursal(
    cuerpo: SucursalCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.crear_sucursal(
        sesion,
        nombre=cuerpo.nombre,
        zona_horaria=cuerpo.zona_horaria,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("sucursales", fila)


@router.post("/categorias", status_code=status.HTTP_201_CREATED)
def crear_categoria(
    cuerpo: CategoriaCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.crear_categoria(
        sesion,
        nombre=cuerpo.nombre,
        dias_umbral_inmovilizado=cuerpo.dias_umbral_inmovilizado,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("categorias", fila)


@router.post("/productos", status_code=status.HTTP_201_CREATED)
def crear_producto(
    cuerpo: ProductoCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.crear_producto(
        sesion,
        nombre=cuerpo.nombre,
        id_categoria=cuerpo.id_categoria,
        es_granel=cuerpo.es_granel,
        precio_vigente=cuerpo.precio_vigente,
        lleva_caducidad=cuerpo.lleva_caducidad,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("productos", fila)


@router.post("/zonas", status_code=status.HTTP_201_CREATED)
def crear_zona(cuerpo: ZonaCuerpo, sesion: Session = Depends(obtener_sesion)) -> dict:
    fila = servicio.crear_zona_exhibicion(
        sesion,
        id_sucursal=cuerpo.id_sucursal,
        nombre=cuerpo.nombre,
        grado_privilegio=cuerpo.grado_privilegio,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("zonas", fila)


@router.post("/medios", status_code=status.HTTP_201_CREATED)
def crear_medio(cuerpo: MedioCuerpo, sesion: Session = Depends(obtener_sesion)) -> dict:
    fila = servicio.crear_medio_pago(
        sesion,
        nombre=cuerpo.nombre,
        requiere_terminal=cuerpo.requiere_terminal,
        admite_tokenizacion=cuerpo.admite_tokenizacion,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("medios", fila)


# --------------------------------------------------------------------------
# Edición
# --------------------------------------------------------------------------


@router.put("/sucursales/{id_entidad:int}")
def editar_sucursal(
    id_entidad: int, cuerpo: SucursalCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.actualizar_sucursal(
        sesion,
        id_sucursal=id_entidad,
        nombre=cuerpo.nombre,
        zona_horaria=cuerpo.zona_horaria,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("sucursales", fila)


@router.put("/categorias/{id_entidad:int}")
def editar_categoria(
    id_entidad: int, cuerpo: CategoriaCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.actualizar_categoria(
        sesion,
        id_categoria=id_entidad,
        nombre=cuerpo.nombre,
        dias_umbral_inmovilizado=cuerpo.dias_umbral_inmovilizado,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("categorias", fila)


@router.put("/productos/{id_entidad:int}")
def editar_producto(
    id_entidad: int, cuerpo: ProductoCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.actualizar_producto(
        sesion,
        id_producto=id_entidad,
        nombre=cuerpo.nombre,
        id_categoria=cuerpo.id_categoria,
        es_granel=cuerpo.es_granel,
        precio_vigente=cuerpo.precio_vigente,
        lleva_caducidad=cuerpo.lleva_caducidad,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("productos", fila)


@router.put("/zonas/{id_entidad:int}")
def editar_zona(
    id_entidad: int, cuerpo: ZonaCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.actualizar_zona_exhibicion(
        sesion,
        id_zona_exhibicion=id_entidad,
        id_sucursal=cuerpo.id_sucursal,
        nombre=cuerpo.nombre,
        grado_privilegio=cuerpo.grado_privilegio,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("zonas", fila)


@router.put("/medios/{id_entidad:int}")
def editar_medio(
    id_entidad: int, cuerpo: MedioCuerpo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio.actualizar_medio_pago(
        sesion,
        id_medio_pago=id_entidad,
        nombre=cuerpo.nombre,
        requiere_terminal=cuerpo.requiere_terminal,
        admite_tokenizacion=cuerpo.admite_tokenizacion,
        id_operador=cuerpo.id_operador,
    )
    sesion.commit()
    return servicio._a_dict("medios", fila)
