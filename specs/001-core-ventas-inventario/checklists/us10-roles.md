# Checklist de especificación: User Story 10 — Roles de operador, sucursal fija y autorización centralizada

**Propósito**: validar la US10 antes de implementarla.
**Feature**: [spec.md](../spec.md) · FR-054 a FR-064 · Phase 12 de [tasks.md](../tasks.md) · Principio VI (enmienda constitucional v2.3.0)

## Calidad de contenido

- [X] Sin detalles de implementación en la redacción de la historia y los escenarios (los FR sí nombran `requiere_rol`/`useRol` porque el Principio VI los fija como mecanismo único, no como opción de diseño)
- [X] Centrada en el valor: quién puede hacer qué tiene una sola respuesta; el operador no ve opciones que no puede usar
- [X] Todas las secciones obligatorias afectadas actualizadas (User Scenarios, Edge Cases, Requirements, Key Entities, Success Criteria)

## Completitud de requisitos

- [X] Sin marcadores [NEEDS CLARIFICATION] — cada decisión de producto vino resuelta en el encargo (relación uno-a-uno, 3 roles cerrados, admin exclusivo de gestión de operadores, admin exento de restricción de sucursal, ocultar no deshabilitar)
- [X] Requisitos verificables (FR-056 regla de conversión exacta; FR-061 código y mensaje exactos; FR-057 mecanismo único; FR-062 ocultar no deshabilitar)
- [X] Criterios de éxito medibles (SC-012 100 % migrados / 0 admin; SC-013 `es_encargado` ausente; SC-014 cajero no ve nada)
- [X] Escenarios de aceptación definidos (9) y casos borde identificados (operador sin turnos, admin sin sucursal elegida, único admin, cambio de sucursal con turno abierto, defensa en profundidad)
- [X] Alcance acotado: autorización, NO autenticación — sin JWT, sin sesión de servidor, PIN + hash intacto (FR-064)
- [X] Dependencias y supuestos: depende del flujo de turno de US1; supuesto verificado de que `App.tsx` ya tiene un estado con el operador del turno reutilizable como fuente de verdad del hook

## Preparación para implementar

- [X] Cada FR tiene criterio de aceptación claro
- [X] Los escenarios cubren cajero, encargado y admin, y la migración de datos
- [X] Migración documentada como cambio de esquema sobre una entidad certificada de 001, con reversión

## Notas

- Sí genera pruebas en `tests/` (a diferencia de US9): autorización, restricción de sucursal en
  apertura de turno y migración de datos son contrato y transición de estado sobre `operador`/`turno`
  — obligatorias por el Principio III. La interfaz (hook, ocultamiento, 6.ª pestaña) sigue exenta.
- Riesgo vigilado: toca datos de sesión/turno ya certificados. Línea base de la suite antes (T096)
  y después (T121) de la migración; todo lo que pasaba antes pasa después o se documenta como test
  actualizado al modelo nuevo.
