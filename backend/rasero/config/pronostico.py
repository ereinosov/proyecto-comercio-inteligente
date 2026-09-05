"""Parámetros de configuración de 004-pronostico-demanda — UN ÚNICO lugar de verdad (T003).

Todos son parámetros de calibración DENTRO de los métodos ya fijados por `/speckit-clarify`
(FR-009 método base de censura, FR-019 horizonte/granularidad, FR-020 suavizado exponencial):
ajustarlos aquí no reabre esas decisiones. Los valores de arranque y su justificación viven en
`research.md` (#5, #7, #8b, #8d, #10). Ninguna de estas constantes debe reaparecer incrustada en
otro archivo — el Principio V ("acotada": los límites del modelo se documentan) exige que estén
todas juntas y nombradas.

Se pueden sobrescribir por variable de entorno (mismo patrón que
`rasero.configuracion.UMBRAL_GLOBAL_DIAS_INMOVILIZADO`) para calibración sin editar código.
"""

import os
from decimal import Decimal

# research.md #5 — ventana del método base de descensura por quiebre (FR-009 a) y de la línea
# base determinista (FR-022). 30 días cubren cuatro ciclos semanales completos: el máximo capta
# el pico semanal real sin quedar a merced de un único día atípico. Más corto (7-14) es frágil;
# más largo (60-90) arrastra un nivel de demanda ya obsoleto. Coincide con el horizonte medio del
# pronóstico, así un solo número gobierna "cuánto pasado es relevante".
VENTANA_METODO_BASE_DIAS: int = int(os.environ.get("PRONOSTICO_VENTANA_METODO_BASE_DIAS", "30"))

# research.md #7 — factor del suavizado exponencial simple (FR-020). Con alfa = 0.3 el 92 % del
# pronóstico lo determina la última semana: reactivo a un cambio real de nivel en pocos días sin
# perseguir el ruido de un único día. 0.5 es demasiado nervioso para pedir stock; 0.1 tarda unas
# tres semanas en reflejar a la mitad un cambio de nivel real.
ALFA_SUAVIZADO: Decimal = Decimal(os.environ.get("PRONOSTICO_ALFA_SUAVIZADO", "0.300"))

# research.md #8b — elasticidad-precio para normalizar el eje de precio (FR-025). Unitaria (1.0)
# como supuesto neutro y EXPLÍCITO: subir el precio un 10 % reduce la demanda ~10 %. Se registra
# en cada corrección de precio (`demanda_corregida.elasticidad_usada`) para que sea auditable.
ELASTICIDAD_PRECIO: Decimal = Decimal(os.environ.get("PRONOSTICO_ELASTICIDAD_PRECIO", "1.000"))

# research.md #3 — ventana de días que se materializa por upsert en cada lectura de la serie o
# del pronóstico (recompute-on-read). El pronóstico no necesita años de historia; esto acota el
# coste de recalcular en cada consulta.
VENTANA_MATERIALIZACION_DIAS: int = int(
    os.environ.get("PRONOSTICO_VENTANA_MATERIALIZACION_DIAS", "90")
)

# research.md #10 — mínimo de períodos diarios SIN quiebre para arriesgar un pronóstico numérico
# (FR-023). Por debajo de este umbral el producto queda en estado "datos insuficientes", nunca un
# número. Media quincena de demanda observable real antes de proyectar.
MINIMO_PERIODOS_SIN_QUIEBRE: int = int(
    os.environ.get("PRONOSTICO_MINIMO_PERIODOS_SIN_QUIEBRE", "14")
)

# research.md #8d — tramos fijos del mes para la estacionalidad intramensual simple (FR-019,
# horizonte medio). No es descomposición estacional formal: sólo comparación de promedios por
# tramo. Los días 14-16 y fin/inicio de mes son donde el enunciado sitúa los picos de quincena.
TRAMOS_MES: tuple[tuple[int, int], ...] = ((1, 7), (8, 15), (16, 22), (23, 31))

# research.md #8c — días de horizonte de cada pronóstico (FR-019). Corto para reposición; medio
# para captar el patrón intramensual con los multiplicadores de tramo.
DIAS_HORIZONTE_CORTO: int = int(os.environ.get("PRONOSTICO_DIAS_HORIZONTE_CORTO", "14"))
DIAS_HORIZONTE_MEDIO: int = int(os.environ.get("PRONOSTICO_DIAS_HORIZONTE_MEDIO", "30"))

# research.md #8c — cuántos días recientes de la serie corregida se reservan para medir el error
# retrospectivo del pronóstico contra la línea base determinista (FR-022, SC-004). El suavizado se
# ajusta sobre el resto y se proyecta un paso a la vez sobre esta cola, comparando el error medio
# absoluto con el de la línea base. 14 días = una quincena de validación fuera de muestra.
VENTANA_VALIDACION_RETROSPECTIVA: int = int(
    os.environ.get("PRONOSTICO_VENTANA_VALIDACION_RETROSPECTIVA", "14")
)

# research.md #8d — mínimo de períodos históricos de un tramo del mes para confiar en su
# multiplicador de estacionalidad; por debajo se usa 1.0 (sin ajuste) y se marca como tal.
MINIMO_PERIODOS_POR_TRAMO: int = int(os.environ.get("PRONOSTICO_MINIMO_PERIODOS_POR_TRAMO", "2"))
