---

description: "Task list template for feature implementation"
---

# Tasks: Pronóstico de Demanda

**Input**: Documentos de diseño desde `/specs/004-pronostico-demanda/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados. Requiere que `001-core-ventas-inventario` ya esté migrado y en ejecución: este módulo **sólo lee** de `001` (`venta`, `renglon_venta`, `movimiento_inventario`, `existencia`, `lote`, `producto`, `producto_precio_sucursal`, `sucursal`, y —cuando `001` la implemente— `consulta_no_atendida`). No escribe en ninguna tabla ajena, así que **no hay fase de Setup con prerrequisito cruzado** como la tuvo `003` (que sí escribía en `producto_precio_sucursal`). La enmienda constitucional **v2.2.4** (que añade `sustitucion_producto` a la tabla de propiedad de `004`) ya está aplicada.

**Pruebas**: se incluyen las 6 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md (Principio III — una descensura que sobrecorrige inmoviliza capital, una que subcorrige deja el sesgo de agotamiento; el pronóstico alimenta decisiones de compra reales), intercaladas junto a la funcionalidad que verifican. **Todas corren contra PostgreSQL real en el puerto 5442, nunca contra mocks ni SQLite** — mismo criterio que `001`/`002`/`003` (la constitución prohíbe SQLite en toda fase porque no reproduce el `NUMERIC` de Postgres). No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario, en el **orden de dependencia ya fijado por spec.md y no renegociable**: US1 descensura por quiebre (P1) → US2 validación sintética (P2) → US3 pronóstico (P3) → US4 corrección por precio (P4) → US5 neutralización de promoción (P5, parcial) → US6 sustitutos (P6). Backend antes que frontend dentro de cada historia. Fundamento (esquema, modelos, router, parámetros) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta)
- **[Story]**: historia de usuario a la que pertenece (US1 … US6)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende
- Cada tarea que toca datos indica explícitamente de dónde:
  - **[004]** — tabla propia de este módulo (`demanda_observada`, `demanda_corregida`, `pronostico`, `sustitucion_producto`)
  - **[001-lectura: ...]** — consulta de **solo lectura** a una o más tablas de `001` (nunca se altera su esquema ni se duplica)
  - **[001-lectura: consulta_no_atendida]** — consulta de solo lectura a la entidad de `001` (001 User Story 3, T050–T053, ya implementada); las tareas con esta etiqueta quedaron desbloqueadas (ver "Bloqueado por 001 — RESUELTO" al final)
  - **[005-futuro]** — gancho a la marca de "promoción activa" de `005-promociones-inteligentes`, inerte hasta que `005` exista (FR-030)

## Convención de rutas (fijada en plan.md, extiende la de 001/002/003, no negociable)

- Backend: `backend/rasero/` (`dominio/`, `persistencia/`, `servicios/`, `api/`, `config/`) y `backend/migraciones/versions/`
- Frontend: `frontend/src/` (`componentes/`, `pantallas/`, `servicios/`) — reutiliza `frontend/src/estilos/tokens.css` sin tokens nuevos; **registro de Análisis exclusivamente** (radio 6px, Source Serif 4) — este módulo no toca el registro de Operación
- Pruebas: `tests/` en la raíz (`unidad/`, `integracion/`, `contrato/`, `utilidades/`)

---

## Phase 1: Foundational (bloqueante para las seis historias)

**Propósito**: esquema de las cuatro entidades propias, modelos ORM, el router compartido, el módulo único de parámetros de configuración y el helper de día local.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T001 Crear `backend/migraciones/versions/0004_pronostico_demanda.py` con las cuatro tablas de data-model.md: `demanda_observada` y `demanda_corregida` con PK compuesta `(id_producto, id_sucursal, periodo)`, columnas `es_sintetico` y (sólo en `demanda_observada`) `demanda_latente_verdadera NULL`; `pronostico` append-only con `serie_pronosticada`/`multiplicadores_tramo` en `JSONB` y `vigente`/`motivo_no_vigente`; `sustitucion_producto` con `UNIQUE (id_producto, id_producto_sustituto)` y `CHECK (id_producto <> id_producto_sustituto)`; índices `(id_producto, id_sucursal, periodo)`, `(id_producto, id_sucursal, horizonte, instante_generacion)`, `(id_producto)` y `(id_producto_sustituto)`; `downgrade` que elimina las cuatro tablas **[004]**
- [X] T002 [P] Crear los modelos SQLAlchemy 2.x `DemandaObservada`, `DemandaCorregida`, `Pronostico`, `SustitucionProducto` en `backend/rasero/persistencia/modelos.py` (depende de T001) **[004]**
- [X] T003 [P] Crear el módulo único de parámetros de configuración con los valores por defecto de research.md (`N = 30`, `alfa = 0.3`, `epsilon = 1.0`, `ventana_materializacion_dias = 90`, `tramos_mes`, `minimo_periodos_sin_quiebre = 14`) en `backend/rasero/config/pronostico.py` — un solo lugar, sin constantes mágicas dispersas (Principio V "acotada": los límites del modelo se documentan)
- [X] T004 [P] Crear el router base y montarlo en `backend/rasero/api/aplicacion.py`, en `backend/rasero/api/pronostico.py` (depende de T002)
- [X] T005 Funciones de dominio compartidas en `backend/rasero/dominio/serie_demanda.py`: `periodo_local(instante, zona_horaria) -> date` (`AT TIME ZONE`, mismo criterio que el cierre por día local de `001`) y el esqueleto de agregación diaria por día local **[001-lectura: sucursal]**

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 2: User Story 1 - Descensurar la demanda por quiebre de stock (Priority: P1) 🎯 MVP

**Goal**: construir la serie de demanda observada y su serie corregida por quiebre de stock, por producto y sucursal, con la corrección mayor o igual a la observada en todo período de quiebre y explicable (de qué valor partió, qué intervalo, qué respaldo).

**Independent Test**: para un producto con un intervalo conocido de existencia cero, la serie corregida sube en ese intervalo, la corrección dice de qué valor observado partió y si se apoyó en el método base o en consultas no atendidas, y los períodos sin quiebre no se alteran.

### Pruebas obligatorias para User Story 1

- [X] T006 [P] [US1] Prueba unitaria del método base de descensura: período de quiebre → corregida = máximo de la demanda observada del producto entre los N días recientes sin quiebre (research.md #5); invariante `corregida >= observada` en todo período de quiebre (FR-006); período sin quiebre → `correccion_quiebre = 0` (FR-011); sin ningún período sin quiebre y sin consultas → "no estimable por censura total" (FR-012), nunca 0 — funciones puras, en `tests/unidad/test_censura.py` **[004]**
- [X] T007 [P] [US1] Prueba de integración: `reconstruir_serie` materializa `demanda_observada` y `demanda_corregida` de una ventana, con `dias_en_quiebre` calculado **replayando `movimiento_inventario`** (no leyendo `existencia`, que no es autoritativa — data-model.md de `001`) — contra PostgreSQL real, puerto 5442, en `tests/integracion/test_reconstruir_serie.py` **[004] [001-lectura: venta, renglon_venta, movimiento_inventario, existencia]**
- [X] T008 [P] [US1] Prueba de integración: `GET /demanda` de una sucursal completa se resuelve con **una** consulta de conjunto y un upsert masivo, nunca un bucle de N llamadas al reconstructor de un solo producto (research.md #3, patrón N+1 explícitamente rechazado) — contra PostgreSQL real, en `tests/integracion/test_demanda_sucursal.py` **[004] [001-lectura]**
- [X] T009 [P] [US1] Prueba del camino de evidencia real (FR-007): cuando existan registros de `consulta_no_atendida` para el intervalo, `respaldo_quiebre = 'consulta_no_atendida'` y la magnitud de la corrección usa el conteo como evidencia directa, no sólo el método base — contra PostgreSQL real, en `tests/integracion/test_descensura_consulta_no_atendida.py` **[004] [001-lectura: consulta_no_atendida]** — el marcador `xfail` se retiró al implementar `001` T050–T053 y `004` T014; en verde

### Implementación backend para User Story 1

- [X] T010 [P] [US1] Funciones puras en `backend/rasero/dominio/censura.py`: `detectar_intervalos_quiebre(movimientos) -> list[Intervalo]`, `maximo_ventana_sin_quiebre(serie, n) -> Decimal | None`, `estimar_latente_metodo_base(...) -> Decimal | None` (implementa T006) **[004]**
- [X] T011 [US1] Ampliar `backend/rasero/dominio/serie_demanda.py`: construir la demanda observada por período (`Σ salida_venta − Σ entrada_anulacion`, día local — research.md #3), anotar `dias_en_quiebre` por replay de `movimiento_inventario`, dejar `precio_vigente_periodo = NULL` (se llena en US4) y `con_promocion = FALSE` (se llena en US5) (depende de T005, T010) **[004] [001-lectura: venta, renglon_venta, movimiento_inventario]**
- [X] T012 [US1] Servicio `demanda.reconstruir_serie(sesion, *, id_sucursal, id_producto=None, desde, hasta)` en `backend/rasero/servicios/demanda.py`: una consulta de conjunto por sucursal-ventana, upsert masivo sobre `demanda_observada`, y deriva `demanda_corregida` aplicando **sólo** la corrección de quiebre en esta historia (precio/promo/sustituto se suman en US4/US5/US6, en el orden fijo de research.md #3) (depende de T011, T002; implementa T007, T008) **[004] [001-lectura: venta, renglon_venta, movimiento_inventario, existencia]**
- [X] T013 [US1] Rama `respaldo_quiebre = 'metodo_base'` (FR-008) y estado `censura_total` (FR-012, `valor` no numérico, `estado: "no_estimable_censura_total"`) en `backend/rasero/servicios/demanda.py` (depende de T012) **[004]**
- [X] T014 [US1] Rama `respaldo_quiebre = 'consulta_no_atendida'` (FR-007): lee `consulta_no_atendida` de `001` por producto, sucursal y día, y usa el conteo de consultas como evidencia directa de la magnitud de la demanda latente en vez de sólo el método base — paso (1c) de `reconstruir_serie` en `backend/rasero/servicios/demanda.py` (depende de T012) **[004] [001-lectura: consulta_no_atendida]** — DESBLOQUEADA: `001` implementó su User Story 3 (T050–T053); el `xfail` de T009 se retiró
- [X] T015 [US1] Endpoint `GET /demanda?id_sucursal=&id_producto=&desde=&hasta=` en `backend/rasero/api/pronostico.py` (depende de T012, T004)
- [X] T016 [P] [US1] Prueba de contrato de `GET /demanda` contra `contracts/openapi.yaml` (forma feliz + `404`) en `tests/contrato/test_contrato_pronostico.py` (depende de T015)

### Implementación frontend para User Story 1

- [X] T017 [P] [US1] Cliente HTTP `obtenerSerieDemanda` en `frontend/src/servicios/pronostico.ts` (depende de T015)
- [X] T018 [US1] Componente `SerieDemanda.tsx`: serie **observada** (tinta normal) frente a **corregida** (color `estimado` `#1F5673` + línea punteada + texto "corregido por quiebre") — los tres portadores simultáneos, nunca sólo color; detalle por período con el respaldo de la corrección ("+8 u · método base" / "+8 u · respaldado por N consultas no atendidas"), en `frontend/src/componentes/SerieDemanda.tsx` (depende de T017). Invoca `new-work` de Impeccable (mundo visual de Análisis ya fijado por la constitución, `PRODUCT.md` existente, no se repite `init`)
- [X] T019 [US1] Pantalla `Pronostico.tsx` (registro de Análisis: radio 6px, Source Serif 4, líneas bajo 80 caracteres) que embebe `SerieDemanda` por producto y sucursal, y nueva pestaña "Pronóstico" en `frontend/src/App.tsx` (depende de T018)
- [X] T020 [US1] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar `SerieDemanda` y la pestaña (depende de T019)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente (por método base). MVP. La rama de evidencia real (T014) queda a la espera de `001`.

---

## Phase 3: User Story 2 - Validar la descensura contra datos sintéticos con demanda latente conocida (Priority: P2)

**Goal**: cargar una serie histórica sintética con demanda latente verdadera conocida y medir el error de la descensura contra ese valor, comprobando que corregir acerca la serie al valor verdadero más que no corregir.

**Independent Test**: se genera una serie sintética con demanda latente verdadera fijada, se corre la descensura y el reporte de error muestra que el error de la serie corregida es menor que el de la serie observada sin corregir, en el escenario con consultas no atendidas sintéticas y en el que no.

### Pruebas obligatorias para User Story 2

- [X] T021 [P] [US2] Prueba de integración (SC-002): sobre una serie sintética con demanda latente verdadera conocida, el error medio de `demanda_corregida` frente al valor verdadero es **menor** que el de `demanda_observada` sin corregir, en el escenario con `consultas_no_atendidas_sinteticas` y en el que no las tiene (FR-014, FR-015, FR-016) — contra PostgreSQL real, en `tests/integracion/test_descensura_sintetica.py` **[004]**
- [X] T022 [P] [US2] Prueba de integración de aislamiento (FR-017): ninguna fila `es_sintetico = TRUE` aparece en `GET /demanda` ni en `GET /productos/{id}/pronostico` de producción; `generar_pronostico` responde `409` para un producto que sólo tiene datos sintéticos — contra PostgreSQL real, en `tests/integracion/test_aislamiento_sintetico.py` **[004]**

### Implementación backend para User Story 2

- [X] T023 [P] [US2] Generador de serie sintética (nivel base + patrón semanal + uno o más intervalos de quiebre con `demanda_latente_verdadera` fijada + `consulta_no_atendida` sintéticas consistentes para el escenario de FR-016), como utilidad de pruebas en `tests/utilidades/generador_sintetico.py` (research.md #9) — **NO** en el paquete de producción, **NO** pertenece al juego de datos "Despensa Los Ríos"
- [X] T024 [US2] Servicio `demanda_sintetica.cargar_serie(sesion, carga)` en `backend/rasero/servicios/demanda_sintetica.py`: valida el requisito de FR-016 (al menos un escenario de quiebre con consultas y uno sin), inserta las filas con `es_sintetico = TRUE` y `demanda_latente_verdadera` (depende de T002, T012) **[004]**
- [X] T025 [US2] Servicio `demanda_sintetica.reporte_error_descensura(sesion, *, id_producto, id_sucursal)` en `backend/rasero/servicios/demanda_sintetica.py`: compara `demanda_corregida.valor` contra `demanda_observada.demanda_latente_verdadera` y contra `demanda_observada.cantidad`, desglosado por camino (`con_consulta_no_atendida` / `solo_metodo_base`) (depende de T024; implementa T021) **[004]**
- [X] T026 [US2] Filtro `es_sintetico = FALSE` en la capa de servicio de **todas** las consultas de producción (`servicios/demanda.py`, `servicios/pronostico.py`) y rechazo `409` en `generar_pronostico` para un producto sólo-sintético (depende de T024; implementa T022) **[004]**
- [X] T027 [US2] Endpoints `POST /demanda-sintetica` y `GET /demanda-sintetica/validacion` en `backend/rasero/api/pronostico.py` (depende de T024, T025, T004)
- [X] T028 [P] [US2] Ampliar la prueba de contrato con ambos endpoints (forma feliz + `400` cuando la serie no cumple FR-016) en `tests/contrato/test_contrato_pronostico.py` (depende de T027)

### Implementación frontend para User Story 2

- [X] T029 [P] [US2] Cliente HTTP `cargarSerieSintetica`, `obtenerValidacionDescensura` en `frontend/src/servicios/pronostico.ts` (depende de T027)
- [X] T030 [US2] Componente `ValidacionDescensura.tsx`: demanda verdadera frente a corregida, error por camino, **rotulado inequívoco "datos sintéticos"** sin posibilidad de confundirlo con una vista de producción (FR-017), en `frontend/src/componentes/ValidacionDescensura.tsx` (depende de T029)
- [X] T031 [US2] Integrar `ValidacionDescensura` en `Pronostico.tsx` como vista de analista separada (depende de T030, T019)
- [X] T032 [US2] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la vista de validación (depende de T031)

**Checkpoint**: User Stories 1 y 2 funcionan juntas; la lógica de descensura queda validada sin depender de datos reales de `001`.

---

## Phase 4: User Story 3 - Generar el pronóstico de demanda a partir de la serie corregida (Priority: P3)

**Goal**: generar un pronóstico por producto, sucursal y horizonte (corto 7–14 d, medio 30 d) sobre la serie corregida, con sus factores, su período de datos y el valor de la línea base determinista; un pronóstico que no supera la línea base no se presenta como vigente.

**Independent Test**: para un producto con serie corregida y suficiente histórico se genera un pronóstico explicable (factores, período de datos, línea base); un producto sin histórico suficiente se marca "datos insuficientes" en vez de recibir un número.

### Pruebas obligatorias para User Story 3

- [X] T033 [P] [US3] Prueba unitaria del suavizado exponencial simple: `nivel_t = α · corregida_t + (1 − α) · nivel_{t−1}` con `α = 0.3` por defecto (research.md #7); multiplicadores por tramo del mes sólo en horizonte medio (research.md #8d); la línea base es el promedio móvil de la demanda **observada sin corregir** (research.md #8c) — funciones puras, en `tests/unidad/test_pronostico.py` **[004]**
- [X] T034 [P] [US3] Prueba de integración (SC-004): un pronóstico cuyo error retrospectivo no es menor que el de la línea base se devuelve con `vigente = false` y `motivo_no_vigente`; un producto con menos de `N` períodos con demanda observada, o menos de 14 sin quiebre, → "datos insuficientes" (FR-023), nunca un número — contra PostgreSQL real, en `tests/integracion/test_pronostico_linea_base.py` **[004]**

### Implementación backend para User Story 3

- [X] T035 [P] [US3] Funciones puras en `backend/rasero/dominio/pronostico.py`: `suavizado_exponencial_simple(serie, alfa) -> Decimal`, `multiplicadores_tramo_mes(serie_historica, tramos) -> dict`, `linea_base_promedio_movil(serie_observada, n) -> Decimal` (implementa T033) **[004]**
- [X] T036 [US3] Servicio `pronostico.generar_pronostico(sesion, *, id_producto, id_sucursal, horizonte)` en `backend/rasero/servicios/pronostico.py`: reconstruye la serie corregida (T012), aplica T035, calcula el error retrospectivo propio y el de la línea base, fija `vigente`, y persiste una fila **append-only** en `pronostico` con `factores` (nivel, `alfa_usado`, `multiplicadores_tramo`), `periodo_datos_desde/hasta` y `valor_linea_base` (FR-018, FR-021, FR-022) (depende de T012, T035, T003) **[004]**
- [X] T037 [US3] Manejo de "datos insuficientes" (FR-023) y "no estimable por censura total" (FR-012) en `generar_pronostico`: fila con `vigente = false`, `serie_pronosticada` vacía y `motivo_no_vigente`, nunca un valor por defecto (depende de T036; implementa T034) **[004]**
- [X] T038 [US3] Endpoint `GET /productos/{id_producto}/pronostico?id_sucursal=&horizonte=&solo_ultimo=` en `backend/rasero/api/pronostico.py` (depende de T036, T004)
- [X] T039 [P] [US3] Ampliar la prueba de contrato con el endpoint de pronóstico (forma feliz + `404` + `409` por censura total o producto sólo-sintético) en `tests/contrato/test_contrato_pronostico.py` (depende de T038)

### Implementación frontend para User Story 3

- [X] T040 [P] [US3] Cliente HTTP `obtenerPronostico` en `frontend/src/servicios/pronostico.ts` (depende de T038)
- [X] T041 [US3] Ampliar `Pronostico.tsx`: serie pronosticada de los dos horizontes superpuesta a la serie corregida y a la línea base determinista; factores visibles (nivel del suavizado, `α`, multiplicadores por tramo del mes); "datos insuficientes" con texto explícito (depende de T040, T019)
- [X] T042 [US3] Momento de animación deliberado al revelar el detalle de por qué un período fue corregido o de la composición del pronóstico — único de la pantalla, sin hover por punto ni fade-in por bloque (constitución, registro de Análisis) — en `frontend/src/pantallas/Pronostico.tsx` (depende de T041)
- [X] T043 [US3] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la vista de pronóstico (depende de T042)

**Checkpoint**: User Stories 1 a 3 funcionan juntas; el pronóstico ya es demostrable sobre serie sintética y sobre serie real corregida por método base.

---

## Phase 5: User Story 4 - Corregir la serie por el precio vigente en cada período histórico (Priority: P4)

**Goal**: normalizar cada período histórico hacia un precio de referencia usando el precio que realmente estuvo vigente en la sucursal ese período, reconstruido de `renglon_venta.precio_aplicado`, sin depender de ningún histórico de precio que `001` no conserva.

**Independent Test**: para un producto con un cambio de precio documentado en su histórico, la serie corregida atribuye parte de la variación de demanda al precio y no a la demanda base, y la corrección es explicable (qué precios, qué períodos, qué factor).

### Pruebas obligatorias para User Story 4

- [X] T044 [P] [US4] Prueba unitaria de la normalización de precio: la demanda de un período con precio `p_hist` se ajusta hacia el precio de referencia `p_ref` por el factor `(p_hist / p_ref) ^ ε` con `ε = 1` por defecto (research.md #8b); el efecto aplicado registra `p_hist`, `p_ref` y `ε` — funciones puras, en `tests/unidad/test_correccion_precio.py` **[004]**
- [X] T045 [P] [US4] Prueba de integración: `precio_vigente_periodo` se reconstruye de `renglon_venta.precio_aplicado` (moda; media ponderada por cantidad como desempate); un período **sin ventas** → `precio_vigente_periodo = NULL` y `correccion_precio = 0` ("sin corrección de precio", FR-027), nunca un precio inventado — contra PostgreSQL real, en `tests/integracion/test_serie_precio.py` **[004] [001-lectura: renglon_venta, producto, producto_precio_sucursal]**

### Implementación backend para User Story 4

- [X] T046 [P] [US4] Función pura `normalizar_demanda_por_precio(cantidad, p_hist, p_ref, epsilon) -> tuple[Decimal, Decimal]` (valor corregido y delta) en `backend/rasero/dominio/serie_demanda.py` (implementa T044) **[004]**
- [X] T047 [US4] Ampliar `backend/rasero/dominio/serie_demanda.py`: reconstruir `precio_vigente_periodo` de `renglon_venta.precio_aplicado`; resolver `p_ref` actual con `COALESCE(producto_precio_sucursal, producto.precio_vigente)` — la misma resolución que `001` usa al vender (depende de T011) **[004] [001-lectura: renglon_venta, producto, producto_precio_sucursal]**
- [X] T048 [US4] Ampliar `demanda.reconstruir_serie`: aplicar la corrección de precio como **paso (2)** del orden fijo (research.md #3), sobre el valor que dejó la descensura por quiebre; registrar `correccion_precio` y `elasticidad_usada`; período con `precio_vigente_periodo = NULL` → sin corrección (FR-027), en `backend/rasero/servicios/demanda.py` (depende de T012, T046, T047; implementa T045) **[004]**
- [X] T049 [P] [US4] Ampliar la prueba de contrato: `PuntoSerie` incluye `precio_vigente_periodo`, `correccion_precio`, `elasticidad_usada` en `tests/contrato/test_contrato_pronostico.py` (depende de T048, T016)

### Implementación frontend para User Story 4

- [X] T050 [US4] Ampliar `SerieDemanda.tsx`: anotación por período del ajuste de precio (qué precio histórico, qué precio de referencia, qué `ε`); "sin corrección de precio" con texto explícito, nunca sólo con la ausencia de un número, en `frontend/src/componentes/SerieDemanda.tsx` (depende de T048, T018)
- [X] T051 [US4] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras la anotación de precio (depende de T050)

**Checkpoint**: User Stories 1 a 4 funcionan juntas; la serie corregida separa cambio de precio de cambio de demanda base.

---

## Phase 6: User Story 5 - Neutralizar los períodos con promoción activa (Priority: P5, parcial — gancho a `005`)

**Goal**: excluir o marcar los períodos con promoción activa al construir la serie corregida, con el gancho de integración a `005` implementado y documentado; hasta que `005` exista, todos los períodos se tratan como sin promoción (FR-030).

**Independent Test**: con una marca de "promoción activa" provista manualmente para un período (simulando la futura entrada de `005`), ese período queda excluido o marcado en la serie corregida, sigue intacto en la observada, y la exclusión queda registrada.

### Pruebas obligatorias para User Story 5

- [X] T052 [P] [US5] Prueba de integración: un período con `con_promocion = TRUE` (inyectado manualmente, simulando `005`) queda en `demanda_corregida` con `excluido_por_promocion = TRUE`; su `demanda_observada` no cambia (FR-031); la serie no tiene un hueco silencioso, el período sigue visible marcado — contra PostgreSQL real, en `tests/integracion/test_serie_promocion.py` **[004] [005-futuro]**

### Implementación backend para User Story 5

- [X] T053 [US5] Ampliar `backend/rasero/dominio/serie_demanda.py`: punto de integración para leer la marca "promoción activa" por producto, sucursal y período de la fuente de `005` cuando exista; hoy, `con_promocion` siempre `FALSE`, con el gancho documentado en el código (FR-030) (depende de T011) **[004] [005-futuro]**
- [X] T054 [US5] Ampliar `demanda.reconstruir_serie`: **paso (3)** del orden fijo — excluir/marcar los períodos con `con_promocion = TRUE` de la serie a precio normal, registrar `excluido_por_promocion` sin borrar el período (FR-029, FR-031), en `backend/rasero/servicios/demanda.py` (depende de T048, T053; implementa T052) **[004]**
- [X] T055 [P] [US5] Ampliar la prueba de contrato: `PuntoSerie` incluye `con_promocion` y `excluido_por_promocion` en `tests/contrato/test_contrato_pronostico.py` (depende de T054)

### Implementación frontend para User Story 5

- [X] T056 [US5] Ampliar `SerieDemanda.tsx`: período promocional marcado y visible (no un hueco), con texto explícito, en `frontend/src/componentes/SerieDemanda.tsx` (depende de T054, T018)
- [X] T057 [US5] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras la marca de promoción (depende de T056)

**Checkpoint**: User Story 5 en su forma parcial: el gancho de integración está listo y probado; la fuente de la marca "promoción activa" llega con `005`.

---

## Phase 7: User Story 6 - Declarar sustitutos y señalar demanda inflada por quiebre de un sustituto (Priority: P6)

**Goal**: permitir declarar manualmente una relación de sustitución entre dos productos y señalar —como marca cualitativa, no como ajuste numérico automático— los períodos en que un producto vendió por encima de lo típico mientras un sustituto suyo estuvo agotado; alimentar además el ajuste cruzado de la descensura (FR-009 b).

**Independent Test**: se declara una relación de sustitución, se produce un período en que uno tuvo quiebre y el otro vendió por encima de su nivel típico, y el sistema emite una señal explicable sin descontar volumen automáticamente.

### Pruebas obligatorias para User Story 6

- [X] T058 [P] [US6] Prueba unitaria de la señal y del ajuste cruzado: producto en quiebre con sustituto declarado que vendió por encima de su máximo de N → señal en la serie del sustituto (FR-033) y `ajuste_cruzado_sustituto > 0` en el producto (FR-009 b), **sin** descontar volumen del sustituto (FR-034); ambos en quiebre → ni señal ni ajuste (FR-036) — funciones puras, en `tests/unidad/test_ajuste_cruzado.py` (renombrado de `test_sustitucion.py` para no colisionar con la prueba de integración del mismo nombre) **[004]**
- [X] T059 [P] [US6] Prueba de integración: declarar / consultar / retirar una relación de sustitución; una relación mutua son dos filas; `CHECK (id_producto <> id_producto_sustituto)`; `UNIQUE` dirigido (`409` al re-declarar la misma dirección) — contra PostgreSQL real, en `tests/integracion/test_sustitucion.py` **[004] [001-lectura: producto]**

### Implementación backend para User Story 6

- [X] T060 [P] [US6] Funciones puras `exceso_sustituto(demanda_sustituto_en_ventana, maximo_n_sustituto) -> Decimal` y `ajuste_cruzado(estimado_base, excesos) -> Decimal` en `backend/rasero/dominio/censura.py` (implementa T058) **[004]**
- [X] T061 [US6] Servicio `sustitucion.declarar / listar / retirar` en `backend/rasero/servicios/sustitucion.py` (depende de T002; implementa T059) **[004] [001-lectura: producto]**
- [X] T062 [US6] Ampliar `demanda.reconstruir_serie`: **paso (4)** del orden fijo — para cada período de quiebre de `P` con sustitutos declarados, calcular el exceso de cada sustituto (T060) y sumarlo a `correccion_quiebre` vía `ajuste_cruzado_sustituto` (research.md #6); anotar `senal_sustitucion` en la serie del sustituto (FR-033) sin descontar su volumen (FR-034), en `backend/rasero/servicios/demanda.py` (depende de T054, T060, T061) **[004]**
- [X] T063 [US6] Endpoints `GET /sustituciones`, `POST /sustituciones` y `DELETE /sustituciones/{id_sustitucion_producto}` en `backend/rasero/api/pronostico.py` (depende de T061, T004)
- [X] T064 [P] [US6] Ampliar la prueba de contrato: `/sustituciones` (`201`/`400`/`404`/`409`, `204`) y `senal_sustitucion` en `PuntoSerie` en `tests/contrato/test_contrato_pronostico.py` (depende de T062, T063)

### Implementación frontend para User Story 6

- [X] T065 [P] [US6] Cliente HTTP `listarSustituciones`, `declararSustitucion`, `retirarSustitucion` en `frontend/src/servicios/pronostico.ts` (depende de T063)
- [X] T066 [US6] Componente `DeclararSustituto.tsx`: formulario de relación dirigida (producto → sustituto) y lista de relaciones declaradas, integrado en `Pronostico.tsx`, en `frontend/src/componentes/DeclararSustituto.tsx` (depende de T065, T019)
- [X] T067 [US6] Ampliar `SerieDemanda.tsx`: señal "demanda potencialmente inflada por el quiebre de <sustituto>" en los períodos afectados — marca cualitativa con texto, sin número de ajuste (FR-034), en `frontend/src/componentes/SerieDemanda.tsx` (depende de T062, T018)
- [X] T068 [US6] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar sustitutos (depende de T067)

**Checkpoint**: las seis historias funcionan de forma independiente. La rama T014 (evidencia real de `consulta_no_atendida`) quedó implementada al desbloquear `001` su User Story 3.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T069 [P] Ejecutar los 12 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno; el escenario 3 (`consulta_no_atendida`) se comprueba como **xfail documentado**, no como fallo
- [X] T070 [P] Auditar `Pronostico.tsx`, `SerieDemanda.tsx`, `ValidacionDescensura.tsx` y `DeclararSustituto.tsx` en busca de color, radio o tipografía incrustados fuera de `frontend/src/estilos/tokens.css`; verificar la distinción **observado / estimado** con los tres portadores simultáneos (color `#1F5673`, forma, texto)
- [X] T071 Actualizar `DESIGN.md` con la skill de Impeccable (`document`), derivándolo de `Pronostico.tsx` ya construido; sidecar `.impeccable/design.json` actualizado en el mismo cambio
- [X] T072 Ejecutar `pytest tests` completo contra PostgreSQL real (puerto 5442) — las 6 suites obligatorias (T006/T007/T008, T021, T033/T034, T044/T045, T052, T058/T059, y la de contrato T016/T028/T039/T049/T055/T064) — y `tsc -b`, `eslint`, `vite build` del frontend, todo en verde (re-ejecutado tras el desbloqueo de `001` T050–T053: T009 en verde sin `xfail`)
- [X] T073 Verificar que `N`, `α`, `ε`, la ventana de materialización, los tramos del mes y el mínimo de períodos sin quiebre viven **sólo** en `backend/rasero/config/pronostico.py` con los valores por defecto de research.md, sin ninguna constante mágica dispersa por el código (Principio V "acotada")

---

## Dependencies & Execution Order

### Dependencias de fase

- **Foundational (Fase 1)**: sin dependencias externas a este módulo salvo que `001` ya esté migrado. **Bloquea** las seis historias de usuario.
- **Historias de usuario (Fases 2–7)**: todas dependen de Foundational. Dentro de cada una, backend antes que frontend.
- **Polish (Fase final)**: depende de que las seis historias estén completas (T014 ya lo está).

### Dependencias entre historias

El orden **US1 → US2 → US3 → US4 → US5 → US6 está fijado por spec.md y no se reordena** (plan.md, "Estado de implementación por historia"):

- **US1 (descensura por quiebre)** es la corrección base sobre la que operan las demás — el servicio `reconstruir_serie` (T012) es la espina dorsal que US4, US5 y US6 amplían con sus pasos (2), (3) y (4) del orden fijo.
- **US2 (validación sintética)** valida la lógica de US1 sin datos reales de `001`; va inmediatamente después porque sin ella la descensura no tiene prueba de fondo mientras dure el bloqueo de `001`.
- **US3 (pronóstico)** consume la serie corregida de US1 (y de US2 para pruebas); no necesita US4/US5/US6.
- **US4, US5, US6** son refinamientos aditivos sobre `demanda_corregida`, cada uno un paso más del orden fijo; comparten `SerieDemanda.tsx` y `reconstruir_serie`, por lo que construirlos en el orden del spec evita conflictos de edición del mismo archivo.

### Dependencia externa bloqueante

- **T014** (rama `respaldo_quiebre = 'consulta_no_atendida'`, FR-007) — implementada: `001` completó su **User Story 3** (T050–T053). Ninguna otra tarea de `004` la necesitaba.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; endpoints antes que su cliente de frontend.
- Backend completo de la historia antes que su frontend.
- Toda historia con superficie de frontend termina con la verificación `tsc -b` / `eslint` / `vite build`.

### Oportunidades de paralelismo

- T002, T003 y T004 de Foundational pueden ejecutarse en paralelo tras T001 (T004 espera a T002).
- Dentro de una historia, las pruebas marcadas [P] entre sí y las funciones de dominio marcadas [P] entre sí son paralelizables.
- US3 (pronóstico) puede empezar en paralelo con US2 una vez que US1 esté cerrada: `generar_pronostico` (T036) sólo necesita `reconstruir_serie` (T012), no el arnés sintético.
- Las ampliaciones de `reconstruir_serie` de US4, US5 y US6 (T048, T054, T062) tocan el **mismo archivo** `servicios/demanda.py` en el mismo punto (el orden fijo de correcciones): **no** son paralelas entre sí, van en secuencia.

---

## Parallel Example: User Story 1

```bash
# Lanzar juntas las pruebas independientes de esta historia:
Task: "Prueba unitaria del método base de descensura en tests/unidad/test_censura.py"
Task: "Prueba de integración de reconstruir_serie en tests/integracion/test_reconstruir_serie.py"
Task: "Prueba de integración de listado de sucursal sin N+1 en tests/integracion/test_demanda_sucursal.py"
Task: "Prueba xfail del camino consulta_no_atendida en tests/integracion/test_descensura_consulta_no_atendida.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Foundational — crítica, bloquea todo lo demás.
2. Completar Fase 2: User Story 1, con sus pruebas obligatorias en verde.
3. **Detenerse y validar**: ejecutar los escenarios 1, 2, 4 y 12 de `quickstart.md`.
4. Demostrar: serie observada intacta, serie corregida por quiebre `>=` observada y explicable, por método base.

### Entrega incremental

1. Foundational → esquema propio, parámetros y router listos.
2. + US1 (descensura por quiebre, método base) → probar de forma independiente → MVP demostrable.
3. + US2 (validación sintética) → probar de forma independiente (escenario 5 de `quickstart.md`) → la descensura queda validada.
4. + US3 (pronóstico) → probar de forma independiente (escenarios 9, 10, 11).
5. + US4 (corrección por precio) → probar de forma independiente (escenario 7).
6. + US5 (neutralización de promoción, parcial) → probar de forma independiente (escenario 8).
7. + US6 (sustitutos) → probar de forma independiente (escenario 6).
8. Fase final: `quickstart.md` completo, auditoría de tokens, `DESIGN.md` actualizado, suite completa en verde.
9. **`001` implementó su User Story 3**: se quitó el `xfail` de T009, se completó T014 y se re-ejecutó T072 — todo en verde.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Foundational en conjunto.
2. Una persona construye US1 (espina dorsal de datos: `reconstruir_serie`).
3. En paralelo, otra persona prepara el generador sintético de US2 (T023) y el arnés de validación.
4. Cerrada US1, US2 y US3 pueden repartirse (US3 sólo necesita `reconstruir_serie`).
5. US4 → US5 → US6 van en secuencia por la edición compartida de `servicios/demanda.py` y `SerieDemanda.tsx`.

---

## Notes

- Las tareas [P] tocan archivos distintos y no dependen de una tarea incompleta.
- La etiqueta [Story] traza cada tarea a su historia de usuario en spec.md.
- Las 6 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md están marcadas y deben pasar antes de fusionar, **todas contra PostgreSQL real en el puerto 5442**; no hay pruebas de interfaz, maquetación ni componentes visuales.
- **[004]** = tabla propia de este módulo; **[001-lectura: ...]** = consulta de solo lectura a `001` (nunca se altera su esquema ni se duplica); **[001-lectura: consulta_no_atendida]** = la lectura bloqueada por `001` User Story 3; **[005-futuro]** = gancho a la marca de promoción de `005`, inerte hoy.
- `004` **no escribe en ninguna tabla de `001`** — a diferencia de `003`, que escribía en `producto_precio_sucursal` vía `fijar_precio_sucursal`. Por eso no hay fase de Setup con prerrequisito cruzado ni ninguna etiqueta `[001-escritura]`.
- `GET /demanda` de una sucursal (T012) DEBE resolverse con una consulta de conjunto, nunca iterando el reconstructor de un solo producto — ver research.md #3 y la prueba T008, que existe específicamente para impedir que esa distinción se pierda durante la implementación.
- `N`, `α` y `ε` son parámetros de configuración con los valores de arranque de research.md (30, 0.3, 1.0); ajustarlos es calibración **dentro** de los métodos ya fijados por `/speckit-clarify`, no una reapertura de FR-009, FR-019 o FR-020.
- Fuera de alcance de este desglose: cualquier librería de series temporales o estadística (statsmodels, Prophet, ML), descomposición estacional formal, estacionalidad anual/festiva, o inferencia automática de relaciones de sustitución — todos evaluados y rechazados en research.md #2, #7 y #8d.

---

## Bloqueado por 001 — RESUELTO

`001-core-ventas-inventario` implementó su User Story 3 (`consulta_no_atendida`, T050–T053). Con eso:

- **T014** — implementada: rama `respaldo_quiebre = 'consulta_no_atendida'` en `backend/rasero/servicios/demanda.py`, paso (1c) de `reconstruir_serie`.
- **T009** — el marcador `@pytest.mark.xfail(strict=True)` se retiró; la prueba está en verde.
- **T072** — se re-ejecutó tras el desbloqueo: suite completa en verde.

Ninguna tarea de `004` queda bloqueada.

**Nota de secuencia (no bloqueo por `001`)**: la parte de T026/T022 que exige que `generar_pronostico` responda `409` para un producto sólo sintético se verifica en **User Story 3** (T036/T037), donde se crea esa función. US2 entregó el mecanismo (`es_producto_solo_sintetico` + guarda `es_sintetico = FALSE` en el upsert de producción) y la prueba de aislamiento de `GET /demanda`, que sí es medible ahora.
