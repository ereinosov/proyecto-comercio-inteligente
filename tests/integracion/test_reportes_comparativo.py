"""US1 de 008 — comparativo entre sucursales. Valores == agregado a mano de 001/003/006;
diferencia relativa contra la mejor; una sola sucursal → `comparable=false`; caché + Actualizar.

008 es solo lectura: los conteos de `venta`/`renglon_venta`/`merma` no cambian al pedir el
comparativo.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import AgregadoReporte, Merma, RenglonVenta, Venta
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.margenes import listar_margenes_sucursal
from rasero.servicios.mermas import clasificar_merma
from rasero.servicios.reportes_comparativo import armar_indicadores, comparativo
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _vender(sesion, escenario, unidades: int, n: int):
    for _ in range(n):
        registrar_venta(
            sesion,
            clave_idempotencia=f"cmp-{uuid.uuid4()}",
            id_turno=escenario["turno"].id_turno,
            referencia_terminal_pago=None,
            instante_origen=datetime.now(timezone.utc),
            renglones=[
                RenglonEntrada(
                    id_producto=escenario["producto"].id_producto,
                    cantidad_unidades=unidades,
                    cantidad_gramos=None,
                )
            ],
        )


def test_comparativo_valores_y_diferencia_relativa(sesion):
    hoy = date.today()
    ini = hoy.replace(day=1)

    a = crear_escenario_basico(sesion, existencia_inicial=0)  # producto 2.50, costo 1.00
    b = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=a["sucursal"].id_sucursal, id_producto=a["producto"].id_producto,
                      cantidad=1000, costo_unitario=Decimal("1.0000"))
    registrar_entrada(sesion, id_sucursal=b["sucursal"].id_sucursal, id_producto=b["producto"].id_producto,
                      cantidad=1000, costo_unitario=Decimal("2.0000"))  # margen peor en B

    _vender(sesion, a, unidades=2, n=5)   # A: 10 tickets-unidad, 5 tickets, ventas 25.00
    _vender(sesion, b, unidades=1, n=3)   # B: 3 tickets, ventas 7.50

    # 003 calcula y cachea el margen de cada sucursal (uso de la pantalla de Precios). 008 luego
    # sólo LEE `margen_calculado`, no dispara este recálculo.
    listar_margenes_sucursal(sesion, id_sucursal=a["sucursal"].id_sucursal)
    listar_margenes_sucursal(sesion, id_sucursal=b["sucursal"].id_sucursal)

    # Una merma valorada en B (para que su celda de merma tenga valor).
    clasificar_merma(sesion, id_producto=b["producto"].id_producto, id_sucursal=b["sucursal"].id_sucursal,
                     cantidad_faltante=3, causa="dano", id_operador_registro=b["operador"].id_operador)
    sesion.commit()

    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar_one()
    mermas_antes = sesion.execute(select(func.count()).select_from(Merma)).scalar_one()

    # `actualizar=True`: la base de pruebas es compartida y otro test pudo cachear este período.
    r = comparativo(sesion, periodo_inicio=ini, periodo_fin=hoy, actualizar=True)

    assert r["comparable"] is True
    ids = {s["id_sucursal"] for s in r["sucursales"]}
    assert {a["sucursal"].id_sucursal, b["sucursal"].id_sucursal} <= ids

    def celda(clave, id_suc):
        fila = next(f for f in r["indicadores"] if f["clave"] == clave)
        return next(c for c in fila["celdas"] if c["id_sucursal"] == id_suc)

    # Valores por sucursal == agregado a mano (SC-002). El comparativo es GLOBAL (todas las
    # sucursales de la base de pruebas), así que sólo se comprueban las celdas de A y B, no cuál
    # es la "mejor" del grupo — la lógica de atención/diferencia se prueba, determinista, en
    # `test_armar_indicadores_marca_atencion_solo_en_el_peor`.
    assert celda("ventas", a["sucursal"].id_sucursal)["valor"] == "25.00"
    assert celda("ventas", b["sucursal"].id_sucursal)["valor"] == "7.50"
    assert celda("tickets", a["sucursal"].id_sucursal)["valor"] == "5"
    assert celda("ticket_promedio", a["sucursal"].id_sucursal)["valor"] == "5.00"

    # Margen: A ≈ (2.50-1.00)/2.50 = 0.60 → "60.0%"; B ≈ (2.50-2.00)/2.50 = 0.20 → "20.0%".
    assert celda("margen_ponderado", a["sucursal"].id_sucursal)["valor"] == "60.0%"
    assert celda("margen_ponderado", b["sucursal"].id_sucursal)["valor"] == "20.0%"
    assert celda("merma_valorada", b["sucursal"].id_sucursal)["valor"] is not None
    assert celda("merma_valorada", a["sucursal"].id_sucursal)["sin_datos"] is True

    # Solo lectura: 008 no tocó 001/006.
    assert sesion.execute(select(func.count()).select_from(Venta)).scalar_one() == ventas_antes
    assert sesion.execute(select(func.count()).select_from(Merma)).scalar_one() == mermas_antes
    assert sesion.execute(select(func.count()).select_from(RenglonVenta)).scalar_one() > 0


def test_una_sola_sucursal_no_es_comparable():
    """FR-008: con una sola sucursal visible, `comparable` es False y ninguna celda lleva
    `diferencia_relativa`. Se prueba sobre `armar_indicadores` (función pura) porque el
    comparativo real es global y la base de pruebas compartida tiene decenas de sucursales.
    """
    una = [{
        "id_sucursal": 1, "nombre": "Única", "activa": True,
        "metricas": {
            "ventas": Decimal("100"), "tickets": Decimal("10"),
            "ticket_promedio": Decimal("10"), "margen_ponderado": Decimal("0.2"),
            "merma_valorada": Decimal("5"), "diferencia_arqueo": Decimal("-1"),
        },
    }]
    comparable, filas = armar_indicadores(una)
    assert comparable is False
    for fila in filas:
        for celda in fila["celdas"]:
            assert celda["diferencia_relativa"] is None
            assert celda["atencion"] is False


def test_armar_indicadores_marca_atencion_solo_en_el_peor():
    dos = [
        {"id_sucursal": 1, "nombre": "Mejor", "activa": True, "metricas": {
            "ventas": Decimal("100"), "tickets": Decimal("10"), "ticket_promedio": Decimal("10"),
            "margen_ponderado": Decimal("0.25"), "merma_valorada": Decimal("2"),
            "diferencia_arqueo": Decimal("0"),
        }},
        {"id_sucursal": 2, "nombre": "Peor", "activa": True, "metricas": {
            "ventas": Decimal("60"), "tickets": Decimal("8"), "ticket_promedio": Decimal("7.5"),
            "margen_ponderado": Decimal("0.18"), "merma_valorada": Decimal("9"),
            "diferencia_arqueo": Decimal("-4"),
        }},
    ]
    comparable, filas = armar_indicadores(dos)
    assert comparable is True

    def celda(clave, id_suc):
        return next(c for f in filas if f["clave"] == clave for c in f["celdas"] if c["id_sucursal"] == id_suc)

    assert celda("margen_ponderado", 2)["atencion"] is True
    assert "pp vs. Mejor" in celda("margen_ponderado", 2)["diferencia_relativa"]
    assert celda("margen_ponderado", 1)["atencion"] is False
    assert celda("merma_valorada", 2)["atencion"] is True   # más merma = peor
    assert celda("merma_valorada", 1)["atencion"] is False


def test_cache_y_actualizar(sesion):
    hoy = date.today()
    a = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=a["sucursal"].id_sucursal, id_producto=a["producto"].id_producto,
                      cantidad=100, costo_unitario=Decimal("1.0000"))
    _vender(sesion, a, unidades=1, n=1)
    sesion.commit()

    ini = hoy.replace(day=1)
    r1 = comparativo(sesion, periodo_inicio=ini, periodo_fin=hoy)
    r2 = comparativo(sesion, periodo_inicio=ini, periodo_fin=hoy)  # de caché
    assert r1["instante_calculo"] == r2["instante_calculo"]

    filas = sesion.execute(
        select(func.count()).select_from(AgregadoReporte).where(AgregadoReporte.tipo == "comparativo")
    ).scalar_one()
    assert filas == 1  # una sola entrada de caché para esa clave

    r3 = comparativo(sesion, periodo_inicio=ini, periodo_fin=hoy, actualizar=True)
    assert r3["instante_calculo"] != r1["instante_calculo"]
