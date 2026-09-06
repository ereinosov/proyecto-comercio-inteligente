"""Parámetros de configuración de 006-caja-mermas-fraude — UN ÚNICO lugar de verdad (T003).

Todos son parámetros de **calibración** dentro de decisiones ya fijadas (arqueo por cierre de
turno; cruce inventario-ventas por conteo físico periódico — FR-021; línea base de los indicadores
por operador como razón sobre la mediana de pares, sin librería — research.md #16). Ajustarlos aquí
no reabre esas decisiones. Su justificación vive en `research.md` #16, NO en comentarios de código
(constitución, Principio V "acotada": los límites del modelo se documentan). Ninguna de estas
constantes debe reaparecer incrustada en otro archivo.

Se pueden sobrescribir por variable de entorno (mismo patrón que `config/pronostico.py` de 004 y
`config/promociones.py` de 005).
"""

import os
from decimal import Decimal

# Ventana de anticipación de la alerta de caducidad (FR-014). research.md #16.
VENTANA_ALERTA_CADUCIDAD_DIAS: int = int(
    os.environ.get("CAJA_VENTANA_ALERTA_CADUCIDAD_DIAS", "14")
)

# Por debajo de esta diferencia absoluta el arqueo se considera cuadrado y no genera anomalía
# (FR-003, FR-004). Arranca en 0.00: toda diferencia distinta de cero se registra. research.md #16.
TOLERANCIA_CUADRE_ARQUEO: Decimal = Decimal(
    os.environ.get("CAJA_TOLERANCIA_CUADRE_ARQUEO", "0.00")
)

# Un operador con menos ventas que este umbral en el período no entra en la mediana de pares ni
# recibe señal: su tasa es demasiado ruidosa para compararla (FR-023). research.md #16.
UMBRAL_MINIMO_VENTAS_INDICADOR: int = int(
    os.environ.get("CAJA_UMBRAL_MINIMO_VENTAS_INDICADOR", "20")
)

# Un operador se señala cuando su tasa de anulaciones es >= esta razón × la mediana de sus pares
# comparables de la misma sucursal y período (FR-018). research.md #16.
RAZON_DESVIACION_ANULACIONES: Decimal = Decimal(
    os.environ.get("CAJA_RAZON_DESVIACION_ANULACIONES", "2.0")
)

# Ídem para la concentración de renglones registrados por debajo del precio de lista (FR-019).
# research.md #16.
RAZON_DESVIACION_PRECIO_BAJO_LISTA: Decimal = Decimal(
    os.environ.get("CAJA_RAZON_DESVIACION_PRECIO_BAJO_LISTA", "2.0")
)
