"""Parámetros de configuración de 007-pagos-seguridad — UN ÚNICO lugar de verdad (T003).

Todos son **configuración de negocio o calibración** dentro de decisiones ya fijadas (tokenización
local sin pasarela; cobertura como métrica, no faltante; exposición a clonación como indicador
consultivo contra una lista que mantiene el negocio). Su justificación vive en `research.md` #10,
NO en comentarios de código (constitución, Principio V "acotada"). Ninguna de estas constantes debe
reaparecer incrustada en otro archivo.

Se pueden sobrescribir por variable de entorno (mismo patrón que `config/caja.py` de 006).
"""

import json
import os

# Catálogo base de medios de pago (research.md #10). Los cinco medios que un minimarket ecuatoriano
# maneja hoy. `requiere_terminal` = su cobro pasa por una `terminal_pago`; `admite_tokenizacion` =
# sólo esos cobros generan `token_pago`. Extensible por fila sin migración.
MEDIOS_PAGO_BASE: list[dict] = [
    {"nombre": "efectivo", "requiere_terminal": False, "admite_tokenizacion": False},
    {"nombre": "tarjeta_debito", "requiere_terminal": True, "admite_tokenizacion": True},
    {"nombre": "tarjeta_credito", "requiere_terminal": True, "admite_tokenizacion": True},
    {"nombre": "transferencia", "requiere_terminal": False, "admite_tokenizacion": False},
    {"nombre": "billetera_movil", "requiere_terminal": False, "admite_tokenizacion": False},
]

# Los últimos N dígitos que se conservan al tokenizar (research.md #10). Cuatro es el máximo que la
# constitución permite ("Datos de pago": identificadores y últimos dígitos) y el mínimo que un
# encargado necesita para conciliar un cobro con el comprobante del cliente.
DIGITOS_CONSERVADOS: int = int(os.environ.get("PAGOS_DIGITOS_CONSERVADOS", "4"))

# Retención mínima de la bitácora de auditoría (research.md #10): año fiscal en curso + anterior.
# `plan.md` puede extenderlo, no reducirlo. No se purga antes de este plazo.
RETENCION_BITACORA_ANIOS: int = int(os.environ.get("PAGOS_RETENCION_BITACORA_ANIOS", "2"))

# Última versión de firmware conocida por modelo de datáfono (research.md #3, #10). Lo puebla el
# negocio. Vacío para un modelo ⇒ "versión de referencia desconocida", nunca "al día" (FR-010).
ULTIMA_VERSION_FIRMWARE: dict[str, str] = json.loads(
    os.environ.get("PAGOS_ULTIMA_VERSION_FIRMWARE", "{}")
)

# Versiones/modelos de firmware con vulnerabilidad de clonación conocida (research.md #3, #10). Cada
# entrada: `{modelo?, version, referencia}`. Lo puebla el negocio desde boletines del fabricante o
# avisos de seguridad. Vacía ⇒ 0 terminales marcadas "expuesta a clonación" (Edge Case del spec).
LISTA_FIRMWARE_VULNERABLE: list[dict] = json.loads(
    os.environ.get("PAGOS_LISTA_FIRMWARE_VULNERABLE", "[]")
)

# Prefijos BIN → marca de tarjeta (research.md #4). Tabla estática mínima; un prefijo no mapeado
# resuelve a "otra". Sólo se usa para clasificar; el PAN se descarta tras extraer marca + últimos 4.
BIN_MARCA: dict[str, str] = json.loads(
    os.environ.get(
        "PAGOS_BIN_MARCA",
        json.dumps(
            {
                "4": "visa",
                "51": "mastercard",
                "52": "mastercard",
                "53": "mastercard",
                "54": "mastercard",
                "55": "mastercard",
                "2221": "mastercard",
                "34": "amex",
                "37": "amex",
                "36": "diners",
                "38": "diners",
                "30": "diners",
            }
        ),
    )
)
