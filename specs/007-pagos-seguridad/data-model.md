# Data Model: Pagos y Seguridad

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo singular,
sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Instantes en `TIMESTAMPTZ`
(UTC); días locales y fechas de vigencia como `DATE`. **Este módulo no persiste ningún importe** —
no hay `total` de pago, no hay settlement, no se mueve dinero real (FR-036). La única magnitud
numérica de negocio es la **cuota de intención de compra no atendida**, que es una razón calculada
con `Decimal` al leer y presentada como cadena decimal; **no se persiste**. **Ningún tipo de coma
flotante aparece en este modelo.**

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las **cinco** entidades que la constitución (**v2.4.0**) asigna a
`007-pagos-seguridad`: `medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`,
`token_pago`. **Ninguna otra.**

`token_pago` se añadió por la enmienda **v2.2.6** (2026-09-05), a raíz de `research.md #1`: la
persistencia del token de un cobro con tarjeta es un **registro autoritativo** con `UNIQUE` por cobro
e idempotencia (FR-019, FR-021), no un evento de log, y no cabía en las otras cuatro entidades
ratificadas. Mismo patrón que `sugerencia_precio` (v2.2.3), `sustitucion_producto` (v2.2.4) y los
tres mecanismos de promoción (v2.2.5). La enmienda está aprobada y aplicada; el informe de impacto
está en el encabezado de `constitution.md`.

**Los indicadores de firmware NO son entidad** (research.md #3): "desactualizada", "expuesta a
clonación" y "versión de referencia desconocida" son **cálculo derivado** en el momento de la
consulta, comparando `terminal_pago.version_firmware` contra la configuración de `research.md #10`.
No tienen tabla, no tienen ciclo de vida, no se recomputan a una fila.

**La cuota de intención de compra no atendida NO es entidad** (research.md #5): los eventos
"un cliente no pudo pagar como quería" se registran en `bitacora_auditoria` (tipo de evento
`intencion_no_atendida`), que es exactamente su naturaleza —un hecho de solo anexado—, y la cuota se
**deriva** al leer, cruzando esos eventos contra `cobertura_pago`. No se crea una sexta entidad.

**Frontera de propiedad explícita — solo lectura de `001`, sin escritura ni posesión**: este módulo
consulta de `001` las entidades `venta` (`id_turno`, `total`, `referencia_terminal_pago`,
`instante`), `turno` (`id_operador`, `id_sucursal`, `instante_apertura`, `instante_cierre`),
`operador` (`id_operador`, `nombre`, `es_encargado` — **nunca** `pin_hash`) y `sucursal`
(`id_sucursal`, `zona_horaria`, `nombre`). **`007` no escribe en ninguna tabla de `001`** —a
diferencia de `003`, que escribe en `producto_precio_sucursal`. En particular, **`007` no escribe
`venta.referencia_terminal_pago`**: ese campo lo puebla el propio servicio de venta de `001` con el
valor del token cuando la tokenización responde a tiempo (FR-007 de `001`), y queda `NULL` en otro
caso; el vínculo **autoritativo** venta↔token es siempre `token_pago.id_venta` (research.md #7). No
se duplica ninguna columna de `001` salvo tres valores **inmutables y derivados** del turno de la
venta en `token_pago` (`id_sucursal`, `dia_local`) y en cada entrada de `bitacora_auditoria`
(`id_sucursal`, `dia_local`), justificados por el filtro obligatorio por sucursal (FR-032, FR-034,
Principio IV) y porque un turno cerrado no cambia de sucursal ni de instante.

## Sin bloqueo por `001`

A diferencia de `006` (bloqueado por `conteo_fisico`/`conteo_renglon` de `001` User Story 5), **este
modelo no tiene ninguna FK ni ninguna lógica bloqueada**: `venta`, `turno`, `sucursal` y `operador`
están entregadas desde el checkpoint de `001` Setup + Foundational + User Story 1 (verificado contra
el repositorio, `research.md #11`). El único punto de integración es el flujo de captura de pago de
`001`, resuelto en `research.md #7` y en `contracts/openapi.yaml`.

---

## `medio_pago`

Catálogo global de los medios de pago que el sistema conoce. Es un catálogo, **no** una tabla de
hechos: una fila por medio, extensible sin cambio de esquema (research.md #5).

| Campo | Tipo | Notas |
|---|---|---|
| `id_medio_pago` | `INTEGER` PK | |
| `nombre` | `TEXT NOT NULL UNIQUE` | `efectivo`, `tarjeta_debito`, `tarjeta_credito`, `transferencia`, `billetera_movil`. Sembrado desde `MEDIOS_PAGO_BASE` (config, research.md #10) |
| `requiere_terminal` | `BOOLEAN NOT NULL` | `TRUE` para las tarjetas: su cobro pasa por una `terminal_pago` |
| `admite_tokenizacion` | `BOOLEAN NOT NULL` | `TRUE` solo para las tarjetas: solo esos cobros generan `token_pago` |
| `activo` | `BOOLEAN NOT NULL DEFAULT TRUE` | Un medio retirado del catálogo global se marca inactivo; nunca se borra (Principio IV) |

*Frontera*: `001` **no** guarda el medio de pago de una `venta` (solo `referencia_terminal_pago`
opaca y `total`). No hay dato de `001` que este catálogo duplique (research.md #5).

---

## `terminal_pago`

Una terminal de pago (datáfono) física del negocio. Es **nueva en este módulo**: `001` solo guarda
una `referencia_terminal_pago` opaca en cada `venta` y declara `terminal_pago` propiedad de `007`
(`001/data-model.md` línea 233; `001/spec.md` §3).

| Campo | Tipo | Notas |
|---|---|---|
| `id_terminal_pago` | `INTEGER` PK | |
| `identificador` | `TEXT NOT NULL UNIQUE` | El número de serie o etiqueta física de la terminal |
| `modelo` | `TEXT NOT NULL` | Clave contra `ULTIMA_VERSION_FIRMWARE` y `LISTA_FIRMWARE_VULNERABLE` (research.md #3, #10) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | Sucursal **actual**. FK de solo lectura |
| `version_firmware` | `TEXT NOT NULL` | `major.minor.patch`. `CHECK (version_firmware ~ '^[0-9]+\.[0-9]+\.[0-9]+$')`. Se compara como tupla de enteros, sin librería de versionado (research.md #3) |
| `fecha_ultima_actualizacion_firmware` | `DATE NULL` | Cuándo se registró la versión actual. NULL si nunca se ha actualizado desde el alta |
| `historial_ubicacion` | `JSONB NOT NULL DEFAULT '[]'` | Array `{id_sucursal, desde, hasta}` (fechas locales; `hasta` NULL = tramo vigente). Una señal de firmware se atribuye a la sucursal donde estaba la terminal **en el momento evaluado** (FR-014), no siempre a la actual (research.md #3) |
| `historial_firmware` | `JSONB NOT NULL DEFAULT '[]'` | Array `{version, fecha, id_operador}` con cada actualización registrada (FR-013). Columna en la fila, no tabla hija (mismo criterio que `arqueo.ajustes` de `006`) |
| `id_operador_registro` | `INTEGER FK → operador (001) NOT NULL` | Encargado que dio de alta la terminal (`es_encargado`, FR-015) |
| `instante_registro` | `TIMESTAMPTZ NOT NULL` | |
| `activa` | `BOOLEAN NOT NULL DEFAULT TRUE` | Una terminal retirada se marca inactiva; **nunca se borra** (Principio IV). El sistema **no** la marca inactiva por una señal de firmware (FR-012) |

*Máquina de estados*: implícita — una terminal está `activa` o retirada (`activa = FALSE`), por
decisión de una persona. **Ninguna transición automática por una señal de firmware** (FR-012,
Principio II).

*Indicadores derivados* (no columnas — research.md #3), calculados en `GET /pagos/terminales`:

- **`desactualizada`** ⟺ `tupla(version_firmware) < tupla(ULTIMA_VERSION_FIRMWARE[modelo])`. Si
  `modelo` no está en `ULTIMA_VERSION_FIRMWARE` ⇒ **`version_referencia_desconocida`**, nunca
  "al día" (FR-010).
- **`expuesta_a_clonacion`** ⟺ `(modelo, version_firmware)` o `version_firmware` figura en
  `LISTA_FIRMWARE_VULNERABLE`, que lleva la `referencia_vulnerabilidad` enumerada en la respuesta
  (FR-011). Lista vacía ⇒ 0 terminales expuestas (Edge Case del spec).

---

## `cobertura_pago`

La **aceptación** de un `medio_pago` en una `sucursal`, con vigencia histórica (research.md #5). Una
fila por (medio, sucursal, tramo de vigencia): la cobertura de un período pasado se resuelve
filtrando por `fecha_desde` / `fecha_hasta`, **no** por el estado actual (FR-002).

| Campo | Tipo | Notas |
|---|---|---|
| `id_cobertura_pago` | `INTEGER` PK | |
| `id_medio_pago` | `INTEGER FK → medio_pago NOT NULL` | |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | Toda cobertura se identifica por sucursal (FR-006) |
| `fecha_desde` | `DATE NOT NULL` | Primer día local en que la sucursal acepta ese medio |
| `fecha_hasta` | `DATE NULL` | Último día local; NULL = aceptación vigente. `CHECK (fecha_hasta IS NULL OR fecha_hasta >= fecha_desde)` |
| `id_operador` | `INTEGER FK → operador (001) NOT NULL` | Encargado que declaró la cobertura (`es_encargado`, FR-007) |
| `instante_registro` | `TIMESTAMPTZ NOT NULL` | |

*Regla de no solape*: para un mismo `(id_medio_pago, id_sucursal)` no puede haber dos filas con
tramos `[fecha_desde, fecha_hasta]` solapados. `PUT /pagos/cobertura` cierra el tramo anterior
(`fecha_hasta = nueva_fecha_desde − 1 día`) al declarar uno nuevo. Índice de exclusión sobre el rango
(ver "Índices").

*Métrica derivada — cuota de intención de compra no atendida* (research.md #5, **no es una tabla**):
`GET /pagos/cobertura` cuenta los eventos `bitacora_auditoria` de tipo `intencion_no_atendida` de la
sucursal y el período, agrupados por `id_medio_pago` (el medio deseado), y los expresa como razón
sobre el total de eventos de intención no atendida del período:

```
cuota_no_atendida(sucursal, periodo, medio_deseado) =
    COUNT(bitacora_auditoria intencion_no_atendida de ese medio, sucursal, periodo)
  / COUNT(bitacora_auditoria intencion_no_atendida de esa sucursal, periodo)
```

Un evento de intención no atendida **nunca** crea una `venta` ni una `consulta_no_atendida` de `001`
(FR-005). Se registra vía `POST /pagos/intencion-no-atendida`, que solo anexa a `bitacora_auditoria`.

---

## `token_pago`

El **registro autoritativo** de un cobro con tarjeta tokenizado (research.md #1, #4). Guarda
**únicamente** el identificador sustituto y el metadato mínimo que la constitución permite conservar
("Datos de pago": identificadores y últimos dígitos). **Ningún campo de PAN, CVV, banda o chip.**

| Campo | Tipo | Notas |
|---|---|---|
| `id_token_pago` | `INTEGER` PK | |
| `token` | `TEXT NOT NULL UNIQUE` | Identificador sustituto **opaco**: UUID v4 de la biblioteca estándar. **No** criptográfico, **no** reversible, **sin** relación derivable con el PAN, **sin** estabilidad entre ventas —la misma tarjeta en dos ventas produce dos tokens (research.md #4) |
| `id_venta` | `INTEGER FK → venta (001) NOT NULL UNIQUE` | **Un token por cobro** (FR-016). FK de **solo lectura**: `007` consulta `venta`, nunca la escribe. Este es el vínculo **autoritativo** venta↔token (research.md #7) |
| `clave_idempotencia` | `TEXT NOT NULL UNIQUE` | **La genera el cliente** (el flujo de captura de pago de `001`, en nombre de la terminal) **antes del primer intento** — misma convención que `venta.clave_idempotencia` de `001` (research.md #15). Un reintento de red del datáfono reenvía la misma clave y el mismo `id_venta` |
| `ultimos_digitos` | `CHAR(4) NOT NULL` | `CHECK (ultimos_digitos ~ '^[0-9]{4}$')` — **barrera de esquema contra FR-018**: aquí no cabe un PAN completo |
| `marca` | `ENUM('visa','mastercard','amex','diners','otra') NOT NULL` | Derivada del rango BIN por una tabla estática mínima (`BIN_MARCA`, config). `otra` cuando el prefijo no está mapeado |
| `tipo` | `ENUM('debito','credito','desconocido') NOT NULL` | Lo reporta el flujo de captura o el operador. `desconocido` cuando no se informa —nunca se adivina (mismo criterio que "no calculable" de `006` y "versión de referencia desconocida" de `terminal_pago`) |
| `id_terminal_pago` | `INTEGER FK → terminal_pago NOT NULL` | La terminal de captura (FR-016) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | **Denormalizado** de `venta → turno.id_sucursal` (inmutable). Filtro obligatorio por sucursal (FR-034) |
| `instante` | `TIMESTAMPTZ NOT NULL` | Cuándo se emitió el token |
| `dia_local` | `DATE NOT NULL` | **Denormalizado**: `(instante AT TIME ZONE sucursal.zona_horaria)::date` (FR-032) |
| `marca_tiempo_origen` | `TIMESTAMPTZ NOT NULL` | Reportada por el flujo de captura. Si el cobro se ejecutó sin conectividad, la reconciliación de `001` desempata por este valor sobre el recurso `id_venta` (FR-022) |

*Máquina de estados*: implícita — un token existe o no existe. No hay estado `pendiente`: si la
tokenización no llega a completarse, **no se crea fila** y la `venta` de `001` queda "sin
tokenización" (FR-020).

*Idempotencia — comportamiento ante un reintento de red del datáfono* (research.md #15, mismo tipo de
precisión que `arqueo.id_turno UNIQUE` de `006`):

1. El reintento reconoce el cobro por su **clave natural `id_venta`** primero. Si ya existe un
   `token_pago` para ese `id_venta`, `POST /pagos/tokens` devuelve `200` con el token existente, sin
   crear una segunda fila (`UNIQUE (id_venta)`, FR-021, SC-009).
2. `clave_idempotencia` (`UNIQUE`) es la **segunda barrera**: en el reintento debe coincidir con la
   registrada. Si llega la misma `id_venta` con una `clave_idempotencia` distinta (bug del cliente),
   `007` **devuelve igualmente el token ya emitido** para esa venta y anexa a `bitacora_auditoria` un
   evento `token_idempotencia_divergente` para revisión. Si llega una `clave_idempotencia` ya usada
   con una `id_venta` distinta (el cliente reutilizó la clave), se rechaza con
   `pagos_clave_idempotencia_reusada` (`409`).
3. Un primer intento que expiró en el cliente pero **sí** se completó en el servidor: el reintento
   trae la misma `id_venta` + la misma `clave_idempotencia`, encuentra la fila y devuelve `200` con
   el mismo `token`. El datáfono nunca recibe un segundo token.

*Rechazo de PAN* (FR-018, SC-006, SC-008): el servicio valida que ningún campo de entrada contenga
una secuencia de 13–19 dígitos que pase la validación de Luhn. Un intento se **rechaza** con
`pagos_pan_detectado` (`400`) y se anexa a `bitacora_auditoria` un evento `pan_rechazado` **sin** el
número. El cuerpo de `POST /pagos/tokens` **nunca** se registra literalmente (research.md #4).

*Ciclo de purga propio* (research.md #4, Assumptions del spec): un `token_pago` vive mientras su
`venta` de `001` sea consultable. Como el PAN **nunca** se almacena, no hay dato sensible que caduque
con urgencia. Una tarea de mantenimiento invocable a mano —`purgar_tokens_huerfanos`, en
`backend/rasero/tareas/`, mismo patrón que `tareas/` de `002`/`005`/`006`— elimina las filas cuyo
`id_venta` ya no resuelve (venta archivada o borrada por `001`). **`007` no dispara el archivado de
`001`** (Principio V: consultiva). El borrado de una fila de `token_pago` anexa un evento
`token_purgado` a `bitacora_auditoria` (que conserva solo `id_venta`, `ultimos_digitos` y `marca` —
nada sensible).

*Frontera con `venta.referencia_terminal_pago`* (research.md #7): el flujo de venta de `001`, al
cobrar con tarjeta, invoca `POST /pagos/tokens` con un breve tiempo de espera; si `007` responde,
`001` guarda el `token` devuelto en `venta.referencia_terminal_pago` **en su propia transacción de
venta** (FR-007 de `001`); si no responde a tiempo, `001` deja ese campo `NULL` y completa la venta
igual (FR-020, Principio II). `007` procesa después el cobro pendiente y crea `token_pago`. En ambos
casos `GET /pagos/ventas/{id_venta}/pago` responde desde `token_pago`, **nunca** desde ese campo de
`001`. `007` no ejecuta ningún `UPDATE` sobre `venta` —no hay `[001-escritura]`, a diferencia de
`003`.

---

## `bitacora_auditoria`

Rastro de **solo anexado** de los hechos de pago (research.md #6). Registra qué pasó, cuándo, en qué
sucursal y terminal, iniciado por quién, y con qué resultado (Principio IV). **Nunca** contiene PAN,
CVV, datos de banda o chip, ni datos personales más allá del identificador mínimo (FR-026).

| Campo | Tipo | Notas |
|---|---|---|
| `id_bitacora_auditoria` | `BIGINT` PK | `BIGINT` porque es la tabla de mayor volumen del módulo |
| `tipo_evento` | `ENUM(...) NOT NULL` | Ver lista abajo |
| `instante` | `TIMESTAMPTZ NOT NULL` | |
| `dia_local` | `DATE NOT NULL` | `(instante AT TIME ZONE sucursal.zona_horaria)::date` (FR-024, FR-032) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | Filtro obligatorio (FR-027) |
| `id_terminal_pago` | `INTEGER FK → terminal_pago NULL` | Cuando el evento involucra una terminal |
| `id_medio_pago` | `INTEGER FK → medio_pago NULL` | El medio afectado; para `intencion_no_atendida` es el medio **deseado** por el cliente (research.md #5) |
| `iniciador_tipo` | `ENUM('operador','proceso') NOT NULL` | |
| `id_operador` | `INTEGER FK → operador (001) NULL` | Cuando `iniciador_tipo = 'operador'`. Solo `id_operador`; nunca `pin_hash` (FR-031) |
| `proceso` | `TEXT NULL` | Cuando `iniciador_tipo = 'proceso'` (p. ej. `purgar_tokens_huerfanos`, `evaluacion_firmware`) |
| `resultado` | `TEXT NOT NULL` | Redactado desde **plantillas**, no desde entrada de usuario (research.md #6): no puede arrastrar un PAN |
| `referencia_recurso_tipo` | `ENUM('token_pago','venta','terminal_pago','medio_pago','cobertura_pago') NULL` | |
| `referencia_recurso_id` | `TEXT NULL` | Id del recurso afectado (`token_pago.token`, `id_venta`, etc.) |
| `clave_idempotencia` | `TEXT NULL UNIQUE` | Para los eventos que llegan por un endpoint idempotente (evita la entrada duplicada por reintento, FR-037) |

*`tipo_evento`* `ENUM`: `token_emitido`, `token_idempotencia_divergente`, `token_purgado`,
`pan_rechazado`, `firmware_actualizado`, `firmware_desactualizado_detectado`,
`terminal_expuesta_detectada`, `terminal_registrada`, `terminal_movida`, `medio_pago_alta`,
`medio_pago_baja`, `cobertura_declarada`, `intencion_no_atendida`, `config_firmware_cambiada`.

*Solo anexado* (FR-025, SC-012): la tabla acepta **solo `INSERT`**. La migración `0007` **revoca
`UPDATE` y `DELETE`** sobre `bitacora_auditoria` al rol de aplicación (`REVOKE UPDATE, DELETE ON
bitacora_auditoria FROM rasero_app`). Ningún servicio ni endpoint de `007` los ejecuta. Un intento
lanza error de permiso de PostgreSQL, verificado por la prueba obligatoria #6.

*Retención* (research.md #10): `RETENCION_BITACORA_ANIOS = 2` (año fiscal en curso + anterior). No se
purga antes. Una tarea futura de archivado no borra: mueve a almacenamiento frío (fuera de alcance
de este desglose).

*Sin datos sensibles*: no hay ningún campo de texto libre poblado por el cliente. `resultado` sale de
plantillas; `referencia_recurso_id` es un id o un token opaco. La prueba obligatoria #1 verifica que
ninguna fila contiene una secuencia que pase Luhn.

---

## Índices

| Tabla | Índice | Motivo |
|---|---|---|
| `medio_pago` | `UNIQUE (nombre)` | Catálogo sin duplicados |
| `terminal_pago` | `UNIQUE (identificador)` | Una fila por datáfono físico |
| `terminal_pago` | `(id_sucursal)` | `GET /pagos/terminales?id_sucursal=` |
| `cobertura_pago` | `EXCLUDE USING gist (id_medio_pago WITH =, id_sucursal WITH =, daterange(fecha_desde, COALESCE(fecha_hasta, 'infinity'::date), '[]') WITH &&)` | Regla de no solape de tramos de vigencia |
| `cobertura_pago` | `(id_sucursal, fecha_desde)` | Resolver la cobertura de un período |
| `token_pago` | `UNIQUE (token)` | Opacidad e integridad del identificador |
| `token_pago` | `UNIQUE (id_venta)` | **Un token por cobro** — idempotencia primaria (FR-021) |
| `token_pago` | `UNIQUE (clave_idempotencia)` | Segunda barrera de idempotencia; detecta reuso de clave |
| `token_pago` | `(id_sucursal, dia_local)` | Reportes por sucursal y día |
| `bitacora_auditoria` | `(id_sucursal, dia_local)` | `GET /pagos/bitacora` filtrado por sucursal y período |
| `bitacora_auditoria` | `(tipo_evento, id_sucursal, dia_local)` | Cuota de intención no atendida; consultas por tipo |
| `bitacora_auditoria` | `(id_terminal_pago)` WHERE `id_terminal_pago IS NOT NULL` | Rastro de una terminal concreta |
| `bitacora_auditoria` | `UNIQUE (clave_idempotencia)` WHERE `clave_idempotencia IS NOT NULL` | Evitar la entrada duplicada por reintento |

## Migración `0007_pagos_seguridad`

`upgrade`: crea los `ENUM` (`marca_tarjeta`, `tipo_tarjeta`, `iniciador_bitacora`,
`tipo_evento_bitacora`, `referencia_recurso_bitacora`), las cinco tablas y sus índices (incluida la
restricción de exclusión `gist` sobre `cobertura_pago`, que requiere la extensión `btree_gist` —
`CREATE EXTENSION IF NOT EXISTS btree_gist`). Todas las FK hacia `001` (`venta`, `turno` vía la
denormalización, `sucursal`, `operador`) referencian tablas ya creadas por la migración `0001`.
Ejecuta `REVOKE UPDATE, DELETE ON bitacora_auditoria FROM rasero_app` para hacer cumplir el solo
anexado a nivel de motor. Siembra `medio_pago` desde `MEDIOS_PAGO_BASE`.

`downgrade`: `GRANT` de vuelta los privilegios sobre `bitacora_auditoria`, elimina las cinco tablas y
los `ENUM` en orden inverso. Sin pérdida de datos de `001` (este módulo nunca escribió allí).
