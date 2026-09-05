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
- **Bloqueo de implementación parcial (no oculto)**: el mecanismo 3 (reactivación) depende de datos
  reales de `senal_fuga`, cuya generación es User Story 3 de `002`, aún no implementada en el último
  checkpoint. Los mecanismos 1 y 2 no tienen ese bloqueo. Se marcará en `plan.md`.

## Estado

**Todos los ítems en verde.** El spec está listo para `/speckit-plan` (la sesión de clarificación
ya se realizó; `/speckit-clarify` no tiene preguntas pendientes que hacer).
