"""Parámetros de configuración de 005-promociones-inteligentes — UN ÚNICO lugar de verdad (T003).

Todos son parámetros de **calibración** dentro de las decisiones ya fijadas (reserva de precio no
de inventario — FR-010; umbral estadístico por prueba z de dos proporciones, p < 0,05 — FR-021;
aleatorización real con semilla fija — FR-016): ajustarlos aquí no reabre esas decisiones. Los
valores de arranque y su justificación viven en `research.md` (#6, #7, #9, #10b, #11, #13).
Ninguna de estas constantes debe reaparecer incrustada en otro archivo — el Principio V
("acotada": los límites del modelo se documentan) exige que estén todas juntas y nombradas.

Se pueden sobrescribir por variable de entorno (mismo patrón que `config/pronostico.py` de 004).
"""

import os
from decimal import Decimal

# --- Mecanismo 1: cupón por fecha fija (cumpleaños) — research.md #6 ---

# El cupón se genera con antelación a la fecha de cumpleaños (no el día exacto): tiempo para que
# el cliente lo vea y planee una visita.
ANTELACION_GENERACION_CUPON_DIAS: int = int(
    os.environ.get("PROMO_ANTELACION_GENERACION_CUPON_DIAS", "7")
)
# Ventana de validez total del cupón: una semana antes + una semana después del cumpleaños.
VALIDEZ_CUPON_DIAS: int = int(os.environ.get("PROMO_VALIDEZ_CUPON_DIAS", "14"))
# Valor del cupón. Parámetro de negocio; se ajusta con datos reales.
DESCUENTO_CUPON_CUMPLEANOS_PCT: Decimal = Decimal(
    os.environ.get("PROMO_DESCUENTO_CUPON_CUMPLEANOS_PCT", "10.00")
)

# --- Mecanismo 2: empuje por recompra con reserva de precio — research.md #7 ---

# La oferta se emite cuando el cliente lleva >= (1 - margen) de su intervalo esperado sin comprar:
# suficientemente cerca de la recompra, con margen para que el código llegue antes.
MARGEN_ANTICIPACION_RECOMPRA: Decimal = Decimal(
    os.environ.get("PROMO_MARGEN_ANTICIPACION_RECOMPRA", "0.20")
)
# Historial identificado que se mira para elegir el producto que el cliente "suele recomprar".
VENTANA_HISTORIAL_RECOMPRA_DIAS: int = int(
    os.environ.get("PROMO_VENTANA_HISTORIAL_RECOMPRA_DIAS", "180")
)
# Mínimo de compras del mismo producto en la ventana para hablar de "patrón" (mismo umbral que
# las 3 visitas de 002 para pasar de datos_insuficientes a calculado).
MIN_COMPRAS_PRODUCTO_RECOMPRA: int = int(os.environ.get("PROMO_MIN_COMPRAS_PRODUCTO_RECOMPRA", "3"))
# Descuento de la reserva de precio.
DESCUENTO_RECOMPRA_PCT: Decimal = Decimal(os.environ.get("PROMO_DESCUENTO_RECOMPRA_PCT", "8.00"))
# Vigencia de la reserva de precio.
VENTANA_RESERVA_RECOMPRA_DIAS: int = int(
    os.environ.get("PROMO_VENTANA_RESERVA_RECOMPRA_DIAS", "21")
)

# --- Mecanismo 3: reactivación con experimento de control — research.md #9, #10b, #11 ---

# Semilla de `random.Random` (Mersenne Twister). Existe SÓLO para reproducibilidad de la
# demostración: mismos datos + misma semilla -> mismos grupos. No convierte la asignación en
# no-aleatoria (research.md #9).
SEMILLA_ALEATORIZACION: int = int(os.environ.get("PROMO_SEMILLA_ALEATORIZACION", "20260905"))
# Reparto tratamiento/control. 50/50 maximiza el poder de la prueba z para un total dado.
PROPORCION_TRATAMIENTO: Decimal = Decimal(os.environ.get("PROMO_PROPORCION_TRATAMIENTO", "0.500"))
# Nivel de significancia de la prueba z de dos proporciones (FR-021). Dos colas.
ALFA_SIGNIFICANCIA: Decimal = Decimal(os.environ.get("PROMO_ALFA_SIGNIFICANCIA", "0.050"))
# Poder objetivo del cálculo del tamaño mínimo de muestra.
PODER_ESTADISTICO: Decimal = Decimal(os.environ.get("PROMO_PODER_ESTADISTICO", "0.800"))
# p_c: tasa a la que se estima que un cliente con senal_fuga activa vuelve SOLO, sin incentivo.
# Valor de planificación; se re-estima con la tasa real del control tras el primer experimento.
TASA_RETORNO_BASE_ESPERADA: Decimal = Decimal(
    os.environ.get("PROMO_TASA_RETORNO_BASE_ESPERADA", "0.15")
)
# MDE: efecto mínimo (en puntos porcentuales) que haría que valga la pena gastar el margen.
# Parámetro de negocio; determina el tamaño mínimo de muestra.
MDE_REACTIVACION_PP: Decimal = Decimal(os.environ.get("PROMO_MDE_REACTIVACION_PP", "15"))
# Descuento ofrecido SÓLO al grupo tratamiento.
DESCUENTO_REACTIVACION_PCT: Decimal = Decimal(
    os.environ.get("PROMO_DESCUENTO_REACTIVACION_PCT", "15.00")
)
# Ventana de observación del retorno tras la asignación (research.md #11): ~6 semanas.
VENTANA_MEDICION_REACTIVACION_DIAS: int = int(
    os.environ.get("PROMO_VENTANA_MEDICION_REACTIVACION_DIAS", "42")
)

# Cuantiles normales para el cálculo del tamaño mínimo de muestra (research.md #10b). No dependen
# de config del usuario: son las constantes de la fórmula.
Z_ALFA_MEDIOS = Decimal("1.959964")  # cuantil de 1 - 0.05/2
Z_BETA = Decimal("0.841621")  # cuantil de 0.80

ALGORITMO_ALEATORIZACION = "random.Random / MT19937 (biblioteca estándar de Python)"
