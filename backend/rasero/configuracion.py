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

# Facturación electrónica SIMULADA (009-facturacion-electronica). Ningún literal de la razón
# social/RUC reales en código: todo por entorno, con un valor de demostración por defecto (mismo
# patrón que VITE_LOGO_COMERCIO). La factura NO tiene validez tributaria — sin SRI, sin firma.
RUC_COMERCIO = os.environ.get("RUC_COMERCIO", "9999999999001")
RAZON_SOCIAL_COMERCIO = os.environ.get("RAZON_SOCIAL_COMERCIO", "Comercio de Demostración")
DIRECCION_COMERCIO = os.environ.get("DIRECCION_COMERCIO", "")
TARIFA_IVA = os.environ.get("TARIFA_IVA", "0.15")
ESTABLECIMIENTO_SRI = os.environ.get("ESTABLECIMIENTO_SRI", "001")
PUNTO_EMISION_SRI = os.environ.get("PUNTO_EMISION_SRI", "001")
