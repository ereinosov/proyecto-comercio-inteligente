"""Validación de cédula / RUC de persona natural (dominio puro, FR-017 de
002-clientes-fidelizacion, User Story 4). Sin base de datos.
"""

import pytest

from rasero.dominio.identidad_cliente import (
    validar_cedula_ecuatoriana,
    validar_identificador,
)

CEDULAS_VALIDAS = [
    "1714035209",
    "0912345675",
    "0123456782",  # provincia 01
    "2410090878",  # provincia 24
    "3001122336",  # provincia 30 (ecuatorianos en el exterior / extranjeros residentes)
]


@pytest.mark.parametrize("cedula", CEDULAS_VALIDAS)
def test_cedula_valida_se_acepta(cedula):
    assert validar_cedula_ecuatoriana(cedula) is True


@pytest.mark.parametrize(
    "cedula",
    [
        "1714035200",  # dígito verificador incorrecto
        "0012345675",  # provincia 00 inexistente
        "2510090878",  # provincia 25 inexistente (y != 30)
        "1764035209",  # tercer dígito 6 (sociedad, fuera de alcance)
        "171403520",  # 9 dígitos
        "17140352099",  # 11 dígitos
        "17140352AB",  # no numérico
        "",
    ],
)
def test_cedula_invalida_se_rechaza(cedula):
    assert validar_cedula_ecuatoriana(cedula) is False


def test_identificador_acepta_cedula_de_10_digitos():
    assert validar_identificador("1714035209") is True


def test_identificador_acepta_ruc_natural_valido():
    assert validar_identificador("1714035209001") is True


def test_identificador_rechaza_ruc_que_no_termina_en_001():
    assert validar_identificador("1714035209002") is False


def test_identificador_rechaza_ruc_con_primeros_10_digitos_invalidos():
    assert validar_identificador("1714035200001") is False


@pytest.mark.parametrize("valor", ["", "123", "abc", "17140352090010", "  "])
def test_identificador_rechaza_lo_demas(valor):
    assert validar_identificador(valor) is False
