"""Configuración de conexión. PostgreSQL nativo, puerto 5442 (constitución v2.2.0).

Nunca SQLite: prohibido en toda fase por la constitución (carece de NUMERIC real).
"""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://rasero@localhost:5442/rasero",
)

if "sqlite" in DATABASE_URL.lower():
    raise RuntimeError("SQLite está prohibido en toda fase (constitución, Restricciones Técnicas).")

UMBRAL_GLOBAL_DIAS_INMOVILIZADO = int(os.environ.get("UMBRAL_GLOBAL_DIAS_INMOVILIZADO", "90"))
