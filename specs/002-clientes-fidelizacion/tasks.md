---

description: "Task list template for feature implementation"
---

# Tasks: Clientes y Fidelización

**Input**: Documentos de diseño desde `/specs/002-clientes-fidelizacion/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados. Requiere además que `001-core-ventas-inventario` ya esté migrado y en ejecución: `visita` referencia `venta`, y el resolver de margen interino lee `lote`/`movimiento_inventario` (research.md #2).

**Pruebas**: se incluyen las 6 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md (Principio III, proporcional al riesgo de datos personales que gestiona este módulo), intercaladas junto a la funcionalidad que verifican. No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario (P1 → P3 de spec.md), backend antes que frontend dentro de cada historia. Fundamento completo (esquema, modelos, router) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta)
- **[Story]**: historia de usuario a la que pertenece (US1, US2, US3)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende

## Convención de rutas (fijada en plan.md, extiende la de 001, no negociable)

- Backend: `backend/rasero/` (dominio/, persistencia/, servicios/, api/, tareas/) y `backend/migraciones/`
- Frontend: `frontend/src/` (componentes/, pantallas/, servicios/) — reutiliza `frontend/src/estilos/tokens.css` ya existente, sin tokens nuevos
- Pruebas: `tests/` en la raíz (unidad/, integracion/, contrato/)

**Sin fase de Setup**: este módulo no introduce ninguna dependencia, directorio ni herramienta nueva (research.md #1: mismo stack que `001`, sin excepción). Se empieza directamente en Foundational.

---

## Phase 1: Foundational (bloqueante para las tres historias)

**Propósito**: esquema de las cuatro entidades de este módulo, modelos ORM y el router que todas las historias comparten.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T001 Crear `backend/migraciones/versions/0002_clientes_fidelizacion.py` con `cliente`, `visita`, `intervalo_compra`, `senal_fuga` de data-model.md: `nombre`/`fecha_nacimiento`/`contacto` de `cliente` como `NULL`-ables (estado post-anonimización), `visita.margen_relativo NUMERIC(6,4)` (ratio, no monto — research.md #2), `visita.id_venta UNIQUE`, `intervalo_compra` con PK = `id_cliente`, `senal_fuga` con índice único parcial `(id_cliente) WHERE estado IN ('activa','confirmada')`, y `downgrade` implementado
- [X] T002 [P] Crear los modelos SQLAlchemy 2.x `Cliente`, `Visita`, `IntervaloCompra`, `SenalFuga` en `backend/rasero/persistencia/modelos.py` (depende de T001)
- [X] T003 [P] Crear el router base y montarlo en `backend/rasero/api/aplicacion.py`, en `backend/rasero/api/clientes.py` (depende de T002)

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 2: User Story 1 - Mantener el catálogo de clientes y su historial de visitas (Priority: P1) 🎯 MVP

**Goal**: registrar clientes y, cuando el cajero los identifica al cobrar, acumular esa compra como una visita en su historial — sin que identificar al cliente demore ni bloquee nunca el cobro.

**Independent Test**: registrar un cliente, completar una venta identificándolo y verificar que se crea una visita con monto y margen congelados; completar otra venta sin identificar a nadie y verificar que no se crea ninguna visita.

### Pruebas obligatorias para User Story 1

- [X] T004 [P] [US1] Prueba de integración: una venta que identifica cliente crea exactamente una visita con `monto_total`/`margen_relativo` congelados; una venta sin cliente no crea ninguna visita ni afecta a nadie; un reintento sobre la misma `id_venta` devuelve la visita original, en `tests/integracion/test_visita_desde_venta.py`

### Implementación backend para User Story 1

- [X] T005 [P] [US1] Función `resolver_margen_visita(id_venta)`: costo total sumando `lote.costo_unitario × cantidad` de los `movimiento_inventario` tipo `salida_venta` de esa venta (lectura, no posesión, de datos de `001` — ver nota de propiedad en data-model.md), y `margen_relativo = (venta.total − costo_total) / venta.total`, en `backend/rasero/servicios/margen_resolver.py` (research.md #2; implementa parte de T004)
- [X] T006 [P] [US1] Función pura `calcular_intervalo_esperado(instantes_visitas)`: mediana de los intervalos entre visitas consecutivas, mínimo 3 visitas para `estado = 'calculado'`, si no `datos_insuficientes` con `intervalo_esperado_dias = None`, en `backend/rasero/dominio/valor_cliente.py` (research.md #3)
- [X] T007 [US1] Servicio `registrar_cliente(nombre, fecha_nacimiento, contacto=None)`, validando nombre y fecha de nacimiento obligatorios (FR-001), en `backend/rasero/servicios/clientes.py` (depende de T002)
- [X] T008 [US1] Servicio `registrar_visita(id_cliente, id_venta)`: valida que la venta exista y no tenga ya una visita (idempotente por `id_venta`, FR-004), congela `monto_total` de `venta.total`, resuelve `margen_relativo` con T005, inserta `visita` y recalcula `intervalo_compra` de ese cliente con T006, en `backend/rasero/servicios/clientes.py` (depende de T005, T006, T007)
- [X] T009 [US1] Endpoint `POST /clientes` en `backend/rasero/api/clientes.py` (depende de T007, T003)
- [X] T010 [US1] Endpoint `POST /clientes/{id_cliente}/visitas` — `201` en la primera, `200` con la visita original en un reintento sobre la misma venta, `404` si cliente o venta no existen, `409` si la venta ya está vinculada a otro cliente — en `backend/rasero/api/clientes.py` (depende de T008)
- [X] T011 [US1] Endpoint `GET /clientes/busqueda?q=`, devolviendo `id_cliente`/`nombre` con `valor: null` (el cálculo real de valor lo conecta User Story 2, T022), en `backend/rasero/api/clientes.py` (depende de T003)
- [X] T012 [P] [US1] Prueba de contrato de `POST /clientes` y `POST /clientes/{id_cliente}/visitas` contra `contracts/openapi.yaml` en `tests/contrato/test_contrato_clientes.py` (depende de T009, T010)

### Implementación frontend para User Story 1

- [X] T013 [P] [US1] Servicio de cliente HTTP `buscarClientes`, `registrarCliente`, `registrarVisita` en `frontend/src/servicios/clientes.ts` (depende de T009, T010, T011)
- [X] T014 [US1] Componente `IdentificarCliente.tsx`: búsqueda opcional contra `GET /clientes/busqueda` con opción de registrar uno nuevo si no hay coincidencia (nombre + fecha de nacimiento), sin mostrar ningún valor todavía, en `frontend/src/componentes/IdentificarCliente.tsx` (depende de T013)
- [X] T015 [US1] Ampliar `frontend/src/pantallas/Venta.tsx`: integrar `IdentificarCliente.tsx` como paso opcional que nunca bloquea ni demora el cobro (FR-003, Principio II); tras confirmar la venta, si se identificó cliente, llamar `registrarVisita` con el `id_venta` resultante (research.md #5) sin revertir la venta si esa llamada falla. Invoca el paso `new-work` de Impeccable para esta composición — mundo visual de Operación ya fijado desde `001`, `PRODUCT.md` existente, no se repite `init` (depende de T014)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente. MVP.

---

## Phase 3: User Story 2 - Medir el valor real de cada cliente (Priority: P2)

**Goal**: mostrar el valor de cada cliente combinando frecuencia, monto y margen — resumen compuesto en Operación, desglose de las tres dimensiones en Análisis — de modo que el orden no sea un simple ranking por gasto total.

**Independent Test**: con clientes de prueba que combinen distintas proporciones de monto, frecuencia y margen, verificar que el orden por valor compuesto difiere del orden por monto total simple (SC-002).

### Pruebas obligatorias para User Story 2

- [X] T016 [P] [US2] Prueba unitaria de intervalo de compra: con 2 visitas queda `datos_insuficientes`; con 3 (dos intervalos) queda `calculado` con la mediana correcta, en `tests/unidad/test_intervalo_compra.py` (verifica T006)
- [X] T017 [P] [US2] Prueba unitaria del valor compuesto: un cliente de monto alto/frecuencia baja/margen bajo puede quedar clasificado por debajo de uno de menor monto pero mayor frecuencia y margen (SC-002); un cliente en `datos_insuficientes` no participa con un valor por defecto, en `tests/unidad/test_valor_cliente.py`

### Implementación backend para User Story 2

- [X] T018 [P] [US2] Función `calcular_percentiles_y_compuesto(poblacion)`: percentil de frecuencia (inverso de `intervalo_esperado_dias`), de monto acumulado, y de margen — `SUM(monto_total × margen_relativo) / SUM(monto_total)`, ponderado por monto, no promedio simple de ratios (research.md #4) —, y promedio simple de los tres percentiles como puntuación compuesta, en `backend/rasero/dominio/valor_cliente.py` (depende de T006; implementa T017)
- [X] T019 [US2] Servicio `listar_valor_clientes(orden)` y `obtener_detalle_cliente(id_cliente)`: arman resumen/desglose con T018, excluyendo de la población comparada a los clientes en `datos_insuficientes` (FR-007) en vez de asignarles un valor, en `backend/rasero/servicios/clientes.py` (depende de T018)
- [X] T020 [US2] Endpoint `GET /clientes` (listado con `orden=valor|monto_total`) en `backend/rasero/api/clientes.py` (depende de T019)
- [X] T021 [US2] Endpoint `GET /clientes/{id_cliente}` (detalle con el desglose de las tres dimensiones) en `backend/rasero/api/clientes.py` (depende de T019)
- [X] T022 [US2] Conectar `GET /clientes/busqueda` (T011) al cálculo real de T019, reemplazando el `valor: null` provisional de User Story 1, en `backend/rasero/api/clientes.py` (depende de T019, T011)
- [X] T023 [P] [US2] Ampliar la prueba de contrato con `GET /clientes` y `GET /clientes/{id_cliente}` en `tests/contrato/test_contrato_clientes.py` (depende de T020, T021)

### Implementación frontend para User Story 2

- [X] T024 [P] [US2] Componente `ValorClienteResumen.tsx`: únicamente la puntuación compuesta, registro de Operación (radio 2px, IBM Plex Sans, sin tarjeta), sin animación de revelación, en `frontend/src/componentes/ValorClienteResumen.tsx` (depende de T022)
- [X] T025 [US2] Integrar `ValorClienteResumen.tsx` en `frontend/src/pantallas/Venta.tsx` junto al cliente identificado en la venta en curso (depende de T015, T024)
- [X] T026 [US2] Pantalla `Clientes.tsx`: registro de Análisis, listado ordenado por valor compuesto, radio 6px, Source Serif 4, líneas bajo 80 caracteres, en `frontend/src/pantallas/Clientes.tsx`, invocando el paso `new-work` de Impeccable para esta superficie nueva (mundo visual de Análisis ya fijado por la constitución, tokens reutilizados sin cambio) (depende de T020)
- [X] T027 [US2] Vista de detalle en `Clientes.tsx`: desglose de frecuencia, monto y margen, con el momento de animación deliberado al revelarlo que cita la constitución para este registro (depende de T021, T026)

**Checkpoint**: User Stories 1 y 2 funcionan juntas de forma independiente.

---

## Phase 4: User Story 3 - Detectar señales de fuga silenciosa por cliente (Priority: P3)

**Goal**: marcar a un cliente como en riesgo cuando supera su propio intervalo de compra esperado, confirmar la fuga a un umbral mayor que dispara retención breve, y anonimizar sus datos personales si no vuelve — nunca con un umbral compartido entre clientes.

**Independent Test**: con historiales de visitas variados por cliente, verificar que la señal se activa y se confirma según el ritmo propio de cada uno, y que la anonimización solo ocurre tras vencer el periodo de retención de una fuga confirmada.

### Pruebas obligatorias para User Story 3

- [X] T028 [P] [US3] Prueba unitaria de umbrales de fuga: supera 1× su intervalo esperado → `activa`; supera 5× su intervalo o 12 meses, el que sea mayor → `confirmada`; nueva visita en cualquiera de los dos estados → `resuelta`, en `tests/unidad/test_fuga_cliente.py` (FR-008, FR-014, FR-009; verifica T030)
- [X] T029 [P] [US3] Prueba de integración: una fuga confirmada con 90 días vencidos sin nueva visita anonimiza al cliente conservando sus métricas agregadas; una nueva visita antes de vencer ese plazo cancela la anonimización programada, en `tests/integracion/test_anonimizacion.py` (FR-015, FR-016)

### Implementación backend para User Story 3

- [X] T030 [P] [US3] Función pura `evaluar_estado_fuga(intervalo_esperado_dias, dias_sin_visita, instante_deteccion_previo)`: aplica los umbrales de FR-008 (1×) y FR-014 (mayor entre 5× y 12 meses) y calcula `instante_purga_programada` al confirmar, en `backend/rasero/dominio/fuga_cliente.py` (implementa T028) — **firma ajustada durante la implementación**: `instante_deteccion_previo` se reemplazó por `ahora` (reloj inyectado); ver docstring del archivo.
- [X] T031 [US3] Servicio `evaluar_fugas_pendientes()`: recorre clientes con `intervalo_compra.estado = 'calculado'` sin señal abierta o con una `activa`, crea o actualiza `senal_fuga` según T030, en `backend/rasero/servicios/clientes.py` (depende de T030)
- [X] T032 [US3] Al ejecutar `registrar_visita` (T008), si el cliente tiene una `senal_fuga` en estado `activa` o `confirmada`, marcarla `resuelta` y limpiar `instante_purga_programada`, en `backend/rasero/servicios/clientes.py` (depende de T008, T031)
- [X] T033 [US3] Servicio `anonimizar_clientes_vencidos()`: para cada `senal_fuga` `confirmada` cuyo `instante_purga_programada` ya venció, vacía `nombre`/`fecha_nacimiento`/`contacto` del cliente y marca `anonimizado = true` (FR-015, FR-016), en `backend/rasero/servicios/anonimizacion.py` (depende de T031)
- [X] T034 [P] [US3] Script de tarea programada `backend/rasero/tareas/mantenimiento_clientes.py`, invocable con `python -m rasero.tareas.mantenimiento_clientes`, que ejecuta `evaluar_fugas_pendientes()` y luego `anonimizar_clientes_vencidos()`, fuera del camino crítico de cualquier petición HTTP (research.md #6) (depende de T031, T033)
- [X] T035 [US3] Incluir en `GET /clientes/{id_cliente}` el estado de fuga (`sin_senal`/`datos_insuficientes`/`activa`/`confirmada`/`resuelta`) y `intervalo_esperado_dias`, en `backend/rasero/api/clientes.py` (depende de T021, T031)
- [X] T036 [US3] Endpoint `GET /clientes/cumpleanos?desde=&hasta=` (FR-012), excluyendo clientes anonimizados, en `backend/rasero/api/clientes.py` (depende de T003)
- [X] T037 [P] [US3] Ampliar la prueba de contrato con `GET /clientes/cumpleanos` en `tests/contrato/test_contrato_clientes.py` (depende de T036)

### Implementación frontend para User Story 3

- [X] T038 [US3] Mostrar el estado de fuga en el detalle de `Clientes.tsx` con los tres portadores obligatorios — color semántico (atención `#9A5B08` para `activa`, crítico `#8E2A2A` para `confirmada`), indicador de forma, y antigüedad en texto ("hace 40 d") —, nunca solo color, en `frontend/src/pantallas/Clientes.tsx` (depende de T027, T035) — implementada junto con T027, no como edición separada posterior.

**Checkpoint**: las tres historias de usuario funcionan de forma independiente.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T039 [P] Ejecutar los 9 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno — corregida la redacción del escenario 7 durante la ejecución (contradecía FR-007; ver research/report de implementación)
- [X] T040 [P] Auditar `IdentificarCliente.tsx`, `ValorClienteResumen.tsx` y `Clientes.tsx` en busca de color, radio o tipografía incrustados fuera de `frontend/src/estilos/tokens.css` — cero hallazgos; cero usos de `--color-marca` fuera de Venta.tsx
- [X] T041 Actualizar `DESIGN.md` con la skill de Impeccable (`document`), derivándolo de `Venta.tsx` ya ampliado y de `Clientes.tsx` ya construido — merge confirmado con el usuario (DESIGN.md ya existía); sidecar `.impeccable/design.json` actualizado en el mismo cambio
- [X] T042 Ejecutar `pytest tests` completo: 47/47 en verde, incluidas las 6 suites obligatorias (T004, T016, T017, T028, T029 y la de contrato T012/T023/T037); `tsc -b`, `eslint` y `vite build` del frontend sin errores

---

## Dependencies & Execution Order

### Dependencias de fase

- **Foundational (Fase 1)**: sin dependencias externas a este módulo salvo que `001` ya esté migrado. **Bloquea** las tres historias de usuario.
- **Historias de usuario (Fases 2-4)**: todas dependen de Foundational. Dentro de cada una, backend antes que frontend.
- **Polish (Fase final)**: depende de que las tres historias estén completas.

### Dependencias entre historias

User Story 1 es la base de datos de la que dependen las otras dos (spec.md lo declara explícitamente): sin `visita` no hay ni intervalo que calcular (US2, US3) ni fuga que detectar (US3). User Story 2 y User Story 3 comparten `intervalo_compra` (T006, T016) pero son independientemente entregables entre sí — US3 no necesita que el valor de cliente (US2) esté terminado, solo que existan visitas. El orden P1→P2→P3 es también el de construcción recomendado por esa misma dependencia de datos, no una cadena de bloqueo adicional.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; endpoints antes que su cliente de frontend.
- Backend completo de la historia antes que su frontend.

### Oportunidades de paralelismo

- T002 y T003 de Foundational pueden ejecutarse en paralelo tras T001.
- Dentro de una historia, las pruebas marcadas [P] entre sí y las funciones de dominio marcadas [P] entre sí son paralelizables.
- User Story 2 y User Story 3 pueden trabajarse en paralelo por personas distintas una vez que User Story 1 esté terminada (ambas solo dependen de que existan visitas, no una de la otra).

---

## Parallel Example: User Story 1

```bash
# Lanzar juntas las dos funciones de dominio/servicio independientes de esta historia:
Task: "Resolver de margen en backend/rasero/servicios/margen_resolver.py"
Task: "Cálculo de intervalo esperado en backend/rasero/dominio/valor_cliente.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Foundational — crítica, bloquea todo lo demás.
2. Completar Fase 2: User Story 1, con su prueba obligatoria en verde.
3. **Detenerse y validar**: ejecutar los escenarios 1 y 2 de quickstart.md.
4. Demostrar: catálogo de clientes con historial de visitas, identificación nunca bloqueante.

### Entrega incremental

1. Foundational → esquema y router listos.
2. + US1 (catálogo y visitas) → probar de forma independiente → MVP demostrable.
3. + US2 (valor de cliente, resumen/desglose) → probar de forma independiente (SC-002).
4. + US3 (fuga silenciosa, retención y anonimización) → probar de forma independiente (escenarios 5 y 6 de quickstart.md, los más delicados por el borrado irreversible de datos personales).
5. Fase final: quickstart.md completo, auditoría de tokens, `DESIGN.md` actualizado, suite completa en verde.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Foundational en conjunto.
2. Una persona construye User Story 1 (es prerrequisito de datos para las otras dos).
3. Completada User Story 1, User Story 2 y User Story 3 pueden asignarse a personas distintas: ambas solo dependen de que existan visitas, no una de la otra.

---

## Notes

- Las tareas [P] tocan archivos distintos y no dependen de una tarea incompleta.
- La etiqueta [Story] traza cada tarea a su historia de usuario en spec.md.
- Las 6 suites obligatorias de la tabla "Pruebas obligatorias" de plan.md están marcadas y deben pasar antes de fusionar; no hay pruebas de interfaz, maquetación ni componentes visuales.
- `margen_relativo` es un ratio (research.md #2), nunca un monto: cualquier tarea que lo toque debe respetar esa unidad para no reordenar clientes por un artefacto de escala cuando `003-precios-margenes` reemplace el resolver interino.
- Fuera de alcance de este desglose: cualquier decisión de promoción, cupón o descuento (pertenece a `005-promociones-inteligentes`, que consume las señales de este módulo, no las produce).
