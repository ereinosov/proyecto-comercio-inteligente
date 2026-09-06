# Checklist de especificación: User Story 9 — Corregir el carrito antes de cobrar

**Propósito**: validar la US9 antes de implementarla.
**Feature**: [spec.md](../spec.md) · FR-051 a FR-053 · Fase 11 de [tasks.md](../tasks.md)

## Calidad de contenido

- [X] Sin detalles de implementación en la redacción de la historia y los escenarios
- [X] Centrada en el valor para el cajero (corregir sin reiniciar la venta)
- [X] Todas las secciones obligatorias afectadas actualizadas (User Scenarios, Edge Cases, Requirements, Success Criteria)

## Completitud de requisitos

- [X] Sin marcadores [NEEDS CLARIFICATION]
- [X] Requisitos verificables y sin ambigüedad (FR-051 control visible; FR-052 recálculo inmediato; FR-053 sin endpoint)
- [X] Criterio de éxito medible (SC-011: <10 s, total inmediato, venta = pantalla)
- [X] Escenarios de aceptación definidos (4) y casos borde identificados (cantidad a cero, único renglón inválido)
- [X] Alcance acotado: estrictamente anterior a "Cobrar"; no toca FEFO, saldo negativo, idempotencia ni backend
- [X] Dependencias y supuestos: depende del flujo de US1; supuesto verificado de que el carrito es estado local de `Venta.tsx`

## Preparación para implementar

- [X] Cada FR tiene criterio de aceptación claro
- [X] Los escenarios cubren el flujo principal y el carrito vacío resultante
- [X] Sin fuga de implementación en la especificación

## Notas

- No genera pruebas en `tests/`: la interfaz está exenta por el Principio III, igual que el resto
  del frontend de 001.
