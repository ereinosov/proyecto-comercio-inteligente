# Specification Quality Checklist: Promociones Inteligentes

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-05
**Updated**: 2026-09-05 (tras la enmienda constitucional v2.2.5 y la sesión de clarificación de FR-010/FR-021)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Los dos [NEEDS CLARIFICATION] quedaron resueltos** en la sesión de clarificación del 2026-09-05
  (ver `## Clarifications` del spec):
  1. **FR-010** — la "reserva" del empuje por recompra es una **reserva de precio, no de
     inventario**: garantiza el precio ofertado dentro de una ventana, no la disponibilidad del
     producto; `005` no escribe contra `existencia`/`movimiento_inventario` de `001`. Se descartó la
     reserva de inventario para mantener la frontera con `001` y el patrón "sugiere, no aplica"
     (FR-028 de `001`).
  2. **FR-021** — el umbral de incrementalidad es **estadístico**: la diferencia de tasas de retorno
     entre tratamiento y control debe ser significativa por una **prueba z de dos proporciones
     (p < 0,05)**. Limitación conocida y no bloqueante: la prueba pierde poder con muestras
     pequeñas; el tamaño mínimo por grupo se calcula en `plan.md`/`research.md` (FR-025).
- **El mecanismo de la reactivación nunca fue una decisión abierta**: grupo de control +
  aleatorización real con semilla fija + incrementalidad como diferencia de tasas de retorno ya
  estaba decidido (Lectura Crítica n.º 6 de la constitución) y no se reabrió.
- **Ambigüedades menores resueltas con defaults documentados en Assumptions**: ventana de generación
  y de validez del cupón, criterio de selección del producto de recompra, estado de `senal_fuga`
  elegible (`activa` por defecto), ventana de medición del experimento, definición de "retorno a
  compra", poder estadístico / tamaño mínimo de muestra, valores de descuento, tamaño relativo de
  los grupos.
- **`cliente.fecha_nacimiento` verificado en `002`** (FR-001 y `data-model.md` de `002`): existe, es
  obligatorio al registrar y `002` ya lo documenta como la base del cupón de `005`. **No hay
  bloqueo.** Ver "Dependencias entre módulos" del spec.
- **Enmienda constitucional v2.2.5 ya aplicada**: la tabla de Propiedad de Datos listaba para `005`
  tres entidades (`campania`, `envio_promocional`, `grupo_control`); la enmienda **v2.2.5**
  (2026-09-05) las reconcilió con las seis reales (`campania`, `cupon`, `oferta_recompra`,
  `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`) — `envio_promocional`
  retirada por contradecir la Lectura Crítica n.º 6, `grupo_control` retirada por ser demasiado
  gruesa para la medición de incrementalidad. Mismo patrón que v2.2.3 (`003`) y v2.2.4 (`004`).
- **Dependencias verificadas en `/speckit-plan` (2026-09-05) — sin bloqueo**: la nota cautelar
  previa suponía que `002` User Story 3 (`senal_fuga`) no estaba implementada. **Verificado contra
  el repositorio**: `002` está **completo** (checkpoint `2fd6381`; `senal_fuga`,
  `evaluar_fugas_pendientes`, `GET /clientes/cumpleanos`, `registrar_visita` entregados), `001` User
  Story 1 completa y `004` completo. **Ninguna historia de `005` está bloqueada.** Ver plan.md,
  "Estado de implementación por historia".

- **Hallazgos de `/speckit-analyze` (2026-09-05) corregidos**: los 8 hallazgos (3 MEDIOS, 5 BAJOS)
  se resolvieron en un solo commit. **G1**: la redención (`POST /promociones/redenciones`,
  `redencion_promocion`, `cupon.estado → 'redimido'`) se construye en **US1** y la reutilizan US2/US3/US4;
  US4 queda como la marca **agregada** de "promoción activa". **I1**: la aserción de acceso de control
  vive en US3 (`test_experimento_reactivacion.py`) usando el endpoint ya construido en US1
  (dependencia hacia atrás, no hacia adelante). **F1**: opción A — dos tareas que editan el mismo
  archivo no llevan ambas `[P]`; la segunda depende de la primera. **I2**: `GET /promociones/ofertas-recompra`
  filtra por `desenlace` (research.md #14 corregido). **I3**: `005` no lee `existencia` ni
  `movimiento_inventario`; las listas de "consultadas" de plan/data-model/spec ya no los incluyen.
  **U1**: `campania` sin endpoint de lectura propio — declarado como Assumption en spec.md.
  **U2**: `Experimento.motivo_muestra_insuficiente` marcado como campo de respuesta derivado en
  data-model.md. **I4**: `POST /promociones/experimentos` documenta `400` y `409` en el contrato.

## Estado

**Todos los ítems en verde.** Fase de planificación completa: `plan.md`, `research.md`,
`data-model.md`, `quickstart.md`, `contracts/openapi.yaml` y `tasks.md` (58 tareas, T001–T058)
generados y corregidos (2026-09-05). El módulo está listo para `/speckit-implement`.
