# /speckit.analyze — 008-reportes-inteligencia

Análisis de consistencia cruzada entre `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `tasks.md` y la constitución (v2.6.0). No modifica ningún artefacto.

## Cobertura de requisitos → tareas

| FR | Tema | Tareas | Estado |
|---|---|---|---|
| FR-001, FR-002 | Solo lectura sobre 001–007 | T035 (auditoría) | ✅ |
| FR-003 | Rol `encargado` en todo endpoint | T004, T013, T021 | ✅ |
| FR-004 | Sin literales de sucursales | T036 | ✅ |
| FR-005–009 | Comparativo entre sucursales | T010–T014 | ✅ |
| FR-010–013 | Tendencias por semana/mes local | T005, T015–T018 | ✅ |
| FR-014–017 | Tablero de KPIs | T019–T021 | ✅ |
| FR-018–025 | Segmentación (k-means) | T007–T009, T022–T026 | ✅ |
| FR-026–028 | Caché y "Actualizar" | T011 | ✅ |
| FR-029–031 | Marca mono, Hueco que Enseña, sin verde | T029, T030–T033 | ✅ |

Cada User Story (P1–P3) tiene fase propia, prueba de integración mapeada a escenarios de
`quickstart.md`, y es entregable de forma independiente. US1 es MVP.

## Constitución

- **v2.6.0** (Propiedad de Datos para 008) hecha **antes** de este plan, según exige la Puerta de
  Sincronización de Enmiendas (v2.2.0) y el patrón v2.2.3–v2.2.6. Declara `agregado_reporte`,
  `segmento_cliente`, `asignacion_segmento` como derivadas/regenerables + la frontera "008 sólo
  lee de 001–007, nada alimenta de vuelta".
- **Principio V** cubre el clustering sin cambios: explicable (Lloyd en Python puro), reversible
  (borrar y recalcular), determinista (semilla fija). Coherente con research §2.
- **v2.5.0** ya asigna "Reportes e inteligencia (spec 008)" al rol `encargado`; el plan lo
  implementa con `exige_rol` router-level. Sin conflicto.
- **Principio I**: sin librería estadística nueva (mismo rechazo que 006 hizo a `scipy`/`numpy`);
  k-means propio, agregaciones SQL. Sin violación.
- **Principio II**: 008 no toca `POST /ventas`; no es camino crítico de ningún cobro.

## Consistencia entre artefactos

- **Contrato ↔ data-model**: los 6 endpoints escriben sólo sobre tablas de 008
  (`POST /segmentos/recalculo` reemplaza `segmento_cliente`/`asignacion_segmento`; los GET
  pueblan `agregado_reporte`). Ningún endpoint modifica 001–007. ✅
- **Contrato ↔ tasks**: los 6 paths están en T012, T016, T020, T025. ✅
- **`corrida`** (timestamp de recálculo) se usa igual en data-model, contrato y quickstart. ✅
- **Frontera con 002**: la etiqueta de segmento en el detalle de cliente se sirve por
  `GET /reportes/segmentos/cliente/{id}` (008), no por un campo nuevo en `GET /clientes/{id}`
  (002). Coherente entre spec FR-023, constitución v2.6.0, research §9, contrato y T034. ✅
- **Zona horaria de períodos**: research §6 y data-model coinciden (zona de `sucursal`, mismo
  criterio que `dia_local` de 006). ✅

## Hallazgos

| # | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| 1 | BAJA | El valor de `k` (3 o 4) se resuelve "por calibración" (research §2, Assumption, T003); no está fijado en la spec. | Aceptable: está documentado como decisión de calibración, no de interfaz, y `dominio/kmeans` acepta `k` como parámetro. Fijar el valor en `config/reportes.py` durante T003 y anotarlo. No bloquea. |
| 2 | BAJA | La entrada de 008 en "Propiedad de Datos" de la constitución no lleva un conteo entre paréntesis como el de 001 ("20 entidades"). | 002 y 006 tampoco lo llevan; es el estilo mayoritario. Sin acción. |
| 3 | INFO | El historial de corridas de clustering no se conserva (sólo la última). | El spec no lo pide; ampliación futura si se quisiera comparar corridas. Documentado en data-model. |

**Veredicto**: **0 CRÍTICO · 0 ALTO · 2 BAJO · 1 INFO.** Los artefactos son consistentes entre sí
y con la constitución v2.6.0. Listo para implementación **tras revisión del usuario** (Parte 4
del prompt: sólo spec, implementación en ronda aparte).
