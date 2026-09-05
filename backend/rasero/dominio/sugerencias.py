"""Algoritmos de sugerencia de precio y colocación (Lecturas Críticas n.º 2 y n.º 3 de la
constitución; research.md #5 y #6 de 003-precios-margenes). Funciones puras: reciben valores ya
resueltos, no tocan la base de datos.
"""

from decimal import Decimal

GRAMOS_POR_KG = Decimal(1000)


def normalizar_precio_observado(
    *, precio_observado: Decimal, presentacion_cantidad: Decimal, presentacion_unidad: str, comparable: bool
) -> Decimal | None:
    """Precio de una observación de competencia por unidad de medida (FR-023 de 001).

    **Nota de propiedad de datos**: la normalización de `observacion_precio` es, por su propio
    FR-023, responsabilidad de `001` ("El sistema DEBE normalizar las observaciones a precio por
    unidad de medida"). `001` declaró ese requisito pero nunca construyó su implementación (User
    Story 4 de `001` — captura y comparación de precios de competencia — no tiene servicio, API ni
    prueba en el código, solo el esquema de la tabla; detectado al implementar esta función).
    `003` no puede esperar a que `001` la construya para generar sus propias sugerencias, así que
    implementa aquí la normalización mínima que su propio consumo necesita, seleccionando su
    versión únicamente sobre este cálculo puntual: convertir a precio por unidad o por kilogramo,
    los dos únicos casos que este dominio compara. Si `001` construye su propia normalización más
    adelante, esta función debe migrar a consumirla — mismo patrón que ya resolvió FR-022 para el
    margen (research.md #8) — para no mantener dos implementaciones del mismo cálculo.
    """
    if not comparable:
        return None
    if presentacion_unidad == "unidad":
        return precio_observado / presentacion_cantidad
    if presentacion_unidad == "gramo":
        return precio_observado / (presentacion_cantidad / GRAMOS_POR_KG)
    # "mililitro": no hay producto de este dominio vendido por volumen (por unidad o por
    # kilogramo, producto.es_granel) — no hay nada contra qué comparar este precio.
    return None


def sugerir_precio(
    *,
    precio_vigente: Decimal,
    costo_vigente: Decimal | None,
    rol: str | None,
    observacion_normalizada: Decimal | None,
) -> Decimal:
    """Lectura Crítica n.º 2: "el precio depende del rol del producto, no de una regla única".

    - Sin rol asignado o sin observación de competencia: mantiene el precio vigente — no hay
      base para ajustar en ninguna dirección (FR-007, FR-010).
    - Gancho de tráfico: iguala o baja hacia el precio de competencia, nunca por debajo del costo
      vigente cuando se conoce (nunca sugiere vender a pérdida). Si el costo vigente no se conoce,
      el piso no puede aplicarse — se documenta como limitación, no se inventa un costo.
    - Generador de margen: solo sube hasta el precio de competencia si el vigente ya estaba por
      debajo (capturar margen que el mercado ya tolera); nunca baja para igualar competencia.
    """
    if rol is None or observacion_normalizada is None:
        return precio_vigente

    if rol == "gancho_trafico":
        candidato = min(precio_vigente, observacion_normalizada)
        if costo_vigente is not None and candidato < costo_vigente:
            candidato = costo_vigente
        return candidato

    if rol == "generador_margen":
        if precio_vigente < observacion_normalizada:
            return observacion_normalizada
        return precio_vigente

    return precio_vigente


def sugerir_colocacion(
    *, rango: int, total_con_margen: int, zonas_ordenadas: list[int]
) -> int | None:
    """Lectura Crítica n.º 3: "el producto de mayor margen va a zona de exhibición privilegiada
    y el de menor margen a zona relegada" — un ranking RELATIVO entre productos de la misma
    sucursal, no una regla que dependa del margen de un solo producto de forma aislada.

    `rango` es la posición 1-indexada del producto entre los que sí tienen margen calculable de
    esa sucursal, ordenados por margen descendente; `zonas_ordenadas` ya viene ordenada por
    `grado_privilegio` descendente. La asignación reparte en franjas proporcionales cuando hay
    más productos que zonas (research.md #6).

    `None` si no hay ninguna zona catalogada o ningún producto con margen — no hay base para
    sugerir nada (FR-018 y el caso de producto sin margen calculable, este último no cubierto
    explícitamente por el spec y decidido aquí: sin margen no hay con qué rankear, así que no se
    genera sugerencia en vez de inventar una posición).
    """
    if not zonas_ordenadas or total_con_margen == 0:
        return None
    indice = min((rango - 1) * len(zonas_ordenadas) // total_con_margen, len(zonas_ordenadas) - 1)
    return zonas_ordenadas[indice]
