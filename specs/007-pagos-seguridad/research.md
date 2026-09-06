# Research: Pagos y Seguridad

**Fase 0** · 2026-09-05 · Plan: [plan.md](./plan.md)

El `spec.md` de `007` no dejó ningún `[NEEDS CLARIFICATION]`: las decisiones de alcance mayor
—alcance de la tokenización (local, sin pasarela), tratamiento de la venta perdida por medio de pago
(métrica de cobertura), evaluación de exposición a clonación (indicador consultivo contra lista
configurable) y retención— se cerraron en el propio spec con el criterio de `003`–`006`. Este
documento fija las **decisiones de diseño** que el plan debía tomar por su cuenta, cada una con su
justificación y las alternativas descartadas.

> **ENTRADA #1 — RESUELTA.** `research.md #1` concluyó que la persistencia del token de un cobro con
> tarjeta necesita una **quinta entidad** (`token_pago`) que la constitución v2.2.5 no anticipaba
> para `007`. La decisión se sometió a aprobación explícita del encargo y la **enmienda v2.2.6** fue
> **aprobada y aplicada el 2026-09-05** (informe de impacto en el encabezado de `constitution.md`;
> citas de "versión vigente" de `001`–`006` sincronizadas a v2.2.6, puerta de sincronización v2.2.0).
> `data-model.md`, `contracts/` y `quickstart.md` se escriben sobre v2.2.6.

---

## 1. Propiedad de datos: la tokenización necesita una quinta entidad → **enmienda v2.2.6**

**Decisión**: la persistencia del token de un cobro con tarjeta requiere una entidad **nueva**,
`token_pago`, que **no** estaba en la entrada de `007-pagos-seguridad` de la tabla de "Propiedad de
Datos y Nomenclatura" de la constitución (v2.2.5: `terminal_pago`, `medio_pago`, `cobertura_pago`,
`bitacora_auditoria`). Se sometió a aprobación explícita y la **enmienda constitucional v2.2.6** que
la añade fue **aprobada y aplicada el 2026-09-05**, antes de escribir `data-model.md`.

**Lo que la revisión de la entrada de `007` encontró** (misma revisión que en `003`/`004`/`005`
destapó discrepancias, y que en `006` no encontró ninguna):

Se contrastó la entrada **completa** de `007` contra el spec y las cuatro preocupaciones del
encargo. **Tres de las cuatro caen limpiamente en las entidades anticipadas**:

| Preocupación del encargo | Entidad anticipada (v2.2.5) | ¿Encaja? |
|---|---|---|
| Firmware de terminal / datáfono (versión, actualización, exposición a clonación) | `terminal_pago` | **Sí** — es el dispositivo; el firmware y sus indicadores son sus atributos. |
| Cobertura de medios de pago aceptados por sucursal | `medio_pago` (catálogo) + `cobertura_pago` (aceptación por sucursal + métrica) | **Sí** — exactamente lo que la Lectura Crítica n.º 4 nombra. |
| Log de actividad de pagos | `bitacora_auditoria` | **Sí** — rastro de solo anexado, Principio IV. |
| **Tokenización de los datos de pago** | *(ninguna)* | **No** — ver abajo. |

**Por qué `token_pago` no cabe en ninguna de las cuatro**:

- **No es `medio_pago`**: `medio_pago` es el **catálogo** global (efectivo, débito, crédito,
  transferencia, billetera). Un token es una **instancia transaccional** por cobro; mezclar
  instancias con un catálogo es el error de modelado que la convención de nomenclatura y la
  disciplina de `003`/`004`/`005` evitan.
- **No es `terminal_pago`**: el token pertenece al **cobro** (a la venta), no al **dispositivo**.
  Una terminal procesa miles de cobros; colgar los tokens de la terminal sería una tabla hija con la
  cardinalidad y la semántica equivocadas.
- **No es `cobertura_pago`**: `cobertura_pago` agrega por (sucursal, medio, período). El token es
  por transacción individual.
- **No es un evento de `bitacora_auditoria`**: esta es la confusión tentadora, y es la que hay que
  rechazar con argumento. `bitacora_auditoria` es un **rastro de solo anexado** (FR-025): se
  escriben eventos, nunca se modifican ni se borran, y puede haber **varias** entradas sobre el
  mismo recurso. `token_pago` es lo contrario:
  1. Es el **registro autoritativo** de la relación `venta` ↔ token: `GET` del pago de una venta
     devuelve **el** token y **sus** últimos cuatro dígitos (FR-019) — una búsqueda por clave, no
     una lectura del evento más reciente de un log.
  2. Tiene **requisito de unicidad**: exactamente un token por cobro.
  3. Tiene **requisito de idempotencia**: un reintento con la misma clave de idempotencia devuelve
     el token ya emitido, **sin crear un segundo registro** (FR-021) — eso exige una restricción
     `UNIQUE` sobre una clave de negocio en la tabla autoritativa, ajena a la naturaleza de un log.
  4. Tiene **ciclo de purga** propio: el token vive mientras la venta sea consultable; una tarea de
     mantenimiento (`purgar_tokens_huerfanos`) borra las filas cuya `venta` archivó `001`
     (`data-model.md`) — un log de solo anexado no representa un ciclo de vida sin generar más
     eventos, y entonces ¿cuál es el autoritativo?
  5. Es el **contrato entre módulos** con `001`: `001` guarda `venta.referencia_terminal_pago` como
     opaca y `007` resuelve el pago de una venta desde `token_pago.id_venta` (FR-019, FR-030). Un
     dato estable con clave única, no una línea de auditoría.

**Mismo patrón que las tres enmiendas anteriores**: `rol_producto` (`003`, v2.2.3),
`sustitucion_producto` (`004`, v2.2.4) y `cupon` / `oferta_recompra` / `experimento_reactivacion`
(`005`, v2.2.5) son todas **declaraciones de negocio que el módulo modela en tabla propia con FK**, y
que la lista original de la constitución no contemplaba **porque se escribió antes de que existiera
el spec del módulo** (informe de impacto de sincronización de `constitution.md`). `token_pago` es
exactamente eso: la constitución ya fija la **regla** ("Datos de pago": conservar únicamente
identificadores y últimos dígitos) pero **no la entidad** que la implementa. La entrada de `007` se
ratificó en v2.0.0 como un supuesto anterior a la especificación de pagos y seguridad.

**Forma de `token_pago`** (base para `data-model.md`, ya con v2.2.6 aplicada):

- `id_token_pago` — clave primaria.
- `token` `TEXT NOT NULL UNIQUE` — identificador sustituto opaco (UUID v4 o equivalente; **no**
  criptográfico, **no** reversible, **sin** relación derivable con el PAN — ver #4).
- `id_venta` `INTEGER NOT NULL` FK → `venta` de `001` (**solo lectura**), `UNIQUE` (un token por
  cobro).
- `clave_idempotencia` `TEXT NOT NULL UNIQUE` — para FR-021.
- `ultimos_digitos` `CHAR(4) NOT NULL` — con `CHECK` de exactamente 4 dígitos (barrera de FR-018).
- `marca` `ENUM('visa', 'mastercard', 'amex', 'diners', 'otra')` — derivada del rango BIN.
- `tipo` `ENUM('debito', 'credito', 'desconocido')` — `desconocido` cuando el flujo de captura no lo
  informa; nunca se adivina.
- `id_terminal_pago` `INTEGER NOT NULL` FK → `terminal_pago` (de `007`) — la terminal de captura.
- `id_sucursal` `INTEGER NOT NULL` — denormalizado del turno de la venta (inmutable).
- `instante` `TIMESTAMPTZ NOT NULL`; `dia_local` `DATE`; `marca_tiempo_origen` `TIMESTAMPTZ` para el
  desempate offline (FR-022).
- **Ningún** campo de PAN, CVV, banda o chip. El `CHECK` sobre `ultimos_digitos` y la validación del
  servicio garantizan que un PAN completo no entra (FR-017, FR-018, SC-006).

Detalle completo (índices, purga, comportamiento de idempotencia) en `data-model.md`.

**Rationale**: la Puerta de propiedad de datos exige que `data-model.md` y la tabla constitucional no
discrepen. Aquí discrepan: el spec necesita `token_pago` y la tabla no la lista. `003`, `004` y `005`
establecieron el precedente de **enmendar primero, diseñar después**. Añadir la entidad sin enmienda
violaría la Puerta; meter el token en `bitacora_auditoria` violaría FR-025 y la semántica de un
rastro de auditoría.

**Alternativas descartadas**:

- **Token dentro de `bitacora_auditoria`** — rechazada por los cinco argumentos de arriba: unicidad,
  idempotencia, ciclo de purga, ser el sistema de registro de la relación venta↔token y rellenar la
  referencia opaca de `001` son incompatibles con un log de solo anexado.
- **Token como string estructurado dentro de `venta.referencia_terminal_pago` de `001`** — rechazada:
  `001` declara ese campo **opaco y no interpretado** (`001/data-model.md`, `001/spec.md` §3); meter
  JSON estructurado ahí acopla `007` a un formato dentro de una columna que `001` posee, y los
  últimos dígitos / marca / tipo / terminal / clave de idempotencia seguirían necesitando un hogar
  consultable por `007`. FR-030 dice explícitamente que `007` **no** cambia la semántica de ese
  campo.
- **Token como tabla hija de `terminal_pago`** — rechazada: sigue siendo una tabla nueva (misma
  enmienda), con la cardinalidad equivocada (el token es de la venta, no del dispositivo).
- **No persistir la relación venta↔token en absoluto** — rechazada: FR-019 exige consultar el token
  y los últimos dígitos de una venta; sin registro no hay consulta.

**VEREDICTO — resuelto**:

> **La enmienda constitucional v2.2.6 fue aprobada y aplicada el 2026-09-05**, antes de escribir
> `data-model.md`, `contracts/` y `quickstart.md`.
>
> - **Qué añadió v2.2.6**: la entidad `token_pago` a la entrada de `007-pagos-seguridad` en la tabla
>   de "Propiedad de Datos y Nomenclatura" (de 4 a 5 entidades: `terminal_pago`, `medio_pago`,
>   `cobertura_pago`, `bitacora_auditoria`, **`token_pago`**), más una viñeta de frontera que aclara
>   que `token_pago` **consulta** `venta` de `001` sin poseerla y **rellena** la
>   `referencia_terminal_pago` opaca sin alterar el esquema de `001`.
> - **Tipo de cambio**: PARCHE (amplía una entrada de la tabla de propiedad; no toca ningún
>   principio) — igual que v2.2.4 (una entidad añadida a `004`).
> - **Puerta de sincronización de enmiendas (v2.2.0)**: se sincronizaron a **v2.2.6** las citas de
>   "versión vigente" en los artefactos de `001`–`006` (mismo barrido que hicieron
>   v2.2.3/v2.2.4/v2.2.5). Las citas históricas no se barrieron.
> - El informe de impacto está en el encabezado de `constitution.md`; el pie del documento quedó en
>   `Versión: 2.2.6`.

---

## 2. Reutilización íntegra del stack de `001`–`006`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + TS + Vite, sin librería de componentes de terceros) que `001`–`006`, sobre la
misma base PostgreSQL 16 (puerto 5442). Migración nueva `0007_pagos_seguridad`. **Cero dependencias
nuevas.**

**Rationale**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función
que una ya presente, salvo justificación registrada. Ninguna característica de este módulo exige un
lenguaje, framework o motor distinto. En particular, **no se añade ninguna librería de
criptografía**: el token no es un valor cifrado reversible sino un identificador sustituto opaco
(ver #4).

**Alternativas descartadas**: ninguna evaluada seriamente para el stack base.

---

## 3. Vigilancia de firmware: indicadores derivados y consultivos, nunca tabla ni bloqueo (FR-008 a FR-015)

**Decisión**: `terminal_pago` guarda los **datos observados** (identificador, modelo, sucursal
actual, historia de ubicación, `version_firmware`, `fecha_ultima_actualizacion_firmware`). Los
**indicadores** "desactualizada" y "expuesta a clonación" son **cálculo derivado en el momento de la
consulta**, no columnas materializadas:

- **desactualizada** = `version_firmware` < última versión de referencia del modelo
  (`ULTIMA_VERSION_FIRMWARE` por modelo, #10). Si no hay última versión de referencia conocida para
  el modelo → **"versión de referencia desconocida"**, nunca "al día" (FR-010).
- **expuesta a clonación** = `version_firmware` o `modelo` ∈ `LISTA_FIRMWARE_VULNERABLE` (#10), con
  la referencia de la vulnerabilidad (boletín / CVE / nota interna) enumerada (FR-011). Lista vacía
  → 0 terminales expuestas (FR-011, Edge Case del spec).

El sistema **nunca** deshabilita, bloquea ni impide el uso de una terminal marcada (FR-012, Principio
V; Principio II: la caja no se bloquea). La comparación de versiones es aritmética de una línea
(orden lexicográfico de tuplas de enteros `major.minor.patch`), **sin librería de versionado**.

**Historia de ubicación**: `terminal_pago` tiene una tabla/atributo de historia
`(id_sucursal, desde, hasta)`; una señal de firmware se atribuye a la sucursal **donde estaba la
terminal en el momento evaluado** (FR-014), no siempre a la actual.

**Rationale**: los indicadores no tienen ciclo de vida (no se cierran, no se anulan, no tienen
estado editable), la constitución los trata como el tipo de "detección de anomalías" del Principio V
—explicable y consultiva—, y materializarlos exigiría recalcularlos cada vez que cambia la
configuración de versiones. Mismo criterio que los indicadores por operador de `006` (`research.md
#2/#7` de `006`) y la alerta de caducidad de `006` (#5): consulta derivada, nunca tabla.

**Alternativas descartadas**: columnas `es_desactualizada` / `es_expuesta` materializadas —hay que
recalcular al cambiar la config, sin ganancia a esta escala—; descubrimiento automático de
vulnerabilidades consultando una fuente externa —fuera de alcance, y la constitución prohíbe que una
función de red sea camino crítico; la lista la mantiene el negocio—; una librería de comparación
semántica de versiones —Principio I, es `tuple(map(int, v.split('.')))`.

---

## 4. Generación del token: identificador sustituto opaco, sin criptografía, sin estabilidad entre ventas (FR-016 a FR-022)

**Decisión**: el token es un **UUID v4** (o equivalente de `secrets`/`uuid` de la biblioteca
estándar) — un identificador aleatorio sin relación matemática con el PAN. **No** es un cifrado
reversible del número, **no** es un hash del número (un hash permitiría un ataque de diccionario
sobre un espacio de PAN pequeño y reconstruiría un identificador **estable** de tarjeta entre
ventas), **no** usa ninguna librería de criptografía de terceros.

- El flujo de captura entrega el PAN → el servicio extrae los **últimos 4 dígitos**, la **marca**
  (por rango BIN, tabla estática mínima) y el **tipo** → genera el UUID → persiste solo eso →
  **descarta el PAN** (nunca toca disco ni log).
- **Sin estabilidad entre ventas**: la misma tarjeta usada en dos ventas produce **dos** tokens
  distintos (dos UUID). El módulo **no** mantiene un índice de PAN→token; solo venta→token. Esto
  impide reconstruir un historial de un titular a partir de los tokens (Principio IV: datos
  personales al mínimo; `research.md` del spec, Assumptions).
- **Rechazo de PAN** (FR-018): `ultimos_digitos` tiene `CHECK (ultimos_digitos ~ '^[0-9]{4}$')`; el
  servicio valida que ningún campo de entrada contenga una secuencia de 13–19 dígitos que pase Luhn;
  un intento se rechaza y se anexa a la bitácora un evento `pan_rechazado` **sin** el número.

**Rationale**: "tokenizar" en un sistema sin pasarela real significa sustituir el dato sensible por
un subrogado inofensivo y descartar el original. Un UUID aleatorio es el subrogado más simple que
cumple: opaco, no reversible, no enumerable, y sin librería nueva (Principio I). La no-estabilidad
entre ventas es una decisión de minimización de datos deliberada.

**Alternativas descartadas**: cifrado simétrico del PAN con una clave del entorno —el PAN cifrado
**es** el PAN a efectos de la constitución ("no se almacena … ni se transmite"); además exige gestión
de clave y una librería—; hash con sal del PAN —estable entre ventas (reconstruye al titular) y
vulnerable a diccionario sobre el espacio BIN+4; token estable tipo "network token" de una pasarela
—no hay pasarela (FR-036).

---

## 5. Cobertura de medios de pago: catálogo global + aceptación histórica por sucursal + métrica de intención no atendida (FR-001 a FR-007)

**Decisión**:

- `medio_pago` es el **catálogo global** (`MEDIOS_PAGO_BASE` de #10: efectivo, tarjeta_debito,
  tarjeta_credito, transferencia, billetera_movil), extensible por fila sin cambio de esquema.
  Atributos: `nombre`, `requiere_terminal` (bool), `admite_tokenizacion` (bool).
- `cobertura_pago` es la **aceptación de un `medio_pago` en una `sucursal`**, con `fecha_desde` (y
  `fecha_hasta` NULL mientras siga vigente) → la cobertura de un período pasado se resuelve
  filtrando por esas fechas, **no** por el estado actual (FR-002). Es **histórico**, no un booleano.
- La **métrica de intención de compra no atendida** NO es una entidad nueva. Los eventos
  "un cliente no pudo pagar como quería" son **hechos de solo anexado** —exactamente la naturaleza de
  `bitacora_auditoria`— y se registran ahí con `tipo_evento = 'intencion_no_atendida'` e
  `id_medio_pago` = el medio deseado. La **cuota** se **deriva** al leer, cruzando esos eventos
  contra `cobertura_pago` (`data-model.md`, sección `cobertura_pago`). Esto evita una sexta entidad
  —misma disciplina con la que `006` mantuvo `anomalia_caja` como una sola tabla en vez de dos—.
  A diferencia de `token_pago` (registro autoritativo con clave única, por eso sí necesita tabla),
  un evento de intención no atendida no tiene estado ni unicidad: es una línea de bitácora. En ningún
  caso crea `venta` ni `consulta_no_atendida` de `001` (FR-005).

**Rationale**: la Lectura Crítica n.º 4 es literal — "métrica de cobertura de medios de pago por
sucursal, no venta perdida en el sentido de faltante de inventario". `001` no guarda el medio de
pago de una venta (solo la `referencia_terminal_pago` opaca y el `total`), así que no hay dato de
`001` que duplicar: el catálogo y la cobertura son enteramente de `007`.

**Alternativas descartadas**: cobertura como booleano `acepta_X` por sucursal —pierde el histórico,
y una consulta de un trimestre pasado mentiría—; modelar la intención no atendida como una `venta` de
importe cero —contradice FR-005 y la Lectura Crítica n.º 4, y ensucia todas las métricas de `001`—;
como `consulta_no_atendida` de `001` —esa entidad es "no hay producto"; esto es "no puedo pagar
así", fenómeno distinto.

---

## 6. Bitácora de auditoría: solo anexado, sin datos sensibles, filtrable por sucursal/terminal/tipo (FR-023 a FR-028)

**Decisión**: `bitacora_auditoria` es **solo INSERT**. Se impide `UPDATE` y `DELETE` (revocación de
privilegios a nivel de rol de base de datos —`REVOKE UPDATE, DELETE ... FROM rasero_app`— + ausencia
de cualquier endpoint o método de servicio que los ejecute; prueba obligatoria #6). El `tipo_evento`
es un `ENUM` cerrado de 14 valores (`token_emitido`, `token_idempotencia_divergente`,
`token_purgado`, `pan_rechazado`, `firmware_actualizado`, `firmware_desactualizado_detectado`,
`terminal_expuesta_detectada`, `terminal_registrada`, `terminal_movida`, `medio_pago_alta`,
`medio_pago_baja`, `cobertura_declarada`, `intencion_no_atendida`, `config_firmware_cambiada`).
Columnas completas en `data-model.md`. **Ningún** campo de texto libre poblado por el cliente:
`resultado` se redacta desde plantillas, `referencia_recurso_id` es un id o un token opaco — nada
puede arrastrar un PAN.

**Retención**: `RETENCION_BITACORA_ANIOS` = 2 (año fiscal en curso + anterior, #10); no se purga
antes.

**Rationale**: Principio IV — "los registros DEBEN ser estructurados y consultables por identificador
… El filtro por sucursal es obligatorio", "sobrescribir … está PROHIBIDO", "los rastros NO DEBEN
contener datos de pago completos ni datos personales más allá del identificador mínimo". La bitácora
de `007` es la aplicación directa de ese principio al dominio de pagos.

**Alternativas descartadas**: bitácora con `UPDATE` para "corregir" una entrada —viola FR-025; una
corrección es una entrada nueva—; un campo `detalle` JSONB libre —riesgo de que una integración
vuelque ahí un PAN; se prefiere un `ENUM` de tipos y `resultado` desde plantilla—; reusar un
sistema de logging de aplicación en vez de una tabla —no es consultable por sucursal ni tiene
garantía de retención.

---

## 7. Frontera con `001`: solo lectura + relleno de la referencia opaca (FR-029 a FR-032)

**Decisión**:

- `007` **solo lee** de `001`: `venta` (`id_turno`, `total`, `referencia_terminal_pago`), `turno`
  (`id_operador`, sucursal), `sucursal` (`zona_horaria`), `operador` (`es_encargado`). Ninguna
  escritura; los tests de frontera cuentan filas de `venta`/`turno`/`operador` antes y después de
  cada operación de `007` (SC-013).
- **`007` NO escribe `venta.referencia_terminal_pago`.** El vínculo **autoritativo** venta↔token es
  `token_pago.id_venta` (FK de solo lectura, `UNIQUE`). El campo `referencia_terminal_pago` de `001`
  lo puebla **el propio servicio de venta de `001`** con el valor del `token` que devuelve
  `POST /pagos/tokens`, dentro de su transacción de venta (FR-007 de `001`), cuando `007` responde
  dentro de un breve tiempo de espera; si `007` no responde a tiempo, `001` deja ese campo `NULL` y
  completa la venta igual (FR-020, Principio II), y `007` procesa el cobro pendiente después y crea
  `token_pago`. `GET /pagos/ventas/{id_venta}/pago` responde **siempre** desde `token_pago`, nunca
  desde ese campo. **No hay `[001-escritura]`**, a diferencia de `003` (que sí escribe en
  `producto_precio_sucursal` vía función-puente). Los tests de frontera cuentan filas de
  `venta`/`turno`/`operador` antes y después de cada operación de `007` (SC-013).
- La atribución de sucursal y operador de un hecho de pago sale de `venta.id_turno → turno`, sin
  tocar `operador.pin_hash` (FR-031).

**Rationale**: `001/spec.md` §3 ya declara "`terminal_pago` sigue siendo propiedad de
`007-pagos-seguridad` y este módulo solo guarda una referencia"; `001/data-model.md` línea 233 la
tipa `TEXT NULL` "referencia opaca". `007` es el módulo que le da sentido, sin cambiar el esquema de
`001` — mismo patrón de frontera que `003`/`004`/`005`/`006` frente a `001`.

**Alternativas descartadas**: que `007` añada una columna a `venta` de `001` —viola la Puerta de
propiedad de datos (un cambio de esquema sobre una entidad ajena se hace en la funcionalidad
propietaria)—; que `001` invoque a `007` de forma síncrona y bloqueante en `POST /ventas` —viola el
Principio II; la tokenización nunca es camino crítico.

---

## 8. Día local y tiempo

**Decisión**: toda entrada de `bitacora_auditoria` y toda agregación de `cobertura_pago` se fecha por
el **día local de la sucursal**: `(instante AT TIME ZONE sucursal.zona_horaria)::date`. Instantes en
`TIMESTAMPTZ` (UTC). Un reporte multi-sucursal declara su criterio de día.

**Rationale**: restricción "Tiempo" de la constitución, idéntica a como `004`, `005` y `006` fijan
sus períodos.

---

## 9. Convención de endpoints — prefijo `/pagos`

**Decisión** (se materializa en `contracts/openapi.yaml`): se reutiliza la convención de `001`–`006`
(sustantivos, `kebab-case`, acciones no-CRUD como subrecurso, un prefijo por módulo). Prefijo
`/pagos`:

| Endpoint (previsto) | FR | Nota |
|---|---|---|
| `GET /pagos/medios` | FR-001 | Catálogo global. |
| `PUT /pagos/cobertura` | FR-002, FR-007 | El encargado declara qué medios acepta una sucursal, con `fecha_desde`. |
| `POST /pagos/intencion-no-atendida` | FR-003 | Registra el evento; **no** crea venta. |
| `GET /pagos/cobertura?id_sucursal=&desde=&hasta=` | FR-004, FR-006 | Cobertura + cuota de intención no atendida por medio deseado. |
| `POST /pagos/terminales` · `PUT /pagos/terminales/{id}` | FR-008, FR-015 | Registrar / mover terminal (encargado). |
| `POST /pagos/terminales/{id}/firmware` | FR-013 | Registrar una actualización de firmware. |
| `GET /pagos/terminales?id_sucursal=` | FR-010, FR-011, FR-014 | Estado derivado: desactualizada / expuesta / desconocida, con motivo. |
| `POST /pagos/tokens` | FR-016, FR-021 | **Idempotente.** Recibe el PAN, devuelve el token. Escribe `token_pago` (v2.2.6). |
| `GET /pagos/ventas/{id_venta}/pago` | FR-019 | Token + últimos 4 dígitos; **nunca** el PAN. |
| `GET /pagos/bitacora?id_sucursal=&id_terminal=&tipo=&desde=&hasta=` | FR-027 | Rastro filtrable, solo lectura. |

**Formato de error** `{ codigo, mensaje }` unificado con `001`–`006`; `mensaje` redactado para el
operador con la acción correctiva, nunca una traza técnica (Principio IV).

**Ningún endpoint** deshabilita una terminal, bloquea un cobro ni mueve dinero (FR-012, FR-035,
FR-036).

---

## 10. Parámetros de configuración → `backend/rasero/config/pagos.py`

Todos en un único lugar de verdad, sobrescribibles por variable de entorno (mismo patrón que
`config/caja.py` de `006`, `config/pronostico.py` de `004`, `config/promociones.py` de `005`). Cada
uno justificado aquí, **no en comentarios de código**:

| Parámetro | Valor de arranque | Dónde se usa | Justificación |
|---|---|---|---|
| `MEDIOS_PAGO_BASE` | `['efectivo', 'tarjeta_debito', 'tarjeta_credito', 'transferencia', 'billetera_movil']` | Semilla del catálogo `medio_pago` (#5) | Los cinco medios que un minimarket ecuatoriano maneja hoy. Extensible por fila sin migración. |
| `DIGITOS_CONSERVADOS` | **4** | Extracción al tokenizar (#4, FR-016) | Los últimos cuatro dígitos son el máximo que la constitución permite conservar y el mínimo que un encargado necesita para conciliar un cobro con el comprobante del cliente. |
| `RETENCION_BITACORA_ANIOS` | **2** | Purga de `bitacora_auditoria` (#6) | Año fiscal en curso + anterior: cubre dos cierres anuales y cualquier revisión retrospectiva de un ejercicio cerrado, sin acumular indefinidamente. `plan.md` puede extenderlo, no reducirlo. |
| `ULTIMA_VERSION_FIRMWARE` | `{}` (por modelo, lo puebla el negocio) | Indicador "desactualizada" (#3, FR-009, FR-010) | El negocio registra la última versión conocida por modelo de datáfono. Vacío ⇒ "versión de referencia desconocida", nunca "al día". |
| `LISTA_FIRMWARE_VULNERABLE` | `[]` (lo puebla el negocio) | Indicador "expuesta a clonación" (#3, FR-009, FR-011) | Lista de `(modelo?, version, referencia_vulnerabilidad)` que el negocio mantiene desde boletines del fabricante o avisos de seguridad. Vacía ⇒ 0 terminales expuestas por vulnerabilidad conocida. El sistema no descubre vulnerabilidades por su cuenta. |

Los cinco son **configuración de negocio o calibración dentro de decisiones ya fijadas**; ajustarlos
no reabre ninguna FR ni la decisión de #1 sobre la entidad `token_pago`.

---

## 11. Estado de dependencias (verificado contra el repositorio)

| Dependencia | Estado real | Fuente |
|---|---|---|
| `001` — `venta` (`id_turno`, `referencia_terminal_pago TEXT NULL`), `turno`, `sucursal` (`zona_horaria`), `operador` (`es_encargado`) | **Entregado** (checkpoint de `001` Setup + Foundational + US1; migración `0001`) | `specs/001-core-ventas-inventario/data-model.md` línea 233; `.../tasks.md` |
| `006-caja-mermas-fraude` | **Entregado** (HEAD `d1da398`); `007` no consume nada de `006` | `git log`; `specs/006-caja-mermas-fraude/spec.md` |
| Constitución — entidad `token_pago` | **Añadida por la enmienda v2.2.6** (aprobada y aplicada el 2026-09-05, ver #1) | tabla de Propiedad de Datos |

**Conclusión para `/speckit-tasks`**: **ninguna User Story de `007` está bloqueada** — ni por datos
de `001` faltantes (a diferencia de `006`) ni por la enmienda (v2.2.6 ya aplicada). US1 (cobertura),
US2 (terminales) y US4 (bitácora) usan entidades desde la ratificación; US3 (tokenización) usa
`token_pago` de v2.2.6.

---

## 15. `clave_idempotencia` de `token_pago`: la genera el cliente, no el backend de `007`

**Decisión** (mismo tipo de precisión que `006` fijó con `arqueo.id_turno UNIQUE`, `research.md #4`
de `006`): la `clave_idempotencia` de un cobro con tarjeta **la genera el cliente** —el flujo de
captura de pago de `001`, en nombre de la terminal/datáfono— **antes del primer intento** de
`POST /pagos/tokens`. `007` **no** la genera. Es la misma convención que `001` ya usa para
`venta.clave_idempotencia` (`001/data-model.md`: "Generada por el cliente antes del primer intento").

**Por qué el cliente y no el backend**: si el backend generase la clave al recibir la petición, un
reintento de red del datáfono —el caso exacto que interesa— llegaría **sin** clave o con una
distinta, y el backend crearía un segundo `token_pago`. La clave solo cumple su función si es
**estable a través de los reintentos del mismo cobro**, y eso obliga a que la fije quien origina el
cobro, una vez, antes de enviarlo. Es la misma razón por la que `001` la pide al cliente para
`venta`.

**Dos barreras, comportamiento determinista** ante un reintento de red del datáfono:

| Situación | Qué llega | Respuesta de `007` |
|---|---|---|
| Reintento normal (el primer intento expiró en el cliente pero pudo completarse en el servidor) | misma `id_venta` + misma `clave_idempotencia` | `200` con el `token` ya emitido; **ninguna** fila nueva (`UNIQUE (id_venta)`) |
| Bug del cliente: repite el cobro con clave nueva | misma `id_venta` + `clave_idempotencia` distinta | `200` con el `token` ya emitido (la clave natural `id_venta` manda) + evento `token_idempotencia_divergente` en la bitácora para revisión |
| Bug del cliente: reutiliza una clave para otro cobro | `clave_idempotencia` ya usada + `id_venta` distinta | `409 pagos_clave_idempotencia_reusada` |
| Primer intento de un cobro nuevo | `id_venta` y `clave_idempotencia` inéditas | `201` con un `token` nuevo |

**Clave natural primero**: la idempotencia **primaria** es `UNIQUE (id_venta)` —un token por cobro,
igual que `006` usa `UNIQUE (id_turno)` para un arqueo por turno—. `clave_idempotencia UNIQUE` es la
**segunda** barrera, que además detecta el reuso de clave entre cobros distintos. Un reintento se
reconoce por `id_venta`; la clave solo tiene que coincidir.

**Offline** (FR-022): un cobro con tarjeta sin conectividad se completa en `001` con su
comportamiento base y se encola; al reconciliar, `POST /pagos/tokens` se reenvía con la misma
`id_venta`, la misma `clave_idempotencia` y `marca_tiempo_origen` = el instante del cobro físico.
La regla de conflicto de `001` (gana la marca de tiempo de origen más antigua sobre el mismo
recurso; el recurso es `id_venta`) aplica sin cambios.

**Alternativas descartadas**: backend genera la clave al recibir —rompe la idempotencia ante
reintento de red, que es justo lo que hay que cubrir—; sin `clave_idempotencia`, solo `UNIQUE
(id_venta)` —suficiente para el 99 % de los casos, pero pierde la detección de reuso de clave y la
señal `token_idempotencia_divergente`, y deja `007` sin la simetría con la convención de `001`—;
clave = hash del PAN —el PAN no se conserva, y un hash del PAN sería un identificador estable de
tarjeta entre ventas, prohibido por `research.md #4`.

---

## Entradas que se cierran en la Fase 1

- **#12 — Ciclo de vida de las entidades y máquina de estados** (análogo a `research.md #13` de
  `006`): `terminal_pago` y `cobertura_pago` son registro + historial; `token_pago` y
  `bitacora_auditoria` son append. Se detalla en `data-model.md`.
- **#13 — Frontend: registros visuales Operación/Análisis y reglas nombradas de `DESIGN.md`**: ya
  esbozado en `plan.md` §"Sistema de diseño en el frontend"; se cierra al construir las pantallas y
  el `documenter` actualiza `DESIGN.md`.
- **#14 — Contrato `openapi.yaml` completo**: se escribe en `contracts/openapi.yaml`.
