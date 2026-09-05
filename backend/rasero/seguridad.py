"""Hash de PIN de operador. Sin autenticación completa (FR-006): un PIN de 4 dígitos tiene
solo 10 000 combinaciones, así que un algoritmo lento tipo bcrypt no aporta frente a fuerza
bruta offline; SHA-256 con sal por operador basta para no guardarlo en claro.
"""

import hashlib
import hmac


def hashear_pin(pin: str, sal: str) -> str:
    return hashlib.sha256(f"{sal}:{pin}".encode()).hexdigest()


def verificar_pin(pin: str, sal: str, pin_hash: str) -> bool:
    return hmac.compare_digest(hashear_pin(pin, sal), pin_hash)
