"""T080 [US7] — Prueba de integración del capital inmovilizado (FR-033 a FR-036).

- un lote de una categoría con umbral CORTO cuya última salida excede ese umbral -> señalado;
- un lote de una categoría con umbral LARGO y la misma antigüedad -> NO señalado;
- una categoría SIN umbral propio hereda el umbral global de respaldo;
- un lote sin costo registrado (centinela `costo_unitario = 0.00`, research.md §11) -> aparece
  con `valor_calculable: false` y `valor_inmovilizado: null`, nunca cero;
- el listado solo hace visible el dato: ninguna acción propuesta ni ejecutada (FR-036).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from tests.apoyo import headers_encargado
from rasero.persistencia.sesion import SesionLocal
from rasero.persistencia.modelos import Categoria, Lote, Producto, Sucursal
from rasero.persistencia.movimientos import registrar_movimiento


# Rol de pantalla `encargado` (constitución v2.5.0): estas pantallas quedaron tras
# `exige_rol('encargado')`. Header por defecto del cliente; una llamada puntual puede
# sobreescribirlo con `headers=`.
_s_cab = SesionLocal()
_CAB_ENCARGADO = headers_encargado(_s_cab)
_s_cab.close()
cliente = TestClient(app, headers=_CAB_ENCARGADO)


def _sucursal(sesion):
    s = Sucursal(nombre=f"Suc CI {datetime.now().timestamp()}", zona_horaria="America/Guayaquil")
    sesion.add(s)
    sesion.flush()
    return s


def _producto(sesion, *, dias_umbral):
    if dias_umbral is None:
        categoria = None
    else:
        categoria = Categoria(
            nombre=f"Cat {datetime.now().timestamp()}-{dias_umbral}",
            dias_umbral_inmovilizado=dias_umbral,
        )
        sesion.add(categoria)
        sesion.flush()
    p = Producto(
        nombre=f"Prod CI {datetime.now().timestamp()}",
        id_categoria=categoria.id_categoria if categoria else None,
        es_granel=False,
        precio_vigente=Decimal("5.0000"),
        lleva_caducidad=False,
    )
    sesion.add(p)
    sesion.flush()
    return p


def _lote_parado(sesion, *, id_sucursal, id_producto, dias_atras, costo="4.0000", cantidad=10):
    instante = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    lote = Lote(
        id_producto=id_producto,
        id_sucursal=id_sucursal,
        costo_unitario=Decimal(costo),
        fecha_caducidad=None,
        instante_entrada=instante,
    )
    sesion.add(lote)
    sesion.flush()
    registrar_movimiento(
        sesion,
        id_sucursal=id_sucursal,
        id_producto=id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(cantidad),
        instante=instante,
    )
    return lote


def test_umbral_corto_senala_largo_no_y_categoria_sin_umbral_hereda_el_global(sesion):
    suc = _sucursal(sesion)
    frescos = _producto(sesion, dias_umbral=5)
    no_perecedero = _producto(sesion, dias_umbral=60)
    sin_umbral = _producto(sesion, dias_umbral=None)

    lote_frescos = _lote_parado(sesion, id_sucursal=suc.id_sucursal, id_producto=frescos.id_producto, dias_atras=40)
    lote_np = _lote_parado(sesion, id_sucursal=suc.id_sucursal, id_producto=no_perecedero.id_producto, dias_atras=40)
    lote_global = _lote_parado(sesion, id_sucursal=suc.id_sucursal, id_producto=sin_umbral.id_producto, dias_atras=120)
    sesion.commit()

    listado = cliente.get(f"/capital-inmovilizado?id_sucursal={suc.id_sucursal}").json()
    por_lote = {f["id_lote"]: f for f in listado}

    assert lote_frescos.id_lote in por_lote, "40 d > umbral corto de 5 -> señalado"
    assert lote_np.id_lote not in por_lote, "40 d < umbral largo de 60 -> no señalado"
    assert lote_global.id_lote in por_lote, "120 d > umbral global de 90 -> señalado"
    assert por_lote[lote_global.id_lote]["umbral_heredado_del_global"] is True
    assert por_lote[lote_global.id_lote]["dias_umbral_aplicado"] == 90
    assert por_lote[lote_frescos.id_lote]["valor_inmovilizado"] == "40.00"  # 10 × 4.00
    assert por_lote[lote_frescos.id_lote]["valor_calculable"] is True


def test_valor_inmovilizado_de_un_granel_convierte_gramos_a_kilogramos(sesion):
    """Regresión #3 de la auditoría: la `cantidad_restante` de un lote a granel está en gramos y
    su `costo_unitario` es por kilogramo. 2000 g a 4.00 / kg = 8.00, nunca 8000.00.
    """
    suc = _sucursal(sesion)
    categoria = Categoria(
        nombre=f"Granel {datetime.now().timestamp()}", dias_umbral_inmovilizado=5
    )
    sesion.add(categoria)
    sesion.flush()
    prod = Producto(
        nombre=f"Queso a peso {datetime.now().timestamp()}",
        id_categoria=categoria.id_categoria,
        es_granel=True,
        precio_vigente=Decimal("6.0000"),
        lleva_caducidad=False,
    )
    sesion.add(prod)
    sesion.flush()
    lote = _lote_parado(
        sesion, id_sucursal=suc.id_sucursal, id_producto=prod.id_producto,
        dias_atras=30, costo="4.0000", cantidad=2000,
    )
    sesion.commit()

    fila = next(
        f for f in cliente.get(f"/capital-inmovilizado?id_sucursal={suc.id_sucursal}").json()
        if f["id_lote"] == lote.id_lote
    )
    assert fila["valor_calculable"] is True
    assert fila["valor_inmovilizado"] == "8.00"


def test_lote_sin_costo_es_no_calculable_nunca_cero(sesion):
    suc = _sucursal(sesion)
    prod = _producto(sesion, dias_umbral=5)
    lote = _lote_parado(
        sesion, id_sucursal=suc.id_sucursal, id_producto=prod.id_producto,
        dias_atras=30, costo="0.0000",
    )
    sesion.commit()

    fila = next(
        f for f in cliente.get(f"/capital-inmovilizado?id_sucursal={suc.id_sucursal}").json()
        if f["id_lote"] == lote.id_lote
    )
    assert fila["valor_calculable"] is False
    assert fila["valor_inmovilizado"] is None  # nunca "0.00"
