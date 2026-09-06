"""Suite obligatoria 5 — unidad (007, US2 — T017). Indicadores de firmware derivados.

- `comparar_version` por tupla de enteros, sin librería de versionado.
- lista de vulnerabilidad vacía -> 0 expuestas.
- sin última versión de referencia -> "versión de referencia desconocida", NUNCA "al día" (FR-010).
"""

from datetime import date

from rasero.dominio.firmware import comparar_version, evaluar_terminal, sucursal_en_fecha


def test_comparar_version_por_tupla_de_enteros():
    assert comparar_version("3.0.1", "3.2.0") == -1
    assert comparar_version("3.2.0", "3.2.0") == 0
    assert comparar_version("3.10.0", "3.9.9") == 1  # 10 > 9, no comparación lexicográfica


def test_expuesta_y_desactualizada_con_motivo_enumerado():
    r = evaluar_terminal(
        version_firmware="3.0.1",
        modelo="P400",
        ultima_version_referencia="3.2.0",
        lista_vulnerable=[{"modelo": "P400", "version": "3.0.1", "referencia": "CVE-2025-0001"}],
    )
    assert r["desactualizada"] is True
    assert r["expuesta_a_clonacion"] is True
    assert r["referencias_vulnerabilidad"] == ["CVE-2025-0001"]


def test_lista_vulnerable_vacia_no_marca_expuesta():
    r = evaluar_terminal(
        version_firmware="3.0.1",
        modelo="P400",
        ultima_version_referencia="3.2.0",
        lista_vulnerable=[],
    )
    assert r["expuesta_a_clonacion"] is False
    assert r["desactualizada"] is True


def test_sin_version_de_referencia_nunca_al_dia():
    r = evaluar_terminal(
        version_firmware="1.4.0",
        modelo="Move5000",
        ultima_version_referencia=None,
        lista_vulnerable=[],
    )
    assert r["version_referencia_desconocida"] is True
    assert r["desactualizada"] is False  # no se asume desactualizada
    # ...pero tampoco "al día": la interfaz muestra "versión de referencia desconocida"


def test_al_dia_sin_senal():
    r = evaluar_terminal(
        version_firmware="3.2.0",
        modelo="P400",
        ultima_version_referencia="3.2.0",
        lista_vulnerable=[],
    )
    assert not r["desactualizada"]
    assert not r["expuesta_a_clonacion"]
    assert not r["version_referencia_desconocida"]


def test_sucursal_en_fecha_por_historial_de_ubicacion():
    historial = [
        {"id_sucursal": 1, "desde": "2026-01-01", "hasta": "2026-05-31"},
        {"id_sucursal": 2, "desde": "2026-06-01", "hasta": None},
    ]
    assert sucursal_en_fecha(historial, date(2026, 3, 15)) == 1
    assert sucursal_en_fecha(historial, date(2026, 7, 1)) == 2
    assert sucursal_en_fecha(historial, date(2025, 12, 1)) is None
