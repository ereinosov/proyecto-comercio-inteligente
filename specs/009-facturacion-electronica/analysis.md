# /speckit.analyze — 009-facturacion-electronica

Análisis de consistencia cruzada entre `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `tasks.md` y la constitución (v2.7.0). No modifica ningún artefacto
(salvo que la propia ejecución del análisis detectó y resolvió una inconsistencia interna del
borrador — ver Hallazgo R1).

## Cobertura de requisitos → tareas

| FR | Tema | Tareas | Estado |
|---|---|---|---|
| FR-001, FR-019 | Aviso de simulación en toda superficie | T009, T013, T026 | ✅ |
| FR-002, SC-005 | Solo lectura sobre 001/002 | T007, T023 | ✅ |
| FR-003 | Rol `cajero` | T004 | ✅ |
| FR-004, FR-021 | RUC/razón social/IVA de config, sin literales | T001, T025 | ✅ |
| FR-005 | Genera tras el cobro, sin bloquearlo (Principio II) | T014 (patrón visita/redención) | ✅ |
| FR-006, FR-009 | Contenido de la factura; comprador o "Consumidor Final" | T007 | ✅ |
| FR-007 | Secuencial correlativo por sucursal, idempotente por venta | T005, T007 | ✅ |
| FR-008 | IVA incluido en el precio; `total == venta.total` | T005, T007 | ✅ |
| FR-010 | Total 0 → sin factura (422) | T007 | ✅ |
| FR-011–013 | Regenerar; idempotente; snapshot inmutable | T007, T018 | ✅ |
| FR-014 | "Ver como documento" (imprimible, sin PDF de servidor) | T016 | ✅ |
| FR-015–017 | Anulación → nota de crédito | T019, T022 | ✅ |
| FR-018 | En la pantalla de "venta registrada" | T014 | ✅ |
| FR-020 | Nunca datos de pago | T007, T024 | ✅ |

Cada User Story (P1–P3) tiene fase propia, prueba de integración mapeada a escenarios de
`quickstart.md` y es entregable independiente. US1 es MVP.

## Constitución

- **v2.7.0** (Propiedad de Datos para 009) hecha **antes** de este plan (Puerta de Sincronización
  de Enmiendas, patrón v2.2.3–v2.2.6). Declara `factura_simulada` + la frontera "009 consume
  `venta`/`cliente` sin poseerlos; la factura se genera tras el cobro y nunca lo bloquea; ningún
  dato de pago en la factura".
- **Principio II**: la generación NO es camino crítico del cobro — repetido y verificado en spec
  FR-005, research §2, plan, tasks T014. El backend `POST /facturas` es independiente de
  `POST /ventas`.
- **Principio IV / Restricciones de datos de pago**: `medio_pago` es una etiqueta; ningún PAN,
  CVV o dígito de tarjeta (FR-020, T024).
- **v2.5.0** (Autorización de pantalla): la factura es flujo de caja → rol `cajero`; NO entra en
  la tabla de pantallas de `encargado`. Sin conflicto.
- **DESIGN.md**: T015 añade una regla MENOR de DESIGN.md ("Presentación de documento formal"), no
  una enmienda constitucional — misma clase que las reglas que specs anteriores añadieron a
  DESIGN.md.

## Consistencia entre artefactos

- **Contrato ↔ data-model**: el schema `Factura` refleja las columnas de `factura_simulada`; los
  4 endpoints escriben sólo sobre `factura_simulada`. ✅
- **Contrato ↔ tasks**: los 4 paths están en T009 y T020. ✅
- **`total == venta.total`** (IVA incluido) coherente en spec (Clarification, FR-008, SC-002,
  Escenario 1, Edge Case), research §6, data-model (invariante 1). ✅
- **Idempotencia por `id_venta`**: `UNIQUE` en data-model, `200` en el contrato, T007 y Escenario
  3. ✅
- **Frontera con 001 en la anulación**: `servicios/ventas.py` de 001 NO cambia; el frontend
  orquesta `emitirNotaCredito` tras `anularVenta` (research §5, T021). Coherente con Propiedad de
  Datos. ✅

## Hallazgos

| # | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| R1 | RESUELTO | El borrador inicial mezclaba "IVA por encima del precio" (Escenario 1 con subtotal 8,63 / total 9,92) con "IVA incluido" (research §6). | Resuelto durante el análisis: se adopta **IVA incluido en el precio** (habitual en el comercio minorista ecuatoriano) → `total == venta.total`, 009 no cambia lo que paga el cliente ni el cobro de 001. Spec (Clarification, FR-008, SC-002, Escenario 1, Edge Case) y data-model ya reflejan esto. |
| 1 | BAJA | La derivación de `medio_pago` ("efectivo" vs "tarjeta") desde `venta.referencia_terminal_pago` (opaco para 001) no está detallada. | Heurística simple en T007: `referencia_terminal_pago` nula → "efectivo", no nula → "tarjeta". Documentar en research al implementar. No bloquea; el campo es opcional (`nullable`). |
| 2 | BAJA | `UNIQUE (id_venta) WHERE tipo='factura'` vs `UNIQUE (id_venta, tipo)` — data-model deja la elección de implementación abierta (una `nota_credito` comparte `id_venta`). | Decidir en T002: índice parcial `WHERE tipo='factura'` es lo más preciso. No afecta al contrato ni a los tests. |
| 3 | INFO | El cobro de 001 sigue sin IVA en `venta.total`; con "IVA incluido" la factura reinterpreta ese total como precio con IVA. | Es la decisión de research §6, coherente con el comercio minorista ecuatoriano y con "009 no cambia el cobro". Si algún día 001 modela IVA explícito, 009 lo hereda. |
| 4 | INFO | Notas de crédito: sólo forma + reversión de totales; sin ciclo tributario completo (motivos codificados, sustento). | Fuera de alcance declarado (Assumptions). Ampliación futura. |

**Veredicto**: **0 CRÍTICO · 0 ALTO · 2 BAJO · 2 INFO · 1 inconsistencia resuelta durante el
análisis.** Los artefactos son consistentes entre sí y con la constitución v2.7.0. Listo para
implementación **tras revisión del usuario** (Parte 4 del prompt: sólo spec).
