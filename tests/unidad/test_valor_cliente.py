"""T017 — Prueba obligatoria (Principio III): un cliente de monto alto/frecuencia baja/margen
bajo puede quedar clasificado por debajo de uno de menor monto pero mayor frecuencia y margen
(SC-002 de 002-clientes-fidelizacion). Un cliente en `datos_insuficientes` no participa con un
valor por defecto: no entra a esta función en absoluto (ver docstring de AgregadoCliente); la
exclusión real ocurre en servicios/clientes.py (T019), verificada en la prueba de contrato/
quickstart de extremo a extremo, no aquí a nivel de función pura.
"""

from decimal import Decimal

from rasero.dominio.valor_cliente import AgregadoCliente, calcular_percentiles_y_compuesto


def test_monto_alto_frecuencia_y_margen_bajos_puede_quedar_por_debajo_de_otro_cliente():
    cliente_a = AgregadoCliente(  # compra grande y esporádica, de bajo margen
        id_cliente=1,
        intervalo_esperado_dias=Decimal("60"),
        monto_total=Decimal("1000.00"),
        margen_ponderado=Decimal("0.05"),
    )
    cliente_b = AgregadoCliente(  # compras frecuentes y de alto margen, menor monto total
        id_cliente=2,
        intervalo_esperado_dias=Decimal("7"),
        monto_total=Decimal("200.00"),
        margen_ponderado=Decimal("0.40"),
    )

    resultados = calcular_percentiles_y_compuesto([cliente_a, cliente_b])
    por_id = {r.id_cliente: r for r in resultados}

    assert por_id[1].percentil_monto > por_id[2].percentil_monto, (
        "A debe ganar en monto: es el punto de partida del caso (un ranking por monto simple "
        "lo pondría primero)"
    )
    assert por_id[2].percentil_frecuencia > por_id[1].percentil_frecuencia
    assert por_id[2].percentil_margen > por_id[1].percentil_margen
    assert por_id[2].compuesto > por_id[1].compuesto, (
        "El valor compuesto de B debe superar al de A: dos de tres dimensiones lo favorecen, "
        "demostrando que el valor no se basa solo en el monto acumulado (SC-002)"
    )


def test_poblacion_vacia_no_produce_ningun_resultado():
    """Si no hay clientes con historial suficiente, la función no inventa nada: lista vacía,
    nunca un valor por defecto.
    """
    assert calcular_percentiles_y_compuesto([]) == []


def test_un_unico_cliente_en_la_poblacion_recibe_percentil_neutro():
    """Sin otro cliente contra quien compararse, el percentil no puede ser 0 ni 100 — se define
    en 50 (neutro), no en un extremo arbitrario.
    """
    unico = AgregadoCliente(
        id_cliente=1,
        intervalo_esperado_dias=Decimal("15"),
        monto_total=Decimal("300.00"),
        margen_ponderado=Decimal("0.20"),
    )

    resultado = calcular_percentiles_y_compuesto([unico])[0]

    assert resultado.percentil_frecuencia == 50.0
    assert resultado.percentil_monto == 50.0
    assert resultado.percentil_margen == 50.0
    assert resultado.compuesto == 50.0
