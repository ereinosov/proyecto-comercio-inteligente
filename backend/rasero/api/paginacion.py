"""Paginación de listados (La Regla del Filtro y la Página, DESIGN.md v1.2.0).

Convención del proyecto:

- La respuesta de todo endpoint de listado paginable es un objeto `{"items": [...], "total": N}`
  (schema `RespuestaPaginada` en cada `contracts/openapi.yaml`). `total` es el número total de
  registros que cumplen el filtro, no el de la página; el frontend calcula el total de páginas
  a partir de él.
- Los parámetros opcionales son `pagina` (1-indexado) y `tamano_pagina`, mismo estilo de
  parámetro opcional que `id_sucursal` en el resto de la API.
- Si `pagina` no se indica, `items` trae todos los registros (comportamiento útil para consumos
  que no pintan un `Paginador`); `total` es igual a `len(items)`.

`TAMANO_PAGINA_DEFECTO = 20` coincide con el del componente `Paginador.tsx`.
"""

from typing import Sequence, TypeVar

TAMANO_PAGINA_DEFECTO = 20

_T = TypeVar("_T")


def paginar(
    items: Sequence[_T],
    *,
    pagina: int | None,
    tamano_pagina: int | None,
) -> dict:
    """Devuelve `{"items": [...], "total": N}`. `total` siempre cuenta la colección completa."""
    total = len(items)
    if pagina is None:
        return {"items": list(items), "total": total}
    pagina = max(1, pagina)
    tamano = (
        tamano_pagina if tamano_pagina and tamano_pagina > 0 else TAMANO_PAGINA_DEFECTO
    )
    inicio = (pagina - 1) * tamano
    return {"items": list(items[inicio : inicio + tamano]), "total": total}
