"""Suite obligatoria 2 (US3, T036) — prueba z de dos proporciones y tamaño mínimo de muestra.

Cuatro casos contra valores calculados a mano (research.md #10a, #10b):
(a) incrementalidad positiva significativa -> 'efectivo'
(b) incrementalidad negativa -> nunca 'efectivo'
(c) incrementalidad positiva no significativa -> 'no_efectivo'
(d) tamano_minimo_muestra(p_c=0.15, MDE=15pp, alfa=0.05, poder=0.80) ~= 121

El valor p usa `math.erf`, no `scipy`.
"""

from decimal import Decimal

from rasero.config import promociones as cfg
from rasero.dominio.experimento import (
    prueba_z_dos_proporciones,
    tamano_minimo_muestra,
    veredicto,
)

_ALFA = Decimal("0.05")


# --- (d) tamaño mínimo de muestra ----------------------------------------------


def test_tamano_minimo_muestra_valores_de_arranque():
    n = tamano_minimo_muestra(
        p_control=Decimal("0.15"),
        mde_puntos_porcentuales=Decimal("15"),
        z_alfa_medios=cfg.Z_ALFA_MEDIOS,
        z_beta=cfg.Z_BETA,
    )
    assert n == 121  # research.md #10b: n* ~= 120.5 -> 121 por grupo (242 elegibles mínimos)


def test_tamano_minimo_muestra_baja_al_subir_el_mde():
    n_15 = tamano_minimo_muestra(
        p_control=Decimal("0.15"),
        mde_puntos_porcentuales=Decimal("15"),
        z_alfa_medios=cfg.Z_ALFA_MEDIOS,
        z_beta=cfg.Z_BETA,
    )
    n_20 = tamano_minimo_muestra(
        p_control=Decimal("0.15"),
        mde_puntos_porcentuales=Decimal("20"),
        z_alfa_medios=cfg.Z_ALFA_MEDIOS,
        z_beta=cfg.Z_BETA,
    )
    assert n_20 < n_15
    assert n_20 == 73  # research.md #10b, tabla de sensibilidad


# --- (a) incrementalidad positiva significativa -------------------------------


def test_incrementalidad_positiva_significativa_es_efectivo():
    r = prueba_z_dos_proporciones(47, 162, 24, 163)
    assert r.retorno_tratamiento == Decimal("0.2901")
    assert r.retorno_control == Decimal("0.1472")
    assert r.incrementalidad == Decimal("0.1429")
    assert abs(r.estadistico_z - Decimal("3.12")) < Decimal("0.02")
    assert r.valor_p < Decimal("0.05")
    assert veredicto(r.incrementalidad, r.valor_p, _ALFA) == "efectivo"


# --- (b) incrementalidad negativa -------------------------------------------------


def test_incrementalidad_negativa_nunca_es_efectivo():
    r = prueba_z_dos_proporciones(22, 162, 30, 163)
    assert r.incrementalidad < 0
    assert veredicto(r.incrementalidad, r.valor_p, _ALFA) == "no_efectivo"


# --- (c) incrementalidad positiva no significativa ---------------------------------


def test_incrementalidad_positiva_no_significativa_es_no_efectivo():
    r = prueba_z_dos_proporciones(30, 162, 26, 163)
    assert r.incrementalidad > 0
    assert abs(r.estadistico_z - Decimal("0.61")) < Decimal("0.03")
    assert r.valor_p >= Decimal("0.05")
    assert veredicto(r.incrementalidad, r.valor_p, _ALFA) == "no_efectivo"


def test_p_valor_es_de_dos_colas_con_z_conocido():
    # z ~= 1.96 -> p de dos colas ~= 0.05.
    r = prueba_z_dos_proporciones(100, 1000, 63, 1000)
    # (0.100 - 0.063) / sqrt(0.0815*0.9185*(2/1000)) ~= 3.02 -> p muy pequeño
    assert r.valor_p < Decimal("0.01")
