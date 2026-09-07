# Data Model: Caja, Mermas y Fraude

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo singular,
sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Montos en `NUMERIC(12,2)`;
cantidades (unidades o gramos, según `producto.es_granel` de `001`) en `NUMERIC(14,0)` — escala
**entero**, gramos para granel, **idéntica a `movimiento_inventario.cantidad` y
`conteo_renglon.diferencia` de `001`**. `001` no usa ninguna cantidad decimal (header de
`001/data-model.md`: «pesos en `INTEGER` de gramos»; `renglon_venta.cantidad_gramos` es `INTEGER`),
así que una merma de deli de 2,35 kg se registra como `2350` y este modelo **no define una escala
decimal propia**: hacerlo divergiría de `conteo_renglon`, la fuente de la que
`merma.cantidad_faltante` se deriva. Instantes en `TIMESTAMPTZ` (UTC); días locales y períodos como
`DATE`. **Ningún tipo de coma flotante aparece en este modelo.** Las razones y tasas
de los indicadores por operador (research.md #7) se calculan con `Decimal` al leer y **no se
persisten** en ninguna columna, salvo el `indicador_snapshot` JSONB de una `anomalia_caja` ya
generada, donde se guardan como cadena decimal.

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las **tres** entidades que la constitución (v2.4.0) asigna a
`006-caja-mermas-fraude` desde la ratificación: `arqueo`, `merma`, `anomalia_caja`. **Ninguna otra.**

A diferencia de `003` (v2.2.3, `costo_producto` retirado y `sugerencia_precio` añadida), `004`
(v2.2.4, `sustitucion_producto` añadida) y `005` (v2.2.5, de 3 a 6 entidades), la revisión completa
de la entrada de `006` **no encontró ninguna discrepancia** (research.md #2): las tres entidades
listadas son las que el spec exige. **Este módulo no motiva ninguna enmienda constitucional.**

La constitución además ya declara legítimo el diseño derivado: *"`anomalia_caja` es propiedad de 006,
pero se **calcula consultando** `movimiento_inventario`, `venta` y `anulacion_venta`, propiedad de
001. Eso es consulta entre funcionalidades, no redefinición... Es además la forma en que la Lectura
Crítica n.º 1 exige detectar el fraude de 'cobrar 5, registrar 3': cruzando salida de inventario
contra venta registrada y tasa de anulaciones por operador, no buscando un descuadre de efectivo que
ese fraude nunca produce."*

**Los indicadores por operador NO son entidad** (decisión cerrada, research.md #2/#7): la tasa de
anulaciones, la concentración de ventas bajo precio de lista y el cruce inventario-ventas son
cálculo derivado sobre `001`. No tienen tabla, no tienen ciclo de vida, no se recomputan a una fila.
El único valor de indicador que se persiste es el `indicador_snapshot` (JSONB) de una `anomalia_caja`
ya creada — un dato de auditoría de esa fila, nunca consultado de forma independiente (research.md
#6).

**Frontera de propiedad explícita — solo lectura, sin escritura ni posesión**: este módulo consulta
de `001` las entidades `turno` (`id_operador`, `id_sucursal`, `instante_apertura`,
`instante_cierre`), `venta` (`total`, `id_turno`, `instante`), `renglon_venta` (`id_producto`,
`precio_aplicado`, `cantidad_unidades`, `cantidad_gramos`), `anulacion_venta` (`id_venta`,
`id_operador`, `instante`), `movimiento_inventario` (`tipo`, `cantidad`, `id_producto`, `id_lote`,
`instante`), `existencia` (`cantidad`), `conteo_fisico` (`id_sucursal`, `alcance`, `estado`,
`instante_resolucion`), `conteo_renglon` (`id_producto`, `id_lote`, `diferencia`), `lote`
(`costo_unitario`, `fecha_caducidad`, `id_producto`, `id_sucursal`), `operador` (`id_operador`,
`nombre`, `es_encargado` — **nunca** `pin_hash`), `producto` (`precio_vigente`, `es_granel`,
`nombre`), `producto_precio_sucursal` (override, FR-050 de `001`) y `sucursal` (`zona_horaria`).
**`006` no escribe en ninguna tabla ajena** — a diferencia de `003`, que escribe en
`producto_precio_sucursal`. Ninguna columna de `001` se duplica en este documento **salvo** tres
valores **inmutables y derivados** de `turno` en `arqueo` (`id_operador`, `id_sucursal`,
`dia_local`), justificados en research.md #4 (rendimiento de la consulta de arqueos por sucursal y
día; un turno cerrado no cambia de operador, sucursal ni instante de cierre).

## Bloqueo por `001` (esquema sí, servicio no)

`conteo_fisico` y `conteo_renglon` **existen en el esquema** desde la migración `0001` de `001` (su
`data-model.md` las define), pero su **servicio y sus endpoints** (`001` User Story 5, tareas
T065–T071) **no están implementados** — verificado contra el repositorio (research.md #10, #17).

Consecuencia para este modelo:

- La FK `merma.id_conteo_renglon` → `conteo_renglon` **se crea en la migración `0006`** (la tabla
  destino existe). Lo que queda bloqueado es la **lógica de servicio** que lee esa fila para
  clasificarla (FR-009, FR-015) y el cruce de FR-020 que la usa — marcado
  `⛔ BLOQUEADA por 001 (T065–T071)` en `tasks.md`, con `xfail`.
- La rama de `POST /caja/mermas` **sin** `id_conteo_renglon` (declaración libre, FR-012), la alerta
  de caducidad (FR-014), el arqueo completo (US1) y los indicadores de FR-018/FR-019 **no** están
  bloqueados.

---

## `arqueo`

Cuadre de la caja al **cierre de un turno** de `001` (research.md #4, #8). Registra el efectivo y
los comprobantes contados contra lo que el sistema registró como cobrado en ese turno. Es **nueva en
este módulo**: `001` tiene conteo físico de **inventario** (`conteo_fisico`), pero ninguna noción de
arqueo de **efectivo**.

| Campo | Tipo | Notas |
|---|---|---|
| `id_arqueo` | `INTEGER` PK | |
| `id_turno` | `INTEGER FK → turno (001) NOT NULL UNIQUE` | **Idempotencia de FR-005**: un turno se arquea a lo sumo una vez. FK de solo lectura |
| `id_operador` | `INTEGER FK → operador (001) NOT NULL` | **Denormalizado** de `turno.id_operador` (inmutable). El operador al que se atribuye la diferencia (FR-003) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | **Denormalizado** de `turno.id_sucursal` (inmutable). Todo arqueo se identifica por sucursal (FR-038) |
| `dia_local` | `DATE NOT NULL` | **Denormalizado**: `(turno.instante_cierre AT TIME ZONE sucursal.zona_horaria)::date` (research.md #12) |
| `monto_esperado` | `NUMERIC(12,2) NOT NULL` | `SUM(venta.total)` de las ventas del turno, **congelado** al cerrar el arqueo (research.md #4). Un turno sin ventas ⇒ `0.00`, no error (FR-007) |
| `monto_contado` | `NUMERIC(12,2) NOT NULL` | Efectivo + comprobantes contados al cierre. **Sin desglose por medio de pago** hasta que exista `007` (research.md #4) |
| `diferencia` | `NUMERIC(12,2) NOT NULL` | Columna calculada al insertar: `monto_contado − monto_esperado`. **Con signo**: negativa = faltante, positiva = sobrante |
| `motivo_conocido` | `TEXT NULL` | Anotado por el encargado ("mal dado el cambio", "pago no registrado"). Su presencia evita que la diferencia genere `anomalia_caja` (FR-004) |
| `ajustes` | `JSONB NOT NULL DEFAULT '[]'` | Array de correcciones posteriores `{instante, id_operador, monto_contado_anterior, monto_contado_nuevo, nota}`. **Nunca** reescribe `monto_contado`/`monto_esperado` (research.md #13) |
| `instante_cierre_arqueo` | `TIMESTAMPTZ NOT NULL` | Cuándo se registró el arqueo (distinto de `turno.instante_cierre`) |
| `marca_tiempo_origen` | `TIMESTAMPTZ NOT NULL` | Reportada por el dispositivo. Si el arqueo se registró offline, la reconciliación de `001` desempata por este valor sobre el recurso `id_turno` (FR-006) |

*Máquina de estados*: implícita — un arqueo existe (cerrado) o no existe. No hay estado `abierto`
persistido (research.md #13).

*Regla de anomalía* (FR-004, FR-027): al cerrar el arqueo, si
`|diferencia| > TOLERANCIA_CUADRE_ARQUEO` (config, arranque `0.00`) **y** `motivo_conocido IS NULL`,
el servicio crea en la misma transacción una `anomalia_caja` de `origen = 'efectivo'` en estado
`sin_explicacion`, con `id_turno`, `id_operador`, `id_sucursal`, `monto = diferencia` y el mismo
`dia_local`.

*Frontera*: el cálculo de `monto_esperado` es una consulta `SELECT SUM(total) FROM venta WHERE
id_turno = :id_turno` a `001`. `arqueo` **no** escribe en `venta` ni en ninguna tabla de `001`
(SC-002, SC-011).

---

## `merma`

Pérdida de producto **sin venta asociada**, clasificada por causa (research.md #5, #11). Consume la
`diferencia` bruta que `001` expone en un `conteo_renglon` —o se declara fuera de un conteo— y le
asigna causa y valoración. La constitución asigna a `006` "la contabilización de la pérdida"; `001`
sigue siendo dueño de la diferencia bruta y de la fecha de caducidad.

| Campo | Tipo | Notas |
|---|---|---|
| `id_merma` | `INTEGER` PK | |
| `id_conteo_renglon` | `INTEGER FK → conteo_renglon (001) NULL` | La línea de conteo que reveló la diferencia. **NULL** = merma declarada fuera de conteo (rotura, vencimiento en estantería, FR-012). FK de solo lectura. **⛔ la rama con valor no nula está bloqueada por `001` (T065–T071)** |
| `id_producto` | `INTEGER FK → producto (001) NOT NULL` | |
| `id_lote` | `INTEGER FK → lote (001) NULL` | El lote afectado. NULL si no se puede determinar (raro; la valoración queda "no calculable") |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | Toda merma se identifica por sucursal (FR-038) |
| `cantidad_faltante` | `NUMERIC(14,0) NOT NULL` | **Escala verificada contra `001/data-model.md`, idéntica a `conteo_renglon.diferencia`** (la línea que esta merma clasifica) **y a `movimiento_inventario.cantidad`**: unidades enteras, o **gramos enteros** si `producto.es_granel` (`001` representa todo peso como gramos enteros — una merma de 2,35 kg de fresco se registra como `2350`). `CHECK (cantidad_faltante > 0)` |
| `causa` | `ENUM('vencimiento','dano','robo_externo','error_conteo','merma_granel','pendiente_clasificar') NOT NULL` | `merma_granel` = deshidratación o merma de corte (FR-015). `pendiente_clasificar` = el encargado no pudo decidir (FR-013); **el sistema nunca impone otra causa** |
| `valoracion` | `NUMERIC(12,2) NULL` | `cantidad_faltante × lote.costo_unitario` del lote FEFO de `001` (por kilogramo si granel). **NULL = "no calculable"** cuando falta el costo — **nunca 0.00** (FR-010, SC-005) |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. La constitución exige moneda en todo importe persistido |
| `periodo_desde` | `DATE NOT NULL` | Primer día local del período entre conteos: fecha de resolución del conteo anterior del mismo alcance, o la fecha de la declaración si es fuera de conteo (FR-011) |
| `periodo_hasta` | `DATE NOT NULL` | Último día local: fecha de resolución del conteo que la reveló, o la fecha de la declaración. `CHECK (periodo_hasta >= periodo_desde)` |
| `estado` | `ENUM('pendiente_clasificar','clasificada') NOT NULL` | `pendiente_clasificar → clasificada` cuando se asigna una `causa` distinta de `pendiente_clasificar` (research.md #13) |
| `conciliar_con_conteo` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` para una merma declarada fuera de conteo: señala que el ajuste de `existencia` lo hará `001` en el próximo conteo (FR-012, FR-034). `006` **no** ajusta `existencia` |
| `id_operador_registro` | `INTEGER FK → operador (001) NOT NULL` | Quién registró/clasificó la merma. **No** es una imputación de la pérdida a ese operador (FR-011) |
| `instante_registro` | `TIMESTAMPTZ NOT NULL` | |
| `nota` | `TEXT NULL` | Detalle libre |

*Sin `id_operador` de imputación* (FR-011): una merma física **nunca** se atribuye al operador de un
turno. `id_operador_registro` es solo quién hizo el registro administrativo.

*Valoración congelada* (research.md #13): `valoracion` se calcula y se fija al registrar, con el
`lote.costo_unitario` vigente entonces; no se recomputa si el costo del lote cambia después.

---

## `anomalia_caja`

Diferencia detectada —de efectivo en un `arqueo` o de inventario en el cruce por operador— que
**ninguna causa conocida explica** (research.md #6). Es **una** entidad con un campo `origen`, no un
cajón que fusione los tres fenómenos: ambos orígenes comparten la misma máquina de estados y el
mismo flujo de revisión humana. El sistema **nunca fuerza una clasificación ni cierra la anomalía
por el paso del tiempo** (FR-029).

| Campo | Tipo | Notas |
|---|---|---|
| `id_anomalia_caja` | `INTEGER` PK | |
| `origen` | `ENUM('efectivo','inventario') NOT NULL` | `efectivo` = de un `arqueo` sin motivo (FR-004). `inventario` = del cruce por operador (FR-020). **⛔ el origen `inventario` está bloqueado por `001` (T065–T071)** |
| `estado` | `ENUM('sin_explicacion','resuelta') NOT NULL DEFAULT 'sin_explicacion'` | Única transición: `sin_explicacion → resuelta`, **solo** por acción de una persona (FR-030). **No hay transición automática por tiempo** (FR-029) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | Toda anomalía se identifica por sucursal (FR-038) |
| `id_arqueo` | `INTEGER FK → arqueo NULL` | Presente cuando `origen = 'efectivo'` |
| `id_turno` | `INTEGER FK → turno (001) NULL` | Presente cuando `origen = 'efectivo'` |
| `id_operador` | `INTEGER FK → operador (001) NULL` | El operador implicado (del turno para efectivo; el más señalado del reparto para inventario). Nunca es una acusación: es la atribución del cálculo (FR-023) |
| `id_producto` | `INTEGER FK → producto (001) NULL` | Presente cuando `origen = 'inventario'` |
| `id_conteo_fisico` | `INTEGER FK → conteo_fisico (001) NULL` | El conteo que reveló el faltante (`origen = 'inventario'`). FK de solo lectura |
| `monto` | `NUMERIC(12,2) NULL` | Magnitud monetaria (`origen = 'efectivo'`): la `diferencia` del arqueo, con signo |
| `magnitud` | `NUMERIC(14,0) NULL` | Magnitud en unidades/gramos (`origen = 'inventario'`): el faltante no explicado atribuido |
| `valor_estimado` | `NUMERIC(12,2) NULL` | Para inventario: `magnitud × lote.costo_unitario` FEFO; NULL si "no calculable" |
| `periodo_desde` | `DATE NULL` | Período del cruce (`origen = 'inventario'`) |
| `periodo_hasta` | `DATE NULL` | |
| `dia_local` | `DATE NOT NULL` | Día local de la sucursal en que se detectó (research.md #12) |
| `indicador_snapshot` | `JSONB NULL` | **Congela** los indicadores por operador en el momento de generarse (`origen = 'inventario'`): `{tasa_anulaciones, concentracion_bajo_lista, faltante_bruto, merma_descontada, anulaciones_descontadas, faltante_no_explicado, reparto_por_turno: [...]}` como cadenas decimales. Existe para que la anomalía no cambie si después se anula una venta del cálculo (research.md #2, #6). NULL para `origen = 'efectivo'` |
| `historial` | `JSONB NOT NULL DEFAULT '[]'` | Array `{estado, instante, id_operador, nota}` con **cada** cambio de estado (FR-030). Columna en la fila, **no** tabla hija (decisión de criterio, research.md #6) |
| `resolucion` | `TEXT NULL` | La etiqueta que una persona asigna al resolver ("error operativo confirmado", "escalado a fraude", "ajuste aceptado"). **Texto libre, no un `ENUM` cerrado** (FR-029 prohíbe imponer una clasificación). **Trade-off aceptado y documentado en research.md #18**: se pierde la agregación de anomalías *resueltas* por categoría (p. ej. "cuántas fueron error de sistema vs. hallazgo real"); ninguna FR ni el enunciado la exigen. Si esa necesidad aparece, la evolución limpia es añadir `categoria_resolucion` (`ENUM` abierto a extensión por migración) **+** conservar `resolucion` como detalle libre — trabajo aditivo, sin tocar las 3 entidades ni abrir enmienda (research.md #18) |
| `id_operador_resolucion` | `INTEGER FK → operador (001) NULL` | Quién resolvió. `CHECK`: no nulo ⟺ `estado = 'resuelta'` |
| `instante_resolucion` | `TIMESTAMPTZ NULL` | `CHECK`: no nulo ⟺ `estado = 'resuelta'` |
| `instante_deteccion` | `TIMESTAMPTZ NOT NULL` | |

*Regla de "no anomalía"* (FR-031, SC-010, SC-012): el servicio **no** crea una `anomalia_caja` si la
diferencia se explica por completo — un `arqueo` con `motivo_conocido`, un faltante de inventario que
coincide con una `merma` ya `clasificada` o con anulaciones registradas. La anomalía es, por
definición, lo que carece de explicación conocida.

*Regla de no cierre automático* (FR-029, SC-009): no existe ninguna tarea, disparador ni consulta
que cambie `estado` a `resuelta` sin `id_operador_resolucion`. Una anomalía puede permanecer
`sin_explicacion` indefinidamente y sigue apareciendo en `GET /caja/anomalias?estado=sin_explicacion`.

---

## Consultas derivadas (no son tablas)

Ninguna se materializa. Todas se calculan al leer, sobre datos de `001` (research.md #7, #5).

### Indicadores por operador (`GET /caja/indicadores-operador`)

Por `(id_operador, id_sucursal, [desde, hasta])`, con `desde`/`hasta` como día local:

- **`tasa_anulaciones`** = `COUNT(anulacion_venta ejecutadas por el operador en el período) /
  COUNT(venta de turnos del operador en el período)`. Atribución: `anulacion_venta.id_operador`
  (quién anuló) y `venta → turno.id_operador` (quién vendió) — FR-049 de `001`.
- **`concentracion_bajo_lista`** = `COUNT(renglon_venta de turnos del operador con precio_aplicado <
  precio_efectivo) / COUNT(renglon_venta de turnos del operador)`. `precio_efectivo =
  COALESCE(producto_precio_sucursal.precio_vigente, producto.precio_vigente)` para la sucursal del
  turno.
- **Línea base** (research.md #7d, #16): un operador se **señala** si su valor
  `≥ RAZON_DESVIACION_* × mediana` de los operadores **comparables** (≥ `UMBRAL_MINIMO_VENTAS_INDICADOR`
  ventas en el período) de la misma sucursal y período. La respuesta expone el valor del operador, la
  mediana de pares, el factor y si se supera — **nunca** la palabra "fraude" (FR-023).

### Cruce inventario-ventas (`POST /caja/cruce-operador`) — **⛔ BLOQUEADO por `001` (T065–T071)**

Por `(id_sucursal, desde, hasta, id_conteo_fisico?)`:

```
faltante_bruto(producto)        = |Σ conteo_renglon.diferencia negativa de ese conteo/producto|
faltante_no_explicado(producto) = faltante_bruto
                                − Σ merma.cantidad_faltante clasificada de ese producto/período
                                − Σ |movimiento_inventario.cantidad| de tipo entrada_anulacion de ese producto/período
reparto_por_turno               = faltante_no_explicado repartido entre los turnos con
                                  movimiento salida_venta de ese producto en el período,
                                  proporcional a las unidades que cada turno movió
```

Cuando `faltante_no_explicado > 0`, se crea una `anomalia_caja` de `origen = 'inventario'` con
`magnitud = faltante_no_explicado`, `id_operador` = el del turno con mayor participación en el
reparto, e `indicador_snapshot` con todo el desglose. Si `faltante_no_explicado <= 0` (la merma y
las anulaciones explican el faltante), **no se crea nada** (FR-025, FR-031).

### Alerta de caducidad (`GET /caja/alertas-caducidad`)

Por `id_sucursal` y `dentro_de_dias` (por defecto `VENTANA_ALERTA_CADUCIDAD_DIAS`): lotes de `001`
con `fecha_caducidad <= (hoy_local + dentro_de_dias)` y `existencia.cantidad > 0`, con
`valor_en_riesgo = existencia.cantidad × lote.costo_unitario` (o "no calculable"). Marca aparte los
lotes con `fecha_caducidad < hoy_local` (**ya caducados** — color crítico en la interfaz, research.md
#15). `006` **no** escribe en `lote` ni da de baja nada (FR-014).

---

## Índices

| Tabla | Índice | Motivo |
|---|---|---|
| `arqueo` | `UNIQUE (id_turno)` | Idempotencia de FR-005 |
| `arqueo` | `(id_sucursal, dia_local)` | `GET /caja/arqueos?id_sucursal=&desde=&hasta=` |
| `merma` | `(id_sucursal, periodo_hasta)` | `GET /caja/mermas` filtrado por sucursal y período |
| `merma` | `(id_producto, periodo_hasta)` | Desglose por producto y descuento en el cruce de FR-020 |
| `merma` | `(id_conteo_renglon)` WHERE `id_conteo_renglon IS NOT NULL` | Evitar clasificar dos veces la misma línea de conteo |
| `anomalia_caja` | `(id_sucursal, estado)` | Cola de anomalías `sin_explicacion` por sucursal (User Story 4) |
| `anomalia_caja` | `(origen, estado)` | `GET /caja/anomalias?origen=&estado=` |
| `anomalia_caja` | `(id_arqueo)` WHERE `id_arqueo IS NOT NULL` | Un arqueo genera a lo sumo una anomalía de efectivo |

## Migración `0006_caja_mermas_fraude`

`upgrade`: crea los tres `ENUM` (`causa_merma`, `estado_merma`, `origen_anomalia`,
`estado_anomalia`), las tres tablas y sus índices. Las FK hacia `001` (`turno`, `operador`,
`sucursal`, `producto`, `lote`, `conteo_renglon`, `conteo_fisico`) referencian tablas ya creadas por
la migración `0001` — **incluidas `conteo_renglon` y `conteo_fisico`, cuyo esquema existe aunque su
servicio no** (research.md #10).

`downgrade`: elimina las tres tablas y los `ENUM`, en orden inverso. Sin pérdida de datos de `001`
(este módulo nunca escribió allí).
