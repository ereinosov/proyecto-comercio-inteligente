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

# Token de sesión de turno (Principio VI, sub-sección "Identidad de sesión", enmienda v2.4.0;
# User Story 11). El secreto se inyecta por entorno; el valor por defecto es SÓLO para desarrollo
# local y nunca debe usarse en un despliegue real (mismo criterio que DATABASE_URL: un secreto en
# el repositorio es un defecto bloqueante, constitución "Configuración y secretos").
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "desarrollo-local-no-usar-en-produccion")
JWT_ALGORITMO = "HS256"
JWT_HORAS_EXPIRACION = int(os.environ.get("JWT_HORAS_EXPIRACION", "12"))
