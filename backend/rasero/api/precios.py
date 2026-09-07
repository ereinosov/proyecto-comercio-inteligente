"""Router de precios y márgenes (T005 router base; T012, T013 margen real de User Story 1;
T021 rol de producto de User Story 2; T031, T032, T042, T043 sugerencias de User Story 3 y 4).

Cada endpoint hace su propio `commit`: los servicios de `servicios/margenes.py` y
`servicios/precios.py` no comitean — dejan la transacción a cargo de quien las invoque, porque
`resolver_margen_producto` es también la función del contrato de migración con 002 (research.md
#8 de 003), que la llamará dentro de su propia transacción.

`GET /productos/{id_producto}/rol` no estaba en el `contracts/openapi.yaml` original: la fase de
diseño solo previó el `PUT` de asignación (T021) y pasó por alto que el frontend necesita leer la
clasificación vigente para mostrarla — el mismo tipo de vacío que 001 encontró para `GET
/productos`/`GET /operadores` durante su propia implementación. Se añadió aquí y al contrato.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import (
    CanalCompetencia,
    MargenCalculado,
    ObservacionPrecio,
    RolProducto,
    ZonaExhibicion,
)
from rasero.persistencia.sesion import obtener_sesion
from rasero.seguridad import exige_rol
from rasero.servicios import margenes as servicio_margenes
from rasero.servicios import precios as servicio_precios

# Pantalla "Precios y márgenes": táctica/gerencial, rol `encargado` (constitución v2.5.0,
# "Autorización de pantalla"). Ningún flujo de caja de un `cajero` consulta márgenes ni roles
# de producto: Venta usa `/productos`, no este router.
router = APIRouter(tags=["precios"], dependencies=[Depends(exige_rol("encargado"))])


class RolNuevo(BaseModel):
    rol: str


class AplicarSugerenciaPrecio(BaseModel):
    id_sugerencia_precio: int


class AplicarSugerenciaColocacion(BaseModel):
    id_sugerencia_colocacion: int


def _margen_a_respuesta(fila: dict | MargenCalculado) -> dict:
    """Acepta tanto el `dict` que arma `listar_margenes_sucursal` como la fila ORM que resulta
    de releer `margen_calculado` tras `resolver_margen_producto` — misma forma de salida en
    ambos endpoints (contracts/openapi.yaml, esquema `MargenProducto`).
    """
    obtener = fila.get if isinstance(fila, dict) else lambda clave: getattr(fila, clave)
    costo_vigente = obtener("costo_vigente")
    margen = obtener("margen")
    return {
        "id_producto": obtener("id_producto"),
        "id_sucursal": obtener("id_sucursal"),
        "costo_vigente": f"{costo_vigente:.4f}" if costo_vigente is not None else None,
        "precio_vigente": f"{obtener('precio_vigente'):.4f}",
        "margen": float(margen) if margen is not None else None,
        "confiable": obtener("confiable"),
        "instante_calculo": obtener("instante_calculo"),
    }


@router.get("/productos/{id_producto}/margen")
def obtener_margen_producto(
    id_producto: int, id_sucursal: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    servicio_margenes.resolver_margen_producto(sesion, id_producto=id_producto, id_sucursal=id_sucursal)
    sesion.commit()
    fila = sesion.get(MargenCalculado, (id_producto, id_sucursal))
    return _margen_a_respuesta(fila)


@router.get("/margenes")
def listar_margenes(id_sucursal: int, sesion: Session = Depends(obtener_sesion)) -> list[dict]:
    filas = servicio_margenes.listar_margenes_sucursal(sesion, id_sucursal=id_sucursal)
    sesion.commit()
    return [_margen_a_respuesta(fila) for fila in filas]


def _rol_a_respuesta(id_producto: int, fila: RolProducto | None) -> dict:
    return {
        "id_producto": id_producto,
        "rol": fila.rol if fila is not None else None,
        "instante_asignacion": fila.instante_asignacion if fila is not None else None,
    }


@router.get("/productos/{id_producto}/rol")
def obtener_rol_producto(id_producto: int, sesion: Session = Depends(obtener_sesion)) -> dict:
    fila = sesion.get(RolProducto, id_producto)
    return _rol_a_respuesta(id_producto, fila)


@router.put("/productos/{id_producto}/rol")
def asignar_rol_producto(
    id_producto: int, cuerpo: RolNuevo, sesion: Session = Depends(obtener_sesion)
) -> dict:
    fila = servicio_precios.asignar_rol_producto(sesion, id_producto=id_producto, rol=cuerpo.rol)
    sesion.commit()
    return _rol_a_respuesta(id_producto, fila)


def _observacion_a_respuesta(id_observacion_precio: int | None, sesion: Session) -> dict | None:
    if id_observacion_precio is None:
        return None
    observacion = sesion.get(ObservacionPrecio, id_observacion_precio)
    canal = sesion.get(CanalCompetencia, observacion.id_canal_competencia)
    dias = (datetime.now(timezone.utc) - observacion.instante_captura).days
    return {
        "id_observacion_precio": observacion.id_observacion_precio,
        "canal": canal.nombre,
        "precio_por_unidad_medida": f"{observacion.precio_observado:.4f}",
        "dias_de_antiguedad": dias,
    }


def _sugerencia_precio_a_respuesta(sugerencia, sesion: Session) -> dict:
    margen_usado = sugerencia.margen_usado
    return {
        "id_sugerencia_precio": sugerencia.id_sugerencia_precio,
        "id_producto": sugerencia.id_producto,
        "id_sucursal": sugerencia.id_sucursal,
        "precio_sugerido": f"{sugerencia.precio_sugerido:.4f}",
        "margen_usado": float(margen_usado) if margen_usado is not None else None,
        "rol_usado": sugerencia.rol_usado,
        "observacion_competencia_usada": _observacion_a_respuesta(
            sugerencia.id_observacion_precio_usada, sesion
        ),
        "instante_generacion": sugerencia.instante_generacion,
        "aplicada": sugerencia.aplicada,
        "instante_aplicacion": sugerencia.instante_aplicacion,
    }


@router.get("/productos/{id_producto}/sugerencia-precio")
def obtener_sugerencia_precio(
    id_producto: int, id_sucursal: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    sugerencia = servicio_precios.generar_sugerencia_precio(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal
    )
    sesion.commit()
    return _sugerencia_precio_a_respuesta(sugerencia, sesion)


@router.post("/productos/{id_producto}/sugerencia-precio/aplicar")
def aplicar_sugerencia_precio(
    id_producto: int, cuerpo: AplicarSugerenciaPrecio, sesion: Session = Depends(obtener_sesion)
) -> dict:
    sugerencia = servicio_precios.aplicar_sugerencia_precio(
        sesion, id_sugerencia_precio=cuerpo.id_sugerencia_precio
    )
    sesion.commit()
    return _sugerencia_precio_a_respuesta(sugerencia, sesion)


def _sugerencia_colocacion_a_respuesta(sugerencia, sesion: Session) -> dict:
    zona = sesion.get(ZonaExhibicion, sugerencia.id_zona_exhibicion)
    margen_usado = sugerencia.margen_usado
    return {
        "id_sugerencia_colocacion": sugerencia.id_sugerencia_colocacion,
        "id_producto": sugerencia.id_producto,
        "id_sucursal": sugerencia.id_sucursal,
        "id_zona_exhibicion": sugerencia.id_zona_exhibicion,
        "zona_nombre": zona.nombre,
        "margen_usado": float(margen_usado) if margen_usado is not None else None,
        "rol_usado": sugerencia.rol_usado,
        "instante_generacion": sugerencia.instante_generacion,
        "aplicada": sugerencia.aplicada,
        "instante_aplicacion": sugerencia.instante_aplicacion,
    }


@router.get("/productos/{id_producto}/sugerencia-colocacion")
def obtener_sugerencia_colocacion(
    id_producto: int, id_sucursal: int, sesion: Session = Depends(obtener_sesion)
) -> dict:
    sugerencia = servicio_precios.generar_sugerencia_colocacion(
        sesion, id_producto=id_producto, id_sucursal=id_sucursal
    )
    sesion.commit()
    return _sugerencia_colocacion_a_respuesta(sugerencia, sesion)


@router.post("/productos/{id_producto}/sugerencia-colocacion/aplicar")
def aplicar_sugerencia_colocacion(
    id_producto: int, cuerpo: AplicarSugerenciaColocacion, sesion: Session = Depends(obtener_sesion)
) -> dict:
    sugerencia = servicio_precios.aplicar_sugerencia_colocacion(
        sesion, id_sugerencia_colocacion=cuerpo.id_sugerencia_colocacion
    )
    sesion.commit()
    return _sugerencia_colocacion_a_respuesta(sugerencia, sesion)
