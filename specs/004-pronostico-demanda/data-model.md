# Data Model: Pronóstico de Demanda

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo
singular, sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Cantidades de
demanda observada en `NUMERIC(14,0)` (misma escala que `movimiento_inventario.cantidad` de `001`:
unidades enteras o gramos según `producto.es_granel`); valores corregidos, pronosticados y
multiplicadores en `NUMERIC` de escala fija (detallada por columna); parámetros de suavizado y
elasticidad en `NUMERIC(4,3)`; instantes en `TIMESTAMPTZ`; períodos como `DATE` (día local de la
sucursal). **Ningún tipo de coma flotante aparece en este modelo ni en el código de cálculo.**

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las cuatro entidades que la constitución asigna a
`004-pronostico-demanda` **tras la enmienda v2.2.4**: `demanda_observada`, `demanda_corregida`,
`pronostico`, `sustitucion_producto`. Ninguna otra.

La entrada original de la constitución para `004` (`demanda_observada`, `demanda_corregida`,
`pronostico`) se revisó **completa** antes de escribir este documento (research.md #2): a
diferencia de `003` —donde v2.2.3 halló que `costo_producto` contradecía una frontera y que
faltaba `sugerencia_precio`—, las tres entradas de `004` no contradecían ninguna frontera (son
artefactos analíticos derivados, coherentes con la misma lógica que asigna `margen_calculado` a
`003`). La **única** omisión era `sustitucion_producto`, exigida por FR-032, User Story 6 y
FR-009 (b), y se añadió por la enmienda **v2.2.4** — mismo patrón que `rol_producto` de `003`
(declaración de negocio sobre un producto, tabla propia con FK, sin tocar el esquema de `producto`
de `001`). No hay discrepancia pendiente entre este documento y la tabla vigente (constitución
v2.3.0; la entrada de 004 no cambió desde v2.2.4 — v2.3.0 sólo cambió el esquema de `operador`
de `001`).

**Frontera de propiedad explícita — sólo lectura, sin escritura ni posesión**: este módulo
consulta `venta`, `renglon_venta` (demanda y precio histórico aplicado), `movimiento_inventario`,
`existencia`, `lote` (intervalos de quiebre y reconstrucción de saldo), `consulta_no_atendida`
(magnitud de demanda latente, **cuando `001` la implemente**), `producto` (`es_granel`,
`precio_vigente`), `producto_precio_sucursal` (precio de referencia actual), `sucursal`
(`zona_horaria` para el día local), y `observacion_precio`/`canal_competencia` (contexto de
precio). Todas son propiedad de `001-core-ventas-inventario`. `004` las **lee sin poseerlas**
(mismo patrón que `002` y `003` ya validaron) y **no escribe en ninguna tabla ajena** — a
diferencia de `003`, que sí escribe en `producto_precio_sucursal` al aplicar una sugerencia. Por
eso `004` no necesita ninguna función-puente de servicio de `001`. La marca de "promoción activa"
por período se consumirá de `005-promociones-inteligentes` cuando exista (hoy: todos los períodos
"sin promoción", FR-030). Ninguna columna de `001` se duplica en este documento.

---

## `demanda_observada`

Serie histórica de demanda tal como se registró, agregada por producto, sucursal y **día local de
la sucursal**. Registro de hechos: no se modifica retroactivamente (FR-004). Se materializa por
`upsert` sobre la ventana de días solicitada al leer la serie o el pronóstico (recompute-on-read,
research.md #3), nunca por disparador ni tarea de fondo.

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` PK, FK → `producto` (`001`) | PK compuesta |
| `id_sucursal` | `INTEGER` PK, FK → `sucursal` (`001`) | PK compuesta |
| `periodo` | `DATE` PK | Día local de la sucursal: `(movimiento.instante AT TIME ZONE sucursal.zona_horaria)::date` (research.md #4). PK compuesta |
| `cantidad` | `NUMERIC(14,0) NOT NULL` | Demanda observada = salida **neta** de mercancía = `Σ salida_venta − Σ entrada_anulacion` del período (una venta anulada no es demanda satisfecha; research.md #3, Assumptions de spec.md). Unidades o gramos según `producto.es_granel` |
| `dias_en_quiebre` | `NUMERIC(4,3) NOT NULL DEFAULT 0` | Fracción del período en quiebre. Con período diario es 0 ó 1: un día cuenta como quiebre **sólo si el saldo reconstruido estuvo ≤ 0 todo el día** (`SALDO_MAXIMO_EN_QUIEBRE`, `dominio/serie_demanda.py`) — un quiebre parcial exigiría una unidad más fina que el día, fuera de alcance (FR-002, FR-005, Assumptions de spec.md) |
| `precio_vigente_periodo` | `NUMERIC(12,4) NULL` | Precio reconstruido de `renglon_venta.precio_aplicado` del período (moda; media ponderada por cantidad como desempate — research.md #8b). `NULL` = período sin ventas, sin precio reconstruible → "sin corrección de precio" (FR-027) |
| `con_promocion` | `BOOLEAN NOT NULL DEFAULT FALSE` | Marca de promoción activa en el período. Hoy siempre `FALSE` (FR-030); la poblará `005` cuando exista |
| `es_sintetico` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` sólo para series cargadas por la User Story 2 (research.md #9). Toda consulta de pronóstico de producción filtra `es_sintetico = FALSE` (FR-017) |
| `demanda_latente_verdadera` | `NUMERIC(14,4) NULL` | Poblada **sólo** para filas sintéticas de períodos de quiebre (FR-013): el valor verdadero conocido contra el que se mide el error de descensura. `NULL` en todo dato real |
| `consultas_no_atendidas_sinteticas` | `INTEGER NULL` | Conteo sintético de consultas no atendidas del período, contrapartida de `consulta_no_atendida` de `001`. Poblado sólo en filas sintéticas de quiebre que declaran ese escenario (FR-016), para tener los datos listos cuando la rama de evidencia real (FR-007 / T014) se desbloquee. `NULL` en todo dato real y en quiebres sintéticos sin consultas |
| `instante_materializacion` | `TIMESTAMPTZ NOT NULL` | Último `upsert` de esta fila (recompute-on-read). No es un histórico |

*Patrón de actualización*: `upsert` (`ON CONFLICT (id_producto, id_sucursal, periodo) DO UPDATE`)
ejecutado por `servicios/demanda.reconstruir_serie` sobre la ventana pedida (por defecto 90 días —
research.md #3). Las anotaciones (`dias_en_quiebre`, `precio_vigente_periodo`, `con_promocion`) se
congelan con el período; un recálculo posterior sólo las revisa si cambió un movimiento de origen
de ese período.

---

## `demanda_corregida`

Serie derivada de `demanda_observada` tras aplicar, **en orden fijo** (research.md #3), las
correcciones por: (1) quiebre de stock, (2) precio, (3) promoción, (4) señal de sustitución. Una
fila por período corregido, con la misma PK compuesta que `demanda_observada`.

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` PK, FK → `producto` (`001`) | PK compuesta |
| `id_sucursal` | `INTEGER` PK, FK → `sucursal` (`001`) | PK compuesta |
| `periodo` | `DATE` PK | Día local de la sucursal. PK compuesta |
| `valor_observado` | `NUMERIC(14,0) NOT NULL` | Snapshot de `demanda_observada.cantidad` de partida (FR-010) — no una FK, para que la serie corregida sea explicable aunque la observada se recompute |
| `valor` | `NUMERIC(14,4) NOT NULL` | Demanda corregida final del período. `>= valor_observado` siempre que `dias_en_quiebre > 0` (FR-006); puede tener decimales tras normalización de precio |
| `correccion_quiebre` | `NUMERIC(14,4) NOT NULL DEFAULT 0` | Delta aplicado por descensura (FR-009). 0 si el período no tuvo quiebre (FR-011) |
| `respaldo_quiebre` | `ENUM('no_aplica','metodo_base','consulta_no_atendida')` NOT NULL DEFAULT `'no_aplica'` | Cómo se estimó la demanda latente: `metodo_base` = máximo de N períodos recientes sin quiebre (FR-008); `consulta_no_atendida` = respaldado por el conteo real de `001` (FR-007). Ver nota de bloqueo abajo |
| `ajuste_cruzado_sustituto` | `NUMERIC(14,4) NOT NULL DEFAULT 0` | Porción del delta de quiebre atribuida al exceso de un sustituto declarado (FR-009 b, research.md #6). Incluida en `correccion_quiebre` |
| `correccion_precio` | `NUMERIC(14,4) NOT NULL DEFAULT 0` | Delta por normalización al precio de referencia (FR-025). 0 si `precio_vigente_periodo` es `NULL` (FR-027) |
| `elasticidad_usada` | `NUMERIC(4,3) NULL` | `ε` aplicado en la corrección de precio (research.md #8b). `NULL` si no hubo corrección de precio |
| `excluido_por_promocion` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` si el período se excluyó de la serie a precio normal por promoción activa (FR-029, FR-031). El período **permanece** en la tabla, marcado — no es un hueco |
| `censura_total` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` si el producto no tiene ningún período sin quiebre del cual estimar y no hay consultas no atendidas (FR-012). Con `TRUE`, `valor` es `NULL`-equivalente: se expone como "no estimable", nunca 0 |
| `es_sintetico` | `BOOLEAN NOT NULL DEFAULT FALSE` | Igual criterio que `demanda_observada` (FR-017) |
| `instante_materializacion` | `TIMESTAMPTZ NOT NULL` | Último `upsert` |

*Nota de bloqueo (`respaldo_quiebre`)*: mientras `001` no implemente su User Story 3
(`consulta_no_atendida`, tareas T050–T053), el valor `consulta_no_atendida` de este `ENUM` **no se
produce**: todo período de quiebre se descensura por `metodo_base` (FR-008) y se marca como
estimación de menor confianza. El `ENUM` incluye el valor desde ya para que el contrato y las
pruebas estén listos cuando `001` desbloquee FR-007 (plan.md, "Estado de implementación por
historia").

*Censura total → `valor` no numérico*: cuando `censura_total = TRUE`, el servicio devuelve el
período con `valor: null` y un `estado: "no_estimable_censura_total"`; la columna `valor` se deja
en 0 en la fila sólo como marcador no expuesto (nunca se presenta ese 0 al usuario — FR-012).

---

## `pronostico`

**Append-only**: cada generación es una fila nueva; ninguna se sobrescribe ni se borra (Principio
IV). El histórico de pronósticos de un producto queda consultable y auditable.

| Campo | Tipo | Notas |
|---|---|---|
| `id_pronostico` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` (`001`) | |
| `id_sucursal` | `INTEGER` FK → `sucursal` (`001`) | Todo pronóstico se identifica por sucursal (FR-037) |
| `horizonte` | `ENUM('corto','medio')` NOT NULL | `corto` = 7–14 días (reposición); `medio` = 30 días (estacionalidad intramensual) — FR-019 |
| `dias_horizonte` | `SMALLINT NOT NULL` | Nº concreto de días proyectados (p. ej. 14, 30) |
| `serie_pronosticada` | `JSONB NOT NULL` | Lista de `{ periodo: DATE, valor: NUMERIC }` — la proyección día a día. `JSONB` porque es un resultado de sólo lectura ligado a esta fila, no una entidad consultable por sí sola (mismo criterio que `conteo_fisico.alcance` de `001`) |
| `nivel_suavizado` | `NUMERIC(14,4) NOT NULL` | `nivel_t` del suavizado exponencial en el instante de generación (FR-021) |
| `alfa_usado` | `NUMERIC(4,3) NOT NULL` | Parámetro α aplicado (research.md #7) |
| `multiplicadores_tramo` | `JSONB NULL` | Sólo horizonte `medio`: `{ tramo: multiplicador }` aplicado (research.md #8d). `NULL` en horizonte `corto` |
| `periodo_datos_desde` | `DATE NOT NULL` | Primer día del histórico usado (FR-021) |
| `periodo_datos_hasta` | `DATE NOT NULL` | Último día del histórico usado |
| `valor_linea_base` | `NUMERIC(14,4) NOT NULL` | Promedio móvil de la demanda **observada sin corregir** sobre la ventana N (FR-022, research.md #8c) |
| `error_retrospectivo` | `NUMERIC(14,4) NULL` | Error del método sobre los últimos días con dato real |
| `error_linea_base` | `NUMERIC(14,4) NULL` | Mismo error para la línea base, para comparar |
| `vigente` | `BOOLEAN NOT NULL` | `TRUE` sólo si `error_retrospectivo < error_linea_base` (SC-004). Si `FALSE`, la interfaz muestra la línea base |
| `motivo_no_vigente` | `TEXT NULL` | P. ej. `"no supera la linea base"`, `"datos insuficientes"` (FR-023) |
| `es_sintetico` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` si se generó sobre una serie sintética (validación); nunca se mezcla con pronósticos de producción (FR-017) |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |

*Producto sin histórico suficiente* (FR-023): no se genera `serie_pronosticada` con números; la
fila se crea con `vigente = FALSE`, `motivo_no_vigente = "datos insuficientes"` y
`serie_pronosticada` vacía. Nunca un valor por defecto.

---

## `sustitucion_producto`

Relación declarada **manualmente** entre un producto y otro que puede sustituirlo (FR-032). Tabla
simple: no se infiere de correlación de ventas ni de ningún otro dato. Añadida a la tabla de
propiedad de la constitución por la enmienda **v2.2.4**.

| Campo | Tipo | Notas |
|---|---|---|
| `id_sustitucion_producto` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` (`001`) NOT NULL | El producto que, al quedar en quiebre, puede empujar demanda hacia su sustituto |
| `id_producto_sustituto` | `INTEGER` FK → `producto` (`001`) NOT NULL | El sustituto. `CHECK (id_producto <> id_producto_sustituto)` |
| `instante_declaracion` | `TIMESTAMPTZ NOT NULL` | Cuándo se declaró la relación |

*Unicidad*: `UNIQUE (id_producto, id_producto_sustituto)` — una relación dirigida se declara a lo
sumo una vez. Una relación **mutua** (A↔B) son dos filas; una relación **circular** está permitida
(research.md, Edge Cases del spec). La dirección importa: la señal (FR-033) y el ajuste cruzado
(FR-009 b) se evalúan según **cuál** de los dos tuvo el quiebre en el período.

*Sin alcance por sucursal*: la sustituibilidad es una propiedad del par de productos, no de la
sucursal (un cliente que quiere azúcar morena y no la hay compra azúcar blanca en cualquier
tienda). El efecto sí se evalúa por sucursal y período, pero la **declaración** es global — mismo
criterio que `rol_producto` de `003` (por producto, no por sucursal).

*Borrado*: `DELETE` permitido (una relación declarada por error se retira). No es append-only
porque, a diferencia de un pronóstico o una visita, no es un hecho histórico sino una
configuración vigente — mismo criterio que `rol_producto` de `003`, que se sobrescribe.

---

## Entidades de `001` consultadas (no poseídas por este módulo)

| Entidad | Qué se consulta |
|---|---|
| `venta` / `renglon_venta` | Demanda observada por período (`salida_venta`); precio histórico aplicado (`renglon_venta.precio_aplicado`, research.md #8b) |
| `movimiento_inventario` | Reconstrucción del saldo día a día (intervalos de quiebre, FR-005); netear anulaciones (`entrada_anulacion`) |
| `existencia` | Referencia rápida; ante discrepancia gana la recomputación desde `movimiento_inventario` (`data-model.md` de `001`) |
| `lote` | Contexto de existencia por lote (no se usa el costo — este módulo no calcula margen) |
| `consulta_no_atendida` | `saldo_en_el_instante` e instante, para la magnitud de la demanda latente (FR-007) — **bloqueado hasta `001` User Story 3** |
| `producto` | `es_granel` (unidad o gramo), `precio_vigente` (precio de referencia base) |
| `producto_precio_sucursal` | Override de precio por sucursal, para el precio de referencia actual (`COALESCE`, misma resolución que `001` al vender) |
| `sucursal` | `zona_horaria`, para agregar por día local (constitución: agregaciones sobre el día local de la sucursal) |
| `observacion_precio` / `canal_competencia` | Contexto de precio de competencia para la vista de análisis (no entra en el cálculo de descensura; `001` User Story 4 tampoco implementada) |

## Consultas derivadas (no son tablas)

- **Serie de un producto para la pantalla de Análisis**: `SELECT` sobre `demanda_observada` y
  `demanda_corregida` filtrando por `id_producto`, `id_sucursal` y rango de `periodo`,
  materializando primero la ventana pedida (research.md #3, #4). Filtra `es_sintetico = FALSE`
  salvo en la vista de validación.
- **Reporte de error de descensura (User Story 2, FR-014/FR-015)**: para las filas con
  `es_sintetico = TRUE`, `demanda_corregida.valor − demanda_observada.demanda_latente_verdadera`
  por período y agregado, junto al mismo cálculo con `demanda_observada.cantidad` (la referencia
  "sin corregir"). No es una tabla: se calcula al pedir la validación.
- **Línea base determinista (FR-022)**: promedio móvil simple de `demanda_observada.cantidad`
  (sin corregir) sobre la ventana N. Se calcula al generar el pronóstico y se congela en
  `pronostico.valor_linea_base`.
- **"Nivel típico" de un producto** (para FR-033 y el método base de descensura): máximo de
  `demanda_observada.cantidad` entre los N períodos recientes con `dias_en_quiebre = 0`. Una sola
  definición, tres usos (research.md #10).

## Migración

`backend/migraciones/versions/0004_pronostico_demanda.py` — crea las cuatro tablas y sus índices
(`(id_producto, id_sucursal, periodo)` en las dos series; `(id_producto, id_sucursal, horizonte,
instante_generacion)` en `pronostico`; `(id_producto)` y `(id_producto_sustituto)` en
`sustitucion_producto`). `downgrade` elimina las cuatro tablas. Ningún cambio de esquema sobre
tablas de `001`/`002`/`003`.
