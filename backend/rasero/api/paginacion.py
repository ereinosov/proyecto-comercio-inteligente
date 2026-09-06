"""Paginación de listados (La Regla del Filtro y la Página, DESIGN.md v1.2.0).

Convención del proyecto — resuelta como ambigüedad menor de implementación (ver resumen de la
tarea de administración de datos maestros):

- El cuerpo de la respuesta sigue siendo un array JSON, igual que antes. No se envuelve en un
  objeto `{items, total}`: eso rompería el contrato de `GET /clientes`, `GET /promociones/cupones`
  y `GET /pagos/bitacora`, ya consumidos por pruebas y frontend.
- El total de registros se devuelve en la cabecera `X-Total-Count` (patrón REST habitual), para
  que el frontend calcule el total de páginas.
- Los parámetros opcionales son `pagina` (1-indexado) y `tamano_pagina`, mismo estilo de
  parámetro opcional que `id_sucursal` en el resto de la API.
- Si `pagina` no se indica, se devuelven todos los registros (comportamiento actual intacto);
  `X-Total-Count` se envía igualmente.

`TAMANO_PAGINA_DEFECTO = 20` coincide con el del componente `Paginador.tsx`.
"""

from typing import Sequence, TypeVar

from fastapi import Response

TAMANO_PAGINA_DEFECTO = 20

_T = TypeVar("_T")


def paginar(
    items: Sequence[_T],
    *,
    pagina: int | None,
    tamano_pagina: int | None,
    response: Response,
) -> list[_T]:
    total = len(items)
    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    if pagina is None:
        return list(items)
    pagina = max(1, pagina)
    tamano = (
        tamano_pagina if tamano_pagina and tamano_pagina > 0 else TAMANO_PAGINA_DEFECTO
    )
    inicio = (pagina - 1) * tamano
    return list(items[inicio : inicio + tamano])
