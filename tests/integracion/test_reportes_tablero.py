"""US3 de 008 — tablero de KPIs consolidados.

Cada cifra coincide con lo que su módulo de origen reporta para el período de la tarjeta; una
tarjeta sin base declara la razón, nunca "0" (FR-016). Solo lectura.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from rasero.persistencia.modelos import Venta
from rasero.servicios.inventario import registrar_entrada
from rasero.servicios.mermas import clasificar_merma
from rasero.servicios.reportes_tablero import tablero
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _tarjeta(cuerpo, modulo):
    return next(t for t in cuerpo["tarjetas"] if t["modulo"] == modulo)


def test_tablero_tiene_una_tarjeta_por_modulo_y_periodos_propios(sesion):
    esc = crear_escenario_basico(sesion, existencia_inicial=0)
    registrar_entrada(sesion, id_sucursal=esc["sucursal"].id_sucursal,
                      id_producto=esc["producto"].id_producto, cantidad=100,
                      costo_unitario=Decimal("1.0000"))
    for _ in range(4):
        registrar_venta(sesion, clave_idempotencia=f"tbl-{uuid.uuid4()}",
                        id_turno=esc["turno"].id_turno, referencia_terminal_pago=None,
                        instante_origen=datetime.now(timezone.utc),
                        renglones=[RenglonEntrada(id_producto=esc["producto"].id_producto,
                                                  cantidad_unidades=1, cantidad_gramos=None)])
    clasificar_merma(sesion, id_producto=esc["producto"].id_producto,
                     id_sucursal=esc["sucursal"].id_sucursal, cantidad_faltante=2, causa="dano",
                     id_operador_registro=esc["operador"].id_operador)
    sesion.commit()

    ventas_antes = sesion.execute(select(func.count()).select_from(Venta)).scalar_one()

    r = tablero(sesion, actualizar=True)
    modulos = {t["modulo"] for t in r["tarjetas"]}
    assert {"ventas", "margenes", "inventario", "mermas", "fraude", "pagos", "promociones", "clientes"} <= modulos

    for t in r["tarjetas"]:
        assert t["periodo_referencia"], "cada tarjeta declara su período de referencia"
        if t["sin_datos"]:
            assert t["razon"], "una tarjeta sin datos declara la razón"
            assert all("0" != c["valor"] for c in t["cifras"]) or not t["cifras"]

    # El tablero es GLOBAL (todas las sucursales de la base compartida): sembramos 4 ventas y 1
    # merma esta semana/mes, así que esas tarjetas NO pueden estar "sin datos", y el nº de
    # tickets es al menos 4.
    tv = _tarjeta(r, "ventas")
    assert tv["sin_datos"] is False
    tickets = next(int(c["valor"]) for c in tv["cifras"] if c["etiqueta"] == "Tickets")
    assert tickets >= 4
    assert _tarjeta(r, "mermas")["sin_datos"] is False

    # Solo lectura: 008 no creó ventas.
    assert sesion.execute(select(func.count()).select_from(Venta)).scalar_one() == ventas_antes


def test_valor_de_inventario_convierte_granel_de_gramos_a_kg(sesion):
    """Regresión #3 de la auditoría: `Existencia.cantidad` de un granel está en gramos y
    `Lote.costo_unitario` es por kg. El "Valor de inventario" del tablero debe dividir entre
    1000 (SQL `CASE`), no sumar gramos × costo/kg en crudo — el bug inflaba la cifra ×1000.
    """

    def valor_inv() -> Decimal:
        r = tablero(sesion, actualizar=True)
        card = _tarjeta(r, "inventario")
        return Decimal(
            next(c["valor"] for c in card["cifras"] if c["etiqueta"] == "Valor de inventario")
        )

    antes = valor_inv()
    esc = crear_escenario_basico(sesion, existencia_inicial=0, es_granel=True)
    registrar_entrada(
        sesion,
        id_sucursal=esc["sucursal"].id_sucursal,
        id_producto=esc["producto"].id_producto,
        cantidad=50_000,  # 50 kg
        costo_unitario=Decimal("2.0000"),  # -> 100.00, no 100 000.00
    )
    sesion.commit()

    delta = valor_inv() - antes
    assert Decimal("95") <= delta <= Decimal("105"), (
        f"delta={delta}; el bug de unidades daría ~100 000"
    )


def test_tarjeta_sin_base_declara_razon_no_cero(sesion):
    # No sembramos nada nuevo relevante; sólo comprobamos la forma de las tarjetas "sin datos".
    r = tablero(sesion, actualizar=True)
    prom = _tarjeta(r, "promociones")
    if prom["sin_datos"]:
        assert "experimento" in prom["razon"].lower()
        assert prom["cifras"] == []
