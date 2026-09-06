# Research: Caja, Mermas y Fraude

**Fase 0** · 2026-09-05 · Plan: [plan.md](./plan.md)

El `spec.md` de `006` no dejó ningún `[NEEDS CLARIFICATION]`: las dos decisiones de alcance mayor
—cadencia del cruce inventario-ventas (FR-021) y tratamiento de la diferencia sin explicación
(FR-027 a FR-031)— se cerraron en el propio spec. Este documento fija las **decisiones de diseño**
que el plan debía tomar por su cuenta, cada una con su justificación y las alternativas descartadas,
y **verifica contra el repositorio** qué partes quedan bloqueadas por la ausencia de
`conteo_fisico` / `conteo_renglon` en `001`.

Aprobado sin cambios el 2026-09-05, incluidas las cuatro decisiones de criterio marcadas: #4 (sin
desglose por medio de pago hasta `007`), #6 (historial de `anomalia_caja` como columna JSONB en la
fila, no tabla hija), #15 (`Arqueo.tsx` en registro de Operación), #16 (línea base por razón sobre
la mediana de pares, sin librería estadística).

La entrada **#18** se añadió el 2026-09-05 **tras la aprobación**, por petición explícita, para
documentar el trade-off de `anomalia_caja.resolucion` como texto libre. No altera ninguna de las 17
decisiones previas ni las tres entidades de `data-model.md`.

---

## 1. Reutilización íntegra del stack de `001`–`005`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + TS + Vite, sin librería de componentes de terceros) que `001`–`005`, sobre la
misma base PostgreSQL 16 (puerto 5442). Migración nueva `0006_caja_mermas_fraude`. **Cero
dependencias nuevas.**

**Rationale**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función
que una ya presente, salvo justificación registrada. Ninguna característica de este módulo exige un
lenguaje, framework o motor distinto. La única tentación —una librería estadística para comparar el
comportamiento de un operador contra sus pares— se descarta en #16: la comparación es una razón
sobre la mediana de un conjunto, aritmética de una pantalla, misma disciplina que el suavizado
exponencial de `004` y la prueba z de `005`.

**Alternativas descartadas**: ninguna evaluada seriamente para el stack base.

---

## 2. Propiedad de datos: exactamente tres entidades, **sin enmienda constitucional**

**Decisión**: `data-model.md` define únicamente `arqueo`, `merma` y `anomalia_caja` — las tres que
la tabla de "Propiedad de Datos y Nomenclatura" de la constitución (v2.3.0) ya asigna a
`006-caja-mermas-fraude` desde la ratificación. **No se abre ninguna enmienda.**

**Lo que la revisión de la entrada de `006` encontró** (misma revisión que en `003`/`004`/`005`
destapó discrepancias): **ninguna**. A diferencia de:

- `003` (v2.2.3): `costo_producto` estaba mal asignada (el costo es de `001`) → se retiró y se
  añadió `sugerencia_precio`.
- `004` (v2.2.4): `sustitucion_producto` faltaba → se añadió.
- `005` (v2.2.5): `envio_promocional` contradecía la Lectura Crítica n.º 6 y `grupo_control` era
  demasiado gruesa → de 3 a 6 entidades.

En `006`, las tres entidades listadas (`arqueo`, `merma`, `anomalia_caja`) son **exactamente** las
que el spec exige, ni una más ni una menos. La constitución además **ya anticipa** el diseño: dice
literalmente que `anomalia_caja` "se calcula consultando `movimiento_inventario`, `venta` y
`anulacion_venta`" y que esa es "la forma en que la Lectura Crítica n.º 1 exige detectar el fraude
de 'cobrar 5, registrar 3'".

**Los indicadores por operador NO son entidad** (decisión cerrada por el encargo): la tasa de
anulaciones, la concentración de ventas bajo precio de lista y el cruce inventario-ventas son
**cálculo derivado** sobre `venta`, `anulacion_venta`, `renglon_venta`, `movimiento_inventario` y
`conteo_renglon` de `001`. Se consultan en el momento, nunca se escriben como fila propia. Mismo
patrón que `resolver_margen_producto` de `003` (deriva el margen al leer, no lo materializa) y la
lectura de `senal_fuga` / `intervalo_compra` en `002`/`005` (se consultan, nunca se redefinen). No
tienen ciclo de vida propio: no se cierran, no se anulan, no tienen estado editable por el encargado.

**Snapshot cuando `anomalia_caja` lo necesita**: si una anomalía de origen inventario debe congelar
el valor de un indicador en el momento de generarse —para que no cambie retroactivamente si después
se anula una venta que formaba parte del cálculo del faltante—, ese valor se guarda en una **columna
JSONB desnormalizada** `indicador_snapshot` en la propia fila de `anomalia_caja`. **No** se crea una
tabla `senal_fraude_operador` ni equivalente.

**Rationale**: la Puerta de propiedad de datos exige que `data-model.md` y la tabla constitucional
no discrepen; aquí no discrepan. Añadir una cuarta tabla para materializar un cálculo que la
constitución describe explícitamente como derivado sería complejidad sin necesidad demostrada
(Principio I) y abriría una enmienda innecesaria.

**Alternativas descartadas**: materializar los indicadores en `senal_fraude_operador` —rechazada:
sin ciclo de vida propio, la constitución ya los llama cálculo derivado, y una tabla que hay que
recalcular y mantener sincronizada con `001` no aporta nada a esta escala—; colgar el snapshot de
una tabla hija de `anomalia_caja` —rechazada: el snapshot es un dato de auditoría de una sola fila,
nunca se consulta de forma independiente, una columna JSONB es la forma correcta (mismo criterio que
#6 para el historial).

---

## 3. Tres fenómenos, tres registros distintos — no una entidad genérica de "descuadre" (FR-037)

**Decisión**: no existe ninguna tabla genérica de "descuadre" con un campo `tipo`. Cada fenómeno
tiene su tabla, con las columnas que **su** lógica necesita y ninguna que no:

| Fenómeno | Entidad | Lo que la distingue estructuralmente |
|---|---|---|
| 1 — merma física | `merma` | `id_conteo_renglon` (NULL si se declaró fuera de conteo), `causa`, `valoracion`, período entre conteos. **Sin** operador imputado, **sin** medios de pago. |
| 2 — diferencia caja-cobrado | `arqueo` | `id_turno UNIQUE`, `monto_esperado` (suma de cobros del turno), `monto_contado`, `diferencia` con signo, `motivo_conocido`. **Sin** producto, **sin** causa de merma. |
| 3 — fraude por sub-registro | cálculo derivado sobre `001` → resultado registrado en `anomalia_caja` de `origen = 'inventario'` | Indicadores por operador (no entidad, #7) + `anomalia_caja` con `indicador_snapshot`. |

**`anomalia_caja` no es "una entidad genérica"**: el spec (FR-027, FR-028) la define como **una**
entidad con un campo `origen` ∈ {`efectivo`, `inventario`}. Es el **residuo por definición** —lo que
ninguna causa conocida explica—, no un cajón que fusione los tres mecanismos. Ambos orígenes
comparten exactamente la misma máquina de estados (`sin_explicacion → resuelta`) y el mismo flujo de
revisión humana; separarlos en dos tablas duplicaría esa máquina sin ganancia. Es la misma decisión
que la constitución ya tomó al listar `anomalia_caja` como **una** entrada.

**Rationale**: la Lectura Crítica n.º 6 impone en `005` que "tres mecanismos" no se colapsen en uno;
la misma disciplina aplica aquí a los **tres fenómenos** de pérdida. Con tres tablas, tratar una
merma como un descuadre de caja exige código que cruza dos entidades y salta a la vista en revisión.

**Alternativas descartadas**: una tabla `descuadre` con `tipo` ∈ {merma, caja, fraude} y columnas
opcionales —rechazada por FR-037 y por el precedente de la Lectura Crítica n.º 6—; dos tablas
`anomalia_efectivo` y `anomalia_inventario` —rechazada: misma máquina de estados, mismo flujo de
resolución, la separación no aporta y complica la lista de "anomalías abiertas" que el encargado
trabaja (FR de User Story 4).

---

## 4. `arqueo`: cuadre de efectivo por turno — frontera con `001` (FR-001 a FR-008)

**Decisión**:

- `arqueo` referencia `turno` de `001` por **clave foránea de solo lectura** `id_turno`, con
  `UNIQUE (id_turno)` → **idempotencia de FR-005**: un turno se arquea a lo sumo una vez; un
  reintento devuelve el arqueo existente; una corrección se registra como ajuste del mismo arqueo
  (columna `ajustes` JSONB), nunca borra el conteo anterior.
- **"Lo esperado en caja"** (`monto_esperado`) se calcula al registrar el arqueo como
  `SUM(venta.total)` de las `venta` cuyo `id_turno` es el del arqueo (consulta a `001`, sin
  modificar ninguna venta). Se **congela** en la fila del arqueo en el momento del cierre.
- **Columnas denormalizadas** `id_operador`, `id_sucursal`, `dia_local`: derivadas de
  `turno` → `turno.id_operador`, `turno.id_sucursal`, y
  `(turno.instante_cierre AT TIME ZONE sucursal.zona_horaria)::date`. Son **inmutables** una vez
  cerrado el turno (un turno no cambia de operador ni de sucursal ni de instante de cierre). Misma
  denormalización controlada que `redencion_promocion.id_sucursal` / `periodo` en `005` (research.md
  #4 de `005`): se documenta aquí para que la revisión no la lea como duplicación de datos de `001`.
- `diferencia = monto_contado − monto_esperado`, **con signo** (negativa = faltante, positiva =
  sobrante). `motivo_conocido` es `TEXT NULL` (FR-004): un texto anotado por el encargado ("mal dado
  el cambio", "pago no registrado"); su presencia evita que la diferencia genere `anomalia_caja`.

**Sin desglose por medio de pago — decisión de criterio aprobada**: `arqueo` compara el **total**
contado (efectivo + comprobantes) contra el **total** registrado del turno. No modela el desglose
efectivo / tarjeta / transferencia porque:

1. `001` solo guarda `venta.referencia_terminal_pago` como **referencia opaca** (su
   `data-model.md` es explícito: "la entidad `terminal_pago` es propiedad de `007-pagos-seguridad` y
   NO se define aquí").
2. `medio_pago` y `cobertura_pago` son propiedad de `007-pagos-seguridad`, **no construido**.

Introducir un `ENUM` de medios de pago propio de `006` invadiría el territorio de `007`. Cuando
`007` exista, el desglose por medio de pago será un **refinamiento aditivo** (columnas o tabla hija
de `arqueo`), sin cambiar el mecanismo. Hasta entonces, el arqueo es total contra total.

**Rationale (Principio II)**: el arqueo **no** participa en `POST /ventas` ni en ningún flujo de
cobro. Se registra **después** del cierre del turno, por una llamada aparte e idempotente (mismo
patrón que `registrar_visita` de `002`, "nunca forma parte de la transacción de venta"). Es
**offline-capable**: si se ejecuta sin conectividad, hereda la regla de reconciliación de `001`
(gana la marca de tiempo de origen más antigua sobre el mismo recurso; el recurso es el `id_turno`).

**Alternativas descartadas**: un `ENUM` de medios de pago propio de `006` —invade a `007`, y `001`
no expone el dato para poblarlo—; arqueo por día en vez de por turno —el enunciado dice
explícitamente que el cuadre diario "no captura a tiempo ni con resolución suficiente para
atribuirlas a un turno u operador concreto"; el turno es lo que ata la diferencia a un responsable—;
calcular `monto_esperado` al leer en vez de congelarlo —una venta anulada después del arqueo
cambiaría el "esperado" de forma retroactiva y haría irreproducible la diferencia registrada.

---

## 5. `merma`: clasificación de la diferencia de `001` + declaración fuera de conteo + alerta de caducidad (FR-009 a FR-017)

**Decisión**:

- `merma` tiene FK `id_conteo_renglon` → `conteo_renglon` de `001`, **NULLABLE**: nula cuando la
  merma se declara fuera de un conteo (FR-012: una unidad rota en estantería, un lote vencido).
  Cuando no es nula, `006` **consume** la `diferencia` bruta que `001` ya expone; **no** reimplementa
  el conteo ni recalcula esa diferencia (FR-033).
- `causa` es `ENUM('vencimiento', 'dano', 'robo_externo', 'error_conteo', 'merma_granel',
  'pendiente_clasificar')`. `merma_granel` cubre deshidratación y merma de corte (FR-015, sobre la
  diferencia de granel que `001` expone por FR-016 de `001`). `pendiente_clasificar` es el estado
  por defecto cuando el encargado no puede decidir la causa (FR-013): **el sistema nunca impone una
  causa**.
- `valoracion` es `NUMERIC(12,2) NULL`. Se calcula como `cantidad_faltante × lote.costo_unitario`
  del lote correspondiente (`lote` de `001`; por kilogramo si `producto.es_granel`). **NULL = "no
  calculable"** cuando el producto no tiene costo de lote registrado — **nunca cero** (FR-010, mismo
  criterio que `001` para capital inmovilizado, `data-model.md` de `001`: "un lote sin costo se
  muestra no calculable, nunca cero").
- Atribuida a `id_sucursal` y al **período entre conteos** (`periodo_desde` / `periodo_hasta`,
  fechas locales; `periodo_desde` = fecha de resolución del conteo anterior del mismo alcance, o la
  fecha de la declaración si es fuera de conteo). **Nunca** se atribuye a un `id_operador` (FR-011:
  una merma física no es una sustracción; imputarla a un operador sería exactamente el error que la
  Lectura Crítica n.º 1 advierte).

**Alerta de caducidad = consulta derivada, no tabla** (FR-014): sobre `lote.fecha_caducidad` de
`001`, lista los lotes cuya caducidad entra en una ventana de anticipación configurable
(`VENTANA_ALERTA_CADUCIDAD_DIAS`, #16), con la existencia restante del lote y su valor en riesgo
(`existencia.cantidad × lote.costo_unitario`). Es **informativa**: `006` **no** da de baja, descuenta
ni traspasa nada (FR-014).

**Declaración de merma fuera de conteo no ajusta existencia** (FR-012, FR-034): `006` registra la
merma y marca que deberá **conciliarse con el próximo conteo físico de `001`**. El ajuste de
`existencia` solo ocurre en `001` cuando ese conteo se resuelve (FR-032 de `001`).

**Rationale**: la constitución asigna a `006` "la política de alerta y la contabilización de la
pérdida"; `001` sigue siendo dueño de `fecha_caducidad` y de la diferencia bruta del conteo. `006`
consume, clasifica y valora; no cuenta y no ajusta.

**Alternativas descartadas**: `causa` como tabla de catálogo —sobreingeniería, seis valores fijos en
un `ENUM` bastan y `001` usa `ENUM` para lo mismo (`movimiento_inventario.tipo`)—; valorar la merma
al costo promedio de todos los lotes del producto —`001` consume por FEFO (caducidad primero,
entrada como desempate), así que el costo relevante es el del lote que habría salido, no un
promedio—; atribuir la merma al operador del turno en que se detectó —FR-011 lo prohíbe
explícitamente.

---

## 6. `anomalia_caja`: el residuo sin explicación + el resultado del cruce de sub-registro (FR-018 a FR-031)

**Decisión**: se crea una `anomalia_caja` cuando una diferencia detectada **no** se explica por
ninguna causa conocida:

- **Origen `efectivo`**: un `arqueo` con `diferencia ≠ 0` (fuera de `TOLERANCIA_CUADRE_ARQUEO`, #16)
  y **sin** `motivo_conocido` anotado → se crea al cerrar el arqueo (FR-004, FR-027).
- **Origen `inventario`**: el cruce inventario-ventas (FR-020) halla un faltante de `conteo_renglon`
  que, tras descontar la merma declarada y clasificada (FR-009 a FR-013) y las anulaciones
  registradas, **no** queda explicado → se crea al ejecutar el cruce (FR-027).

**Columnas**:

- `origen` `ENUM('efectivo', 'inventario')`.
- `estado` `ENUM('sin_explicacion', 'resuelta')`, por defecto `sin_explicacion`.
- `resolucion` `TEXT NULL` — la etiqueta que una persona asigna al resolver ("error operativo
  confirmado", "escalado a fraude", "ajuste aceptado"); libre, no un `ENUM` cerrado, porque el
  encargo no fijó el catálogo y forzarlo sería el tipo de clasificación que FR-029 prohíbe imponer.
- `id_operador_resolucion` `INTEGER NULL` FK → `operador` (de `001`, solo lectura) — quién resolvió.
- `instante_resolucion` `TIMESTAMPTZ NULL`.
- `historial` `JSONB NOT NULL DEFAULT '[]'` — **decisión de criterio aprobada**: un array de
  entradas `{estado, instante, id_operador, nota}` con cada cambio de estado (FR-030: "conservando
  el estado anterior en el historial"). Se modela como **columna JSONB en la propia fila**, **no**
  como tabla hija, porque el historial de una anomalía nunca se consulta de forma independiente de
  su anomalía, y el límite de tres entidades del encargo es explícito. Mismo criterio que el
  `indicador_snapshot`.
- `indicador_snapshot` `JSONB NULL` — para una anomalía de origen inventario, el valor de los
  indicadores por operador (tasa de anulaciones, concentración bajo precio de lista, faltante
  atribuido) **congelado** en el momento de generarse, para que no cambie si después se anula una
  venta que formaba parte del cálculo (#2, #7). Nula para las de origen efectivo.
- Atribución: `id_sucursal` siempre; `id_turno` / `id_operador` para las de origen efectivo;
  `id_producto` y `periodo_desde` / `periodo_hasta` para las de origen inventario. `monto` para
  efectivo; `magnitud` (cantidad) para inventario.

**El sistema nunca fuerza ni cierra** (FR-029): no hay transición automática `sin_explicacion →
resuelta` por el paso del tiempo, ni reclasificación, ni ocultamiento. Permanece visible hasta que
una persona la resuelve — mismo criterio que la `operacion_pendiente` desplazada por conflicto de
`001`, que "permanece visible; eliminarla u ocultarla está PROHIBIDO".

**Una diferencia totalmente explicada NO genera anomalía** (FR-031): si el faltante coincide con una
merma declarada, o con un error de cambio anotado, o con una anulación registrada, no se crea nada.

**Rationale**: FR-027 a FR-031 ya están decididos en el spec y no se reabren. La anomalía es, por
construcción, "lo que no tiene explicación conocida"; darle un `ENUM` de causas cerradas
contradiría su definición.

**Alternativas descartadas**: `resolucion` como `ENUM` cerrado —el encargo no fijó el catálogo y
FR-029 prohíbe imponer una clasificación—; historial e `indicador_snapshot` como tablas hijas
—violan el límite de tres entidades y no se consultan de forma independiente—; cerrar automáticamente
una anomalía tras N días sin revisión —FR-029 lo prohíbe explícitamente.

---

## 7. Indicadores por operador: cálculo derivado sobre `001`, nunca entidad (FR-018 a FR-020)

**Decisión**: los tres indicadores se calculan en el momento de la consulta a partir de `001`:

### 7a. Tasa de anulaciones por operador (FR-018)

```
tasa_anulaciones(operador, período, sucursal) =
    COUNT(anulacion_venta que ese operador ejecutó en el período)
  / COUNT(venta de turnos de ese operador en el período)
```

Atribución: `anulacion_venta.id_operador` para **quién anuló** (que puede no ser quién vendió,
FR-049 de `001`: un encargado anula ventas de turnos cerrados), y `venta → turno.id_operador` para
**quién vendió**. El indicador cuenta la anulación en la tasa de **quien la ejecutó**.

### 7b. Concentración de ventas bajo precio de lista (FR-019)

```
concentracion_bajo_lista(operador, período, sucursal) =
    COUNT(renglon_venta de turnos de ese operador con precio_aplicado < precio_efectivo)
  / COUNT(renglon_venta de turnos de ese operador)
```

`precio_efectivo` se resuelve como en `001` (`data-model.md` de `001`):
`COALESCE(producto_precio_sucursal.precio_vigente, producto.precio_vigente)` para la sucursal del
turno. Un `renglon_venta.precio_aplicado` por debajo de ese valor es una venta registrada bajo
precio de lista.

### 7c. Cruce inventario-ventas (FR-020) — **bloqueado por `001`, ver #10**

```
faltante_no_explicado(producto, período, sucursal) =
    |conteo_renglon.diferencia negativa|          (faltante bruto de 001)
  − Σ merma clasificada de ese producto/período   (006, US2)
  − Σ |cantidad| de anulaciones de ese producto/período   (001)
```

El `faltante_no_explicado` se reparte entre los turnos que registraron `movimiento_inventario` de
tipo `salida_venta` de ese producto en el período, **proporcional** a las unidades que cada turno
movió. El resultado es un indicador por (turno, operador), no una imputación individual: ningún
operador queda señalado en exclusiva solo por haber trabajado en el período (Edge Case del spec).

### 7d. Línea base — decisión de criterio aprobada (#16, sin librería estadística)

Un indicador **señala** a un operador cuando su valor supera a la **mediana de los operadores
comparables de la misma sucursal en el mismo período** multiplicada por un factor configurable
(`RAZON_DESVIACION_ANULACIONES`, `RAZON_DESVIACION_PRECIO_BAJO_LISTA`, valor de arranque **2,0**).
"Comparables" = operadores con al menos `UMBRAL_MINIMO_VENTAS_INDICADOR` ventas en el período (para
que la tasa de uno con tres ventas no dispare una señal por ruido).

**Por qué la mediana y no la media**: la mediana es robusta a un único operador con una tasa
extrema (justo el caso que interesa detectar), que arrastraría la media hacia arriba y escondería
la desviación. Es aritmética de una línea (`sorted(valores)[n//2]`), derivable a mano, sin
`statistics.median` siquiera necesario aunque esté en la biblioteca estándar.

**Rationale**: decisión cerrada por el encargo (research.md #2/#7). Estos indicadores no tienen
ciclo de vida (no se cierran, no se anulan, no tienen estado editable), la constitución los describe
como cálculo derivado, y materializarlos en tabla exigiría recalcularlos y sincronizarlos con `001`
sin ninguna ganancia a esta escala. El único caso en que un valor de indicador se persiste es el
`indicador_snapshot` de una `anomalia_caja` ya generada (#6).

**Alternativas descartadas**: media ± k·desviación estándar —menos robusta a outliers, y la
desviación estándar es una fórmula más que explicar sin ganancia—; z-score / percentiles con `scipy`
—Principio I, sin necesidad demostrada—; umbral absoluto fijo ("más de 5 anulaciones = señal")
—ignora el volumen de ventas del operador y la variación normal entre sucursales, justo lo que la
comparación contra pares corrige.

---

## 8. Cadencia (FR-021) — ya decidida en el spec, fijada aquí como disparadores concretos

**Decisión** (no reabre FR-021, lo instrumenta):

- **Arqueo de caja**: a cada **cierre de turno**, vía `POST /caja/arqueos`. Contar efectivo al
  cierre es barato y ya habitual; no añade carga operativa.
- **Cruce inventario-ventas por operador**: a cada **conteo físico periódico de `001`** (el negocio
  los programa en una rotación semanal por categoría, con los frescos y los productos de alto
  valor/alta rotación con más frecuencia — calendario que fija el negocio al operar, no este plan),
  y **bajo demanda** vía `POST /caja/cruce-operador` cuando un indicador de #7a/#7b se desvía de su
  línea base.
- **NO** en cada venta (inviable para un minimarket de barrio). **NO** un conteo físico diario del
  catálogo completo (irreal).

**Rationale**: el enunciado exige un cuadre "frecuente, no diario". El turno da la frecuencia y la
atribución para el efectivo; el conteo periódico por categoría da la frecuencia para el inventario
—captura el sub-registro en cuestión de días y lo mantiene atribuible a los turnos, y por tanto a
los operadores, que trabajaron en ese intervalo, porque los turnos quedan registrados en `001`.

---

## 9. Estado `sin_explicacion` (FR-027 a FR-031) — ya decidido en el spec

Revisión manual; el sistema nunca fuerza una clasificación ni cierra la anomalía por el paso del
tiempo; anomalía = por definición lo que carece de explicación conocida; una diferencia totalmente
explicada no genera anomalía. Ver #6 para el modelado. No se reabre.

---

## 10. BLOQUEO de implementación: `conteo_fisico` / `conteo_renglon` de `001` no implementados

**Verificado contra el repositorio** (`git log`, `specs/001-core-ventas-inventario/tasks.md`):

- El último checkpoint del proyecto (`873228d`, "001 Setup+Foundational+User Story 1") cubre `venta`,
  `renglon_venta`, `turno`, `operador` y **`anulacion_venta`** (tarea T032 de `001`, en `[X]`).
- **`conteo_fisico` y `conteo_renglon` (User Story 5 de `001`, tareas T065–T071) están en `[ ]`**:
  no hay servicio de inicio ni de resolución de conteo, ni endpoints `POST /conteos-fisicos` /
  `POST /conteos-fisicos/{id}/resolucion`, ni pantallas `ConteoFisico.tsx` / `ResolucionConteo.tsx`.

**Consecuencia por historia de `006`** (mismo tratamiento que el bloqueo de `consulta_no_atendida`
documentado en `004`: se marca, no se oculta, con `xfail` en la fase de `tasks.md`):

| Historia de `006` | ¿Construible ahora? | Detalle |
|---|---|---|
| **US1 — Arqueo de caja** | **Sí, completa** | Solo necesita `turno` y `venta` (entregadas). |
| **US2 — Clasificar mermas** | **Parcial** | **Bloqueado**: clasificar una `diferencia` de `conteo_renglon` (FR-009, FR-015). **No bloqueado**: alerta de caducidad (FR-014) y declaración de merma fuera de conteo (FR-012) — solo necesitan `lote`. |
| **US3 — Cruce por operador** | **Parcial** | **No bloqueado**: tasa de anulaciones (FR-018, #7a) y concentración bajo precio de lista (FR-019, #7b) — necesitan `venta`, `anulacion_venta`, `renglon_venta` (entregadas). **Bloqueado**: el cruce contra el faltante de inventario (FR-020, #7c) — necesita `conteo_renglon`. |
| **US4 — Anomalías** | **Parcial** | **No bloqueado**: anomalías de `origen = 'efectivo'` (desde US1). **Bloqueado**: anomalías de `origen = 'inventario'` (dependen del cruce de FR-020). |

**El spec y el plan se escriben y aprueban ahora.** Las tablas `merma` y `anomalia_caja` se crean en
la migración `0006` completas (incluida la FK `merma.id_conteo_renglon` → `conteo_renglon`, que la
migración `0001` **sí** define aunque su servicio no esté implementado — verificado: `conteo_renglon`
está en `001/data-model.md` y la migración `0001` la incluye). Lo que queda bloqueado es la **lógica
de servicio** que lee esas filas, no el esquema.

**Punto de reactivación** (para `plan.md` y `tasks.md`): cuando `001` implemente su User Story 5
(T065–T071), se quitan los marcadores `xfail` de las pruebas de FR-009/FR-015/FR-020 y se completan
las tareas marcadas `⛔ BLOQUEADA por 001 (T065–T071)`.

---

## 11. Valoración de mermas y anomalías de inventario: al costo del lote FEFO de `001`

**Decisión**: `valoracion = cantidad_faltante × lote.costo_unitario` del lote que la política de
salida de `001` (caducidad más próxima primero, entrada más antigua como desempate — FR-048 de
`001`) habría consumido. Por kilogramo si `producto.es_granel`. No se promedia el costo entre lotes.
Un producto sin ningún lote con costo → `valoracion = NULL` ("no calculable"), **nunca cero**.

**Rationale**: el costo relevante de una unidad que se perdió es el de la unidad que habría salido a
vender, y `001` la habría tomado por FEFO. Promediar entre lotes inventaría un costo que ninguna
unidad real tuvo. Mismo criterio que `001` para el capital inmovilizado.

**Alternativas descartadas**: costo promedio ponderado —no refleja qué unidad se perdió—; último
costo de compra —ignora que puede haber stock más antiguo a otro costo—; cero cuando falta el costo
—finge una cifra, prohibido por el mismo criterio que `001`.

---

## 12. Día local y tiempo

**Decisión**: todo `arqueo`, `merma` y `anomalia_caja` se fecha por el **día local de la sucursal**:
`(instante AT TIME ZONE sucursal.zona_horaria)::date`, resuelto vía la sucursal de la operación.
Instantes almacenados en `TIMESTAMPTZ` (UTC). Las agregaciones de negocio (mermas de un período,
anomalías de un día, arqueos de una semana) se calculan sobre el día local, nunca sobre `::date` del
instante crudo.

**Rationale**: restricción "Tiempo" de la constitución, idéntica a como `004` fija
`demanda_observada.periodo` y `005` fija `redencion_promocion.periodo`.

---

## 13. Ciclo de vida de las entidades: append + máquina de estados (como `005`, no recompute-on-read)

**Decisión**: a diferencia de `margen_calculado` de `003` y `demanda_corregida` de `004` (que se
**recomputan** al leer porque son funciones de datos de `001` que cambian), las entidades de `006`
son **hechos con máquina de estados**:

- `arqueo`: inmutable una vez cerrado. Las correcciones se anotan en `ajustes` (JSONB), no
  reescriben `monto_contado` ni `monto_esperado`.
- `merma`: `pendiente_clasificar → clasificada` (cuando se asigna una causa distinta de
  `pendiente_clasificar`). La `valoracion` se congela en el momento de registrar (con el costo del
  lote vigente entonces).
- `anomalia_caja`: `sin_explicacion → resuelta` (transición explícita por acción de una persona,
  #6).

Ninguna se recomputa; ninguna se borra (Principio IV). Los **únicos cálculos derivados** del módulo
son: la alerta de caducidad (#5), los tres indicadores por operador (#7) y el cruce inventario-ventas
(#7c) — todos consultas sobre `001`, ninguno una tabla.

**Rationale**: los insumos de estas entidades son **decisiones y eventos de `006`** (cerrar un
arqueo, clasificar una merma, resolver una anomalía), no datos de `001` que cambien por debajo. No
hay nada que recomputar.

---

## 14. Convención de endpoints — prefijo `/caja`

**Decisión**: se reutiliza la convención de `001`–`005` (sustantivos, `kebab-case`, acciones no-CRUD
como subrecurso, un prefijo por módulo). El prefijo es `/caja` (el módulo es "caja, mermas y
fraude"; "caja" es el término del dominio que engloba el arqueo, y mermas y anomalías cuelgan de él):

| Endpoint | FR | Nota |
|---|---|---|
| `POST /caja/arqueos` | FR-001–007 | Registra el arqueo de un turno. **Idempotente** por `id_turno`. |
| `GET /caja/arqueos?id_sucursal=&desde=&hasta=&id_turno=&solo_descuadrados=` | FR-003, FR-038 | `id_sucursal` obligatorio si no se pasa `id_turno`. |
| `GET /caja/arqueos/{id_arqueo}` | FR-039 | Detalle: montos, diferencia, motivo, ajustes. |
| `POST /caja/mermas` | FR-009, FR-012, FR-013, FR-015 | Clasifica una `diferencia` de `conteo_renglon` **o** declara una merma fuera de conteo (según venga `id_conteo_renglon` o no). |
| `GET /caja/mermas?id_sucursal=&causa=&id_producto=&desde=&hasta=` | FR-016, FR-038 | Desglose por causa/producto/sucursal. |
| `GET /caja/alertas-caducidad?id_sucursal=&dentro_de_dias=` | FR-014 | Consulta derivada sobre `lote` de `001`. |
| `POST /caja/cruce-operador` | FR-020, FR-021 | Ejecuta el cruce inventario-ventas para `{id_sucursal, desde, hasta, id_conteo_fisico?}`. **⛔ bloqueado por `001` User Story 5** para la parte de faltante de inventario. |
| `GET /caja/indicadores-operador?id_sucursal=&desde=&hasta=` | FR-018, FR-019, FR-022, FR-023 | Consulta derivada: tasa de anulaciones y concentración bajo precio de lista por operador, con la línea base de pares y qué operadores se desvían. |
| `GET /caja/anomalias?id_sucursal=&estado=&origen=&desde=&hasta=` | FR-028, FR-038 | Lista de anomalías; el encargado trabaja las `sin_explicacion`. |
| `GET /caja/anomalias/{id_anomalia_caja}` | FR-028, FR-039 | Detalle: origen, monto/magnitud, atribución, historial, `indicador_snapshot`. |
| `POST /caja/anomalias/{id_anomalia_caja}/resolucion` | FR-030 | Una persona asigna `{resolucion, id_operador, nota?}`; registra `estado_anterior` en `historial`. |

**Ningún endpoint** ajusta `existencia`, `movimiento_inventario`, `venta` ni ningún precio de `001`;
ninguno bloquea, suspende o sanciona a un operador (FR-024, FR-032, FR-040); ninguno ejecuta un
conteo físico (FR-033).

**Formato de error** `{ codigo, mensaje }` unificado con `001`–`005` (nunca `{ detalle }`); el
`mensaje` redactado para el operador con la acción correctiva, nunca una traza técnica (Principio
IV).

**Rationale**: consistencia con el contrato ya publicado; no hay ninguna razón de este dominio para
desviarse.

**Alternativas descartadas**: prefijos separados `/arqueos`, `/mermas`, `/anomalias` —tres prefijos
para un módulo rompen la convención de `001`–`005`, que usa uno por módulo (`/promociones`,
`/pronostico`, …)—; un `PATCH /caja/anomalias/{id}` genérico en vez de `/resolucion` —la resolución
es una transición de estado con reglas (registra historial, exige operador), no una edición libre de
campos.

---

## 15. Frontend — registro visual **mixto**: `Arqueo.tsx` en Operación, el resto en Análisis

**Decisión** (decisión de criterio aprobada):

- **`Arqueo.tsx` — registro de OPERACIÓN**. La constitución lista literalmente "**Operación** (punto
  de venta, inventario, **arqueo**)". Arquear una caja es una tarea operativa de cierre de turno,
  no una decisión gerencial: alta densidad, la tabla como elemento principal, sin tarjetas, radio
  **2px**, IBM Plex Sans con cifras tabulares reales (las columnas de efectivo contado y esperado
  alinean por dígito), **sin animación** salvo la confirmación de la acción de cerrar el arqueo.
  Vive junto al cierre de turno.
- **`Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx` — registro de ANÁLISIS**.
  Clasificar la causa de una merma, revisar una anomalía sin explicación y leer las señales de
  desviación por operador son **decisiones**: una decisión por bloque, aire visual, líneas de texto
  bajo 80 caracteres, radio **6px**, Source Serif 4. Un momento de animación deliberado por pantalla
  (al revelar el detalle de una anomalía o el desglose de un indicador), nunca hover por fila ni
  fade-in por bloque.

**Reglas de `DESIGN.md` que aplican sin tocar el documento**:

- **La Regla del Registro Sin Dinero**: **ninguna** pantalla de este módulo compromete dinero —el
  arqueo registra un conteo, la clasificación de merma es contable, la resolución de anomalía es
  administrativa—. Por tanto **cero apariciones del Verde Rasero** en las cuatro pantallas, igual
  que `Clientes.tsx` (la primera superficie que quedó en cero apariciones, comportamiento correcto).
- **La Regla de la Sola Voz**: no aplica por ausencia (no hay acción que comprometa dinero), que es
  precisamente lo que la Regla del Registro Sin Dinero formaliza.
- **La Regla del Significado** (los tres semánticos): **crítico `#8E2A2A`** para una anomalía
  `sin_explicacion` y para un lote ya **caducado** en la alerta de caducidad (la constitución
  reserva el crítico para "caducado, anomalía" — este módulo es su caso de uso literal);
  **atención `#9A5B08`** para un lote **próximo a caducar** (aún no vencido) y para una diferencia de
  arqueo con motivo conocido anotado (dato que requiere seguimiento pero no es crítico);
  **estimado `#1F5673`** para todo valor **calculado, no observado**: el faltante atribuido
  proporcionalmente a un turno, la señal de desviación de un indicador, la valoración de una merma.
  El dato **observado** —la `diferencia` bruta del conteo de `001`, el efectivo contado, la tasa de
  anulaciones cruda— va en tinta normal.
- **La Regla de los Tres Portadores**: "sin explicación", "no calculable", "muestra insuficiente de
  ventas para comparar" y "lote caducado" se comunican siempre con color semántico + indicador de
  forma (punto lleno / medio / hueco) + texto explícito — nunca solo color, nunca solo la ausencia
  de un número. Una anomalía `sin_explicacion` usa el **punto hueco** (como `senal_fuga` `confirmada`
  en `002`): marca que ese dato está pendiente de que una persona lo cierre.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado en `001`); este módulo **no** repite
`init`. Se invoca `new-work` de Impeccable para las cuatro pantallas con el mundo visual ya fijado
(los dos registros, la paleta y la tipografía de `DESIGN.md`, sin cambio). El agente `documenter`
actualiza `DESIGN.md` **al final**, derivándolo de las pantallas construidas — no antes.

**Rationale**: la constitución es explícita en clasificar "arqueo" como Operación; el resto del
módulo es análisis gerencial. Separar los registros por pantalla es exactamente lo que `DESIGN.md`
pide ("un cajero y un gerente no miran la misma clase de pantalla").

**Alternativas descartadas**: todo el módulo en Análisis —contradice la mención literal de "arqueo"
en Operación—; todo en Operación —la clasificación de merma y la revisión de anomalías son decisiones
de una por bloque, no filas de una tabla densa.

---

## 16. Parámetros de configuración → `backend/rasero/config/caja.py`

Todos en un único lugar de verdad, sobrescribibles por variable de entorno (mismo patrón que
`config/pronostico.py` de `004` y `config/promociones.py` de `005`). Cada uno justificado aquí, **no
en comentarios de código**:

| Parámetro | Valor de arranque | Dónde se usa | Justificación |
|---|---|---|---|
| `VENTANA_ALERTA_CADUCIDAD_DIAS` | **14** | Alerta de caducidad (#5, FR-014) | Dos semanas de anticipación: tiempo para rebajar, promocionar o traspasar un lote antes de que sea merma, sin llenar la alerta de lotes que aún tienen mes de vida. Se puede afinar por categoría en una versión futura (mismo patrón que `categoria.dias_umbral_inmovilizado` de `001`, que arranca con un valor global y admite override por categoría). |
| `TOLERANCIA_CUADRE_ARQUEO` | **0.00** | Cierre de arqueo (#4, FR-003, FR-004) | Por defecto, **toda** diferencia distinta de cero se registra y —si no tiene motivo— genera anomalía. El valor existe como parámetro por si un comercio decide tolerar el redondeo de monedas de baja denominación (p. ej. 0,05); arrancar en 0,00 es la postura conservadora coherente con la precisión monetaria exacta de la constitución. |
| `UMBRAL_MINIMO_VENTAS_INDICADOR` | **20** | Línea base de los indicadores por operador (#7d, FR-023) | Un operador con menos de 20 ventas en el período tiene una tasa de anulaciones o una concentración de precios demasiado ruidosa para compararla contra sus pares: una sola anulación sobre 3 ventas es 33 %, sobre 20 es 5 %. Por debajo de este umbral el operador **no** entra en el cálculo de la mediana de pares ni recibe señal. 20 es el mínimo para que una proporción tenga sentido comparativo a la escala de un turno de minimarket. |
| `RAZON_DESVIACION_ANULACIONES` | **2.0** | Señal de FR-018 (#7d) | Un operador se señala cuando su tasa de anulaciones es **≥ 2×** la mediana de sus pares comparables de la misma sucursal y período. El doble de la mediana es una desviación difícil de explicar por variación normal del trabajo de caja y fácil de defender ante el operador señalado ("tu tasa es el triple de la de tus compañeros ese mes"). Ajustable con datos reales. |
| `RAZON_DESVIACION_PRECIO_BAJO_LISTA` | **2.0** | Señal de FR-019 (#7d) | Mismo criterio y mismo valor de arranque que el anterior, para la concentración de renglones registrados por debajo del precio de lista. Se mantiene igual al de anulaciones por simplicidad de defensa; se separan en dos parámetros para poder calibrarlos por separado cuando haya datos. |

Los cinco son parámetros de **calibración dentro de decisiones ya fijadas** (arqueo por turno, cruce
por conteo periódico, línea base por razón sobre la mediana): ajustarlos no reabre FR-021 ni la
decisión de research.md #2/#7 sobre no materializar los indicadores. `RAZON_DESVIACION_*` y
`UMBRAL_MINIMO_VENTAS_INDICADOR` se re-estiman con la distribución real de tasas por operador tras
las primeras semanas de datos.

---

## 17. Estado de dependencias (verificado contra el repositorio)

| Dependencia | Estado real | Fuente |
|---|---|---|
| `001` — `venta`, `renglon_venta`, `turno`, `operador`, **`anulacion_venta`** (T032), `producto`, `sucursal`, `producto_precio_sucursal`, `lote` | **Entregado** (checkpoint `873228d`) | `specs/001-core-ventas-inventario/tasks.md` T001–T043 en `[X]`, migración `0001` |
| `001` — **`conteo_fisico`, `conteo_renglon`** (User Story 5, T065–T071) | **NO entregado** (`[ ]`); el **esquema** sí existe en la migración `0001` | `specs/001-core-ventas-inventario/tasks.md` líneas 166–180 |
| `007-pagos-seguridad` — `medio_pago`, `terminal_pago` | **NO existe** (ni spec) | tabla de Propiedad de Datos de la constitución |

**Conclusión para `/speckit-tasks`**: US1 completa; US2, US3 y US4 con partes bloqueadas por `001`
User Story 5, marcadas `⛔ BLOQUEADA por 001 (T065–T071)` y con `xfail` en las pruebas
correspondientes — mismo tratamiento exacto que `004` dio a `consulta_no_atendida`. El plan de
tareas ordena US1 → US2 → US3 → US4; las partes no bloqueadas de US2/US3/US4 se construyen ya.

---

## 18. `anomalia_caja.resolucion` como texto libre: trade-off aceptado

**Decisión**: `anomalia_caja.resolucion` es `TEXT NULL` libre, no un `ENUM` cerrado. La transición a
`resuelta` (FR-030) registra esa etiqueta, quién la asignó y cuándo, y conserva el estado anterior en
`historial` (JSONB, #6).

**Trade-off aceptado**: con texto libre **se pierde la capacidad de agregar y reportar las anomalías
ya resueltas por categoría** — por ejemplo, "de las 40 anomalías de este trimestre, cuántas
resultaron ser error del sistema, cuántas un hallazgo de fraude real y cuántas un ajuste aceptado".
Ese informe exigiría normalizar cadenas a posteriori y nunca sería del todo fiable.

**A cambio de**: no imponer una taxonomía cerrada de resoluciones que **ni el enunciado del docente
ni ninguna FR ya fijada piden**, y que corre el riesgo de emerger distinta a la que adivinemos hoy.

**Verificación de que ninguna FR ya fijada exige esa agregación**:

- **FR-030** solo exige registrar la resolución, quién y cuándo, y conservar el historial. No pide
  agregarla.
- **FR-029** prohíbe explícitamente que el sistema **fuerce** una clasificación de una anomalía.
- **SC-009** mide anomalías en estado `sin_explicacion` (las abiertas), no las resueltas por
  categoría.
- **FR-016** sí exige desglose por causa — pero de **`merma`**, no de `anomalia_caja`, y `merma`
  **sí** tiene un `ENUM` `causa` cerrado por eso mismo. La asimetría es deliberada: la causa de una
  merma es contable y acotada (vencimiento / daño / robo externo / error de conteo / merma de
  granel); la resolución de una anomalía es una conclusión de investigación humana, más abierta.

**Regla de reversión** (a aplicar solo si una FR futura o una lectura del enunciado exige la
agregación): añadir `categoria_resolucion ENUM(...) NULL` **abierta a extensión** (nuevos valores por
migración, sin romper filas existentes) y conservar `resolucion TEXT` como detalle libre. Es trabajo
**aditivo** — una columna nueva `NULL` y un backfill opcional—: no cambia las tres entidades
(`arqueo`, `merma`, `anomalia_caja`) ni abre enmienda constitucional. Las tres opciones que FR-030 ya
cita ("error operativo confirmado", "escalado a fraude", "ajuste aceptado") serían los valores de
arranque de ese `ENUM`.

**Alternativas descartadas**: `ENUM` cerrado desde ahora —contradice el espíritu de FR-029 y fija una
taxonomía que el alcance no pidió—; un catálogo en tabla (`tipo_resolucion`) —sobreingeniería para
tres o cuatro valores, y tanto `001` (`movimiento_inventario.tipo`) como este mismo modelo
(`merma.causa`) usan `ENUM` para lo análogo—; un campo estructurado JSONB —ni consultable ni
agregable, lo peor de ambos mundos.
