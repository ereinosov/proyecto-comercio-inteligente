# Specification Quality Checklist: Caja, Mermas y Fraude

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-05
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

- **Cero [NEEDS CLARIFICATION].** Las dos decisiones de alcance mayor se resolvieron con una decisión
  razonable documentada, por indicación explícita del encargo (ver `## Clarifications` y `##
  Assumptions` del spec):
  1. **Cadencia del cruce inventario-ventas (FR-021)**: arqueo de caja a cada cierre de turno; cruce
     inventario-ventas a cada conteo físico periódico de `001` (rotación semanal por categoría, que
     fija el negocio) y bajo demanda cuando un indicador por operador se desvía. NO por venta, NO
     conteo diario del catálogo completo.
  2. **Diferencia sin explicación conocida (FR-027 a FR-031)**: se registra como `anomalia_caja`
     estado `sin_explicacion`, pendiente de revisión manual; el sistema nunca fuerza una
     clasificación ni la cierra por el paso del tiempo.
- **Verificaciones de frontera de datos resueltas ANTES de escribir los FR** (contra
  `001/data-model.md`, constitución v2.2.6; documentadas en "Dependencias entre módulos"):
  1. Campos/tablas de `001` que ya existen: `existencia`, `movimiento_inventario` (`tipo`,
     `cantidad`), `venta` (`id_turno`), `renglon_venta` (`precio_aplicado`), `anulacion_venta`
     (`id_operador`), `lote` (`costo_unitario`, `fecha_caducidad`), `operador` (`pin_hash`,
     `es_encargado`), `turno` (`id_operador`), `conteo_fisico` (`alcance`, `estado`), `conteo_renglon`
     (`diferencia`). `006` los consulta, no los reimplementa.
  2. `001` **sí** tiene conteo físico de inventario **parcial** (`conteo_fisico.alcance JSONB`);
     `001` **no** tiene arqueo de caja. `006` introduce `arqueo` por primera vez y reutiliza
     `conteo_fisico` de `001` sin ejecutar conteos.
  3. Atribución por operador vía `venta.id_turno → turno.id_operador` y `anulacion_venta.id_operador`,
     sin reimplementar la autenticación por PIN ni acceder a `operador.pin_hash` (FR-035).
  4. Diferencia no explicada → `anomalia_caja` estado `sin_explicacion` (decidido, no NEEDS
     CLARIFICATION).
- **Este spec NO requiere enmienda constitucional.** Sus tres entidades (`arqueo`, `merma`,
  `anomalia_caja`) coinciden con la tabla de Propiedad de Datos de la constitución (v2.2.6) desde la
  ratificación. A diferencia de `003` (v2.2.3), `004` (v2.2.4) y `005` (v2.2.5), no hay discrepancia
  que reconciliar en el alcance aquí definido. La constitución ya anticipa que `anomalia_caja` "se
  calcula consultando `movimiento_inventario`, `venta` y `anulacion_venta`" — los indicadores por
  operador y el cruce de FR-018 a FR-020 son cálculo derivado, no entidades separadas.
- **Punto pendiente señalado para `/speckit-plan` (posible enmienda, NO hecha aquí)**: si
  `data-model.md` decide materializar los indicadores por operador / el cruce en una tabla propia
  (candidata `senal_fraude_operador`), sería una 4.ª entidad nueva y exigiría enmienda antes de
  `/speckit-plan`, del mismo tipo que v2.2.3/v2.2.4/v2.2.5. Expectativa actual: **no hace falta**.
  Ídem, con menor probabilidad, para un eventual `conteo_efectivo` (desglose del arqueo por medio de
  pago) cuando exista `007-pagos-seguridad`.
- **BLOQUEO de implementación declarado (no oculto)**, mismo patrón que `004` frente a
  `consulta_no_atendida`: `001` `conteo_fisico`/`conteo_renglon` (User Story 5) están especificadas
  pero no implementadas. User Story 1 de `006` (arqueo) NO está bloqueada; la clasificación de mermas
  de conteo (US2) y el cruce contra faltante de inventario (US3, FR-020) SÍ; la alerta de caducidad,
  la merma fuera de conteo, la tasa de anulaciones y la concentración de ventas bajo precio de lista
  NO. Se marca en `plan.md`.
- **Ambigüedades menores resueltas con defaults en Assumptions**: "lo esperado en caja" como suma de
  `venta.total` del turno (sin desglose por medio de pago hasta que exista `007`), valoración de
  merma al costo del lote FEFO, ventana de alerta de caducidad configurable por categoría con
  respaldo global, reparto proporcional del faltante no explicado entre turnos, línea base del cruce
  como comportamiento de operadores/turnos comparables de la misma sucursal.

## Estado

**Todos los ítems en verde.** Cero `NEEDS CLARIFICATION`. Spec listo para `/speckit-clarify`
(opcional — no hay ambigüedad abierta) o directamente para `/speckit-plan`, con el punto pendiente de
verificación de entidades señalado explícitamente en "Dependencias entre módulos".
