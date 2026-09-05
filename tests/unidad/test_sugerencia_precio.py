"""T026 — algoritmo de sugerencia de precio (Lectura Crítica n.º 2 de la constitución,
research.md #5 de 003). Función pura, sin base de datos.
"""

from decimal import Decimal

from rasero.dominio.sugerencias import normalizar_precio_observado, sugerir_precio


def test_gancho_de_trafico_iguala_o_baja_a_competencia():
    precio = sugerir_precio(
        precio_vigente=Decimal("10.0000"),
        costo_vigente=Decimal("5.0000"),
        rol="gancho_trafico",
        observacion_normalizada=Decimal("8.0000"),
    )
    assert precio == Decimal("8.0000")


def test_gancho_de_trafico_nunca_baja_del_costo_vigente():
    precio = sugerir_precio(
        precio_vigente=Decimal("10.0000"),
        costo_vigente=Decimal("6.0000"),
        rol="gancho_trafico",
        observacion_normalizada=Decimal("4.0000"),  # por debajo del costo
    )
    assert precio == Decimal("6.0000"), "nunca sugiere vender a pérdida"


def test_gancho_de_trafico_sin_costo_conocido_no_aplica_piso():
    precio = sugerir_precio(
        precio_vigente=Decimal("10.0000"),
        costo_vigente=None,
        rol="gancho_trafico",
        observacion_normalizada=Decimal("4.0000"),
    )
    assert precio == Decimal("4.0000")


def test_generador_de_margen_sube_hasta_competencia_si_estaba_por_debajo():
    precio = sugerir_precio(
        precio_vigente=Decimal("7.0000"),
        costo_vigente=Decimal("2.0000"),
        rol="generador_margen",
        observacion_normalizada=Decimal("9.0000"),
    )
    assert precio == Decimal("9.0000")


def test_generador_de_margen_no_baja_para_igualar_competencia():
    precio = sugerir_precio(
        precio_vigente=Decimal("10.0000"),
        costo_vigente=Decimal("2.0000"),
        rol="generador_margen",
        observacion_normalizada=Decimal("8.0000"),  # por debajo del vigente
    )
    assert precio == Decimal("10.0000")


def test_cualquier_rol_sin_observacion_mantiene_el_precio_vigente():
    for rol in ("gancho_trafico", "generador_margen"):
        precio = sugerir_precio(
            precio_vigente=Decimal("10.0000"), costo_vigente=Decimal("5.0000"), rol=rol, observacion_normalizada=None
        )
        assert precio == Decimal("10.0000")


def test_sin_rol_asignado_mantiene_el_precio_vigente_sin_ajuste():
    precio = sugerir_precio(
        precio_vigente=Decimal("10.0000"),
        costo_vigente=Decimal("5.0000"),
        rol=None,
        observacion_normalizada=Decimal("3.0000"),
    )
    assert precio == Decimal("10.0000"), "FR-007: sin clasificar, no se aplica ninguna dirección"


def test_normalizar_observacion_por_unidad():
    precio = normalizar_precio_observado(
        precio_observado=Decimal("5.00"), presentacion_cantidad=Decimal("2"), presentacion_unidad="unidad", comparable=True
    )
    assert precio == Decimal("2.50")


def test_normalizar_observacion_por_gramo_a_kilogramo():
    precio = normalizar_precio_observado(
        precio_observado=Decimal("2.00"),
        presentacion_cantidad=Decimal("500"),
        presentacion_unidad="gramo",
        comparable=True,
    )
    assert precio == Decimal("4.00")  # 500g a $2 => $4/kg


def test_normalizar_observacion_no_comparable_devuelve_none():
    precio = normalizar_precio_observado(
        precio_observado=Decimal("5.00"), presentacion_cantidad=Decimal("1"), presentacion_unidad="unidad", comparable=False
    )
    assert precio is None


def test_normalizar_observacion_en_mililitros_no_es_comparable_a_este_dominio():
    precio = normalizar_precio_observado(
        precio_observado=Decimal("3.00"),
        presentacion_cantidad=Decimal("750"),
        presentacion_unidad="mililitro",
        comparable=True,
    )
    assert precio is None
