---

description: "Task list template for feature implementation"
---

# Tasks: Precios y Márgenes

**Input**: Documentos de diseño desde `/specs/003-precios-margenes/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados. Requiere además que `001-core-ventas-inventario` y `002-clientes-fidelizacion` ya estén migrados y en ejecución: este módulo consulta `producto`, `producto_precio_sucursal`, `zona_exhibicion`, `lote`, `existencia`, `observacion_precio` y `canal_competencia` de `001`, y `002` es quien consume el contrato de migración de FR-022.

**Pruebas**: se incluyen las 5 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md (Principio III — una sugerencia de precio aplicada cambia directamente lo que se cobra), intercaladas junto a la funcionalidad que verifican. **Todas corren contra PostgreSQL real en el puerto 5442, nunca contra mocks ni SQLite** — mismo criterio que ya exigen `001` y `002` (la constitución prohíbe SQLite en toda fase precisamente porque no reproduce el comportamiento de `NUMERIC` de Postgres). No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario (P1 → P4 de spec.md, orden ya fijado por el spec y no renegociable: US1 margen real → US2 rol de producto → US3 precio sugerido → US4 colocación sugerida), backend antes que frontend dentro de cada historia. Fundamento completo (esquema, modelos, router) antes de cualquier historia; el prerrequisito cruzado con `001` (Setup) antes de Fundamento.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta)
- **[Story]**: historia de usuario a la que pertenece (US1 … US4)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende
- Cada tarea que toca datos indica explícitamente de dónde: **[003]** tabla propia de este módulo, **[001-lectura]** consulta de solo lectura a una tabla de `001`, **[001-escritura]** escritura en `producto_precio_sucursal` de `001` vía `fijar_precio_sucursal` (el único caso de escritura cruzada, justificado en research.md #7), o **[contrato-002]** el punto de integración de FR-022

## Convención de rutas (fijada en plan.md, extiende la de 001/002, no negociable)

- Backend: `backend/rasero/` (dominio/, persistencia/, servicios/, api/) y `backend/migraciones/`
- Frontend: `frontend/src/` (componentes/, pantallas/, servicios/) — reutiliza `frontend/src/estilos/tokens.css` ya existente, sin tokens nuevos; **registro de Análisis exclusivamente** (radio 6px, Source Serif 4) — este módulo no toca el registro de Operación
- Pruebas: `tests/` en la raíz (unidad/, integracion/, contrato/)

---

## Phase 1: Setup — prerrequisito cruzado con `001`

**Propósito**: a diferencia de `002` (que no necesitó fase de Setup porque no introducía dependencia ni tocaba otro módulo), `003` sí depende de un cambio previo en un archivo de `001`: `fijar_precio_sucursal`, la función que permite aplicar una sugerencia de precio (research.md #7). Se aísla en su propia fase porque **no es esquema propio de `003`** — es completar una capacidad que `001` ya declaraba (FR-050) sin implementar — y porque bloquea a User Story 3, no a Foundational ni a User Story 1/2.

**⚠️ CRÍTICO**: no iniciar User Story 3 (precio sugerido) hasta terminar esta fase. User Story 1 (margen real) y User Story 2 (rol de producto) no dependen de ella y pueden avanzar en paralelo.

- [X] T001 [P] Prueba de integración de `fijar_precio_sucursal`: crea el override si no existía, lo actualiza si ya existía, en una sola transacción — contra PostgreSQL real, puerto 5442, en `tests/integracion/test_fijar_precio_sucursal.py` **[001-escritura]**
- [X] T002 Implementar `fijar_precio_sucursal(sesion, *, id_producto, id_sucursal, precio_vigente) -> ProductoPrecioSucursal` (upsert `ON CONFLICT (id_producto, id_sucursal) DO UPDATE`) en `backend/rasero/servicios/catalogo.py` — **archivo de `001`, ampliado para cumplir una capacidad que su FR-050 ya declaraba** (research.md #7), no un cambio de alcance de `001` (depende de T001) **[001-escritura]**

**Checkpoint**: `001` tiene la función de escritura que User Story 3 necesitará. Foundational puede empezar sin esperar esto.

---

## Phase 2: Foundational (bloqueante para las cuatro historias)

**Propósito**: esquema de las cuatro entidades propias de este módulo, modelos ORM y el router que todas las historias comparten.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T003 Crear `backend/migraciones/versions/0003_precios_margenes.py` con `rol_producto`, `margen_calculado`, `sugerencia_precio`, `sugerencia_colocacion` de data-model.md: `rol_producto` con PK = `id_producto`; `margen_calculado` con PK compuesta `(id_producto, id_sucursal)`, `costo_vigente`/`margen` `NULL`-ables (FR-003); `sugerencia_precio`/`sugerencia_colocacion` append-only con `id_observacion_precio_usada`/`id_zona_exhibicion` como FK hacia tablas de `001`; y `downgrade` implementado **[003]**
- [X] T004 [P] Crear los modelos SQLAlchemy 2.x `RolProducto`, `MargenCalculado`, `SugerenciaPrecio`, `SugerenciaColocacion` en `backend/rasero/persistencia/modelos.py` (depende de T003) **[003]**
- [X] T005 [P] Crear el router base y montarlo en `backend/rasero/api/aplicacion.py`, en `backend/rasero/api/precios.py` (depende de T004)

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Calcular el margen real de un producto (Priority: P1) 🎯 MVP

**Goal**: mostrar el margen real de cualquier producto, resuelto por sucursal, recalculado en cada lectura — y migrar `002` para que consuma esta definición en vez de su fórmula interina (FR-022).

**Independent Test**: para un producto con costo y precio conocidos, y uno a granel, el margen real mostrado coincide con el cálculo esperado, sin depender de que exista ninguna sugerencia todavía.

### Pruebas obligatorias para User Story 1

- [X] T006 [P] [US1] Prueba unitaria de margen real: costo $6/precio $10 → `margen: 0.40`; producto a granel aplica conversión gramos/kg; sin existencia con lote → `margen: null` (FR-003); costo ≤ 0 → `confiable: false` (FR-004) — contra PostgreSQL real, en `tests/unidad/test_margen_calculado.py` **[003] [001-lectura: producto, lote, existencia]** — **corrección durante implementación**: (a) "granel aplica conversión gramos/kg" era un error heredado de spec.md/research.md — `costo_unitario` y `precio_vigente` ya están en la misma base (por unidad o por kg) y su cociente no convierte nada; verificado explícitamente para no reintroducir el error (ver docstring de los archivos de prueba). (b) esta tarea se dividió en `tests/unidad/test_margen_calculado.py` (funciones puras `calcular_margen`/`es_confiable`, sin DB) y `tests/integracion/test_resolver_margen_producto.py` (los mismos escenarios contra PostgreSQL real vía `resolver_margen_producto`), porque en este repo `tests/unidad/` es exclusivamente de funciones puras (ningún archivo existente ahí usa el fixture `sesion`) — "contra PostgreSQL real" y "unitaria" eran instrucciones contradictorias tal como estaba redactada la tarea.
- [X] T007 [P] [US1] Prueba de integración: `GET /margenes?id_sucursal=` resuelve una sucursal de cientos de productos con una única consulta de conjunto y un único upsert masivo — nunca un bucle de N consultas individuales (research.md #4, patrón N+1 explícitamente rechazado) — en `tests/integracion/test_listado_margenes.py` **[003] [001-lectura]**
- [X] T008 [P] [US1] Prueba de integración del contrato de migración (FR-022): `resolver_margen_visita` de `002`, tras el refactor de T015, produce el mismo valor que `servicios/margenes.resolver_margen_producto` de `003` para el/los productos de una venta nueva; una `visita` creada **antes** de la migración conserva su `margen_relativo` original — contra PostgreSQL real, en `tests/integracion/test_migracion_margen_visita.py` **[contrato-002]**

### Implementación backend para User Story 1

- [X] T009 [P] [US1] Funciones puras `calcular_margen(costo, precio) -> Decimal | None` y `es_confiable(costo) -> bool` en `backend/rasero/dominio/margenes.py` (implementa T006) **[003]**
- [X] T010 [US1] Servicio `resolver_margen_producto(sesion, *, id_producto, id_sucursal) -> Decimal | None`: resuelve precio vigente (`COALESCE` override/base, `producto_precio_sucursal`/`producto`), costo vigente vía el lote FEFO de `001` (`(id_sucursal, id_producto, fecha_caducidad NULLS LAST, instante_entrada, id_lote)`), aplica T009 y hace upsert en `margen_calculado`, en `backend/rasero/servicios/margenes.py` (depende de T004, T009) **[003] [001-lectura: producto, producto_precio_sucursal, lote, existencia]** — esta es también la función del contrato con `002` (research.md #8)
- [X] T011 [US1] Servicio `listar_margenes_sucursal(sesion, *, id_sucursal) -> list[dict]`: una sola consulta de conjunto (`JOIN`/subconsulta lateral, sin bucle por producto) más un único upsert masivo sobre `margen_calculado` (research.md #4) en `backend/rasero/servicios/margenes.py` (depende de T004, T009; implementa T007) **[003] [001-lectura]**
- [X] T012 [US1] Endpoint `GET /productos/{id_producto}/margen?id_sucursal=` en `backend/rasero/api/precios.py` (depende de T010, T005)
- [X] T013 [US1] Endpoint `GET /margenes?id_sucursal=` en `backend/rasero/api/precios.py` (depende de T011, T005)
- [X] T014 [P] [US1] Prueba de contrato de `GET /margenes` y `GET /productos/{id_producto}/margen` contra `contracts/openapi.yaml` en `tests/contrato/test_contrato_precios.py` (depende de T012, T013)
- [X] T015 [US1] Refactor de `backend/rasero/servicios/margen_resolver.py` — **archivo de `002`**: reemplazar el cálculo propio de costo/margen por una llamada a `servicios/margenes.resolver_margen_producto` (T010) por cada `renglon_venta`, conservando la ponderación por monto entre renglones que ya es propiedad de `002` (research.md #4 de `002`); costo desconocido para un renglón conserva el mismo tratamiento ya documentado ("se trata como costo cero") (depende de T010; implementa T008) **[contrato-002]**

### Implementación frontend para User Story 1

- [X] T016 [P] [US1] Cliente HTTP `obtenerMargen`, `listarMargenes` en `frontend/src/servicios/precios.ts` (depende de T012, T013)
- [X] T017 [US1] Pantalla `Precios.tsx`: listado de productos de una sucursal con su margen real, registro de Análisis (radio 6px, Source Serif 4, líneas bajo 80 caracteres), "no calculable" y "no confiable" comunicados con texto explícito, nunca con la ausencia de un número. Invoca el paso `new-work` de Impeccable (mundo visual de Análisis ya fijado por la constitución, `PRODUCT.md` existente, no se repite `init`), en `frontend/src/pantallas/Precios.tsx` (depende de T016)
- [X] T018 [US1] Ampliar `frontend/src/App.tsx`: nueva pestaña "Precios" (depende de T017)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente. MVP — y `002` ya consume la definición canónica de margen.

---

## Phase 4: User Story 2 - Clasificar el rol comercial de un producto (Priority: P2)

**Goal**: permitir marcar cada producto como gancho de tráfico o generador de margen, insumo que usarán las sugerencias de precio (US3) y colocación (US4).

**Independent Test**: clasificar un producto y confirmar que la clasificación persiste y es consultable, sin depender de que exista ninguna sugerencia todavía.

### Pruebas obligatorias para User Story 2

- [X] T019 [P] [US2] Prueba unitaria: asignar un rol lo persiste y lo refleja en consultas posteriores; cambiar el rol sobrescribe `instante_asignacion` sin dejar historial (research.md #3); un producto nunca clasificado aparece "sin clasificar" en cualquier sugerencia, nunca con un rol supuesto (FR-007) — contra PostgreSQL real, en `tests/unidad/test_rol_producto.py` **[003]**

### Implementación backend para User Story 2

- [X] T020 [US2] Servicio `asignar_rol_producto(sesion, *, id_producto, rol) -> RolProducto` (upsert por `id_producto`) en `backend/rasero/servicios/precios.py` (depende de T004; implementa T019) **[003]**
- [X] T021 [US2] Endpoints `GET` y `PUT /productos/{id_producto}/rol` en `backend/rasero/api/precios.py` (depende de T020, T005) — **corrección durante implementación**: el `GET` no estaba en el diseño original (solo el `PUT` de asignación); el frontend necesita leer la clasificación vigente para mostrarla, mismo vacío que 001 encontró para `GET /productos`. Añadido aquí y a `contracts/openapi.yaml`.
- [X] T022 [P] [US2] Ampliar la prueba de contrato con `PUT /productos/{id_producto}/rol` en `tests/contrato/test_contrato_precios.py` (depende de T021)

### Implementación frontend para User Story 2

- [X] T023 [P] [US2] Cliente HTTP `asignarRol` en `frontend/src/servicios/precios.ts` (depende de T021)
- [X] T024 [US2] Componente `RolProductoSelector.tsx`: asignar/cambiar gancho de tráfico | generador de margen, integrado en `Precios.tsx`, en `frontend/src/componentes/RolProductoSelector.tsx` (depende de T023, T017)
- [X] T025 [US2] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar el selector de rol (depende de T024)

**Checkpoint**: User Stories 1 y 2 funcionan juntas de forma independiente.

---

## Phase 5: User Story 3 - Sugerir precio de venta usando margen, rol y competencia (Priority: P3)

**Goal**: sugerir un precio por producto y sucursal a partir de margen real, rol y la observación de competencia vigente más reciente — y permitir que el encargado la aplique, nunca de forma automática.

**Independent Test**: para un producto con margen y rol ya definidos, generar una sugerencia y verificar que es explicable a partir de esos insumos, con y sin observación de competencia disponible.

### Pruebas obligatorias para User Story 3

- [X] T026 [P] [US3] Prueba unitaria del algoritmo de sugerencia de precio (Lectura Crítica n.º 2, research.md #5): gancho de tráfico con competencia sugiere igualar o bajar sin cruzar el costo vigente como piso; generador de margen sube hasta el precio de competencia solo si el vigente ya estaba por debajo; cualquier rol sin observación mantiene el precio vigente ("sin referencia de competencia", FR-010); sin `rol_producto` → "sin clasificar", sin ajuste — en `tests/unidad/test_sugerencia_precio.py` **[003]**
- [X] T027 [P] [US3] Prueba de integración: aplicar una sugerencia de precio crea o actualiza `producto_precio_sucursal` vía `fijar_precio_sucursal` (T002) y deja registro de qué sugerencia lo originó (FR-013); aplicar la misma sugerencia dos veces devuelve `409` en la segunda — contra PostgreSQL real, en `tests/integracion/test_aplicar_sugerencia_precio.py` **[001-escritura] [003]**

### Implementación backend para User Story 3

- [X] T028 [P] [US3] Función pura `sugerir_precio(precio_vigente, costo_vigente, rol, observacion_normalizada) -> Decimal` en `backend/rasero/dominio/sugerencias.py` (implementa T026) **[003]**
- [X] T029 [US3] Servicio `generar_sugerencia_precio(sesion, *, id_producto, id_sucursal) -> SugerenciaPrecio`: resuelve `margen_calculado` (T010), `rol_producto` (T020) y la observación de competencia vigente y comparable más reciente de `001` (excluye `comparable = false`, FR-011), aplica T028, persiste el snapshot (`margen_usado`, `rol_usado`, `id_observacion_precio_usada`) en `sugerencia_precio`, en `backend/rasero/servicios/precios.py` (depende de T010, T020, T028) **[003] [001-lectura: observacion_precio, canal_competencia]**
- [X] T030 [US3] Servicio `aplicar_sugerencia_precio(sesion, *, id_sugerencia_precio) -> SugerenciaPrecio`: en una sola transacción, llama a `fijar_precio_sucursal` (T002) con `precio_sugerido` y marca la sugerencia `aplicada = true` con su `instante_aplicacion`; `409` si ya estaba aplicada, en `backend/rasero/servicios/precios.py` (depende de T002, T029; implementa T027) **[001-escritura] [003]**
- [X] T031 [US3] Endpoint `GET /productos/{id_producto}/sugerencia-precio?id_sucursal=` en `backend/rasero/api/precios.py` (depende de T029, T005)
- [X] T032 [US3] Endpoint `POST /productos/{id_producto}/sugerencia-precio/aplicar` en `backend/rasero/api/precios.py` (depende de T030, T005)
- [X] T033 [P] [US3] Ampliar la prueba de contrato con ambos endpoints en `tests/contrato/test_contrato_precios.py` (depende de T031, T032)

### Implementación frontend para User Story 3

- [X] T034 [P] [US3] Cliente HTTP `obtenerSugerenciaPrecio`, `aplicarSugerenciaPrecio` en `frontend/src/servicios/precios.ts` (depende de T031, T032)
- [X] T035 [US3] Componente `SugerenciaPrecioColocacion.tsx` (sección de precio): tarjeta con insumos visibles (margen usado, rol usado, observación de competencia con sus tres portadores de antigüedad — color, forma, texto) y botón de aplicar, con el único momento de animación deliberado de este módulo al confirmar, integrado en `Precios.tsx`, en `frontend/src/componentes/SugerenciaPrecioColocacion.tsx` (depende de T034, T024)
- [X] T036 [US3] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la tarjeta de sugerencia de precio (depende de T035)

**Checkpoint**: User Stories 1 a 3 funcionan juntas de forma independiente.

---

## Phase 6: User Story 4 - Sugerir colocación en zona de exhibición (Priority: P4)

**Goal**: sugerir una zona de exhibición por producto y sucursal a partir del margen real (Lectura Crítica n.º 3), usando el catálogo de zonas que ya provee `001`.

**Independent Test**: para un producto con rol y margen ya definidos, pedir una sugerencia de colocación y verificar que referencia una zona existente del catálogo de `001`, con su justificación.

### Pruebas obligatorias para User Story 4

- [X] T037 [P] [US4] Prueba unitaria del algoritmo de colocación (Lectura Crítica n.º 3, research.md #6): productos ordenados por `margen_calculado.margen` descendente se asignan a zonas ordenadas por `grado_privilegio` descendente; `rol_producto` no altera el ranking, solo aparece en la explicación; sin ninguna zona catalogada para la sucursal → sin sugerencia (FR-018) — en `tests/unidad/test_sugerencia_colocacion.py` **[003]**
- [X] T038 [P] [US4] Prueba de integración: dos sugerencias de colocación distintas pueden apuntar a la misma zona para productos distintos sin bloquearse (FR-019); aplicar una sugerencia de colocación solo la marca `aplicada`, nunca reubica nada físico ni escribe en `zona_exhibicion` (FR-017) — contra PostgreSQL real, en `tests/integracion/test_aplicar_sugerencia_colocacion.py` **[003] [001-lectura: zona_exhibicion]**

### Implementación backend para User Story 4

- [X] T039 [P] [US4] Función pura `sugerir_colocacion(*, rango, total_con_margen, zonas_ordenadas) -> id_zona_exhibicion | None` en `backend/rasero/dominio/sugerencias.py` (implementa T037) **[003]** — **corrección durante implementación** (research.md #6): la firma original (`sugerir_colocacion(margen, zonas_ordenadas)`, un solo margen) era incompatible con el propio algoritmo decidido en research.md #6, que es un ranking relativo entre productos — no se puede resolver con el margen de uno solo. Corregida a recibir el `rango` del producto entre los que tienen margen calculable.
- [X] T040 [US4] Servicio `generar_sugerencia_colocacion(sesion, *, id_producto, id_sucursal) -> SugerenciaColocacion`: calcula el ranking de margen de toda la sucursal reutilizando `listar_margenes_sucursal` (T011, ya libre de N+1), ordena las `zona_exhibicion` de `001` por `grado_privilegio`, aplica T039, persiste el snapshot; `404` si no hay ninguna zona catalogada (FR-018) o si el producto no tiene margen calculable (edge case decidido en research.md #6, no cubierto explícitamente por el spec), en `backend/rasero/servicios/precios.py` (depende de T010, T011, T020, T039) **[003] [001-lectura: zona_exhibicion]**
- [X] T041 [US4] Servicio `aplicar_sugerencia_colocacion(sesion, *, id_sugerencia_colocacion) -> SugerenciaColocacion`: marca `aplicada = true` con su `instante_aplicacion`, sin tocar ninguna tabla de `001`; `409` si ya estaba aplicada, en `backend/rasero/servicios/precios.py` (depende de T040; implementa T038) **[003]**
- [X] T042 [US4] Endpoint `GET /productos/{id_producto}/sugerencia-colocacion?id_sucursal=` en `backend/rasero/api/precios.py` (depende de T040, T005)
- [X] T043 [US4] Endpoint `POST /productos/{id_producto}/sugerencia-colocacion/aplicar` en `backend/rasero/api/precios.py` (depende de T041, T005)
- [X] T044 [P] [US4] Ampliar la prueba de contrato con ambos endpoints en `tests/contrato/test_contrato_precios.py` (depende de T042, T043)

### Implementación frontend para User Story 4

- [X] T045 [P] [US4] Cliente HTTP `obtenerSugerenciaColocacion`, `aplicarSugerenciaColocacion` en `frontend/src/servicios/precios.ts` (depende de T042, T043)
- [X] T046 [US4] Ampliar `SugerenciaPrecioColocacion.tsx` con la sección de colocación (zona sugerida, insumos visibles, botón de confirmar ejecución física) (depende de T045, T035)
- [X] T047 [US4] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la sección de colocación (depende de T046)

**Checkpoint**: las cuatro historias de usuario funcionan de forma independiente.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T048 [P] Ejecutar los 9 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno
- [X] T049 [P] Auditar `Precios.tsx`, `RolProductoSelector.tsx` y `SugerenciaPrecioColocacion.tsx` en busca de color, radio o tipografía incrustados fuera de `frontend/src/estilos/tokens.css`
- [X] T050 Actualizar `DESIGN.md` con la skill de Impeccable (`document`), derivándolo de `Precios.tsx` ya construido; sidecar `.impeccable/design.json` actualizado en el mismo cambio
- [X] T051 Ejecutar `pytest tests` completo contra PostgreSQL real (puerto 5442) — incluidas las 5 suites obligatorias (T006/T007, T026, T027/T038, T008, y la de contrato T014/T022/T033/T044) — y `tsc -b`, `eslint`, `vite build` del frontend, todo en verde

---

## Dependencies & Execution Order

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias externas más allá de `001` ya migrado. Bloquea únicamente a User Story 3 (aplicar sugerencia de precio); no bloquea Foundational ni User Story 1/2.
- **Foundational (Fase 2)**: sin dependencias externas a este módulo salvo que `001` ya esté migrado. **Bloquea** las cuatro historias de usuario.
- **Historias de usuario (Fases 3-6)**: todas dependen de Foundational; User Story 3 depende además de Setup. Dentro de cada una, backend antes que frontend.
- **Polish (Fase final)**: depende de que las cuatro historias estén completas.

### Dependencias entre historias

El orden **US1 → US2 → US3 → US4 ya está fijado por el spec y no se reordena**: User Story 1 (margen real) es el insumo de las otras tres — sin `margen_calculado` no hay qué mostrar en User Story 2 en la práctica (aunque `rol_producto` no depende técnicamente de él) ni qué usar en los algoritmos de sugerencia de User Story 3 y 4. User Story 2 (rol) es insumo directo de los algoritmos de User Story 3 y 4, aunque ambas ya contemplan el caso "sin clasificar" (FR-007) y por tanto no bloquean su propia construcción — solo empobrecen su explicación hasta que existan roles asignados. User Story 3 y User Story 4 son independientes entre sí en datos (una sugiere precio, la otra colocación) pero comparten el mismo componente de frontend (`SugerenciaPrecioColocacion.tsx`), por lo que construirlas en el orden del spec evita conflictos de edición del mismo archivo.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; endpoints antes que su cliente de frontend.
- Backend completo de la historia antes que su frontend.
- Toda historia con superficie de frontend termina con la verificación de `tsc -b`/`eslint`/`vite build` antes de darse por cerrada.

### Oportunidades de paralelismo

- T004 y T005 de Foundational pueden ejecutarse en paralelo tras T003.
- Setup (T001-T002) puede avanzar en paralelo con Foundational (T003-T005): no comparten archivos.
- Dentro de una historia, las pruebas marcadas [P] entre sí y las funciones de dominio marcadas [P] entre sí son paralelizables.
- User Story 2 puede empezar en paralelo con la segunda mitad de User Story 1 (T015-T018) una vez que Foundational esté listo, porque `asignar_rol_producto` (T020) no depende de `resolver_margen_producto` (T010) — aunque conviene cerrar User Story 1 primero para no fragmentar la validación de `Precios.tsx`.

---

## Parallel Example: User Story 1

```bash
# Lanzar juntas las pruebas independientes de esta historia:
Task: "Prueba unitaria de margen real en tests/unidad/test_margen_calculado.py"
Task: "Prueba de integración de listado sin N+1 en tests/integracion/test_listado_margenes.py"
Task: "Prueba de integración de migración de 002 en tests/integracion/test_migracion_margen_visita.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 2: Foundational — crítica, bloquea todo lo demás (Setup, Fase 1, puede ir en paralelo).
2. Completar Fase 3: User Story 1, con sus tres pruebas obligatorias en verde.
3. **Detenerse y validar**: ejecutar los escenarios 1 a 3 y 9 de quickstart.md.
4. Demostrar: margen real por sucursal, recalculado en cada lectura, y `002` ya consumiendo la definición canónica.

### Entrega incremental

1. Setup + Foundational → prerrequisito con `001` y esquema propio listos.
2. + US1 (margen real, migración de `002`) → probar de forma independiente → MVP demostrable.
3. + US2 (rol de producto) → probar de forma independiente.
4. + US3 (precio sugerido) → probar de forma independiente (escenarios 5 y 6 de quickstart.md, los que tocan dinero real vía `producto_precio_sucursal`).
5. + US4 (colocación sugerida) → probar de forma independiente (escenario 7, el caso deliberadamente cruzado margen/rol).
6. Fase final: quickstart.md completo, auditoría de tokens, `DESIGN.md` actualizado, suite completa en verde.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. Una persona completa Setup (T001-T002) mientras otra completa Foundational (T003-T005) — no comparten archivos.
2. Completado Foundational, una persona construye User Story 1 (es prerrequisito de datos real para US3/US4, aunque no bloquea a US2 en el esquema).
3. En paralelo, otra persona puede construir User Story 2 (rol de producto) tan pronto Foundational esté listo.
4. Completadas US1 y US2, User Story 3 (requiere además Setup) y User Story 4 pueden repartirse, coordinando la edición compartida de `SugerenciaPrecioColocacion.tsx`.

---

## Notes

- Las tareas [P] tocan archivos distintos y no dependen de una tarea incompleta.
- La etiqueta [Story] traza cada tarea a su historia de usuario en spec.md.
- Las 5 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md están marcadas y deben pasar antes de fusionar, todas contra PostgreSQL real en el puerto 5442; no hay pruebas de interfaz, maquetación ni componentes visuales.
- **[003]** = tabla propia de este módulo; **[001-lectura]** = consulta de solo lectura a una tabla de `001` (nunca se altera su esquema ni se duplica); **[001-escritura]** = el único caso de escritura cruzada, siempre vía `fijar_precio_sucursal` (T002), nunca por acceso directo al ORM de `001` (research.md #7); **[contrato-002]** = el punto de integración de FR-022.
- `GET /margenes` (T011) DEBE resolverse con una consulta de conjunto, nunca iterando `resolver_margen_producto` (T010) una vez por producto — ver research.md #4 y la prueba T007, que existe específicamente para impedir que esta distinción se pierda durante la implementación.
- Fuera de alcance de este desglose: cualquier objetivo numérico de margen por rol, modelado de elasticidad de demanda, o historial completo de reclasificaciones de `rol_producto` — todos evaluados y rechazados en research.md por no tener base declarada en el spec.
