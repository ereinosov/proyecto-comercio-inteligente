"""Parámetros de configuración de la comparación de precios de competencia
(001-core-ventas-inventario, User Story 4) — UN ÚNICO lugar de verdad.

Calibración DENTRO de la decisión ya fijada (FR-002 de US4: la antigüedad de una observación se
comunica con tres portadores simultáneos —color, forma, texto— y "un precio de hace dos semanas
no pesa como uno de hoy"). Ajustar estos umbrales aquí no reabre esa decisión. El valor de
arranque y su justificación viven en `specs/001-core-ventas-inventario/research.md` §12.

Se pueden sobrescribir por variable de entorno, mismo patrón que `config/pronostico.py` de 004,
`config/promociones.py` de 005 y `config/caja.py` de 006.

`indicador_forma` es presentación pura: no entra en ningún cálculo ni decisión del sistema
(FR-028: el sistema no ajusta ningún precio).
"""

import os

# research.md §12 — una observación con antigüedad <= este número de días se muestra "lleno"
# (reciente). Una semana: el dato todavía refleja el precio de estos días.
ANTIGUEDAD_LLENO_DIAS: int = int(os.environ.get("COMPETENCIA_ANTIGUEDAD_LLENO_DIAS", "7"))

# research.md §12 — por encima de este número de días la observación se muestra "hueco" (vieja);
# entre LLENO y este valor, "medio". 21 días deja "hace dos semanas" (14 d) ya fuera de "lleno"
# y todavía en "medio", coherente con FR-002 de US4.
ANTIGUEDAD_HUECO_DIAS: int = int(os.environ.get("COMPETENCIA_ANTIGUEDAD_HUECO_DIAS", "21"))
