# Implementation Plan: Pagos y Seguridad

**Branch**: `007-pagos-seguridad` (sobre `master`; sin rama dedicada) | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-pagos-seguridad/spec.md`

> **ESTADO DE ESTE PLAN**: Fase 0 (`research.md`) completa. `research.md #1` concluyó que la
> persistencia del token de un cobro con tarjeta necesita una **quinta entidad** (`token_pago`) que
> la constitución v2.2.5 no anticipaba para `007`. La **enmienda v2.2.6** que la añade fue **aprobada
> y aplicada el 2026-09-05** (informe de impacto en el encabezado de `constitution.md`; citas de
> "versión vigente" de `001`–`006` sincronizadas a v2.2.6, puerta de sincronización v2.2.0). Mismo
> procedimiento que v2.2.3 (`003`), v2.2.4 (`004`) y v2.2.5 (`005`), con la diferencia de que aquí la
> enmienda se sometió a aprobación explícita antes de aplicarse. La **Fase 1** (`data-model.md`,
> `contracts/`, `quickstart.md`) se escribe sobre v2.2.6.

## Summary

Cierra el flanco de pagos de un minimarket **sin convertirse en un procesador de pagos** (FR-036,
SC-014): no hay pasarela, adquirente, autorización ni settlement, y no se mueve dinero real. Cuatro
preocupaciones acotadas del enunciado, cada una con su lógica propia (FR-033):

1. **Cobertura de medios de pago por sucursal** (`medio_pago` + `cobertura_pago`) — catálogo global
   de medios y su aceptación **histórica** por sucursal (fecha-desde, para que un período pasado
   refleje el estado de entonces, FR-002), más la métrica de **intención de compra no atendida**
   cuando el cliente no puede pagar como quería. Es la métrica que la **Lectura Crítica n.º 4** de
   la constitución nombra literalmente; **no** es `consulta_no_atendida` de `001` (eso es "no hay
   producto"), **no** es faltante de inventario (FR-005).
2. **Terminales de pago y vigilancia de firmware** (`terminal_pago`) — registro de cada datáfono
   físico con su modelo, sucursal actual, **historia de ubicación**, versión de firmware y fecha de
   última actualización. Indicadores **derivados y consultivos**: "desactualizada" (versión por
   debajo de la última de referencia del modelo) y "expuesta a clonación" (versión o modelo en una
   lista de vulnerabilidad conocida que el negocio mantiene). El sistema **nunca** deshabilita una
   terminal (FR-012, Principio V; Principio II: la caja no se bloquea).
3. **Tokenización de los datos de pago** (`token_pago` — **entidad añadida por la enmienda v2.2.6**) —
   cuando una `venta` de `001` se cobra con tarjeta, este módulo recibe el número, devuelve un **token
   opaco** y persiste **únicamente** {token, últimos cuatro dígitos, marca, tipo, terminal de
   captura, referencia de venta, clave de idempotencia}. El PAN, el CVV y los datos de banda/chip
   **nunca** se almacenan, registran ni transmiten (FR-017), en ningún punto; un intento de
   persistir un PAN completo se **rechaza** y se registra sin el número (FR-018). Es el cumplimiento
   directo de la sección "Datos de pago" de la constitución y del Principio IV.
4. **Bitácora de auditoría de la actividad de pagos** (`bitacora_auditoria`) — rastro de **solo
   anexado** (FR-025) de los hechos de pago: emisión de token, rechazo de PAN, actualización de
   firmware, detección de exposición, alta/baja de un medio en una sucursal, cambio de cobertura,
   intención no atendida. Cada entrada: tipo, instante en **día local de la sucursal**, sucursal,
   terminal cuando aplica, iniciador, resultado y referencia al recurso. Nunca datos de pago
   completos ni personales más allá del identificador mínimo (FR-026, Principio IV).

Se construye como extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic sobre
PostgreSQL 16 (puerto 5442) y del mismo frontend React 18 + TS + Vite que `001`–`006`. **Cero
dependencias nuevas.** Una migración `0007_pagos_seguridad`.

**Dos ejes que condicionan el plan**:

1. **Enmienda constitucional v2.2.6 — aprobada y aplicada** (a diferencia de `006`, y como
   `003`/`004`/`005`): la tabla de "Propiedad de Datos y Nomenclatura" asignaba a `007` cuatro
   entidades (`terminal_pago`, `medio_pago`, `cobertura_pago`, `bitacora_auditoria`). **Tres de las
   cuatro preocupaciones caían limpiamente en ellas.** La cuarta —la persistencia del token— **no**:
   `research.md #1` concluyó que `token_pago` es un registro autoritativo con requisito de unicidad
   e idempotencia (FR-019, FR-021), no un evento de log, y que ninguna de las cuatro entidades lo
   absorbe sin forzar su semántica. Es el mismo patrón exacto de `rol_producto` (`003`),
   `sustitucion_producto` (`004`) y `cupon`/`oferta_recompra` (`005`): una declaración de negocio
   que el módulo modela en tabla propia con FK, y que la lista original de la constitución no
   contemplaba porque **se escribió antes de que existiera el spec de `007`**. La enmienda **v2.2.6**
   (2026-09-05) añadió `token_pago` (de 4 a 5 entidades) y sincronizó las citas de "versión vigente"
   en `001`–`006`. La Fase 1 se escribe sobre esa base.
2. **Sin bloqueo de implementación por `001`** (a diferencia de `006`): `venta`, `turno` y
   `sucursal` (con `zona_horaria`) y la `referencia_terminal_pago` opaca están entregadas desde el
   checkpoint actual de `001` (Setup + Foundational + User Story 1). **Ninguna User Story de `007`
   está bloqueada por datos de `001` que falten** (ver "Estado de implementación por historia").

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001`–`006`. Introducir un segundo lenguaje o framework para la misma función está
PROHIBIDO por el Principio I. **No se usa ninguna librería de criptografía de terceros** para generar
el token: es un identificador sustituto opaco (UUID v4 o equivalente de la biblioteca estándar), no
un token criptográfico reversible — `research.md #4`.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend); Vite
+ React sin librería de componentes de terceros (frontend). Todas ya presentes. Este plan **no añade
ninguna dependencia nueva**.

**Storage**: la misma base PostgreSQL 16 de `001`–`006`, nativa en desarrollo, puerto **5442**. Las
entidades se agregan al mismo esquema mediante la migración `0007_pagos_seguridad`; no se crea una
base ni un esquema aparte. SQLite sigue PROHIBIDO. La migración `0007` crea las cinco tablas de la
entrada de `007` en la tabla de propiedad tras v2.2.6.

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`–`006`.

**Target Platform**: mismo servidor de un solo nodo y mismo navegador de escritorio.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se crea
un servicio nuevo.

**Performance Goals**: registrar una terminal, tokenizar un cobro o anexar una entrada de bitácora
responde en menos de 1 s. `GET /pagos/cobertura` y `GET /pagos/bitacora` para una sucursal y una
ventana de ≤ 90 días responden en menos de 2 s p95 — consultas de agregación indexadas por sucursal
y por día local, nunca un bucle por venta.

**Constraints**: ninguna función de este módulo participa en `POST /ventas` ni es camino crítico de
un cobro (Principio II, FR-020): si la tokenización falla, la `venta` de `001` se completa igual y se
marca "sin tokenización". El módulo **nunca** almacena, registra ni transmite el PAN, el CVV ni datos
de banda/chip, en ningún punto (FR-017, Principio IV); **nunca** deshabilita ni bloquea una terminal
(FR-012); **nunca** integra una pasarela real ni mueve dinero (FR-036); **nunca** modifica `venta`,
`turno`, `operador` ni `sucursal` de `001` (FR-029), y rellena la `referencia_terminal_pago` opaca
sin cambiar su tipo ni su semántica en el esquema de `001` (FR-030). Toda salida se identifica por
sucursal (FR-006, FR-034, Principio IV). Toda marca de tiempo en UTC, toda agregación por día local
de la sucursal (FR-032).

**Scale/Scope**: mismo orden de magnitud que `001`–`006` — decenas de terminales, cientos de cobros
con tarjeta por semana y por sucursal, dos sucursales en el alcance de examen (cifra de entrega, no
del modelo). `token_pago` y `bitacora_auditoria` son **append**; `terminal_pago` y `cobertura_pago`
son **registro + historial de cambios**. Los indicadores de firmware ("desactualizada", "expuesta")
son las **únicas consultas derivadas** del módulo — ninguna es tabla (se calculan al leer,
comparando `terminal_pago.version_firmware` contra la configuración de `research.md #10`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.6** (vigente) — versión que esta misma
funcionalidad motivó (enmienda v2.2.6, ver "Nota sobre la propiedad de datos" abajo). **Resultado de
la puerta: PASA en los cinco principios y en la Puerta de propiedad de datos** (una vez añadida
`token_pago` por v2.2.6).

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria` y —tras v2.2.6— `token_pago`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack de `001`–`006`; **no** introduce librería nueva — el token es un identificador sustituto opaco de la biblioteca estándar, no un token criptográfico (`research.md #4`). |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna función participa en `POST /ventas`. La tokenización **no es camino crítico** (FR-020): si falla, la `venta` de `001` se completa con su comportamiento base y se marca "sin tokenización". La emisión de token es **idempotente** por clave de idempotencia (FR-021). Es offline-capable: un cobro sin conectividad se completa en `001` y la tokenización se resuelve al reconciliar con la marca de tiempo de origen de `001` (FR-022). El registro de terminales, la cobertura y la bitácora son administrativos. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias": que el PAN **nunca** se persista ni aparezca en ningún campo, archivo de registro, bitácora o respuesta (SC-006); que un intento de persistir un PAN se rechace y se registre sin el número (SC-008); la idempotencia de la emisión de token (SC-009); que la `venta` de `001` se complete aunque la tokenización falle (SC-010); la frontera de solo lectura con `001` (SC-013); la bitácora de solo anexado (SC-012); que ninguna señal de firmware deshabilite una terminal (SC-005). Interfaz y maquetación de las pantallas quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `bitacora_auditoria` es de solo anexado (FR-025): una entrada no se modifica ni se borra. Cada hecho de pago genera una entrada con tipo, instante en día local, sucursal, terminal cuando aplica, iniciador y resultado (FR-023, FR-024). **Ningún rastro contiene datos de pago completos, CVV, banda/chip ni datos personales más allá del identificador mínimo** (FR-026) — es el requisito literal del Principio IV. Todo lleva `id_sucursal`; `GET /pagos/bitacora`, `/pagos/cobertura` y `/pagos/terminales` filtran por sucursal y nunca agregan dos sin discriminar (FR-006). El estado de una terminal es reconstruible por su historia de ubicación y de firmware. |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: cada señal de "desactualizada" indica la versión actual y la de referencia; cada "expuesta a clonación" enumera la referencia de la vulnerabilidad que la motiva (FR-011, SC-004). **Consultiva por defecto**: el módulo detecta y explica exposición; **nunca** deshabilita una terminal, bloquea un cobro ni sanciona (FR-012, FR-035). La acción correctiva (actualizar, aislar, reemplazar) la decide una persona. **Con línea base**: "desactualizada" se mide contra la última versión de referencia del modelo; si falta, la terminal se marca "versión de referencia desconocida", **nunca** "al día" (FR-010). **Acotada**: límites documentados — sin pasarela real (FR-036), lista de vulnerabilidad como configuración del negocio y no descubrimiento automático (`research.md #3`), el token sin estabilidad entre ventas para no reconstruir un identificador de tarjeta (`research.md #4`). **Visible**: registro mixto Operación/Análisis con los tres portadores para "expuesta", "desactualizada", "versión de referencia desconocida" y "sin tokenización" (`research.md #15`). |

**Nota sobre la propiedad de datos — la enmienda v2.2.6 que este módulo motiva**:

Al preparar este plan se contrastó la entrada **completa** de `007-pagos-seguridad` en la tabla de
"Propiedad de Datos y Nomenclatura" (entonces `terminal_pago`, `medio_pago`, `cobertura_pago`,
`bitacora_auditoria`) contra el spec y las fronteras de la propia sección (`research.md #1`). **Se
encontró una discrepancia**, del mismo tipo que en `003` (v2.2.3), `004` (v2.2.4) y `005` (v2.2.5):

- **Tres de las cuatro preocupaciones caen limpiamente**: firmware de terminal → `terminal_pago`;
  cobertura de medios → `medio_pago` + `cobertura_pago`; log de actividad → `bitacora_auditoria`.
- **La cuarta —persistencia del token de un cobro con tarjeta— no tiene entidad anticipada.** No es
  el catálogo `medio_pago`, no es el dispositivo `terminal_pago`, no es la métrica `cobertura_pago`,
  y **no** es un evento de `bitacora_auditoria`: es el **registro autoritativo** de la relación
  `venta` ↔ token, con requisito de **unicidad** (un token por cobro) y de **idempotencia** (FR-019,
  FR-021), y es lo que rellena la `referencia_terminal_pago` opaca de `001` (FR-030). Un log de solo
  anexado (FR-025) no puede ser el sistema de registro de un dato con clave única y ciclo de purga.

`research.md #1` concluyó que hace falta una **quinta entidad `token_pago`** y, por tanto, la
**enmienda constitucional v2.2.6** que la añade a la tabla de Propiedad de Datos, **antes** de
escribir `data-model.md`. La constitución ya anticipaba la **regla** ("Datos de pago": conservar
únicamente identificadores y últimos dígitos) pero no la **entidad** que la implementa — exactamente
la clase de omisión que las tres enmiendas anteriores corrigieron ("la lista se escribió antes de
que existiera el spec del módulo").

La decisión y su justificación están en `research.md #1`, con el mismo formato usado en
`003`/`004`/`005`. La enmienda **v2.2.6** se sometió a aprobación explícita y fue **aprobada y
aplicada el 2026-09-05** (informe de impacto en el encabezado de `constitution.md`; citas de "versión
vigente" de `001`–`006` sincronizadas a v2.2.6). La Fase 1 (`data-model.md`, `contracts/`,
`quickstart.md`) se escribe sobre esa base.

**Lecturas Críticas del Enunciado aplicadas** (decisiones de análisis ya tomadas, no reabiertas):

- **Lectura n.º 4** ("hay venta perdida antes de que exista transacción"): es el eje de la User
  Story 1. La constitución ya decidió que el cliente que no puede pagar como quiere "se trata como
  métrica de cobertura de medios de pago por sucursal, no como venta perdida en el sentido de
  faltante de inventario". `007` lo implementa en `cobertura_pago` (FR-003 a FR-005); **no** lo
  modela como `consulta_no_atendida` de `001` ni como `venta`.
- **Frontera `001` / `007`** (ya escrita en el spec de `001` y en su `data-model.md`): `001` guarda
  `venta.referencia_terminal_pago` como **referencia opaca `TEXT NULL`** y declara `terminal_pago`
  propiedad de `007`. El esquema lo refleja: `token_pago` (v2.2.6) tiene una FK de solo lectura
  `id_venta` → `venta` de `001`, y `007` rellena la referencia opaca sin cambiar su tipo ni su
  semántica (FR-030). `007` no define ninguna entidad de venta ni de turno.
- **"Datos de pago"** (Restricciones Técnicas y de Datos): `007` no introduce la regla, la hace
  cumplir en cada cobro con tarjeta (FR-016 a FR-019). El Principio IV la refuerza para los rastros.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`–`006`. Nueva migración Alembic `0007` sobre el mismo esquema. |
| Datos de pago: no se almacena el PAN completo; solo identificadores y últimos dígitos | `token_pago` (v2.2.6) conserva **únicamente** {token opaco, últimos 4 dígitos, marca, tipo, terminal, referencia de venta}. Ningún campo de PAN, CVV ni banda/chip en el esquema. Validación de rechazo (FR-018) en el servicio y prueba obligatoria de que **ningún** campo, log o respuesta contiene un PAN (SC-006). |
| Precisión exacta en dinero | Este módulo **no persiste importes** — no hay `total` de pago, no hay settlement (FR-036). La cobertura es un conteo de eventos (`INTEGER`); la métrica de intención no atendida es una razón calculada con `Decimal` y presentada como cadena. Ningún `float`. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`. Claves foráneas `id_sucursal`, `id_medio_pago`, `id_terminal_pago`, `id_venta`, `id_operador`. |
| Tiempo en UTC, agregaciones por día local de la sucursal | Instantes en `TIMESTAMPTZ`; `bitacora_auditoria.dia_local` y las agregaciones de `cobertura_pago` son **días locales**: `(instante AT TIME ZONE sucursal.zona_horaria)::date` (FR-032, `research.md #8`). |
| Propiedad de datos: exactamente las entidades de 007 | `data-model.md` define únicamente las cinco entidades de la tabla de propiedad tras v2.2.6 (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`). `venta`, `turno`, `operador`, `sucursal` (de `001`) se **consultan, nunca se redefinen ni se escriben**. Los tests de frontera cuentan filas antes y después para verificar 0 escrituras (SC-013). |
| Sistema de diseño: registros Operación y Análisis | Ver "Sistema de diseño en el frontend". `TerminalesPago.tsx` y `BitacoraPagos.tsx` son Operación (2px, IBM Plex Sans, cifras tabulares, tabla como elemento principal); `CoberturaPago.tsx` es Análisis (6px, Source Serif 4, una decisión por bloque). Regla del Registro Sin Dinero: cero apariciones del Verde Rasero (`research.md #13`). |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0007_pagos_seguridad`) con `downgrade` que elimina las cinco tablas y sus `ENUM`. |
| Datos personales recogidos solo con finalidad y retención documentadas | `007` **no captura datos de cliente**. De la tarjeta: solo marca, tipo y últimos 4 dígitos, con la finalidad (conciliar un cobro con el comprobante) y la retención (mientras la venta sea consultable) documentadas en el spec. Del operador: solo `id_operador` y `es_encargado`, nunca el PIN. |
| Configuración y secretos por entorno | La lista de versiones de firmware vulnerables y la última versión por modelo son **configuración del negocio** (`backend/rasero/config/pagos.py`), sobrescribible por entorno; ningún secreto en el repositorio. |

**Resultado de la puerta**: **PASA** en los cinco principios y en todas las decisiones técnicas
fijadas. La Puerta de propiedad de datos pasa una vez añadida `token_pago` por la enmienda **v2.2.6**
(aprobada y aplicada el 2026-09-05). Sin otras desviaciones que requieran Complexity Tracking.

**Re-verificación tras la Fase 1 (data-model.md, contracts/openapi.yaml, quickstart.md)**: **sin
cambios en el veredicto**. El diseño confirma que (a) las tablas son exactamente las cinco de la
tabla de propiedad tras v2.2.6 (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`,
`token_pago`); los indicadores de firmware y la cuota de intención no atendida son cálculo derivado,
no tablas (research.md #3, #5); (b) no hay `float` ni ningún campo de PAN/CVV/banda en el esquema —
`token_pago.ultimos_digitos` es `CHAR(4)` con `CHECK` de exactamente 4 dígitos; (c) el contrato no
expone ningún endpoint que deshabilite una terminal, bloquee un cobro o mueva dinero, y `POST
/pagos/tokens` no es camino crítico (FR-020); (d) toda FK hacia `001` (`token_pago.id_venta`,
`id_sucursal`, `id_operador`, `id_terminal_pago`→propia) es de solo lectura y ninguna columna de
`001` se duplica salvo `id_sucursal`/`dia_local` denormalizados del turno de la venta, inmutables;
`007` **no** ejecuta `UPDATE` sobre `venta` (no hay `[001-escritura]`); (e) `GET /pagos/cobertura`,
`/pagos/terminales` y `/pagos/bitacora` exigen `id_sucursal`; (f) la migración `0007` ejecuta
`REVOKE UPDATE, DELETE ON bitacora_auditoria` y ningún servicio los ejecuta; (g) la idempotencia de
`token_pago` es `UNIQUE (id_venta)` primaria + `UNIQUE (clave_idempotencia)` secundaria, con la clave
generada por el cliente (research.md #15).

## Estado de implementación por historia (dependencias verificadas contra el repositorio)

El spec (sección "Dependencias entre módulos") exige que este plan diga qué se puede construir ya.
**Verificación**: `git log` (HEAD `d1da398`), `specs/001-core-ventas-inventario/tasks.md` y
`specs/001-core-ventas-inventario/data-model.md` en el árbol de trabajo.

| Dependencia | Estado real | Fuente |
|---|---|---|
| `001` — `venta` (con `id_turno` y `referencia_terminal_pago TEXT NULL` opaca), `turno` (`id_operador`, sucursal), `sucursal` (`zona_horaria`), `operador` (`es_encargado`) | **Entregado** (checkpoint de `001` Setup + Foundational + User Story 1; `venta`, `turno`, `sucursal`, `operador` en la migración `0001`) | `specs/001-core-ventas-inventario/tasks.md`, `.../data-model.md` línea 233 (`referencia_terminal_pago`) |
| `001` — cualquier dato de conteo, inventario o merma | **No relevante**: `007` no toca inventario | — |
| `006-caja-mermas-fraude` | **Entregado** (HEAD `d1da398`); difirió a `007` el desglose del arqueo por medio de pago. `007` **no consume nada de `006`** | `specs/006-caja-mermas-fraude/spec.md` Assumptions |
| Constitución — entidad `token_pago` | **Añadida por la enmienda v2.2.6** (aprobada y aplicada el 2026-09-05, tras `research.md #1`) | tabla de Propiedad de Datos, `research.md #1` |

| Historia de `007` | ¿Construible ahora? | Nota |
|---|---|---|
| **US1 — Cobertura de medios de pago por sucursal** | **Sí, completa** | Solo `sucursal` de `001` (entregada). `medio_pago` + `cobertura_pago` están en la tabla de propiedad desde la ratificación. |
| **US2 — Terminales y vigilancia de firmware** | **Sí, completa** | Solo su propio registro y `sucursal`. `terminal_pago` desde la ratificación. |
| **US3 — Tokenización de los datos de pago** | **Sí, completa** | Necesita `venta` y `referencia_terminal_pago` (entregadas) y la entidad `token_pago` (**enmienda v2.2.6, ya aplicada**). Único punto de integración: el flujo de captura de pago del servicio de venta de `001` — `contracts/`/`data-model.md` definen si `007` expone un contrato que `001` invoca o si procesa la referencia de forma diferida; en ambos casos la venta de `001` no se bloquea (FR-020). |
| **US4 — Bitácora de auditoría de pagos** | **Sí, completa** | Transversal a US1–US3. `bitacora_auditoria` desde la ratificación. Registra los hechos de las tres historias anteriores. |

**Conclusión para `/speckit-tasks`** (cuando se llegue): el plan de tareas ordenará US1 → US2 → US3
→ US4. **Ninguna historia está bloqueada**: la enmienda v2.2.6 que habilita `token_pago` (US3) ya
está aplicada, y no hay bloqueo de implementación por datos de `001` faltantes, a diferencia de
`006`.

## Project Structure

### Documentation (this feature)

```text
specs/007-pagos-seguridad/
├── plan.md              # Este archivo
├── research.md          # Fase 0 — COMPLETA (research.md #1 motivó la enmienda v2.2.6, ya aplicada)
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   └── openapi.yaml
├── checklists/
│   └── requirements.md  # COMPLETO (16/16)
├── spec.md
└── tasks.md             # Fase 2 (/speckit-tasks — no lo crea este comando)
```

### Source Code (repository root)

Misma estructura de primer nivel que `001`–`006`, fijada y no negociable. Este módulo **extiende**
`backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel. (Rutas
verificadas: `backend/migraciones/versions/` contiene `0001`–`0006`; `backend/rasero/config/` ya
existe con `caja.py`, `pronostico.py`, `promociones.py`.) **Este árbol es la intención de diseño; los
archivos de código se crean en `/speckit-tasks` y la implementación posterior.**

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── config/
│   │   │   └── pagos.py                        # NUEVO — parámetros de research.md #10 (retención de bitácora, medios base, dígitos conservados), sobrescribibles por entorno
│   │   ├── dominio/
│   │   │   ├── firmware.py                     # NUEVO — funciones puras: "desactualizada" (comparación de versión), "expuesta a clonación" (pertenencia a lista), "versión de referencia desconocida" (research.md #3)
│   │   │   └── token.py                        # NUEVO — función pura: generación del identificador opaco, extracción de últimos 4 dígitos + marca + tipo, validación de rechazo de PAN completo (research.md #4)
│   │   ├── persistencia/
│   │   │   └── modelos.py                      # AMPLIADO — MedioPago, TerminalPago, CoberturaPago, BitacoraAuditoria (+ TokenPago tras v2.2.6)
│   │   ├── servicios/
│   │   │   ├── cobertura_pago.py               # NUEVO (US1) — declarar medios por sucursal (histórico), registrar intención no atendida, calcular cobertura y cuota no atendida
│   │   │   ├── terminales_pago.py              # NUEVO (US2) — registrar/mover terminal, registrar actualización de firmware, evaluar exposición (consulta derivada)
│   │   │   ├── tokenizacion.py                 # NUEVO (US3) — emitir_token (idempotente), consultar_pago_de_venta, rechazar_pan; rellena referencia_terminal_pago de 001
│   │   │   └── bitacora_pagos.py               # NUEVO (US4) — anexar_entrada (solo INSERT), consultar_bitacora (filtros sucursal/terminal/tipo)
│   │   └── api/
│   │       └── pagos.py                        # NUEVO — routers de cobertura, terminales, tokenizacion, bitacora
│   └── migraciones/versions/
│       └── 0007_pagos_seguridad.py             # NUEVO — tablas + ENUM, con downgrade (NO se escribe hasta v2.2.6)
├── frontend/src/
│   ├── pantallas/
│   │   ├── CoberturaPago.tsx                   # NUEVO — registro de ANÁLISIS: qué medios acepta cada sucursal, cuota de intención no atendida por medio deseado, "¿habilitar un medio nuevo?"
│   │   ├── TerminalesPago.tsx                  # NUEVO — registro de OPERACIÓN: tabla de terminales por sucursal, versión de firmware, estado (desactualizada / expuesta / al día), registrar actualización
│   │   └── BitacoraPagos.tsx                   # NUEVO — registro de OPERACIÓN: rastro consultable de hechos de pago, filtros por sucursal / terminal / tipo, solo lectura
│   ├── servicios/
│   │   └── pagos.ts                            # NUEVO — cliente HTTP de los endpoints /pagos
│   └── App.tsx                                 # AMPLIADO — pestaña "Terminales" (Operación) y grupo "Pagos" (Análisis: Cobertura; + Bitácora como consulta de Operación)
└── tests/
    ├── unidad/
    │   ├── test_firmware_dominio.py            # NUEVO — desactualizada / expuesta / versión de referencia desconocida, con lista vacía y sin última versión conocida
    │   └── test_token_dominio.py               # NUEVO — token opaco sin relación derivable ni estabilidad entre ventas; rechazo de PAN completo; extracción de últimos 4 + marca + tipo
    ├── integracion/
    │   ├── test_cobertura.py                   # NUEVO (US1) — cobertura histórica por sucursal (FR-002); intención no atendida NO crea venta ni consulta_no_atendida (FR-005, SC-002); desglose por sucursal, nunca agregado sin discriminar (FR-006, SC-003)
    │   ├── test_terminales.py                  # NUEVO (US2) — desactualizada / expuesta con motivo enumerado (FR-010, FR-011, SC-004); ninguna señal deshabilita la terminal (FR-012, SC-005); atribución por sucursal en el momento evaluado (FR-014)
    │   ├── test_tokenizacion.py                # NUEVO (US3) — solo {token, últimos 4, marca, tipo, terminal, venta} persistido (SC-007); NINGÚN campo/log/respuesta contiene PAN (SC-006); rechazo de PAN registrado sin el número (FR-018, SC-008); idempotencia (SC-009); venta de 001 se completa aunque falle la tokenización (FR-020, SC-010); 0 escrituras en venta (SC-013)
    │   └── test_bitacora.py                    # NUEVO (US4) — una entrada por hecho de pago con tipo/día local/sucursal/iniciador/resultado (SC-011); solo anexado: UPDATE y DELETE rechazados (FR-025, SC-012); ninguna entrada con PAN/CVV/banda (FR-026); filtros por sucursal/terminal/tipo (FR-027)
    └── contrato/
        └── test_contrato_pagos.py             # NUEVO — respuestas de contracts/openapi.yaml en forma feliz y modos de fallo, con el formato de error {codigo, mensaje} unificado en 001–006
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001`–`006` cambia de propiedad ni de esquema. Este módulo **solo lee** de `001` (`venta`, `turno`,
`sucursal`, `operador`) y **rellena** la `referencia_terminal_pago` opaca que `001` ya reserva, sin
alterar su tipo ni su semántica (FR-030). No necesita ninguna función nueva en los servicios de
`001` más allá del punto de integración del flujo de captura de pago, cuya forma decide
`data-model.md`/`contracts/` tras v2.2.6.

`frontend/src/App.tsx` se **amplía** (no se reescribe). `TerminalesPago.tsx` y `BitacoraPagos.tsx`
viven en el registro de Operación; `CoberturaPago.tsx` en Análisis.

## Pruebas obligatorias

Derivadas del Principio III. El riesgo central del módulo es doble: (a) que un número de tarjeta
completo (PAN), un CVV o datos de banda/chip acaben persistidos, registrados o devueltos en algún
punto —la violación más grave que este módulo puede cometer, prohibida por la constitución ("Datos de
pago") y el Principio IV—; (b) que una señal de firmware deshabilite una terminal o bloquee un cobro,
convirtiendo una alerta consultiva en una interrupción de caja (Principio II).

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | El PAN nunca se persiste ni se expone | `tests/integracion/test_tokenizacion.py` + `tests/unidad/test_token_dominio.py` | Tras tokenizar N cobros, **ningún** valor de columna, **ninguna** línea de log de la aplicación, **ninguna** entrada de `bitacora_auditoria` y **ninguna** respuesta de `GET /pagos/...` contiene una secuencia de 13–19 dígitos que pase Luhn (SC-006). `token_pago` guarda exactamente {token, últimos 4, marca, tipo, id_terminal, id_venta} y nada más (SC-007). El token no permite derivar el PAN ni un identificador estable de tarjeta entre dos ventas (FR-019). |
| 2 | Rechazo de PAN completo | `tests/integracion/test_tokenizacion.py` | Un intento de escribir un PAN completo en cualquier campo (`ultimos_digitos` con > 4 dígitos, un campo de "número") se **rechaza** con error `{codigo, mensaje}` y se anexa a la bitácora una entrada de tipo `pan_rechazado` **sin** el número (FR-018, SC-008). |
| 3 | Idempotencia de la emisión de token | `tests/integracion/test_tokenizacion.py` | 10 `POST /pagos/tokens` con la misma clave de idempotencia → exactamente un `token_pago`, misma respuesta (SC-009). |
| 4 | La tokenización no es camino crítico | `tests/integracion/test_tokenizacion.py` | Simulada una falla de la tokenización (captura cancelada, error interno), la `venta` de `001` se completa con su comportamiento base y queda marcada "sin tokenización"; 0 cobros bloqueados por el módulo de pagos (FR-020, SC-010). Por conteo directo de filas, `POST /pagos/tokens` no toca `venta`, `turno` ni `operador` de `001` (SC-013). |
| 5 | Señales de firmware consultivas, con motivo | `tests/unidad/test_firmware_dominio.py` + `tests/integracion/test_terminales.py` | "desactualizada" indica versión actual y de referencia; "expuesta a clonación" enumera la referencia de la vulnerabilidad (FR-010, FR-011, SC-004). Lista de vulnerabilidad vacía → 0 terminales expuestas (solo desactualizadas por versión). Sin última versión de referencia del modelo → "versión de referencia desconocida", **nunca** "al día". **Ninguna** señal deshabilita, bloquea o impide el uso de la terminal (FR-012, SC-005). |
| 6 | Bitácora de solo anexado, sin datos sensibles | `tests/integracion/test_bitacora.py` | Cada hecho de pago (emisión de token, rechazo de PAN, actualización de firmware, cambio de cobertura, intención no atendida) genera una entrada con tipo, instante en día local, sucursal, iniciador y resultado (SC-011). Un `UPDATE` o `DELETE` sobre una entrada existente se **rechaza** (FR-025, SC-012). Ninguna entrada contiene PAN, CVV ni datos de banda/chip (FR-026). Filtros por sucursal, terminal y tipo (FR-027). |
| 7 | Cobertura por sucursal, nunca faltante de inventario | `tests/integracion/test_cobertura.py` | La cobertura de un período pasado refleja los medios disponibles **entonces**, no solo los actuales (FR-002, SC-001). Un evento de intención no atendida **no** crea `venta` ni `consulta_no_atendida` de `001` (FR-005, SC-002). Ninguna vista agrega la cobertura o la intención no atendida de dos sucursales sin discriminar la de origen (FR-006, SC-003). |
| 8 | Contrato público | `tests/contrato/test_contrato_pagos.py` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados, con el formato de error `{codigo, mensaje}` unificado en `001`–`006`. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `CoberturaPago.tsx`,
`TerminalesPago.tsx`, `BitacoraPagos.tsx`.

## Sistema de diseño en el frontend

**Registro visual mixto** (`research.md #13`), confirmado contra `DESIGN.md`:

- **`TerminalesPago.tsx` y `BitacoraPagos.tsx` — OPERACIÓN**. La constitución lista "**Operación**
  (punto de venta, inventario, arqueo)"; un registro de dispositivos (terminales) y un libro de
  rastro (bitácora) son de la misma familia que el inventario: alta densidad, la tabla como elemento
  principal, sin tarjetas, radio **2px**, IBM Plex Sans con cifras tabulares reales (versiones de
  firmware y fechas alinean por dígito), **sin animación** salvo la confirmación de registrar una
  terminal o una actualización de firmware.
- **`CoberturaPago.tsx` — ANÁLISIS**. Decidir si habilitar un medio de pago nuevo en una sucursal es
  una **decisión gerencial**: una decisión por bloque, aire visual, líneas bajo 80 caracteres, radio
  **6px**, Source Serif 4. Un único momento de animación deliberado por pantalla (al revelar el
  desglose de la intención no atendida por medio deseado), nunca hover por fila ni fade-in por
  bloque.

**Reglas nombradas de `DESIGN.md` aplicadas sin tocar el documento** (el `documenter` lo actualiza al
final):

- **La Regla del Registro Sin Dinero**: **ninguna** de las tres pantallas tiene una acción que
  comprometa dinero —`007` no mueve dinero (FR-036); registrar una terminal, declarar cobertura y
  consultar la bitácora no son cobros— → **cero apariciones del Verde Rasero `#0F5132`**, igual que
  `Clientes.tsx` y las cuatro pantallas de `006`.
- **La Regla de la Sola Voz**: no aplica por ausencia de acción de dinero.
- **La Regla del Significado** (los tres semánticos, uso reservado):
  - **crítico `#8E2A2A`** — una terminal **expuesta a clonación** y un **intento de PAN rechazado**
    en la bitácora. Es el caso de uso literal que la constitución cita para el crítico ("anomalía").
  - **atención `#9A5B08`** — una terminal **desactualizada** (aún sin vulnerabilidad conocida) y una
    terminal con **"versión de referencia desconocida"** (dato en seguimiento, no crítico).
  - **estimado `#1F5673`** — todo valor **calculado, no observado**: el indicador derivado de
    exposición, la cuota de intención no atendida. El dato **observado** (la versión de firmware
    registrada, la fecha de última actualización, el conteo de eventos) va en tinta normal.
- **La Regla de los Tres Portadores**: "expuesta a clonación", "desactualizada", "versión de
  referencia desconocida" y "venta sin tokenización" se comunican con color semántico + forma (punto
  lleno / medio / hueco) + texto explícito. Una terminal expuesta usa el **punto lleno**; una
  desactualizada, el **punto medio**; "versión de referencia desconocida", el **punto hueco**.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado en `001`); este módulo **no** repite
`init`. Se invoca `new-work` de Impeccable para las tres pantallas con el mundo visual fijado (los
dos registros, la paleta y la tipografía de `DESIGN.md`, sin cambio). El agente `documenter`
actualiza `DESIGN.md` al finalizar, derivándolo de las pantallas construidas — no antes.

## Complexity Tracking

*Sin desviaciones que requieran justificación en la tabla de complejidad.* Este módulo no introduce
ninguna segunda tecnología (ninguna librería de criptografía ni de terceros — el token es un
identificador sustituto opaco de la biblioteca estándar, `research.md #4`), no viola ninguna frontera
de propiedad de datos (solo lee de `001`, nunca escribe; rellena la referencia opaca que `001` ya
reserva) y no necesita ningún mecanismo (disparador de base de datos, cola, servicio externo) más
allá de endpoints HTTP y, opcionalmente, una tarea invocable a mano para el barrido periódico de
estado de firmware — mismo patrón que `tareas/` de `002`, `005` y la alerta de caducidad de `006`.

**La única cuestión de gobernanza fue la enmienda v2.2.6** (añade `token_pago` a la tabla de
Propiedad de Datos), documentada y justificada en `research.md #1` con el formato de
`003`/`004`/`005`, sometida a aprobación explícita y **aplicada el 2026-09-05**. No es una desviación
de un principio: es la corrección de una omisión de la lista de entidades, del mismo tipo que las
tres enmiendas anteriores.
