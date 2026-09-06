"""Endpoints de clientes: POST /clientes, POST /clientes/{id_cliente}/visitas,
GET /clientes/busqueda, GET /clientes, GET /clientes/{id_cliente} (T009, T010, T011, T020, T021,
T022).

Nota de enrutado: `{id_cliente}` se declara `{id_cliente:int}` (convertidor de ruta de
Starlette/FastAPI) para que `/clientes/busqueda` y `/clientes/cumpleanos` nunca puedan ser
capturados por esa ruta dinámica sin importar el orden de declaración — un literal como
"busqueda" no coincide con el patrón numérico y Starlette prueba la siguiente ruta.
"""

from datetime import date

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.api.paginacion import paginar
from rasero.errores import RecursoNoEncontrado
from rasero.persistencia.modelos import Visita
from rasero.persistencia.sesion import obtener_sesion
from rasero.servicios import clientes as servicio_clientes

router = APIRouter(tags=["clientes"])


# `nombre` y `fecha_nacimiento` son OPCIONALES: un cliente puede quedar registrado sólo por su
# identificador (o sin ningún dato personal), como el modelo ORM ya los admite NULL. Forzarlos
# aquí contradecía el caso del cliente que sólo se anota para no duplicarlo entre visitas y el
# de "consumidor final". El `identificador` (cédula o RUC de persona natural) también es
# opcional (FR-003/FR-017): TODA su validación —longitud incluida— vive en el dominio
# (`identidad_cliente.py`) y se reporta como `IdentificadorInvalido` -> `{codigo, mensaje}`. No
# se pone `max_length` en Pydantic a propósito: un límite ahí produciría un 422 con forma
# `{"detail": [...]}` en vez del contrato `{codigo, mensaje}` que el frontend sabe mostrar.
class ClienteNuevo(BaseModel):
    nombre: str | None = None
    fecha_nacimiento: date | None = None
    contacto: str | None = None
    identificador: str | None = None


class VisitaNueva(BaseModel):
    id_venta: int


class ClienteEditado(BaseModel):
    nombre: str | None = None
    fecha_nacimiento: date | None = None
    contacto: str | None = None
    identificador: str | None = None


def _cliente_a_respuesta(cliente) -> dict:
    return {
        "id_cliente": cliente.id_cliente,
        "nombre": cliente.nombre,
        "fecha_nacimiento": cliente.fecha_nacimiento,
        "contacto": cliente.contacto,
        "identificador": cliente.identificador,
        "fecha_alta": cliente.fecha_alta,
        "anonimizado": cliente.anonimizado,
    }


def _visita_a_respuesta(visita: Visita) -> dict:
    return {
        "id_visita": visita.id_visita,
        "id_cliente": visita.id_cliente,
        "id_venta": visita.id_venta,
        "instante": visita.instante,
        "monto_total": f"{visita.monto_total:.2f}",
        # Ratio, no monto (research.md #2 de 002): nunca formatear como moneda de 2 decimales.
        "margen_relativo": float(visita.margen_relativo),
    }


def _resumen_a_respuesta(resumen: dict) -> dict:
    return {
        "id_cliente": resumen["id_cliente"],
        "nombre": resumen["nombre"],
        "valor": resumen["valor"],
        "monto_total": f"{resumen['monto_total']:.2f}",
    }


@router.post("/clientes", status_code=status.HTTP_201_CREATED)
def registrar_cliente(cuerpo: ClienteNuevo, sesion: Session = Depends(obtener_sesion)) -> dict:
    cliente = servicio_clientes.registrar_cliente(
        sesion,
        nombre=cuerpo.nombre,
        fecha_nacimiento=cuerpo.fecha_nacimiento,
        contacto=cuerpo.contacto,
        identificador=cuerpo.identificador,
    )
    return _cliente_a_respuesta(cliente)


@router.get("/clientes")
def listar_clientes(
    orden: str = "valor",
    busqueda: str | None = None,
    pagina: int | None = None,
    tamano_pagina: int | None = None,
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    filas = servicio_clientes.listar_valor_clientes(sesion, orden=orden, busqueda=busqueda)
    respuestas = [_resumen_a_respuesta(f) for f in filas]
    return paginar(respuestas, pagina=pagina, tamano_pagina=tamano_pagina)


@router.get("/clientes/busqueda")
def buscar_clientes(q: str, sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    filas = servicio_clientes.buscar_clientes_con_valor(sesion, q=q)
    return [_resumen_a_respuesta(f) for f in filas]


@router.get("/clientes/fuga/resumen")
def resumen_fuga(sesion: Session = Depends(obtener_sesion)) -> dict:
    """US6: distribución instantánea de clientes por segmento de fuga, para el gráfico de la
    pantalla de Clientes. Lectura pura; snapshot (no serie temporal — `senal_fuga` no guarda
    histórico periódico). Ruta con segmento literal `fuga/resumen`, nunca capturada por
    `/clientes/{id_cliente:int}`.
    """
    return servicio_clientes.resumen_fuga_por_segmento(sesion)


@router.get("/clientes/cumpleanos")
def clientes_con_cumpleanos(
    desde: date, hasta: date, sesion: Session = Depends(obtener_sesion)
) -> list[dict]:
    clientes = servicio_clientes.clientes_con_cumpleanos(sesion, desde=desde, hasta=hasta)
    return [
        {
            "id_cliente": c.id_cliente,
            "nombre": c.nombre,
            "fecha_nacimiento": c.fecha_nacimiento,
        }
        for c in clientes
    ]


@router.get("/clientes/{id_cliente:int}")
def obtener_cliente(id_cliente: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    detalle = servicio_clientes.obtener_detalle_cliente(sesion, id_cliente=id_cliente)
    if detalle is None:
        raise RecursoNoEncontrado(f"El cliente {id_cliente} no existe.")

    respuesta = _cliente_a_respuesta(detalle["cliente"])
    respuesta["valor"] = detalle["valor"]
    respuesta["fuga"] = detalle.get("fuga")
    return respuesta


@router.put("/clientes/{id_cliente:int}")
def editar_cliente(
    id_cliente: int, cuerpo: ClienteEditado, sesion: Session = Depends(obtener_sesion)
) -> dict:
    cliente = servicio_clientes.actualizar_cliente(
        sesion,
        id_cliente=id_cliente,
        nombre=cuerpo.nombre,
        fecha_nacimiento=cuerpo.fecha_nacimiento,
        contacto=cuerpo.contacto,
        identificador=cuerpo.identificador,
    )
    return _cliente_a_respuesta(cliente)


@router.post("/clientes/{id_cliente:int}/visitas")
def registrar_visita(
    id_cliente: int, cuerpo: VisitaNueva, response: Response, sesion: Session = Depends(obtener_sesion)
) -> dict:
    visita, creada_ahora = servicio_clientes.registrar_visita(
        sesion, id_cliente=id_cliente, id_venta=cuerpo.id_venta
    )
    response.status_code = status.HTTP_201_CREATED if creada_ahora else status.HTTP_200_OK
    return _visita_a_respuesta(visita)
