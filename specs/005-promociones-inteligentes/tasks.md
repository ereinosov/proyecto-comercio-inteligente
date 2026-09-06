---

description: "Task list template for feature implementation"
---

# Tasks: Promociones Inteligentes

**Input**: Documentos de diseño desde `/specs/005-promociones-inteligentes/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados contra la constitución **v2.2.6** (sin cambios para `005` desde v2.2.5). Requiere que `001-core-ventas-inventario` User Story 1 y `002-clientes-fidelizacion` completo ya estén migrados y en ejecución: este módulo **sólo lee** de `001` (`venta`, `renglon_venta`, `producto`, `producto_precio_sucursal`, `sucursal`, `turno`) y de `002` (`cliente` vía `GET /clientes/cumpleanos`, `visita`, `intervalo_compra`, `senal_fuga`). **No lee ni escribe `existencia` ni `movimiento_inventario`** — la disponibilidad al vender la resuelve `001` (FR-011). **No escribe en ninguna tabla ajena**, ni siquiera vía función-puente, a diferencia de `003`. La enmienda constitucional **v2.2.5** (que reconcilia las 6 entidades de `005`: `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`) ya está aplicada (commit `a2bb668`). **Ninguna tarea está bloqueada**: `002` está completo (checkpoint `2fd6381`), `001` User Story 1 completa (`873228d`), `004` completo (`41ad08c`) y esperando la marca de `005`.

**Pruebas**: se incluyen las 7 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md (Principio III — una aleatorización correlacionada con un atributo del cliente invalida silenciosamente toda afirmación de incrementalidad y con ella la decisión de gastar margen; una prueba de significancia mal calculada declara "efectiva" una campaña con suerte; una redención que escribe contra `001` corrompe inventario), intercaladas junto a la funcionalidad que verifican. **Todas corren contra PostgreSQL real en el puerto 5442, nunca contra mocks ni SQLite** — mismo criterio que `001`–`004`. No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario, en el **orden de prioridad ya fijado por spec.md y no renegociable**: US1 cupón por fecha fija — **con su ciclo de redención completo** (P1) → US2 empuje por recompra con reserva de precio — con su redención (P2) → US3 reactivación con experimento de control (P3, la más compleja: asignación de grupos con semilla, tamaño mínimo de muestra, prueba z) → US4 exposición de la **marca agregada** de "promoción activa" hacia `004` (P4). La ruta `POST /promociones/redenciones` y el modelo `redencion_promocion` se construyen **en US1** (mecanismo 1) y las historias siguientes **reutilizan** ese endpoint y modelo, cada una añadiendo el efecto de su propio mecanismo. Backend antes que frontend dentro de cada historia. Fundamento (esquema, modelos, router, parámetros, helpers puros) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta). Dos tareas que editan el **mismo** archivo no llevan ambas `[P]`: la segunda depende de la primera.
- **[Story]**: historia de usuario a la que pertenece (US1 … US4)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende
- Cada tarea que toca datos indica explícitamente de dónde:
  - **[005]** — tabla propia de este módulo (`campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`)
  - **[001-lectura: ...]** — consulta de **solo lectura** a una o más tablas de `001` (nunca se altera su esquema ni se duplica). `005` no lee `existencia` ni `movimiento_inventario`; los tests de frontera los consultan **sólo** para verificar por conteo que no hubo escritura.
  - **[002-lectura: ...]** — consulta de **solo lectura** a una o más tablas de `002` (nunca se altera su esquema; `senal_fuga` nunca se modifica — FR-028)

## Convención de rutas (fijada en plan.md, extiende la de 001–004, no negociable)

- Backend: `backend/rasero/` (`dominio/`, `persistencia/`, `servicios/`, `api/`, `config/`, `tareas/`) y `backend/migraciones/versions/`
- Frontend: `frontend/src/` (`componentes/`, `pantallas/`, `servicios/`) — reutiliza `frontend/src/estilos/tokens.css` sin tokens nuevos; **registro de Análisis** para `Promociones.tsx` (radio 6px, Source Serif 4); **registro de Operación** sólo para `AplicarPromocionVenta.tsx` dentro de `Venta.tsx` (radio 2px, IBM Plex Sans, sin animación salvo confirmación), no bloqueante — mismo patrón que `IdentificarCliente.tsx` de `002`
- Pruebas: `tests/` en la raíz (`unidad/`, `integracion/`, `contrato/`)

---

## Phase 1: Foundational (bloqueante para las cuatro historias)

**Propósito**: esquema de las seis entidades propias, modelos ORM, el router compartido, el módulo único de parámetros de configuración y las funciones de dominio puras.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T001 Crear `backend/migraciones/versions/0005_promociones_inteligentes.py` con las seis tablas de data-model.md: `campania` (`tipo ENUM`, `id_sucursal NULL`, `CHECK (ventana_hasta >= ventana_desde)`); `cupon` con `UNIQUE (id_cliente, fecha_objetivo)` (FR-007) e índice `(estado, valido_hasta)`; `oferta_recompra` con índice único parcial `UNIQUE (id_cliente, id_producto) WHERE desenlace = 'pendiente'` (FR-014), `justificacion JSONB`, e índice `(estado_reserva, reserva_hasta)`; `experimento_reactivacion` con todas las columnas de parametrización y resultado (semilla, tamaño de muestra, tasas, z, p, veredicto); `asignacion_experimento` con `grupo ENUM('tratamiento','control')` **sin tercer valor**, `id_senal_fuga BIGINT NOT NULL`, `UNIQUE (id_experimento_reactivacion, id_cliente)` e índice `(id_cliente)`; `redencion_promocion` con `id_venta BIGINT NOT NULL` (referencia de solo lectura, sin FK con cascada), `CHECK` de exactamente un `id_*` de origen, tres índices únicos parciales sobre los `id_*` de origen, e índice `(id_sucursal, periodo)` para la marca activa; `downgrade` que elimina las seis tablas en orden inverso de dependencia **[005]**
- [X] T002 [P] Crear los modelos SQLAlchemy 2.x `Campania`, `Cupon`, `OfertaRecompra`, `ExperimentoReactivacion`, `AsignacionExperimento`, `RedencionPromocion` en `backend/rasero/persistencia/modelos.py` con los `CheckConstraint` de `data-model.md` (depende de T001) **[005]**
- [X] T003 [P] Crear el módulo único de parámetros de configuración `backend/rasero/config/promociones.py` con los valores de arranque de research.md #13 (`ANTELACION_GENERACION_CUPON_DIAS = 7`, `VALIDEZ_CUPON_DIAS = 14`, `DESCUENTO_CUPON_CUMPLEANOS_PCT = 10.00`, `MARGEN_ANTICIPACION_RECOMPRA = 0.20`, `VENTANA_HISTORIAL_RECOMPRA_DIAS = 180`, `MIN_COMPRAS_PRODUCTO_RECOMPRA = 3`, `DESCUENTO_RECOMPRA_PCT = 8.00`, `VENTANA_RESERVA_RECOMPRA_DIAS = 21`, `SEMILLA_ALEATORIZACION = 20260905`, `PROPORCION_TRATAMIENTO = 0.5`, `ALFA_SIGNIFICANCIA = 0.05`, `PODER_ESTADISTICO = 0.80`, `TASA_RETORNO_BASE_ESPERADA = 0.15`, `MDE_REACTIVACION_PP = 15`, `DESCUENTO_REACTIVACION_PCT = 15.00`, `VENTANA_MEDICION_REACTIVACION_DIAS = 42`), sobrescribibles por variable de entorno — mismo patrón que `config/pronostico.py` de `004`; sin ninguna constante mágica dispersa (Principio V "acotada")
- [X] T004 [P] Crear el router base `backend/rasero/api/promociones.py` con prefijo `/promociones` y montarlo en `backend/rasero/api/aplicacion.py` (depende de T002)
- [X] T005 [P] Funciones de dominio puras compartidas en `backend/rasero/dominio/promociones.py`: `ventana_validez_cupon(fecha_objetivo, antelacion_dias, validez_dias) -> tuple[date, date]` y `periodo_local_venta(instante, zona_horaria) -> date` (`(instante AT TIME ZONE zona)::date`, mismo criterio de día local que `001`/`004` — 005 implementa el suyo, no importa el de `004`)

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 2: User Story 1 - Generar el cupón por fecha fija y cerrar su ciclo de redención (Priority: P1) 🎯 MVP

**Goal**: generar un `cupon` para cada cliente cuya fecha de cumpleaños entra en la ventana de generación (vía la consulta de cumpleañeros de `002`, nunca `cliente.fecha_nacimiento`, de forma idempotente y sin grupo de control) **y** cerrar su ciclo: el cliente puede redimir el cupón en una venta de `001` mediante `POST /promociones/redenciones`, dejándolo en estado `'redimido'`, sin que `005` escriba en ninguna tabla de `001`. Esta historia construye la **base compartida** de la redención (modelo `redencion_promocion`, servicio `registrar_redencion`, endpoint) que US2 y US3 reutilizan.

**Independent Test**: para un cliente con fecha de nacimiento conocida y una ventana que la cubre, el sistema emite exactamente un cupón; ejecutar la generación dos veces no lo duplica; un cliente anonimizado no recibe cupón; y el cliente puede redimir ese cupón en una venta registrada por `001` (`POST /promociones/redenciones`), quedando `cupon.estado = 'redimido'`, con un segundo POST idempotente (200) y sin que se cree ningún `movimiento_inventario` ni cambie `existencia`/`venta`/`renglon_venta`.

### Pruebas obligatorias para User Story 1

- [X] T006 [P] [US1] Prueba unitaria de la ventana de validez del cupón: `ventana_validez_cupon` produce `valido_desde = fecha_objetivo − ANTELACION_GENERACION_CUPON_DIAS` y `valido_hasta = fecha_objetivo + VALIDEZ_CUPON_DIAS` (research.md #6) — función pura, en `tests/unidad/test_promociones_dominio.py` (depende de T005) **[005]**
- [X] T007 [P] [US1] Prueba de integración (frontera con `002`): `generar_cupones` obtiene los clientes **exclusivamente** de la consulta de cumpleañeros de `002` (FR-002), nunca lee `cliente.fecha_nacimiento`; un cliente `anonimizado` no aparece y no recibe cupón (FR-003) — contra PostgreSQL real, puerto 5442, en `tests/integracion/test_generacion_cupones.py` (depende de T001, T002) **[005] [002-lectura: cliente]**
- [X] T008 [US1] Prueba de integración de idempotencia de la generación (FR-007): ejecutar la generación dos veces para el mismo rango, y una tercera para un rango solapado, **no** crea un segundo cupón por la misma `(id_cliente, fecha_objetivo)` (`UNIQUE`); la segunda corrida reporta `cupones_generados: 0` — contra PostgreSQL real, en `tests/integracion/test_generacion_cupones.py` (depende de T007) **[005]**
- [X] T009 [US1] Prueba de integración del ciclo de redención del cupón y **frontera con `001`**: registrar una redención de un cupón vigente sobre una venta de `001` vincula la venta y deja `cupon.estado = 'redimido'` (FR-005, FR-030); redimir un cupón fuera de `[valido_desde, valido_hasta]` → `400`; un segundo `POST /promociones/redenciones` con el mismo `id_cupon` → `200` con la misma `id_redencion_promocion` (idempotencia por índice único parcial); comprobar por conteo directo que `POST /promociones/redenciones` **no** añadió filas a `movimiento_inventario`, no cambió `existencia`, y no modificó `venta` ni `renglon_venta` (FR-029) — contra PostgreSQL real, en `tests/integracion/test_generacion_cupones.py` (depende de T008) **[005] [001-lectura: venta, renglon_venta, turno, sucursal]**

### Implementación backend para User Story 1

- [X] T010 [P] [US1] Implementar `ventana_validez_cupon(...)` en `backend/rasero/dominio/promociones.py` (depende de T005; implementa T006) **[005]**
- [X] T011 [US1] Servicio `promociones.generar_cupones(sesion, *, desde, hasta, nombre_campania=None)` en `backend/rasero/servicios/promociones.py`: crea una `campania` de `tipo = 'fecha_fija'`, llama en proceso a `servicio_clientes.clientes_con_cumpleanos(sesion, desde, hasta)` de `002`, y por cada cliente crea un `cupon` con `fecha_objetivo` (día/mes del cumpleaños, año del rango), `porcentaje_descuento` snapshot de config, y `estado = 'generado'`, capturando la violación de `UNIQUE (id_cliente, fecha_objetivo)` por fila (idempotencia — mismo patrón que `registrar_visita` de `002`) (depende de T002, T010; implementa T007, T008) **[005] [002-lectura: cliente]**
- [X] T012 [US1] Barrido de vencimiento en `backend/rasero/servicios/promociones.py`: marcar `cupon.estado = 'vencido'` cuando `CURRENT_DATE > valido_hasta` y no hay redención — ejecutado dentro de `generar_cupones` y al listar cupones (depende de T011) **[005]**
- [X] T013 [US1] Servicio **base** `promociones.registrar_redencion(sesion, *, id_venta, tipo_origen, id_cupon=None, id_oferta_recompra=None, id_asignacion_experimento=None, id_producto=None)` en `backend/rasero/servicios/promociones.py`: valida la coherencia `tipo_origen` ↔ `id_*` (`CHECK` de un solo origen); rechaza (`400`) un cupón fuera de `[valido_desde, valido_hasta]` y una `id_asignacion_experimento` cuyo `grupo` sea `'control'` (acceso al modelo `AsignacionExperimento` de T002, sin servicio de US3); deriva y denormaliza `id_sucursal` y `periodo` de `venta → turno → sucursal` con `periodo_local_venta` (T005, research.md #4); calcula `descuento_aplicado` de `renglon_venta.precio_aplicado`; inserta `redencion_promocion` de forma **idempotente** (índice único parcial sobre el `id_*` de origen — un segundo POST devuelve la fila existente con `200`); en la misma transacción marca `cupon.estado = 'redimido'` (las ramas `oferta_recompra` y `reactivacion` se completan en US2 y no requieren más lógica aquí). **No** escribe en ninguna tabla de `001` ni de `002` (depende de T002, T005, T012; implementa T009) **[005] [001-lectura: venta, renglon_venta, turno, sucursal]**
- [X] T014 [US1] Endpoints `POST /promociones/cupones/generacion`, `GET /promociones/cupones?id_cliente=&estado=&vigentes=` y `POST /promociones/redenciones` en `backend/rasero/api/promociones.py` (depende de T011, T013, T004)
- [X] T015 [P] [US1] Tarea programada `backend/rasero/tareas/generacion_cupones.py`, invocable con `python -m rasero.tareas.generacion_cupones <desde> <hasta>`, que llama a `generar_cupones` fuera del camino crítico de cualquier petición HTTP — mismo patrón que `tareas/mantenimiento_clientes.py` de `002` (depende de T011)
- [X] T016 [P] [US1] Prueba de contrato de `POST /promociones/cupones/generacion`, `GET /promociones/cupones` y `POST /promociones/redenciones` contra `contracts/openapi.yaml` (forma feliz + `400` por rango inválido / cupón fuera de ventana / origen incoherente + `404` + `200` de idempotencia en la redención), con el formato de error `{codigo, mensaje}`, en `tests/contrato/test_contrato_promociones.py` (depende de T014)

### Implementación frontend para User Story 1

- [X] T017 [P] [US1] Cliente HTTP `generarCupones`, `listarCupones`, `registrarRedencion` en `frontend/src/servicios/promociones.ts` (depende de T014)
- [X] T018 [US1] Componente `GeneracionCupones.tsx` (registro de Análisis: radio 6px, Source Serif 4, líneas bajo 80 caracteres) para disparar la generación de un rango y ver los cupones emitidos con su estado (generado / redimido / vencido); pantalla `Promociones.tsx` con la sección de cupones; nueva pestaña "Promociones" en `frontend/src/App.tsx` (depende de T017). Invoca `new-work` de Impeccable (mundo visual de Análisis ya fijado por la constitución, `PRODUCT.md` existente, no se repite `init`)
- [X] T019 [US1] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la pestaña Promociones (depende de T018)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente — cupón por fecha fija con su ciclo completo (generación → redención → estado `'redimido'`), sin ninguna maquinaria estadística. MVP.

---

## Phase 3: User Story 2 - Empujar la recompra con reserva de precio y cerrar su redención (Priority: P2)

**Goal**: proponer, a un cliente cuyo tiempo desde la última compra se acerca a su intervalo de compra esperado (de `002`), una oferta de un producto que suele recomprar, con una **reserva de precio** (garantiza el precio, no el stock) que **no toca el inventario de `001`**; y cerrar su redención: redimir la oferta deja `oferta_recompra.desenlace = 'comprado'`, **reutilizando** el endpoint y el modelo `redencion_promocion` de US1 (no se duplica la tabla ni la ruta).

**Independent Test**: para un cliente con `intervalo_compra.estado = 'calculado'` y un producto claramente recomprado, al acercarse a su intervalo el sistema propone una oferta con su `precio_garantizado`; generar la oferta no produce ningún movimiento de inventario; no se crea una segunda oferta activa para el mismo par (cliente, producto); y redimir esa oferta (mismo `POST /promociones/redenciones` de US1, con `tipo_origen: "oferta_recompra"`) la deja en `desenlace = 'comprado'`, mientras que una oferta cuya reserva venció sigue en `'reserva_vencida'`.

### Pruebas obligatorias para User Story 2

- [X] T020 [US2] Prueba unitaria de la selección del producto de recompra y del filtro de elegibilidad: `seleccionar_producto_recompra` devuelve el producto con mayor número de ventas distintas en la ventana (≥ `MIN_COMPRAS_PRODUCTO_RECOMPRA`, desempate por compra más reciente — research.md #7); `cliente_en_ventana_recompra` es `True` sólo si los días sin compra están en `[intervalo · (1 − MARGEN_ANTICIPACION_RECOMPRA), intervalo]` — funciones puras, en `tests/unidad/test_promociones_dominio.py` (depende de T006) **[005]**
- [X] T021 [P] [US2] Prueba de integración de **frontera con el inventario de `001`** (FR-010, FR-011): `detectar_ofertas_recompra` **no** crea ningún `movimiento_inventario` ni cambia `existencia` de `001` (verificación por conteo); `precio_garantizado` = `COALESCE(producto_precio_sucursal.precio_vigente, producto.precio_vigente)` de la sucursal − `DESCUENTO_RECOMPRA_PCT` — contra PostgreSQL real, en `tests/integracion/test_oferta_recompra.py` (depende de T001, T002) **[005] [001-lectura: producto, producto_precio_sucursal]**
- [X] T022 [US2] Prueba de integración de idempotencia y vencimiento (FR-014): dos detecciones seguidas no crean una segunda `oferta_recompra` con `desenlace = 'pendiente'` para el mismo `(id_cliente, id_producto)` (índice único parcial); una oferta cuya `reserva_hasta` venció sin compra pasa a `estado_reserva = 'vencida'` y `desenlace = 'reserva_vencida'`, sin liberar stock (nunca se apartó) — contra PostgreSQL real, en `tests/integracion/test_oferta_recompra.py` (depende de T021) **[005] [002-lectura: intervalo_compra, visita]**
- [X] T023 [US2] Prueba de integración de la redención de la oferta de recompra: `POST /promociones/redenciones` con `tipo_origen: "oferta_recompra"` sobre una oferta `pendiente` deja `oferta_recompra.desenlace = 'comprado'`; una oferta ya en `'reserva_vencida'` no puede quedar `'comprado'`; se reutiliza el endpoint y el modelo de US1, no se crea una tabla ni una ruta nueva — contra PostgreSQL real, en `tests/integracion/test_oferta_recompra.py` (depende de T022) **[005] [001-lectura: venta]**

### Implementación backend para User Story 2

- [X] T024 [US2] Funciones puras `seleccionar_producto_recompra(historial_compras) -> int | None` y `cliente_en_ventana_recompra(dias_sin_compra, intervalo_esperado_dias, margen) -> bool` añadidas a `backend/rasero/dominio/promociones.py` (funciones nuevas, sin solape con `ventana_validez_cupon` de T010) (depende de T010; implementa T020) **[005]**
- [X] T025 [US2] Servicio `promociones.detectar_ofertas_recompra(sesion, *, id_sucursal)` en `backend/rasero/servicios/promociones.py`: crea una `campania` de `tipo = 'recompra'`; para cada cliente con `intervalo_compra.estado = 'calculado'` en `002` que cumple `cliente_en_ventana_recompra` (T024), consulta su historial identificado (`visita → venta → renglon_venta` de `001`, ventana `VENTANA_HISTORIAL_RECOMPRA_DIAS`), elige el producto con `seleccionar_producto_recompra` (T024), resuelve el precio de la sucursal y aplica `DESCUENTO_RECOMPRA_PCT` → `precio_garantizado`, y crea la `oferta_recompra` con su `justificacion` (JSONB con los `id_venta` que la sustentan), capturando la violación del índice único parcial. **No** consulta ni escribe `existencia` ni `movimiento_inventario` (depende de T002, T013, T024; implementa T021, T022) **[005] [001-lectura: venta, renglon_venta, producto, producto_precio_sucursal] [002-lectura: intervalo_compra, visita]**
- [X] T026 [US2] Barrido de vencimiento de la reserva en `backend/rasero/servicios/promociones.py`: `estado_reserva = 'vencida'` y `desenlace = 'reserva_vencida'` cuando `CURRENT_DATE > reserva_hasta` y `desenlace = 'pendiente'` (depende de T025) **[005]**
- [X] T027 [US2] Completar la rama `oferta_recompra` de `promociones.registrar_redencion` (T013): al redimir una oferta `pendiente`, marcar `oferta_recompra.desenlace = 'comprado'` en la misma transacción — **una sola línea de efecto**, reutiliza toda la validación y la idempotencia de T013, no toca el endpoint ni el modelo (depende de T013, T026; implementa T023) **[005]**
- [X] T028 [US2] Endpoints `POST /promociones/ofertas-recompra/deteccion` y `GET /promociones/ofertas-recompra?id_cliente=&desenlace=` en `backend/rasero/api/promociones.py` (depende de T025, T004)
- [X] T029 [P] [US2] Ampliar la prueba de contrato con ambos endpoints de ofertas (forma feliz + `404` cuando la sucursal no existe) y con la rama `oferta_recompra` de `POST /promociones/redenciones` en `tests/contrato/test_contrato_promociones.py` (depende de T028, T016)

### Implementación frontend para User Story 2

- [X] T030 [P] [US2] Cliente HTTP `detectarOfertasRecompra`, `listarOfertasRecompra` añadidos a `frontend/src/servicios/promociones.ts` (funciones nuevas, sin solape con las de T017) (depende de T028, T017)
- [X] T031 [US2] Componente `OfertasRecompra.tsx`: lista de ofertas propuestas con su producto, su `precio_garantizado` y su `justificacion` (qué compras del cliente la sustentan — FR-009, Principio V "explicable"); integrado en `Promociones.tsx` (depende de T030, T018)
- [X] T032 [US2] Componente `AplicarPromocionVenta.tsx` (**registro de Operación**: radio 2px, IBM Plex Sans con cifras tabulares, sin animación salvo la confirmación de la acción): lista los cupones (US1) y ofertas (US2) vigentes del cliente identificado para que el cajero marque uno como aplicado y registre la redención **después** de la venta — **no bloqueante** (si `005` no responde, el cobro sigue), mismo patrón exacto que `IdentificarCliente.tsx` de `002`, en `frontend/src/componentes/AplicarPromocionVenta.tsx` (depende de T017, T030)
- [X] T033 [US2] Montar `AplicarPromocionVenta` en `frontend/src/pantallas/Venta.tsx` en el mismo punto de extensión donde ya vive `IdentificarCliente` (cuando hay un cliente identificado) — `Venta.tsx` se **amplía**, no se reescribe; no cambia el flujo de cobro (depende de T032)
- [X] T034 [US2] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar las ofertas de recompra y el componente de caja (depende de T033)

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente; la reserva de precio queda demostrada sin ninguna escritura contra el inventario de `001`, y ambos mecanismos comparten un único `POST /promociones/redenciones`.

---

## Phase 4: User Story 3 - Medir la reactivación de clientes inactivos contra un grupo de control (Priority: P3)

**Goal**: repartir los clientes con `senal_fuga` activa de `002` en tratamiento/control por aleatorización real con semilla fija, calcular el tamaño mínimo de muestra, ofrecer el descuento sólo al tratamiento, y al cerrar la ventana medir el % de retorno de cada grupo y juzgar la incrementalidad con una prueba z de dos proporciones (p < 0,05). El grupo de control es obligatorio (Lectura Crítica n.º 6, FR-023).

**Independent Test**: para una población de elegibles conocida, la asignación es reproducible con la misma semilla y no predecible por la paridad del id; sólo el tratamiento recibe el descuento (redimir la asignación de un control por el `POST /promociones/redenciones` de US1 → `400`); el cierre calcula incrementalidad, z, p y veredicto; una población menor que `2 × n*` se marca "muestra insuficiente"; ninguna `senal_fuga` de `002` se modifica.

### Pruebas obligatorias para User Story 3

- [X] T035 [P] [US3] Prueba unitaria de `asignar_grupos` sobre **múltiples semillas** (no una sola corrida): para ~200 semillas distintas, la fracción media asignada a tratamiento converge a `PROPORCION_TRATAMIENTO`; la proporción de `id_cliente` **pares** en tratamiento no difiere significativamente de la de control (sin correlación con el id — SC-006); misma semilla + mismos ids → **exactamente** los mismos grupos en dos llamadas (SC-005); semilla distinta → grupos distintos — función pura, en `tests/unidad/test_experimento_asignacion.py` (depende de T005) **[005]**
- [X] T036 [P] [US3] Prueba unitaria de la prueba z de dos proporciones y del tamaño mínimo de muestra, en **cuatro casos** contra valores calculados a mano: (a) incrementalidad positiva significativa → `valor_p < 0,05` → `veredicto = 'efectivo'`; (b) incrementalidad **negativa** → nunca `'efectivo'` (Edge Case); (c) incrementalidad positiva **no significativa** (`valor_p ≥ 0,05`) → `'no_efectivo'`; (d) `tamano_minimo_muestra(p_control = 0.15, mde = 15, alfa = 0.05, poder = 0.80)` ≈ **121** por grupo (research.md #10b). El valor p usa `math.erf`, no `scipy` — en `tests/unidad/test_prueba_z.py` (depende de T005) **[005]**
- [X] T037 [P] [US3] Prueba de integración del **ciclo de vida del experimento** (sin depender de rutas de otras historias): crear el experimento asigna cada elegible a un `grupo` y registra la semilla; una población con `n_elegibles < 2 × tamano_minimo_muestra` crea el experimento con `veredicto = 'muestra_insuficiente'` y **sin** filas de `asignacion_experimento` (FR-025); parámetros inválidos (`ventana_medicion_dias <= 0`, `mde_puntos_porcentuales` fuera de `(0, 100)`, `porcentaje_descuento` fuera de `(0, 100)`) → `400`; crear un segundo experimento mientras hay uno `en_curso` → `409`; cerrar tras la ventana calcula `retorno_tratamiento`, `retorno_control`, `incrementalidad`, `estadistico_z`, `valor_p` y `veredicto` (FR-019 a FR-024); cerrar dos veces da el mismo resultado; cerrar un experimento cuya ventana no venció, o uno `muestra_insuficiente`, → `409` — contra PostgreSQL real, en `tests/integracion/test_experimento_reactivacion.py` (depende de T001, T002) **[005] [002-lectura: senal_fuga, visita]**
- [X] T038 [US3] Prueba de integración de **frontera con `002`** (FR-028) y de la redención de reactivación: crear el experimento y cerrarlo **no** cambia el `estado` ni el `instante_deteccion` de ninguna `senal_fuga` de `002`; `asignacion_experimento.id_senal_fuga` es idéntico antes y después del cierre (referencia de auditoría inmutable); `POST /promociones/redenciones` con `tipo_origen: "reactivacion"` y la `id_asignacion_experimento` de un cliente de **control** → `400` (usa el endpoint base de US1, ya construido — FR-018), y con la de un cliente de **tratamiento** → `201`/`200` sin alterar `asignacion_experimento` — contra PostgreSQL real, en `tests/integracion/test_experimento_reactivacion.py` (depende de T014, T037) **[005] [002-lectura: senal_fuga]**

### Implementación backend para User Story 3

- [X] T039 [P] [US3] Funciones puras en `backend/rasero/dominio/experimento.py`: `asignar_grupos(ids_elegibles, *, semilla, proporcion_tratamiento) -> dict[int, str]` (`sorted` + `random.Random(semilla).shuffle`, Mersenne Twister de la biblioteca estándar — research.md #9); `tamano_minimo_muestra(*, p_control, mde_puntos_porcentuales, alfa, poder) -> int` (research.md #10b, con `z_{α/2} = 1.959964`, `z_β = 0.841621`); `prueba_z_dos_proporciones(retornos_t, n_t, retornos_c, n_c) -> ResultadoPrueba` con `incrementalidad`, `estadistico_z` y `valor_p = 1 − erf(|z| / sqrt(2))` (`math.erf`, dos colas — research.md #10a); `veredicto(incrementalidad, valor_p, alfa) -> str`. Toda la aritmética con `Decimal` (incluida la raíz vía `Decimal.sqrt()`), sólo `math.erf` toca `float` y su salida se cuantiza a `NUMERIC` (implementa T035, T036) **[005]**
- [X] T040 [US3] Servicio `experimentos.crear_experimento(sesion, *, id_sucursal=None, semilla=None, ventana_medicion_dias=None, porcentaje_descuento=None, mde_puntos_porcentuales=None, nombre_campania=None)` en `backend/rasero/servicios/experimentos.py`: valida los parámetros (`400`) y rechaza (`409`) si ya hay un `experimento_reactivacion` con `veredicto = 'en_curso'`; consulta los clientes con `senal_fuga.estado = 'activa'` en `002` que no estén ya en un experimento en curso; calcula `tamano_minimo_muestra` (T039); si `n_elegibles >= 2 × n*` crea la `campania` (`tipo = 'reactivacion'`), el `experimento_reactivacion` (`veredicto = 'en_curso'`, semilla y algoritmo registrados) y una `asignacion_experimento` por cliente con su `grupo` (de `asignar_grupos`, T039) y su `id_senal_fuga`; si no, crea el experimento con `veredicto = 'muestra_insuficiente'` y sin asignaciones (depende de T002, T039; implementa T037) **[005] [002-lectura: senal_fuga]**
- [X] T041 [US3] Servicio `experimentos.cerrar_experimento(sesion, *, id_experimento_reactivacion)` en `backend/rasero/servicios/experimentos.py`: para cada `asignacion_experimento`, fija `retorno = TRUE` (y `id_venta_retorno`, `instante_retorno`) si el cliente registró una `visita` de `002` en `[instante_asignacion, instante_asignacion + ventana_medicion_dias]` (research.md #11); calcula las tasas por grupo, aplica `prueba_z_dos_proporciones` y `veredicto` (T039), persiste todo en el `experimento_reactivacion` con `instante_cierre`; **idempotente** (cerrar dos veces = mismo resultado); `409` si la ventana no venció o el experimento es `muestra_insuficiente` (depende de T040; implementa T037, T038) **[005] [002-lectura: visita]**
- [X] T042 [US3] Endpoints `POST /promociones/experimentos`, `GET /promociones/experimentos/{id_experimento_reactivacion}`, `GET /promociones/experimentos/{id_experimento_reactivacion}/asignaciones` y `POST /promociones/experimentos/{id_experimento_reactivacion}/cierre` en `backend/rasero/api/promociones.py` (depende de T040, T041, T004)
- [X] T043 [P] [US3] Ampliar la prueba de contrato con los cuatro endpoints de experimento (forma feliz + `400` por parámetros inválidos + `404` + `409` por experimento en curso o cierre no aplicable) en `tests/contrato/test_contrato_promociones.py` (depende de T042, T029)

### Implementación frontend para User Story 3

- [X] T044 [P] [US3] Cliente HTTP `crearExperimento`, `obtenerExperimento`, `obtenerAsignaciones`, `cerrarExperimento` añadidos a `frontend/src/servicios/promociones.ts` (funciones nuevas, sin solape con las de T017/T030) (depende de T042, T030)
- [X] T045 [US3] Componente `ResultadoExperimento.tsx`: el % de retorno **observado** de cada grupo (dato, tinta normal) frente a la incrementalidad, el estadístico z, el valor p y el veredicto (**inferencia**: color `estimado` `#1F5673` + indicador de forma + texto explícito, p. ej. "incrementalidad +12,4 pp · z = 2,63 · p = 0,004 · significativa" / "p = 0,21 · no significativa" / "muestra insuficiente: 84 elegibles, mínimo 242"); nunca sólo color, nunca un número sin su prueba; integrado en `Promociones.tsx` (depende de T044, T018)
- [X] T046 [US3] Momento de animación deliberado al revelar el detalle de un experimento cerrado — único de la pantalla, sin hover por fila ni fade-in por tarjeta (constitución, registro de Análisis) — en `frontend/src/pantallas/Promociones.tsx` (depende de T045)
- [X] T047 [US3] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar el resultado del experimento (depende de T046)

### Datos de demostración para el experimento (research.md #10c)

- [X] T048 [P] [US3] Utilidad de datos de demostración del experimento de reactivación en `backend/rasero/semilla_reactivacion.py`, invocable con `python -m rasero.semilla_reactivacion`: crea **325** clientes de "Despensa Los Ríos" con `senal_fuga` activa (**margen operativo** sobre el mínimo real `n* = 242` del diseño experimental — research.md #10c) usando **exclusivamente los servicios públicos de `002` (`registrar_cliente`, `registrar_visita`) y de `001` (ventas)**, con su última compra lo bastante atrás como para que `evaluar_fugas_pendientes` de `002` les asigne la `senal_fuga` (005 **nunca** escribe directo en `senal_fuga` ni en `visita`); más un ayudante `simular_retornos(id_experimento, tasa_control=0.15, tasa_tratamiento=0.29)` que registra las `visita` de retorno de la ventana de medición a esas tasas por grupo vía `registrar_visita` de `002`, de modo que el cierre arroje `veredicto = 'efectivo'` de forma **reproducible** con `SEMILLA_ALEATORIZACION = 20260905` (ver quickstart.md escenario 7). **Datos de demostración para el examen, no un supuesto del modelo ni un parámetro de diseño** — el mínimo real exigido sigue siendo `n* = 242` (depende de T040, T041) **[005]** — el atrezo de clientes se crea vía los servicios públicos de `002`/`001`, nunca por escritura directa a sus tablas

**Checkpoint**: User Stories 1 a 3 funcionan de forma independiente; la reactivación mide incrementalidad contra un grupo de control real, con aleatorización reproducible y una prueba de significancia explicable. El juego sintético de 325 clientes (T048) permite mostrar un veredicto real en la demo; el mínimo de diseño (`n* = 242`) no cambia.

---

## Phase 5: User Story 4 - Exponer la marca agregada de "promoción activa" para el pronóstico de demanda (Priority: P4)

**Goal**: derivar de **todas** las redenciones ya registradas por US1, US2 y US3 la marca de "promoción activa" por producto, sucursal y período que `004` consume, cerrando el contrato FR-029 a FR-031 y FR-039 de `004`. Esta historia **no** construye la redención (ya está en US1/US2/US3): sólo aporta la **consulta agregada de solo lectura** sobre el histórico de redenciones.

**Independent Test**: dada una redención ya registrada (por cualquiera de los tres mecanismos), `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` devuelve ese `(id_producto, id_sucursal, periodo)` con su tipo; una redención de cupón/reactivación (`id_producto = NULL`) se expande a todos los renglones de la venta; un producto sin redención no aparece; la consulta exige `id_sucursal` y nunca mezcla dos sucursales.

### Pruebas obligatorias para User Story 4

- [X] T049 [P] [US4] Prueba de integración de la marca agregada de "promoción activa" (FR-031, FR-032, FR-035, SC-009): tras registrar una redención de cupón (`id_producto = NULL`) y una de oferta de recompra (`id_producto` fijado) sobre ventas de `001`, `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` devuelve cada `(id_producto, id_sucursal, periodo)` con su `tipo`; la redención de cupón se **expande** a todos los productos de su venta vía `renglon_venta` de `001`; un producto sin redención en ese período no aparece; la consulta **exige** `id_sucursal` y nunca mezcla dos sucursales — contra PostgreSQL real, en `tests/integracion/test_marca_promocion_activa.py` (depende de T014, T027) **[005] [001-lectura: venta, renglon_venta]**

### Implementación backend para User Story 4

- [X] T050 [US4] Servicio `promociones.consultar_marca_activa(sesion, *, id_sucursal, desde, hasta) -> list[dict]` en `backend/rasero/servicios/promociones.py`: agrega `redencion_promocion` por `(id_producto, id_sucursal, periodo)` en la ventana pedida y lista los `tipo_origen` distintos; **expande** las filas con `id_producto = NULL` a todos los productos de su venta vía `renglon_venta` de `001` (research.md #5); exige `id_sucursal` y nunca agrega dos sucursales (FR-035). Solo lectura sobre `redencion_promocion`; no registra ni modifica ninguna redención (depende de T002, T013, T027; implementa T049) **[005] [001-lectura: renglon_venta]**
- [X] T051 [US4] Endpoint `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` en `backend/rasero/api/promociones.py` (depende de T050, T004)
- [X] T052 [P] [US4] Ampliar la prueba de contrato con `GET /promociones/marca-activa` (forma feliz + `404` cuando la sucursal no existe) en `tests/contrato/test_contrato_promociones.py` (depende de T051, T043)

**Checkpoint**: las cuatro historias funcionan de forma independiente; el contrato con `004` queda cerrado y su eje de promoción (hoy inerte, FR-030 de `004`) puede empezar a consumir la marca real. US4 no tiene superficie de frontend propia: la marca la consume `004` máquina a máquina.

---

## Phase 6: User Story 5 - Visualizar el resultado del experimento de reactivación (Priority: P5)

**Propósito**: dos barras control vs. tratamiento + el texto de inferencia ya existente
(FR-040..FR-042). Lectura pura sobre el experimento de US3; no reabre el checkpoint de US1–US4.
Añadida 2026-09-07. **Puerta de propiedad de datos**: no introduce ni modifica ninguna entidad
ni contrato — consume `GET /promociones/experimentos/{id}` (US3) tal cual; no requiere enmienda
constitucional (verificado contra la entrada de 005 en la tabla de Propiedad de Datos).

- [X] T054 [US5] Fuente de datos: `GET /promociones/experimentos/{id}` (US3) ya devuelve `retorno_control`, `retorno_tratamiento` (nullables), `estadistico_z`, `valor_p`, `incrementalidad`, `veredicto`, `motivo_muestra_insuficiente`. El gráfico consume ese contrato sin cambios.
- [X] T055 [P] [US5] `frontend/src/componentes/graficos/ExperimentoReactivacionGrafico.tsx`: `<BarChart>` de Recharts de 2 barras (Control / Tratamiento) sobre `GraficoContenedor` (registro Análisis). Ambas barras color Estimado (#1F5673), sin significado semántico entre sí — nunca verde/rojo. Cuando `retorno_control`/`retorno_tratamiento` son `null` (muestra insuficiente / en curso), estado vacío con el motivo real, sin forzar veredicto (FR-042). `TooltipPropio`.
- [X] T056 [US5] Integrar el gráfico en `frontend/src/componentes/ResultadoExperimento.tsx` sobre las tasas de texto y el texto de inferencia con sus portadores de forma (▲/▬/◇), que no cambian.
- [X] T057 [US5] Verificación `tsc -b`, `eslint`, `vite build` sin errores.

**Checkpoint US5**: el resultado del experimento muestra el gráfico de 2 barras; el texto de la prueba y sus portadores de forma siguen igual; muestra insuficiente se muestra con honestidad.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T053 [P] Ejecutar los 12 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno (incluidos los cálculos de z y p a mano de los escenarios 7 y 8, y la reproducibilidad del `veredicto = 'efectivo'` del escenario 7 con la semilla fija; el escenario 5 carga la utilidad `python -m rasero.semilla_reactivacion` de T048)
- [X] T054 [P] Auditar `Promociones.tsx`, `GeneracionCupones.tsx`, `OfertasRecompra.tsx`, `ResultadoExperimento.tsx` (Análisis) y `AplicarPromocionVenta.tsx` (Operación) en busca de color, radio o tipografía incrustados fuera de `frontend/src/estilos/tokens.css`; verificar en `ResultadoExperimento.tsx` la distinción **dato / inferencia** con los tres portadores simultáneos (color `#1F5673`, forma, texto)
- [X] T055 Actualizar `DESIGN.md` con la skill de Impeccable (`document`), derivándolo de `Promociones.tsx` ya construido; sidecar `.impeccable/design.json` actualizado en el mismo cambio
- [X] T056 Ejecutar `pytest tests` completo contra PostgreSQL real (puerto 5442) — las 7 suites obligatorias (T035 → `test_experimento_asignacion.py`; T036 → `test_prueba_z.py`; T037/T038 → `test_experimento_reactivacion.py`; T007/T008/T009 → `test_generacion_cupones.py`, ciclo del cupón incluida su redención y frontera con `001`; T021/T022/T023 → `test_oferta_recompra.py`; T049 → `test_marca_promocion_activa.py`; contrato T016/T029/T043/T052 → `test_contrato_promociones.py`) más la unidad de dominio `test_promociones_dominio.py` (T006/T020) — y `tsc -b`, `eslint`, `vite build` del frontend, todo en verde
- [X] T057 Verificar que **todos** los parámetros de research.md #13 viven **sólo** en `backend/rasero/config/promociones.py` con sus valores de arranque (`p_c = 0.15`, `MDE = 15`, `SEMILLA_ALEATORIZACION = 20260905`, etc.), sin ninguna constante mágica dispersa por el código (Principio V "acotada"); confirmar por `grep` que `backend/rasero/` no importa `scipy`, `statsmodels` ni `numpy` — la prueba z usa `math.erf`
- [X] T058 [P] Verificar la frontera completa por `grep` sobre `backend/rasero/servicios/promociones.py` y `backend/rasero/servicios/experimentos.py`: cero escrituras (`INSERT`/`UPDATE`/`add`/`merge`) sobre `existencia`, `movimiento_inventario`, `venta`, `renglon_venta`, `senal_fuga`, `intervalo_compra`, `cliente`, `demanda_observada`, `demanda_corregida`, `pronostico`, y cero **lecturas** de `existencia` / `movimiento_inventario` en el código de esos dos servicios (FR-011, FR-028, FR-029, FR-033, mismo espíritu que las pruebas de frontera de `003` y `004`)

---

## Dependencies & Execution Order

### Dependencias de fase

- **Foundational (Fase 1)**: sin dependencias externas salvo que `001` y `002` ya estén migrados y en ejecución. **Bloquea** las cuatro historias de usuario.
- **Historias de usuario (Fases 2–5)**: todas dependen de Foundational. Dentro de cada una, pruebas antes que implementación, dominio puro antes que servicio, servicio antes que endpoint, backend completo antes que frontend.
- **Polish (Fase final)**: depende de que las cuatro historias estén completas.

### Dependencias entre historias

El orden **US1 → US2 → US3 → US4 está fijado por spec.md y no se reordena** (plan.md, "Estado de implementación por historia"):

- **US1 (cupón por fecha fija + ciclo de redención)** establece la base compartida: `servicios/promociones.py` (`generar_cupones`, `registrar_redencion`), el router `api/promociones.py` (`POST /promociones/redenciones`), el modelo `redencion_promocion` (ya en el esquema desde Foundational), la pantalla `Promociones.tsx` y la pestaña. US2, US3 y US4 **reutilizan** el endpoint y el modelo de redención.
- **US2 (empuje por recompra + su redención)** añade `detectar_ofertas_recompra` y **una línea de efecto** a `registrar_redencion` (`oferta_recompra.desenlace = 'comprado'`, T027); comparte `dominio/promociones.py`, `servicios/promociones.py` y `Promociones.tsx` con US1, por lo que va después de US1.
- **US3 (reactivación con experimento)** vive en archivos nuevos propios (`dominio/experimento.py`, `servicios/experimentos.py`); **no** añade lógica a `registrar_redencion` (la validación del grupo `control` ya está en la base de T013). Su prueba T038 usa `POST /promociones/redenciones` (de US1) para la aserción de acceso de control — dependencia **hacia atrás** (US1 < US3), no hacia adelante. Comparte el router y `Promociones.tsx` con US2.
- **US4 (marca agregada de promoción activa)** sólo añade `consultar_marca_activa` (solo lectura) y `GET /promociones/marca-activa`. Su prueba T049 necesita redenciones de los tres tipos, así que va última.

### Sin dependencia externa bloqueante

A diferencia de `004` (bloqueado por `consulta_no_atendida` de `001` User Story 3), **ninguna tarea de `005` está bloqueada**. `002` está completo (`senal_fuga`, `intervalo_compra`, `GET /clientes/cumpleanos`, `registrar_visita`), `001` User Story 1 completa (`venta`, `renglon_venta`, `producto_precio_sucursal`) y `004` completo y esperando la marca.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican; **ninguna prueba de integración antes de la migración T001 y los modelos T002**.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; **ningún endpoint antes de su modelo y su servicio**.
- Backend completo de la historia antes que su frontend.
- Toda historia con superficie de frontend termina con la verificación `tsc -b` / `eslint` / `vite build`.

### Oportunidades de paralelismo

- T002, T003, T004 y T005 de Foundational pueden ejecutarse en paralelo tras T001 (T004 espera a T002).
- Dentro de una historia, las pruebas marcadas `[P]` entre sí y las funciones de dominio marcadas `[P]` entre sí son paralelizables. Las que editan el mismo archivo van en secuencia por dependencia declarada, **no** en paralelo: `test_promociones_dominio.py` (T006→T020); `test_generacion_cupones.py` (T007→T008→T009); `test_oferta_recompra.py` (T021→T022→T023); `dominio/promociones.py` (T005→T010→T024); `test_experimento_reactivacion.py` (T037→T038); `servicios/promociones.py` (T011→T012→T013→T025→T026→T027→T050); `frontend/src/servicios/promociones.ts` (T017→T030→T044); `test_contrato_promociones.py` (T016→T029→T043→T052).
- **US3 puede empezar en paralelo con US2** una vez cerrada US1: `dominio/experimento.py` y `servicios/experimentos.py` son archivos nuevos que no colisionan con los de US2. Sólo `api/promociones.py` y `Promociones.tsx` se editan en ambas — coordinar esas dos ediciones.
- Las ampliaciones de `servicios/promociones.py` de US1, US2 y US4 (T011/T013, T025/T027, T050) tocan el **mismo archivo**: van en secuencia, no en paralelo.
- T048 (utilidad de datos de demostración, `semilla_reactivacion.py`, archivo nuevo) puede correr en paralelo con T042–T047 una vez que T040/T041 estén listos; sólo se **ejecuta** en la validación de `quickstart.md` (T053).

---

## Parallel Example: User Story 3

```bash
# Lanzar juntas las pruebas independientes de esta historia:
Task: "Prueba unitaria de asignar_grupos sobre múltiples semillas en tests/unidad/test_experimento_asignacion.py"
Task: "Prueba unitaria de la prueba z en sus cuatro casos en tests/unidad/test_prueba_z.py"
Task: "Prueba de integración del ciclo de vida del experimento en tests/integracion/test_experimento_reactivacion.py"

# Lanzar juntas las funciones puras nuevas de US3:
Task: "asignar_grupos, tamano_minimo_muestra, prueba_z_dos_proporciones, veredicto en backend/rasero/dominio/experimento.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Foundational — crítica, bloquea todo lo demás.
2. Completar Fase 2: User Story 1, con sus pruebas obligatorias en verde.
3. **Detenerse y validar**: ejecutar los escenarios 1, 2, 11 y 12 de `quickstart.md`, y la **parte de US1** del escenario 10 (la redención; la parte de `marca-activa` llega con US4).
4. Demostrar: la fecha de un cliente entra en la ventana → se genera un cupón; ejecutar la generación dos veces no lo duplica; un anonimizado no recibe cupón; el cliente redime el cupón en una venta y queda `'redimido'`, con un segundo POST idempotente, sin que `005` toque `001`. Sin ninguna maquinaria estadística.

### Entrega incremental

1. Foundational → esquema propio, parámetros, router y helpers listos.
2. + US1 (cupón por fecha fija + ciclo de redención) → probar de forma independiente → MVP demostrable.
3. + US2 (empuje por recompra con reserva de precio + su redención) → probar de forma independiente (escenarios 3 y 4 de `quickstart.md`).
4. + US3 (reactivación con experimento) → probar de forma independiente (escenarios 5 a 9; el juego sintético de 325 clientes de T048 permite mostrar un `veredicto` real —`efectivo`— en la demo, sobre el mínimo de diseño `n* = 242` que no cambia).
5. + US4 (marca agregada de "promoción activa") → probar de forma independiente (parte de `marca-activa` del escenario 10) → el eje de promoción de `004` queda desbloqueado.
6. Fase final: `quickstart.md` completo, auditoría de tokens, `DESIGN.md` actualizado, suite completa en verde, verificación de frontera.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Foundational en conjunto.
2. Una persona construye US1 (base compartida: `servicios/promociones.py` con `generar_cupones` + `registrar_redencion`, router, `Promociones.tsx`).
3. Cerrada US1, US2 y US3 pueden repartirse: US3 vive en archivos nuevos propios (`dominio/experimento.py`, `servicios/experimentos.py`) y sólo comparte el router y la pantalla con US2.
4. US4 va después de US1–US3 porque su prueba de la marca necesita redenciones de los tres orígenes.

---

## Notes

- Las tareas `[P]` tocan archivos distintos y no dependen de una tarea incompleta. Dos tareas que editan el mismo archivo nunca llevan ambas `[P]`: la segunda declara `(depende de <la primera>)` (fix del hallazgo F1 de `/speckit-analyze`).
- La etiqueta `[Story]` traza cada tarea a su historia de usuario en spec.md.
- Las 7 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md están marcadas y deben pasar antes de fusionar, **todas contra PostgreSQL real en el puerto 5442**; no hay pruebas de interfaz, maquetación ni componentes visuales.
- **[005]** = tabla propia de este módulo; **[001-lectura: ...]** y **[002-lectura: ...]** = consulta de solo lectura (nunca se altera su esquema ni se duplica). No existe ninguna etiqueta `[001-escritura]` ni `[002-escritura]`: `005` **no escribe en ninguna tabla ajena**, ni siquiera vía función-puente (a diferencia de `003`, que escribía en `producto_precio_sucursal`). `005` tampoco **lee** `existencia` ni `movimiento_inventario`: la disponibilidad al vender la resuelve `001` (FR-011); los tests de frontera los consultan sólo para verificar por conteo que no hubo escritura.
- La redención de una promoción se registra **después** de la venta, por `POST /promociones/redenciones` (construido en US1, reutilizado por US2/US3/US4), nunca dentro de la transacción de `POST /ventas` de `001` (Principio II) — mismo patrón que `POST /clientes/{id}/visitas` de `002`.
- La aleatorización del experimento (T039) es `random.Random(semilla)` (Mersenne Twister, biblioteca estándar): reproducible con semilla fija, uniforme e independiente de cualquier atributo del cliente. La prueba T035 existe específicamente para impedir que se cuele un reparto correlacionado con el `id` (p. ej. `id % 2`), prohibido por FR-016.
- El tamaño mínimo de muestra (T039) y la prueba z (T039) son `math.erf` + constantes (`z_{α/2} = 1.959964`, `z_β = 0.841621`): aritmética derivable a mano, sin `scipy`/`statsmodels`. Los valores de arranque de research.md #10 (`p_c = 0.15`, `MDE = 15 pp`, `n* ≈ 121`/grupo, 242 elegibles mínimos) son parámetros de calibración documentados, no requieren cambio.
- **Distinción para la defensa oral** (research.md #10c): `n* = 242` es el **mínimo real** que el diseño experimental exige. Los **325 clientes** sintéticos de T048 y las tasas de retorno simuladas (15 % / 29 %) son **atrezo de la presentación** para poder mostrar un veredicto real, no un parámetro del modelo ni un supuesto de diseño. Si la población real fuera menor que 242, el sistema responde `muestra_insuficiente`, no una conclusión inventada (FR-025).
- **`campania` no tiene ruta de lectura propia en el contrato** (decisión declarada como Assumption en spec.md): ningún escenario de aceptación de las cuatro historias requiere listar campañas de forma independiente de sus mecanismos; se alcanza siempre por el `id_campania` que llevan `cupon`, `oferta_recompra` y `experimento_reactivacion`. Por eso no hay ninguna tarea que cree un endpoint de campañas.
- Fuera de alcance de este desglose, evaluados y rechazados en research.md #9, #10: cualquier librería estadística externa (`scipy`, `statsmodels`, `numpy`), aleatorización estratificada o por bloques, y cualquier entidad genérica única de promoción (prohibida por la Lectura Crítica n.º 6 — el esquema tiene una entidad por mecanismo).
