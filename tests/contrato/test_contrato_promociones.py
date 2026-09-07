"""Prueba obligatoria de contrato (Principio III) de 005-promociones-inteligentes contra
`specs/005-promociones-inteligentes/contracts/openapi.yaml`. Contra PostgreSQL real, puerto 5442.

Cubre las cuatro historias (T016 cupones + redención; T029 ofertas de recompra; T043 experimentos;
T052 marca activa) en su forma feliz y en sus modos de fallo declarados, siempre con el formato de
error unificado `{codigo, mensaje}`.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.apoyo import crear_escenario_basico, headers_encargado
from tests.apoyo_promociones import (
    _venta,
    crear_cliente_churned,
    crear_cliente_cumpleanos,
    crear_cliente_en_ventana_recompra,
    escenario_dos_productos,
    limpiar_experimentos,
    marcar_fugas,
)

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Cupon, OfertaRecompra
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.experimentos import crear_experimento
from rasero.servicios.promociones import detectar_ofertas_recompra, generar_cupones


# Rol de pantalla `encargado` (constitución v2.5.0): estas pantallas quedaron tras
# `exige_rol('encargado')`. Header por defecto del cliente; una llamada puntual puede
# sobreescribirlo con `headers=`.
_s_cab = SesionLocal()
_CAB_ENCARGADO = headers_encargado(_s_cab)
_s_cab.close()
cliente = TestClient(app, headers=_CAB_ENCARGADO)

CLAVES_CUPON = (
    "id_cupon",
    "id_campania",
    "id_cliente",
    "motivo",
    "fecha_objetivo",
    "valido_desde",
    "valido_hasta",
    "porcentaje_descuento",
    "estado",
    "instante_generacion",
)
CLAVES_OFERTA = (
    "id_oferta_recompra",
    "id_campania",
    "id_cliente",
    "id_producto",
    "id_sucursal",
    "intervalo_esperado_dias_disparo",
    "justificacion",
    "precio_garantizado",
    "reserva_desde",
    "reserva_hasta",
    "estado_reserva",
    "desenlace",
    "instante_generacion",
)
CLAVES_EXPERIMENTO = (
    "id_experimento_reactivacion",
    "id_campania",
    "id_sucursal",
    "semilla",
    "algoritmo",
    "proporcion_tratamiento",
    "ventana_medicion_dias",
    "porcentaje_descuento",
    "parametros_muestra",
    "n_elegibles",
    "n_tratamiento",
    "n_control",
    "retorno_tratamiento",
    "retorno_control",
    "incrementalidad",
    "estadistico_z",
    "valor_p",
    "veredicto",
    "motivo_muestra_insuficiente",
    "instante_asignacion",
    "instante_cierre",
)
CLAVES_ASIGNACION = (
    "id_asignacion_experimento",
    "id_experimento_reactivacion",
    "id_cliente",
    "id_senal_fuga",
    "grupo",
    "retorno",
    "id_venta_retorno",
    "instante_retorno",
)
CLAVES_REDENCION = (
    "id_redencion_promocion",
    "tipo_origen",
    "id_cupon",
    "id_oferta_recompra",
    "id_asignacion_experimento",
    "id_venta",
    "id_producto",
    "id_sucursal",
    "periodo",
    "descuento_aplicado",
    "instante_redencion",
)
CLAVES_MARCA = ("id_producto", "id_sucursal", "periodo", "tipos")

_HOY = date.today()


def _es_error(cuerpo: dict) -> bool:
    return set(cuerpo) >= {"codigo", "mensaje"} and isinstance(cuerpo["mensaje"], str)


# ==========================================================================
# T016 — cupones + redención (US1)
# ==========================================================================


def test_generacion_de_cupones_forma_feliz_e_idempotencia():
    sesion = SesionLocal()
    crear_cliente_cumpleanos(
        sesion,
        nombre=f"Contrato cupón {datetime.now().timestamp()}",
        fecha_nacimiento=date(1985, _HOY.month, _HOY.day),
    )
    sesion.close()

    cuerpo = {"desde": _HOY.isoformat(), "hasta": _HOY.isoformat()}
    primera = cliente.post("/promociones/cupones/generacion", json=cuerpo)
    assert primera.status_code == 200
    for clave in ("id_campania", "cupones_generados", "cupones_ya_existentes"):
        assert clave in primera.json()
    assert primera.json()["cupones_generados"] >= 1

    segunda = cliente.post("/promociones/cupones/generacion", json=cuerpo)
    assert segunda.status_code == 200
    assert segunda.json()["cupones_generados"] == 0  # idempotencia por (id_cliente, fecha_objetivo)

    listado = cliente.get("/promociones/cupones", params={"vigentes": True})
    assert listado.status_code == 200
    # Listado paginado: { items, total } (schema RespuestaPaginada).
    items = listado.json()["items"]
    assert isinstance(items, list) and items
    for clave in CLAVES_CUPON:
        assert clave in items[0], f"falta '{clave}' en Cupon"


def test_generacion_con_rango_invalido_es_400_con_error():
    respuesta = cliente.post(
        "/promociones/cupones/generacion",
        json={
            "desde": _HOY.isoformat(),
            "hasta": (_HOY - timedelta(days=1)).isoformat(),
        },
    )
    assert respuesta.status_code == 400
    assert _es_error(respuesta.json())


def test_redencion_forma_feliz_idempotencia_y_fallos():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    cli = crear_cliente_cumpleanos(
        sesion,
        nombre=f"Contrato redención {datetime.now().timestamp()}",
        fecha_nacimiento=date(1980, _HOY.month, _HOY.day),
    )
    generar_cupones(sesion, desde=_HOY, hasta=_HOY)
    sesion.commit()
    cupon = sesion.execute(select(Cupon).where(Cupon.id_cliente == cli.id_cliente)).scalar_one()
    venta = _venta(sesion, escenario, instante=datetime.now(timezone.utc))
    id_venta, id_cupon = venta.id_venta, cupon.id_cupon
    sesion.close()

    primera = cliente.post(
        "/promociones/redenciones",
        json={"id_venta": id_venta, "tipo_origen": "cupon", "id_cupon": id_cupon},
    )
    assert primera.status_code == 201
    for clave in CLAVES_REDENCION:
        assert clave in primera.json(), f"falta '{clave}' en Redencion"

    segunda = cliente.post(
        "/promociones/redenciones",
        json={"id_venta": id_venta, "tipo_origen": "cupon", "id_cupon": id_cupon},
    )
    assert segunda.status_code == 200  # idempotencia por origen
    assert segunda.json()["id_redencion_promocion"] == primera.json()["id_redencion_promocion"]

    # tipo_origen incoherente con el id_* provisto -> 400.
    incoherente = cliente.post(
        "/promociones/redenciones",
        json={
            "id_venta": id_venta,
            "tipo_origen": "oferta_recompra",
            "id_cupon": id_cupon,
        },
    )
    assert incoherente.status_code == 400
    assert _es_error(incoherente.json())

    # venta inexistente -> 404.
    faltante = cliente.post(
        "/promociones/redenciones",
        json={"id_venta": 999999, "tipo_origen": "cupon", "id_cupon": id_cupon},
    )
    assert faltante.status_code == 404
    assert _es_error(faltante.json())


def test_redencion_de_cupon_fuera_de_ventana_es_400():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    cli = crear_cliente_cumpleanos(
        sesion,
        nombre=f"Contrato fuera ventana {datetime.now().timestamp()}",
        fecha_nacimiento=date(1980, _HOY.month, _HOY.day),
    )
    generar_cupones(sesion, desde=_HOY, hasta=_HOY)
    sesion.commit()
    cupon = sesion.execute(select(Cupon).where(Cupon.id_cliente == cli.id_cliente)).scalar_one()
    # Venta muy anterior a valido_desde.
    venta = _venta(sesion, escenario, instante=datetime.now(timezone.utc) - timedelta(days=120))
    id_venta, id_cupon = venta.id_venta, cupon.id_cupon
    sesion.close()

    respuesta = cliente.post(
        "/promociones/redenciones",
        json={"id_venta": id_venta, "tipo_origen": "cupon", "id_cupon": id_cupon},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "cupon_fuera_de_ventana"


# ==========================================================================
# T029 — ofertas de recompra (US2)
# ==========================================================================


def test_deteccion_y_listado_de_ofertas_forma_feliz():
    sesion = SesionLocal()
    escenario = escenario_dos_productos(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    crear_cliente_en_ventana_recompra(
        sesion,
        escenario,
        nombre=f"Contrato oferta {datetime.now().timestamp()}",
        id_producto=escenario["producto_2"].id_producto,
    )
    sesion.close()

    deteccion = cliente.post(
        "/promociones/ofertas-recompra/deteccion", json={"id_sucursal": id_sucursal}
    )
    assert deteccion.status_code == 200
    for clave in ("id_campania", "ofertas_propuestas", "ofertas_ya_activas"):
        assert clave in deteccion.json()
    assert deteccion.json()["ofertas_propuestas"] == 1

    listado = cliente.get("/promociones/ofertas-recompra", params={"desenlace": "pendiente"})
    assert listado.status_code == 200
    assert isinstance(listado.json(), list) and listado.json()
    for clave in CLAVES_OFERTA:
        assert clave in listado.json()[0], f"falta '{clave}' en OfertaRecompra"


def test_deteccion_de_ofertas_sucursal_inexistente_es_404():
    respuesta = cliente.post(
        "/promociones/ofertas-recompra/deteccion", json={"id_sucursal": 999999}
    )
    assert respuesta.status_code == 404
    assert _es_error(respuesta.json())


def test_redencion_de_oferta_de_recompra_por_contrato():
    sesion = SesionLocal()
    escenario = escenario_dos_productos(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    id_producto = escenario["producto_2"].id_producto
    crear_cliente_en_ventana_recompra(
        sesion,
        escenario,
        nombre=f"Contrato oferta redim {datetime.now().timestamp()}",
        id_producto=id_producto,
    )
    detectar_ofertas_recompra(sesion, id_sucursal=id_sucursal)
    sesion.commit()
    oferta = sesion.execute(
        select(OfertaRecompra).where(OfertaRecompra.id_producto == id_producto)
    ).scalar_one()
    venta = _venta(sesion, escenario, instante=datetime.now(timezone.utc), id_producto=id_producto)
    id_venta, id_oferta = venta.id_venta, oferta.id_oferta_recompra
    sesion.close()

    respuesta = cliente.post(
        "/promociones/redenciones",
        json={
            "id_venta": id_venta,
            "tipo_origen": "oferta_recompra",
            "id_oferta_recompra": id_oferta,
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["tipo_origen"] == "oferta_recompra"

    detalle = cliente.get("/promociones/ofertas-recompra").json()
    marcada = next(o for o in detalle if o["id_oferta_recompra"] == id_oferta)
    assert marcada["desenlace"] == "comprado"


# ==========================================================================
# T043 — experimentos (US3)
# ==========================================================================


def _poblar_elegibles(n: int, prefijo: str) -> int:
    sesion = SesionLocal()
    limpiar_experimentos(sesion)
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000000)
    for i in range(n):
        crear_cliente_churned(
            sesion,
            escenario,
            nombre=f"{prefijo}-{i}-{datetime.now().timestamp()}",
            dias_desde_ultima=150,
        )
    marcar_fugas(sesion)
    id_sucursal = escenario["sucursal"].id_sucursal
    sesion.close()
    return id_sucursal


def test_experimento_ciclo_por_contrato():
    id_sucursal = _poblar_elegibles(40, "ContratoExp")

    creado = cliente.post(
        "/promociones/experimentos",
        json={
            "id_sucursal": id_sucursal,
            "mde_puntos_porcentuales": "50",
            "semilla": 20260905,
        },
    )
    assert creado.status_code == 201
    cuerpo = creado.json()
    for clave in CLAVES_EXPERIMENTO:
        assert clave in cuerpo, f"falta '{clave}' en Experimento"
    for clave in (
        "tasa_retorno_base_esperada",
        "mde_puntos_porcentuales",
        "alfa",
        "poder",
        "tamano_minimo_muestra",
    ):
        assert clave in cuerpo["parametros_muestra"]
    assert cuerpo["veredicto"] == "en_curso"
    id_exp = cuerpo["id_experimento_reactivacion"]

    detalle = cliente.get(f"/promociones/experimentos/{id_exp}")
    assert detalle.status_code == 200
    assert detalle.json()["id_experimento_reactivacion"] == id_exp

    asignaciones = cliente.get(f"/promociones/experimentos/{id_exp}/asignaciones")
    assert asignaciones.status_code == 200
    assert len(asignaciones.json()) == 40
    for clave in CLAVES_ASIGNACION:
        assert clave in asignaciones.json()[0], f"falta '{clave}' en Asignacion"

    # Segundo experimento con uno en curso -> 409.
    conflicto = cliente.post("/promociones/experimentos", json={"id_sucursal": id_sucursal})
    assert conflicto.status_code == 409
    assert _es_error(conflicto.json())

    # Cierre con la ventana no vencida -> 409.
    cierre_temprano = cliente.post(f"/promociones/experimentos/{id_exp}/cierre")
    assert cierre_temprano.status_code == 409
    assert _es_error(cierre_temprano.json())


def test_experimento_parametros_invalidos_es_400():
    id_sucursal = _poblar_elegibles(4, "ContratoExpInv")
    respuesta = cliente.post(
        "/promociones/experimentos",
        json={"id_sucursal": id_sucursal, "ventana_medicion_dias": 0},
    )
    assert respuesta.status_code == 400
    assert _es_error(respuesta.json())


def test_experimento_inexistente_es_404():
    respuesta = cliente.get("/promociones/experimentos/999999")
    assert respuesta.status_code == 404
    assert _es_error(respuesta.json())


# ==========================================================================
# T052 — marca activa (US4)
# ==========================================================================


def test_marca_activa_forma_feliz_y_sucursal_inexistente():
    sesion = SesionLocal()
    escenario = crear_escenario_basico(sesion, existencia_inicial=100000)
    cli = crear_cliente_cumpleanos(
        sesion,
        nombre=f"Contrato marca {datetime.now().timestamp()}",
        fecha_nacimiento=date(1980, _HOY.month, _HOY.day),
    )
    generar_cupones(sesion, desde=_HOY, hasta=_HOY)
    sesion.commit()
    cupon = sesion.execute(select(Cupon).where(Cupon.id_cliente == cli.id_cliente)).scalar_one()
    venta = _venta(sesion, escenario, instante=datetime.now(timezone.utc))
    id_sucursal, id_venta, id_cupon = (
        escenario["sucursal"].id_sucursal,
        venta.id_venta,
        cupon.id_cupon,
    )
    sesion.close()

    cliente.post(
        "/promociones/redenciones",
        json={"id_venta": id_venta, "tipo_origen": "cupon", "id_cupon": id_cupon},
    )

    respuesta = cliente.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": id_sucursal,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list) and respuesta.json()
    for clave in CLAVES_MARCA:
        assert clave in respuesta.json()[0], f"falta '{clave}' en MarcaPromocionActiva"

    inexistente = cliente.get(
        "/promociones/marca-activa",
        params={
            "id_sucursal": 999999,
            "desde": _HOY.isoformat(),
            "hasta": _HOY.isoformat(),
        },
    )
    assert inexistente.status_code == 404
    assert _es_error(inexistente.json())
