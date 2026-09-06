"""Funciones de dominio puras de la vigilancia de firmware (007, US2 — T019).

Los indicadores "desactualizada" / "expuesta a clonación" / "versión de referencia desconocida"
son cálculo DERIVADO al leer (research.md #3): no hay tabla de indicadores. La comparación de
versiones es aritmética de una línea (tupla de enteros), SIN librería de versionado.

El sistema NUNCA deshabilita una terminal a partir de estas señales (FR-012, Principio V; Principio
II: la caja no se bloquea). Son consultivas.
"""

from datetime import date


def comparar_version(a: str, b: str) -> int:
    """-1 si `a < b`, 0 si iguales, 1 si `a > b`. Versiones `major.minor.patch`."""
    ta = tuple(int(x) for x in a.split("."))
    tb = tuple(int(x) for x in b.split("."))
    return (ta > tb) - (ta < tb)


def _en_lista_vulnerable(
    modelo: str, version: str, lista: list[dict]
) -> list[str]:
    """Referencias (CVE, boletín, nota interna) que aplican a esta terminal. Vacío si ninguna."""
    referencias: list[str] = []
    for entrada in lista:
        modelo_entrada = entrada.get("modelo")
        version_entrada = entrada.get("version")
        coincide_modelo = modelo_entrada is None or modelo_entrada == modelo
        coincide_version = version_entrada is None or version_entrada == version
        if coincide_modelo and coincide_version:
            referencias.append(entrada.get("referencia", "sin referencia"))
    return referencias


def evaluar_terminal(
    *,
    version_firmware: str,
    modelo: str,
    ultima_version_referencia: str | None,
    lista_vulnerable: list[dict],
) -> dict:
    """Indicadores derivados de una terminal.

    - `version_referencia_desconocida`: no hay última versión de referencia para el modelo →
      NUNCA se asume "al día" (FR-010).
    - `desactualizada`: la versión está por debajo de la última de referencia.
    - `expuesta_a_clonacion`: la versión o el modelo figuran en la lista de vulnerabilidad; lista
      vacía ⇒ nunca expuesta (Edge Case del spec).
    """
    referencias = _en_lista_vulnerable(modelo, version_firmware, lista_vulnerable)
    if ultima_version_referencia is None:
        desactualizada = False
        version_referencia_desconocida = True
    else:
        desactualizada = comparar_version(version_firmware, ultima_version_referencia) < 0
        version_referencia_desconocida = False
    return {
        "desactualizada": desactualizada,
        "expuesta_a_clonacion": bool(referencias),
        "version_referencia_desconocida": version_referencia_desconocida,
        "referencias_vulnerabilidad": referencias,
        "ultima_version_referencia": ultima_version_referencia,
    }


def sucursal_en_fecha(historial_ubicacion: list[dict], fecha: date) -> int | None:
    """La sucursal donde estaba la terminal en `fecha`, según su historia de ubicación
    `[{id_sucursal, desde, hasta}]` (fechas ISO; `hasta` `None` = tramo vigente). `None` si ningún
    tramo cubre la fecha (FR-014).
    """
    for tramo in historial_ubicacion:
        desde = date.fromisoformat(tramo["desde"])
        hasta = date.fromisoformat(tramo["hasta"]) if tramo.get("hasta") else None
        if fecha >= desde and (hasta is None or fecha <= hasta):
            return tramo["id_sucursal"]
    return None
