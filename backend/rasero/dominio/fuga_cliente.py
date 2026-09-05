"""Umbrales de fuga silenciosa (FR-008, FR-014, FR-015 de 002-clientes-fidelizacion). Función
pura: clasifica el estado a partir del propio intervalo esperado del cliente y del tiempo
transcurrido desde su última visita — nunca un umbral compartido con otros clientes (constitución,
Lectura Crítica n.º 5).

Nota de implementación: el plan (tasks.md, T030) esbozaba un parámetro
`instante_deteccion_previo`. Al implementar se simplificó a `ahora` (reloj inyectado, para que
la función siga siendo pura y comprobable con un instante fijo): el `instante_deteccion` de una
señal ya abierta es dato propio de la fila `senal_fuga` existente, que el servicio ya tiene y no
necesita recalcular aquí; lo único que esta función necesita producir de nuevo es el instante de
confirmación y la purga programada, y para eso basta con el reloj actual, no con el anterior.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

MULTIPLICADOR_CONFIRMACION = 5
PISO_DIAS_CONFIRMACION = 365  # 12 meses (research.md #FR-014: un ciclo estacional completo)
DIAS_RETENCION_TRAS_CONFIRMACION = 90


@dataclass
class ResultadoFuga:
    estado: str  # "sin_senal" | "activa" | "confirmada"
    instante_purga_programada: datetime | None  # solo si estado == "confirmada"


def evaluar_estado_fuga(
    *, intervalo_esperado_dias: Decimal, dias_sin_visita: float, ahora: datetime
) -> ResultadoFuga:
    """FR-008: `dias_sin_visita >= intervalo_esperado_dias` (1×) -> `activa`.
    FR-014: `dias_sin_visita >= max(5 × intervalo_esperado_dias, 365)` -> `confirmada`, con
    `instante_purga_programada = ahora + 90 días`.
    """
    umbral_activa = float(intervalo_esperado_dias)
    umbral_confirmada = max(umbral_activa * MULTIPLICADOR_CONFIRMACION, PISO_DIAS_CONFIRMACION)

    if dias_sin_visita < umbral_activa:
        return ResultadoFuga(estado="sin_senal", instante_purga_programada=None)

    if dias_sin_visita >= umbral_confirmada:
        return ResultadoFuga(
            estado="confirmada",
            instante_purga_programada=ahora + timedelta(days=DIAS_RETENCION_TRAS_CONFIRMACION),
        )

    return ResultadoFuga(estado="activa", instante_purga_programada=None)
