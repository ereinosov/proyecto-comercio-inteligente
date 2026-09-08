"""Cálculo de la factura simulada (009-facturacion-electronica). Funciones puras.

**IVA incluido en el precio** (research §6): `total == venta.total` de 001 (lo que el cliente
pagó), y el `subtotal` se descompone hacia atrás. Así 009 no cambia lo que paga el cliente ni el
cobro de 001. Redondeo medio hacia arriba (mismo criterio que `dominio/totales` de 001), y
`monto_iva = total - subtotal` para que no se pierda un céntimo por redondeo.
"""

from decimal import ROUND_HALF_UP, Decimal

_DOS = Decimal("0.01")


def descomponer_iva(total: Decimal, tarifa: Decimal) -> tuple[Decimal, Decimal]:
    """(subtotal, monto_iva) con el IVA YA INCLUIDO en `total`. `subtotal + monto_iva == total`."""
    total = Decimal(total).quantize(_DOS, rounding=ROUND_HALF_UP)
    subtotal = (total / (Decimal(1) + Decimal(tarifa))).quantize(_DOS, rounding=ROUND_HALF_UP)
    monto_iva = total - subtotal
    return subtotal, monto_iva


def formatear_secuencial(establecimiento: str, punto: str, numero: int) -> str:
    """`EEE-PPP-NNNNNNNNN` (3-3-9 dígitos con ceros a la izquierda)."""
    est = str(establecimiento).zfill(3)[-3:]
    pto = str(punto).zfill(3)[-3:]
    return f"{est}-{pto}-{numero:09d}"
