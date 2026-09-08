"""009 — flujo de la factura simulada.

- factura al generar tras el cobro; `total == venta.total` (IVA incluido); `subtotal + iva ==
  total`; "Consumidor Final" sin cliente, identificado con cédula;
- idempotente por `id_venta` (una fila);
- correlativo sin huecos;
- `venta`/`renglon_venta` sin cambios (SC-005);
- anulación → nota de crédito que referencia la factura anulada; sin factura → 204;
- aviso de simulación siempre presente.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from rasero.errores import FacturaNoAplicable, VentaNoAnulada
from rasero.persistencia.modelos import FacturaSimulada, RenglonVenta, Venta
from rasero.servicios.clientes import registrar_cliente, registrar_visita
from rasero.servicios.facturacion import (
    AVISO_SIMULACION,
    emitir_nota_credito,
    factura_a_respuesta,
    generar_factura,
    obtener_facturas_de_venta,
)
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.ventas import RenglonEntrada, anular_venta, registrar_venta
from tests.apoyo import crear_escenario_basico


def _cobrar(sesion, esc, renglones):
    venta, _c, _a, _l = registrar_venta(
        sesion,
        clave_idempotencia=f"fac-{uuid.uuid4()}",
        id_turno=esc["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=datetime.now(timezone.utc),
        renglones=renglones,
    )
    return venta


def test_factura_al_cobrar_iva_incluido_y_consumidor_final(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=100,
                      costo_unitario=Decimal("1.0000"))
    # producto 2.50 → venta de 4 unidades = 10.00
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=4, cantidad_gramos=None)])
    sesion.commit()

    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar_one()
    renglones_antes = sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one()

    factura, creada = generar_factura(sesion, id_venta=venta.id_venta)
    assert creada is True
    r = factura_a_respuesta(factura)

    assert r["total"] == f"{Decimal(venta.total):.2f}"     # IVA incluido → total == venta.total
    assert Decimal(r["subtotal"]) + Decimal(r["monto_iva"]) == Decimal(r["total"])
    assert r["comprador"]["tipo"] == "consumidor_final"
    assert r["secuencial"].startswith("001-001-")
    assert r["aviso_simulacion"] == AVISO_SIMULACION
    assert len(r["renglones"]) == 1
    assert r["medio_pago"] == "efectivo"

    # Solo lectura sobre 001.
    assert sesion.execute(select(func.count()).select_from(Venta)).scalar_one() == ventas_antes
    assert sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one() == renglones_antes


def test_comprador_identificado_con_cedula(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=1, cantidad_gramos=None)])
    cliente = registrar_cliente(sesion, nombre="María Torres", fecha_nacimiento=None,
                                identificador="1710034065")
    registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta)
    sesion.commit()

    factura, _ = generar_factura(sesion, id_venta=venta.id_venta)
    r = factura_a_respuesta(factura)
    assert r["comprador"]["tipo"] == "identificado"
    assert r["comprador"]["nombre"] == "María Torres"
    assert r["comprador"]["identificador"] == "1710034065"


def test_idempotente_por_venta_y_correlativo_sin_huecos(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=100,
                      costo_unitario=Decimal("1.0000"))
    ventas = [
        _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                             cantidad_unidades=1, cantidad_gramos=None)])
        for _ in range(3)
    ]
    sesion.commit()

    numeros = []
    for v in ventas:
        f1, c1 = generar_factura(sesion, id_venta=v.id_venta)
        f2, c2 = generar_factura(sesion, id_venta=v.id_venta)  # segunda vez
        assert c1 is True and c2 is False
        assert f1.id_factura_simulada == f2.id_factura_simulada
        numeros.append(f1.numero)
        filas = sesion.execute(
            select(func.count()).select_from(FacturaSimulada).where(
                FacturaSimulada.id_venta == v.id_venta, FacturaSimulada.tipo == "factura"
            )
        ).scalar_one()
        assert filas == 1

    assert numeros == list(range(numeros[0], numeros[0] + 3))  # correlativo sin huecos


def test_venta_total_cero_no_genera_factura(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    # Venta directa con total 0: se inserta una venta a mano con total 0.
    v = Venta(clave_idempotencia=f"cero-{uuid.uuid4()}", id_turno=esc["turno"].id_turno,
              referencia_terminal_pago=None, instante=datetime.now(timezone.utc),
              total=Decimal("0.00"))
    sesion.add(v)
    sesion.commit()
    with pytest.raises(FacturaNoAplicable):
        generar_factura(sesion, id_venta=v.id_venta)


def test_anulacion_genera_nota_de_credito(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=100,
                      costo_unitario=Decimal("1.0000"))
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=2, cantidad_gramos=None)])
    sesion.commit()
    factura, _ = generar_factura(sesion, id_venta=venta.id_venta)

    anular_venta(sesion, id_venta=venta.id_venta,
                 id_operador_ejecuta=esc["operador"].id_operador, motivo="prueba")
    sesion.commit()

    nota, creada = emitir_nota_credito(sesion, id_venta=venta.id_venta)
    assert creada is True
    assert nota.tipo == "nota_credito"
    assert nota.id_factura_referida == factura.id_factura_simulada
    assert Decimal(nota.total) == -Decimal(factura.total)  # revierte

    sesion.refresh(factura)
    assert factura.estado == "anulada"

    # Idempotente.
    nota2, c2 = emitir_nota_credito(sesion, id_venta=venta.id_venta)
    assert c2 is False and nota2.id_factura_simulada == nota.id_factura_simulada


def test_anular_venta_sin_factura_no_genera_nota(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=1, cantidad_gramos=None)])
    anular_venta(sesion, id_venta=venta.id_venta,
                 id_operador_ejecuta=esc["operador"].id_operador, motivo=None)
    sesion.commit()

    nota, creada = emitir_nota_credito(sesion, id_venta=venta.id_venta)
    assert nota is None and creada is False


def test_nota_de_credito_de_venta_no_anulada_da_409(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=1, cantidad_gramos=None)])
    sesion.commit()
    with pytest.raises(VentaNoAnulada):
        emitir_nota_credito(sesion, id_venta=venta.id_venta)


def test_obtener_facturas_de_venta(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=10,
                      costo_unitario=Decimal("1.0000"))
    venta = _cobrar(sesion, esc, [RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                 cantidad_unidades=1, cantidad_gramos=None)])
    sesion.commit()

    antes = obtener_facturas_de_venta(sesion, id_venta=venta.id_venta)
    assert antes["factura"] is None and antes["nota_credito"] is None

    generar_factura(sesion, id_venta=venta.id_venta)
    despues = obtener_facturas_de_venta(sesion, id_venta=venta.id_venta)
    assert despues["factura"] is not None
