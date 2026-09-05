"""Resolver de margen de una visita (research.md #2 de 002-clientes-fidelizacion, Complexity
Tracking de plan.md) — **migrado** (FR-022 de 003-precios-margenes, research.md #8 de 003) para
consumir la definición canónica de margen de `003` en vez de calcular su propia aproximación.

`resolver_margen_visita` conserva su firma y su contrato externo exactos —
`(sesion, *, id_venta) -> Decimal`, un ratio congelado en `visita.margen_relativo` en el instante
de la visita (FR-005 de 002) — solo cambió cómo obtiene el margen de cada producto vendido.

Frontera de propiedad de datos: `resolver_margen_producto` (de `003`, propietaria de
`margen_calculado`) resuelve el margen de UN producto en UNA sucursal; combinar el margen de
varios productos de una misma venta en un solo ratio de visita sigue siendo responsabilidad de
`002` (research.md #8 de 003) — la misma ponderación por monto que ya usaba la fórmula interina.
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Turno, Venta
from rasero.servicios.margenes import resolver_margen_producto

CUATRO_DECIMALES = Decimal("0.0001")

# Fallback explícito cuando 003 no puede calcular el margen de un producto (sin costo vigente
# disponible en 001, FR-003 de 003 — `resolver_margen_producto` devuelve `None`): se trata ese
# renglón como si su costo fuera cero, exactamente el mismo tratamiento que la fórmula interina ya
# documentaba para un movimiento sin lote ("ese tramo del renglón se trata como costo cero, la
# aproximación más simple"). NO se propaga un error: una venta ya cobrada y confirmada en 001 no
# puede quedar sin visita, ni con un margen inventado distinto de este piso conocido, solo porque
# un producto carece de costo registrado — ese es justamente el tipo de dato faltante que FR-003
# ya contempla como caso esperado, no como falla. Margen 1.0000 (100%) es la traducción de "costo
# cero" a la unidad de esta función (ratio), no una suposición optimista sobre ese producto.
MARGEN_SIN_COSTO_CONOCIDO = Decimal("1.0000")


def resolver_margen_visita(sesion: Session, *, id_venta: int) -> Decimal:
    """`margen_relativo` de una venta: el margen de cada renglón (resuelto por `003`), ponderado
    por su importe — `Σ(renglon.importe × margen_producto) / venta.total` —, no un promedio simple
    entre renglones (misma razón ya documentada en research.md #4 de 002: un renglón de 2 con 90%
    de margen no debe pesar igual que uno de 200 con 20%).
    """
    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise ValueError(f"La venta {id_venta} no existe.")

    if venta.total == 0:
        return Decimal("0.0000")

    turno = sesion.get(Turno, venta.id_turno)

    margen_ponderado = Decimal("0")
    for renglon in venta.renglones:
        margen_producto = resolver_margen_producto(
            sesion, id_producto=renglon.id_producto, id_sucursal=turno.id_sucursal
        )
        if margen_producto is None:
            margen_producto = MARGEN_SIN_COSTO_CONOCIDO
        margen_ponderado += renglon.importe * margen_producto

    margen = margen_ponderado / venta.total
    return margen.quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)
