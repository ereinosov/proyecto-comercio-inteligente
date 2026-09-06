"""Funciones de dominio puras de la tokenización (007, US3 — T033).

"Tokenizar" aquí es una operación LOCAL sin pasarela (research.md #4): recibir el número de
tarjeta, extraer los últimos 4 dígitos + marca + tipo, devolver un identificador sustituto OPACO
y descartar el número. El PAN nunca se almacena, registra ni transmite (FR-017).

- `generar_token` — UUID v4 de la biblioteca estándar. NO criptográfico, NO reversible, SIN
  relación derivable con la entrada, SIN estabilidad entre ventas (dos llamadas para la misma
  tarjeta dan tokens distintos).
- `extraer_metadato` — últimos 4 dígitos + marca (por rango BIN) + tipo. NO devuelve el número.
- `es_luhn_valido`, `detectar_pan` — barreras contra FR-018: rechazar un PAN completo donde no
  corresponda. `detectar_pan` NO devuelve el número, sólo si lo encontró.
"""

import re
import uuid

_SECUENCIA_LARGA = re.compile(r"\d{13,19}")


def generar_token() -> str:
    """Identificador sustituto opaco. Aleatorio; sin relación con el PAN."""
    return str(uuid.uuid4())


def solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def es_luhn_valido(numero: str) -> bool:
    digitos = [int(d) for d in solo_digitos(numero)]
    if not (13 <= len(digitos) <= 19):
        return False
    suma = 0
    for i, d in enumerate(reversed(digitos)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        suma += d
    return suma % 10 == 0


def detectar_pan(texto: str | None) -> bool:
    """`True` si `texto` contiene una secuencia de 13–19 dígitos que pasa Luhn (un PAN). NUNCA
    devuelve el número — sólo si lo detectó (FR-018).
    """
    if not texto:
        return False
    for coincidencia in _SECUENCIA_LARGA.findall(texto):
        if es_luhn_valido(coincidencia):
            return True
    return False


def _marca_por_bin(numero_limpio: str, bin_marca: dict[str, str]) -> str:
    """Marca de la tarjeta por prefijo BIN. Prefijo no mapeado ⇒ "otra"."""
    for longitud in (4, 2, 1):
        prefijo = numero_limpio[:longitud]
        if prefijo in bin_marca:
            return bin_marca[prefijo]
    return "otra"


def extraer_metadato(
    numero_tarjeta: str, bin_marca: dict[str, str], *, digitos_conservados: int = 4
) -> tuple[str, str]:
    """`(ultimos_digitos, marca)`. NO devuelve el número. El llamador descarta `numero_tarjeta`
    inmediatamente después.
    """
    limpio = solo_digitos(numero_tarjeta)
    ultimos = limpio[-digitos_conservados:]
    return ultimos, _marca_por_bin(limpio, bin_marca)
