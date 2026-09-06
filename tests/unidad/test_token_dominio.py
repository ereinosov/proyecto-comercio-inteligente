"""Suite obligatoria 1 — unidad (007, US3 — T028). El PAN nunca se persiste ni se expone.

- `generar_token`: opaco, sin relación con la entrada, sin estabilidad entre llamadas.
- `extraer_metadato`: últimos 4 + marca por BIN; NO devuelve el número.
- `detectar_pan` / `es_luhn_valido`: barrera de FR-018.
"""

import re

from rasero.config import pagos as cfg
from rasero.dominio.token import (
    detectar_pan,
    es_luhn_valido,
    extraer_metadato,
    generar_token,
)

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_token_es_uuid_v4_opaco_y_sin_estabilidad():
    t1 = generar_token()
    t2 = generar_token()
    assert _UUID.match(t1)
    assert t1 != t2  # dos llamadas -> dos tokens (sin estabilidad entre ventas)


def test_es_luhn_valido():
    assert es_luhn_valido("4111111111111111") is True
    assert es_luhn_valido("5555555555554444") is True
    assert es_luhn_valido("4111111111111112") is False  # dígito de control roto
    assert es_luhn_valido("123") is False  # muy corto
    assert es_luhn_valido("1" * 25) is False  # muy largo


def test_extraer_metadato_no_devuelve_el_numero():
    ultimos, marca = extraer_metadato("4111111111111111", cfg.BIN_MARCA, digitos_conservados=4)
    assert ultimos == "1111"
    assert marca == "visa"
    ultimos, marca = extraer_metadato("5555555555554444", cfg.BIN_MARCA)
    assert (ultimos, marca) == ("4444", "mastercard")
    ultimos, marca = extraer_metadato("378282246310005", cfg.BIN_MARCA)
    assert (ultimos, marca) == ("0005", "amex")
    # BIN no mapeado -> "otra"
    _, marca = extraer_metadato("9999888877776666", cfg.BIN_MARCA)
    assert marca == "otra"


def test_detectar_pan_encuentra_secuencias_que_pasan_luhn_sin_devolverlas():
    assert detectar_pan("pago con 4111111111111111 aprobado") is True
    assert detectar_pan("tipo=credito nota=ok") is False
    assert detectar_pan("ref 1234") is False
    assert detectar_pan(None) is False
    # el valor devuelto es un bool, nunca el número
    assert detectar_pan("4111111111111111") is True
