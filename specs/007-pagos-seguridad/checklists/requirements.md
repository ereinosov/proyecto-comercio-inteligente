# Specification Quality Checklist: Pagos y Seguridad

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

**16/16 ítems en verde.**

## Notes

- **Cero [NEEDS CLARIFICATION].** Las decisiones de alcance mayor se resolvieron con una decisión
  razonable documentada, con el mismo criterio que `003`–`006` (ver `## Clarifications` y `##
  Assumptions` del spec):
  1. **Alcance de la tokenización**: operación local, sin pasarela ni bóveda de terceros; se conserva
     solo {token, últimos cuatro dígitos, marca, tipo, terminal, referencia de venta}; el PAN nunca
     se persiste (constitución, "Datos de pago"; Principio IV).
  2. **Venta perdida por medio de pago no aceptado**: métrica de cobertura de medios de pago por
     sucursal, no faltante de inventario ni `consulta_no_atendida` de `001` (Lectura Crítica n.º 4).
  3. **Exposición a clonación**: indicador derivado y consultivo, calculado contra una lista de
     versiones/modelos vulnerables que el negocio mantiene; el sistema nunca deshabilita una
     terminal (Principio V; Principio II).
  4. **Retención**: bitácora ≥ año fiscal en curso + anterior; token mientras la venta sea
     consultable (sin dato sensible que caduque, porque el PAN no se guarda).
- **Verificaciones de frontera de datos resueltas ANTES de escribir los FR** (contra
  `001/data-model.md`, `001/spec.md` FR-007 y Lectura Crítica n.º 3, constitución v2.2.6;
  documentadas en "Dependencias entre módulos"):
  1. `001` ya reserva `venta.referencia_terminal_pago` como `TEXT NULL` **opaca** y declara
     `terminal_pago` propiedad de `007`. `007` rellena esa referencia con un token sin alterar el
     esquema de `001` (FR-030).
  2. `001` **no** guarda el medio de pago de una venta (solo la referencia opaca y el `total`).
     `medio_pago` y `cobertura_pago` son enteramente de `007`; no hay dato de `001` que duplicar.
     `006` ya difirió a `007` el desglose del arqueo por medio de pago.
  3. Lectura Crítica n.º 4 (venta perdida antes de que exista transacción) → métrica de cobertura,
     decidido por la constitución; `007` la implementa (FR-003 a FR-005).
  4. "Datos de pago" de la constitución (no se almacena el PAN completo) → `007` la hace cumplir
     (FR-016 a FR-019), no introduce regla nueva.
- **Decisión de entidad RESUELTA — enmienda v2.2.6 aprobada y aplicada (2026-09-05)**: tres de las
  cuatro preocupaciones caían ya en las cuatro entidades ratificadas de `007` (`terminal_pago`,
  `medio_pago`, `cobertura_pago`, `bitacora_auditoria`). La cuarta —**persistencia del token de un
  cobro con tarjeta**— no tenía entidad anticipada. `research.md #1` concluyó, con el mismo formato
  usado en `003`/`004`/`005`, que el token es un registro autoritativo (`UNIQUE` por cobro,
  idempotencia FR-021) que **no cabe** en `bitacora_auditoria` (solo anexado) ni en las otras tres, y
  necesita tabla propia. La enmienda **v2.2.6** añadió `token_pago` a la tabla de Propiedad de Datos
  (de 4 a 5 entidades) y sincronizó las citas de "versión vigente" en `001`–`006`.
- **BLOQUEO de implementación**: **ninguna User Story de `007` está bloqueada** por datos de `001`
  que falten. `venta`, `turno` y `sucursal` (con `zona_horaria`) y la `referencia_terminal_pago`
  opaca están disponibles desde el checkpoint actual de `001` (Setup + Foundational + US1). Único
  punto de integración: el flujo de captura de pago de `001` al cobrar con tarjeta; `plan.md` define
  el mecanismo, y en todo caso la venta de `001` no se bloquea si `007` no responde (FR-020).
- **Ambigüedades menores resueltas con defaults en Assumptions**: origen del PAN en el flujo de
  captura de `001`, token opaco sin estabilidad entre ventas, lista de versiones vulnerables como
  configuración del negocio, "versión de referencia desconocida" cuando falta la última versión por
  modelo, día local de sucursal para toda agregación, reservas de configuración al encargado.
- **Sin procesamiento financiero real**: FR-036 y SC-014 acotan explícitamente que no hay pasarela,
  adquirente ni movimiento de dinero real.

## Estado

**Todos los ítems en verde.** Cero `NEEDS CLARIFICATION`. La decisión de entidad del token está
resuelta: la enmienda **v2.2.6** (aprobada y aplicada el 2026-09-05) añadió `token_pago`. Spec y
plan listos; `data-model.md`, `contracts/openapi.yaml` y `quickstart.md` se escriben sobre v2.2.6.
