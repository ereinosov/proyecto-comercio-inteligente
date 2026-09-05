# Data Model: Promociones Inteligentes

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo
singular, sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Porcentajes de
descuento en `NUMERIC(5,2)`; precios garantizados y descuentos aplicados en `NUMERIC(12,4)` (misma
escala que `renglon_venta.precio_aplicado` de `001`); proporciones de retorno e incrementalidad en
`NUMERIC(6,4)`; el estadístico z en `NUMERIC(8,5)` y el valor p en `NUMERIC(7,6)`; instantes en
`TIMESTAMPTZ`; fechas de vigencia y períodos como `DATE` (día local de la sucursal).
**Ningún tipo de coma flotante aparece en este modelo.** El único punto donde el cálculo toca
`float` es la evaluación de `math.erf` para el valor p (research.md #10a); su resultado se cuantiza
de inmediato a `NUMERIC(7,6)` antes de persistirse.

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las **seis** entidades que la constitución asigna a
`005-promociones-inteligentes` **tras la enmienda v2.2.5**: `campania`, `cupon`, `oferta_recompra`,
`experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`. Ninguna otra.

La entrada original de la constitución para `005` (`campania`, `envio_promocional`, `grupo_control`)
se revisó **completa** antes de escribir este documento (research.md #2): a diferencia de `004`
—donde v2.2.4 sólo añadió una entidad omitida— y como `003` en v2.2.3, aquí se **retiraron dos**
entidades y se **añadieron cinco**. `envio_promocional`, entidad genérica única de "envío de
promoción", es literalmente el "mecanismo único" que la **Lectura Crítica n.º 6** PROHÍBE; se
sustituyó por una entidad por mecanismo (`cupon`, `oferta_recompra`) más el registro transversal
`redencion_promocion`. `grupo_control` a secas no captura la semilla, la ventana, el tamaño mínimo
de muestra ni el desenlace por cliente que FR-016 a FR-024 exigen; se precisó en
`experimento_reactivacion` + `asignacion_experimento`. `campania` se conservó como paraguas. Se
corrigió por la enmienda **v2.2.5** (commit `a2bb668`) — ver research.md #2 y el informe de impacto
de sincronización al inicio de `constitution.md`. No hay discrepancia pendiente entre este documento
y la tabla vigente (constitución v2.2.5).

**Frontera de propiedad explícita — sólo lectura, sin escritura ni posesión**: este módulo consulta
`cliente` (`002`), `visita` (`002`), `intervalo_compra` (`002`, `intervalo_esperado_dias` y
`estado`), `senal_fuga` (`002`, `estado` e `id_senal_fuga`), y de `001` consulta `venta`,
`renglon_venta`, `producto` (`precio_vigente`, `es_granel`), `producto_precio_sucursal` (override),
`sucursal` (`zona_horaria`) y `turno` (para resolver la sucursal de una venta). **`005` no escribe
en ninguna tabla ajena** — a diferencia de `003`, que escribe en `producto_precio_sucursal` al
aplicar una sugerencia. En particular, **`005` nunca lee ni escribe `existencia` ni
`movimiento_inventario`**: la reserva del empuje por recompra es **de precio, no de inventario**, y
la disponibilidad al vender la resuelve `001` (FR-010, FR-011). `005` tampoco toca `senal_fuga`
(FR-028): la lee y guarda su `id` para auditoría. Ninguna columna de `001` ni de `002` se duplica
en este documento, salvo dos valores **inmutables y derivados** en `redencion_promocion`
(`id_sucursal`, `periodo`) justificados en research.md #4 para la consulta de marca activa que
`004` consume.

---

## `campania`

Paraguas de una corrida de promoción de **un solo mecanismo** (research.md #3). Agrupa los cupones
de un rango, o las ofertas de recompra de una detección, o el experimento de una reactivación.

| Campo | Tipo | Notas |
|---|---|---|
| `id_campania` | `INTEGER` PK | |
| `tipo` | `ENUM('fecha_fija','recompra','reactivacion') NOT NULL` | El mecanismo. No hay campañas de tipo mixto (Lectura Crítica n.º 6) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NULL` | `NULL` = toda la cadena (un cupón de cumpleaños o un experimento pueden no acotarse a una sucursal). No `NULL` = la campaña sólo cubre esa sucursal (FR-035) |
| `nombre` | `TEXT NOT NULL` | Etiqueta legible ("Cumpleaños — septiembre 2026") |
| `ventana_desde` | `DATE NOT NULL` | Primer día local de vigencia |
| `ventana_hasta` | `DATE NOT NULL` | Último. `CHECK (ventana_hasta >= ventana_desde)` |
| `instante_creacion` | `TIMESTAMPTZ NOT NULL` | |

*Sin recompute*: `campania` es un registro de una decisión, nunca se recalcula (research.md #12).

*Sin ruta de lectura propia en el contrato* (decisión declarada como Assumption en spec.md):
ningún escenario de aceptación de las cuatro historias requiere listar campañas de forma
independiente de sus mecanismos; se alcanza siempre por el `id_campania` que llevan `cupon`,
`oferta_recompra` y `experimento_reactivacion`. `campania` es agrupación interna, no un recurso del
contrato `openapi.yaml`.

---

## `cupon`

Cupón por fecha fija (cumpleaños). Regla directa: la fecha del cliente entra en la ventana → se
genera. Sin grupo de control, sin medición (FR-001, FR-006).

| Campo | Tipo | Notas |
|---|---|---|
| `id_cupon` | `BIGINT` PK | |
| `id_campania` | `INTEGER FK → campania NOT NULL` | Regla de aplicación: `campania.tipo = 'fecha_fija'` |
| `id_cliente` | `INTEGER FK → cliente (002) NOT NULL` | Sólo lectura de `002` |
| `motivo` | `ENUM('fecha_fija_cumpleanos') NOT NULL DEFAULT 'fecha_fija_cumpleanos'` | El único motivo hoy; `ENUM` para admitir otras fechas fijas sin cambiar la columna |
| `fecha_objetivo` | `DATE NOT NULL` | El cumpleaños de este año. Lo trae la respuesta de `GET /clientes/cumpleanos` de `002` (FR-002); `005` **nunca** lee `cliente.fecha_nacimiento` |
| `valido_desde` | `DATE NOT NULL` | `fecha_objetivo − ANTELACION_GENERACION_CUPON_DIAS` (research.md #6) |
| `valido_hasta` | `DATE NOT NULL` | `fecha_objetivo + VALIDEZ_CUPON_DIAS` |
| `porcentaje_descuento` | `NUMERIC(5,2) NOT NULL` | Snapshot de `DESCUENTO_CUPON_CUMPLEANOS_PCT` al generar |
| `estado` | `ENUM('generado','redimido','vencido') NOT NULL DEFAULT 'generado'` | `redimido` al crearse su `redencion_promocion`; `vencido` cuando la fecha actual supera `valido_hasta` sin redención |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |

*Idempotencia* (FR-007): `UNIQUE (id_cliente, fecha_objetivo)`. Ejecutar la generación dos veces
para el mismo rango, o para rangos solapados, no crea un segundo cupón por la misma fecha objetivo
del mismo cliente; la generación captura y descarta la violación de unicidad por fila (mismo patrón
que `registrar_visita` de `002` con `id_venta UNIQUE`).

*Cliente anonimizado* (FR-003): no aparece en la respuesta de `GET /clientes/cumpleanos` de `002`
(`002` ya filtra `anonimizado = FALSE AND fecha_nacimiento IS NOT NULL`), así que nunca se le crea
un cupón. `005` no necesita comprobarlo por su cuenta.

*Redención fuera de ventana* (Edge Case): `POST /promociones/redenciones` rechaza registrar una
redención de un cupón cuya fecha de venta cae fuera de `[valido_desde, valido_hasta]`; el cupón
sigue su curso a `vencido`.

---

## `oferta_recompra`

Oferta proactiva de un producto que el cliente suele recomprar, con **reserva de precio** (FR-010).
La reserva garantiza el precio, **no** la disponibilidad (FR-011): no aparta stock ni escribe
contra `existencia` / `movimiento_inventario` de `001`.

| Campo | Tipo | Notas |
|---|---|---|
| `id_oferta_recompra` | `BIGINT` PK | |
| `id_campania` | `INTEGER FK → campania NOT NULL` | `campania.tipo = 'recompra'` |
| `id_cliente` | `INTEGER FK → cliente (002) NOT NULL` | |
| `id_producto` | `INTEGER FK → producto (001) NOT NULL` | El producto que el cliente suele recomprar (research.md #7) |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | La sucursal cuyo precio queda garantizado (el precio difiere por sucursal vía `producto_precio_sucursal`). La reserva se redime en esta sucursal (FR-035) |
| `intervalo_esperado_dias_disparo` | `NUMERIC(8,2) NOT NULL` | Snapshot de `intervalo_compra.intervalo_esperado_dias` de `002` que disparó la oferta (FR-013, explicabilidad). `005` **consulta** ese valor, no lo recalcula |
| `justificacion` | `JSONB NOT NULL` | `{ ventas_consideradas: [id_venta, …], compras_del_producto: N, ventana_dias: 180 }` — qué compras del propio cliente sustentan la elección (FR-009). `JSONB` porque es contexto de sólo lectura ligado a la fila, no una entidad consultable (mismo criterio que `pronostico.serie_pronosticada` de `004`) |
| `precio_garantizado` | `NUMERIC(12,4) NOT NULL` | Precio resuelto para `id_sucursal` al generar (`COALESCE(producto_precio_sucursal.precio_vigente, producto.precio_vigente)`) menos `DESCUENTO_RECOMPRA_PCT`. **Es lo único que la reserva garantiza** (FR-010) |
| `reserva_desde` | `DATE NOT NULL` | Día local de emisión |
| `reserva_hasta` | `DATE NOT NULL` | `reserva_desde + VENTANA_RESERVA_RECOMPRA_DIAS` |
| `estado_reserva` | `ENUM('vigente','vencida') NOT NULL DEFAULT 'vigente'` | `vencida` cuando la fecha actual supera `reserva_hasta` |
| `desenlace` | `ENUM('pendiente','comprado','no_comprado','reserva_vencida') NOT NULL DEFAULT 'pendiente'` | `comprado` = el cliente redimió; `reserva_vencida` = venció sin compra; `no_comprado` = cerrada a mano |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |

*Una oferta activa por par* (FR-014): índice único parcial
`UNIQUE (id_cliente, id_producto) WHERE desenlace = 'pendiente'`.

*Redención sin stock* (FR-011, Edge Case): si al momento de comprar no hay existencia suficiente,
el cliente recibe el mismo trato que cualquier comprador sin oferta (sin garantía de
disponibilidad). El esquema no modela una "reserva de stock" porque no existe: `005` no aparta
unidades. Si el cliente compra a pesar de todo, la `redencion_promocion` registra el
`descuento_aplicado` real.

---

## `experimento_reactivacion`

La corrida experimental del mecanismo 3 (FR-015 a FR-025). Guarda toda su parametrización y su
resultado. **Append + estado** (`veredicto`), nunca se recomputa (research.md #12).

| Campo | Tipo | Notas |
|---|---|---|
| `id_experimento_reactivacion` | `BIGINT` PK | |
| `id_campania` | `INTEGER FK → campania NOT NULL` | `campania.tipo = 'reactivacion'` |
| `id_sucursal` | `INTEGER FK → sucursal (001) NULL` | `NULL` = elegibles de toda la cadena; si no, sólo los cuya última visita fue en esa sucursal |
| `semilla` | `BIGINT NOT NULL` | Semilla de `random.Random` usada (FR-017). Snapshot de `SEMILLA_ALEATORIZACION` salvo que se pase otra al crear |
| `algoritmo` | `TEXT NOT NULL` | `"random.Random / MT19937 (biblioteca estándar de Python)"` (FR-024, research.md #9) |
| `proporcion_tratamiento` | `NUMERIC(4,3) NOT NULL` | `0,500` por defecto — maximiza el poder de la prueba z (research.md #9) |
| `ventana_medicion_dias` | `SMALLINT NOT NULL` | `42` por defecto (research.md #11) |
| `porcentaje_descuento` | `NUMERIC(5,2) NOT NULL` | Descuento ofrecido **sólo** al grupo tratamiento (FR-018) |
| `tasa_retorno_base_esperada` | `NUMERIC(5,4) NOT NULL` | `p_c` para el cálculo del tamaño mínimo de muestra (research.md #10b) |
| `mde_puntos_porcentuales` | `NUMERIC(5,2) NOT NULL` | Efecto mínimo detectable usado |
| `alfa` | `NUMERIC(4,3) NOT NULL` | `0,050` — nivel de significancia de la prueba z (FR-021) |
| `poder` | `NUMERIC(4,3) NOT NULL` | `0,800` — poder objetivo del cálculo de muestra |
| `tamano_minimo_muestra` | `INTEGER NOT NULL` | `n*` por grupo, calculado por `dominio/experimento.tamano_minimo_muestra(...)` (research.md #10b). Guardado para que la interfaz explique un "muestra insuficiente" |
| `n_elegibles` | `INTEGER NOT NULL` | Clientes con `senal_fuga` activa al crear el experimento |
| `n_tratamiento` | `INTEGER NULL` | `NULL` si `veredicto = 'muestra_insuficiente'` (no se asignaron grupos) |
| `n_control` | `INTEGER NULL` | Idem |
| `retorno_tratamiento` | `NUMERIC(6,4) NULL` | Proporción de retorno del grupo tratamiento. `NULL` hasta el cierre |
| `retorno_control` | `NUMERIC(6,4) NULL` | Proporción de retorno del grupo control |
| `incrementalidad` | `NUMERIC(6,4) NULL` | `retorno_tratamiento − retorno_control` (FR-020). Puede ser negativa |
| `estadistico_z` | `NUMERIC(8,5) NULL` | Prueba z de dos proporciones (research.md #10a) |
| `valor_p` | `NUMERIC(7,6) NULL` | Prueba de **dos colas**: `1 − erf(|z| / √2)` |
| `veredicto` | `ENUM('en_curso','efectivo','no_efectivo','muestra_insuficiente') NOT NULL DEFAULT 'en_curso'` | `muestra_insuficiente` al crear si `n_elegibles < 2 × tamano_minimo_muestra`; `efectivo` al cerrar si `incrementalidad > 0 AND valor_p < alfa`; `no_efectivo` en cualquier otro cierre (FR-021, Edge Case de incrementalidad negativa) |
| `instante_asignacion` | `TIMESTAMPTZ NOT NULL` | Inicio de la ventana de medición |
| `instante_cierre` | `TIMESTAMPTZ NULL` | Cuándo se calcularon las tasas y la prueba z |

*Muestra insuficiente* (FR-025): cuando `n_elegibles < 2 × tamano_minimo_muestra`, el experimento
se crea con `veredicto = 'muestra_insuficiente'`, **sin** filas de `asignacion_experimento` y sin
enviar tratamiento. No se fuerza ninguna conclusión de incrementalidad.

*Campo de respuesta derivado — `motivo_muestra_insuficiente`*: el contrato
(`contracts/openapi.yaml`, schema `Experimento`) expone una cadena legible
`"84 elegibles, mínimo 242 (MDE 15 pp, poder 0,80)"`. **No es una columna de esta tabla**: se
**calcula al vuelo al serializar la respuesta**, a partir de `n_elegibles`, `tamano_minimo_muestra`,
`mde_puntos_porcentuales` y `poder`, y sólo cuando `veredicto = 'muestra_insuficiente'` (`null` en
cualquier otro caso). Almacenarlo sería redundante: sus cuatro insumos ya son columnas.

---

## `asignacion_experimento`

Una fila por cliente inactivo elegible, con su grupo y su desenlace de retorno. Es la
materialización del **grupo de control obligatorio** (Lectura Crítica n.º 6, FR-023).

| Campo | Tipo | Notas |
|---|---|---|
| `id_asignacion_experimento` | `BIGINT` PK | |
| `id_experimento_reactivacion` | `BIGINT FK → experimento_reactivacion NOT NULL` | |
| `id_cliente` | `INTEGER FK → cliente (002) NOT NULL` | |
| `id_senal_fuga` | `BIGINT NOT NULL` | La `senal_fuga` de `002` (por su `id`) que hizo elegible al cliente. Referencia de **auditoría**, no FK con cascada — cruza el límite de propiedad. `005` **nunca** modifica `senal_fuga` (FR-028) |
| `grupo` | `ENUM('tratamiento','control') NOT NULL` | **Sin tercer valor** (research.md #3): no existe un estado "en el experimento sin grupo" desde el que se pueda afirmar eficacia |
| `retorno` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` si el cliente registró una `visita` de `002` dentro de la ventana de medición (research.md #11) |
| `id_venta_retorno` | `BIGINT NULL` | La venta de `001` de la primera visita en la ventana (referencia de sólo lectura, vía `visita` de `002`) |
| `instante_retorno` | `TIMESTAMPTZ NULL` | Instante de esa primera visita |

*Unicidad*: `UNIQUE (id_experimento_reactivacion, id_cliente)` — un cliente aparece a lo sumo una
vez por experimento. Índice adicional `(id_cliente)` para detectar clientes ya en un experimento en
curso (no se reasignan).

*Sólo el tratamiento recibe descuento* (FR-018): no hay columna "descuento" en esta tabla; el
derecho al descuento **es** `grupo = 'tratamiento'`. La `redencion_promocion` de una reactivación
apunta a la `asignacion_experimento`, y el porcentaje aplicable es
`experimento_reactivacion.porcentaje_descuento`. Un cliente de control no tiene forma de generar una
redención de reactivación válida.

---

## `redencion_promocion`

El hecho de que un `cupon`, una `oferta_recompra` o una `asignacion_experimento` (tratamiento) se
usó en una **venta de `001`**. Registro de hecho **inmutable**. Referencia la venta por FK de
**sólo lectura**, sin copiar sus datos (research.md #4).

| Campo | Tipo | Notas |
|---|---|---|
| `id_redencion_promocion` | `BIGINT` PK | |
| `tipo_origen` | `ENUM('cupon','oferta_recompra','reactivacion') NOT NULL` | Qué mecanismo se redimió |
| `id_cupon` | `BIGINT FK → cupon NULL` | Exactamente uno de los tres `id_*` de origen no nulo, coherente con `tipo_origen` (`CHECK`) |
| `id_oferta_recompra` | `BIGINT FK → oferta_recompra NULL` | |
| `id_asignacion_experimento` | `BIGINT FK → asignacion_experimento NULL` | Sólo válido si esa asignación tiene `grupo = 'tratamiento'` (regla de aplicación) |
| `id_venta` | `BIGINT NOT NULL` | Referencia de **sólo lectura** a `venta` (`001`). No es FK con cascada — cruza el límite de propiedad; su existencia se valida al registrar (research.md #4). Mismo patrón que `visita.id_venta` de `002` |
| `id_producto` | `INTEGER FK → producto (001) NULL` | El producto que la promoción afectó. `NULL` = toda la venta (cupón / reactivación); la consulta de marca lo expande a todos los renglones de la venta (research.md #5). Una `oferta_recompra` siempre trae `id_producto` |
| `id_sucursal` | `INTEGER FK → sucursal (001) NOT NULL` | **Denormalizado** de `venta → turno → sucursal` — inmutable, para la consulta de marca activa (research.md #4) |
| `periodo` | `DATE NOT NULL` | **Denormalizado**: `(venta.instante AT TIME ZONE sucursal.zona_horaria)::date` — el día local de la venta. Inmutable |
| `descuento_aplicado` | `NUMERIC(12,4) NULL` | Monto del descuento efectivamente aplicado (diferencia entre precio de lista y `renglon_venta.precio_aplicado`), si se puede determinar. `NULL` si no |
| `instante_redencion` | `TIMESTAMPTZ NOT NULL` | Cuándo se registró la redención (posterior a la venta) |

*Idempotencia y "una redención por origen"*: índices únicos parciales
`UNIQUE (id_cupon) WHERE id_cupon IS NOT NULL`,
`UNIQUE (id_oferta_recompra) WHERE id_oferta_recompra IS NOT NULL`,
`UNIQUE (id_asignacion_experimento) WHERE id_asignacion_experimento IS NOT NULL`. Un `POST` repetido
sobre el mismo origen devuelve la redención existente (200), no crea otra.

*Efecto sobre el origen*: al crearse una redención, el servicio `registrar_redencion` marca
`cupon.estado = 'redimido'` o `oferta_recompra.desenlace = 'comprado'` en la misma transacción. Una
redención de reactivación no cambia `asignacion_experimento` (el `retorno` se computa al cerrar el
experimento, mirando `visita` de `002` — la redención es una señal adicional, no la fuente del
retorno).

*Un solo endpoint y un solo servicio, construidos incrementalmente*: `POST /promociones/redenciones`
y `registrar_redencion` se crean **con el mecanismo 1** (US1) — toda la validación (coherencia
`tipo_origen`↔`id_*`, ventana de vigencia del cupón, rechazo del grupo `control`), la idempotencia
y la denormalización de `id_sucursal`/`periodo` viven ahí. El mecanismo 2 (US2) añade **una línea**
(`oferta_recompra.desenlace = 'comprado'`); el mecanismo 3 (US3) no añade nada al servicio. `004`
(US4) sólo **lee** este registro vía `consultar_marca_activa`. No hay una tabla ni una ruta de
redención por mecanismo — mismo esquema transversal para los tres (research.md #4).

---

## Entidades de `001` y `002` consultadas (no poseídas por este módulo)

| Entidad | Módulo | Qué se consulta |
|---|---|---|
| `cliente` | `002` | Identidad del destinatario de un cupón/oferta/asignación (por `id_cliente`). Nunca `fecha_nacimiento` directamente |
| `visita` | `002` | Historial de compra identificada del cliente (para el producto de recompra, research.md #7); detección de "retorno a compra" en la ventana del experimento (research.md #11) |
| `intervalo_compra` | `002` | `intervalo_esperado_dias` y `estado` (`'calculado'`) para la elegibilidad del empuje de recompra (FR-008). Se **consulta**, nunca se recalcula |
| `senal_fuga` | `002` | `estado = 'activa'` para la población elegible del experimento (FR-015); `id_senal_fuga` para auditoría. **Nunca se modifica** (FR-028) |
| `venta` | `001` | Referencia de una redención (`id_venta`); resolución de sucursal y día local vía `turno` |
| `renglon_venta` | `001` | Productos y `precio_aplicado` de una venta con redención (para `descuento_aplicado` y para expandir la marca de un cupón a todos sus productos, research.md #5) |
| `producto` | `001` | `precio_vigente` (precio base para la reserva de precio), `es_granel` |
| `producto_precio_sucursal` | `001` | Override de precio por sucursal, para resolver el precio garantizado de una oferta de recompra |
| `sucursal` | `001` | `zona_horaria`, para el día local de `redencion_promocion.periodo` |
| `turno` | `001` | Vínculo `venta → sucursal` |

`005` **no consulta** `existencia` ni `movimiento_inventario` de `001`: la disponibilidad al vender
la resuelve `001` (FR-011), y la reserva del empuje por recompra es de precio, no de inventario.
Las pruebas de frontera (`test_generacion_cupones.py`, `test_oferta_recompra.py`) los leen **sólo**
para verificar por conteo que `005` nunca les añadió filas.

## Consultas derivadas (no son tablas)

- **`marca_promocion_activa`** (FR-031 a FR-034, la que `004` consume): agrupa `redencion_promocion`
  por `(id_producto, id_sucursal, periodo)` dentro de la ventana pedida y lista los `tipo_origen`
  distintos. Las filas con `id_producto = NULL` se **expanden** a todos los productos de su venta
  vía `renglon_venta` de `001`. Filtra siempre por `id_sucursal` (FR-035). No es una tabla:
  `redencion_promocion` ya es un registro de hechos append-only y la agregación indexada por
  `(id_sucursal, periodo)` es barata a esta escala (research.md #5, #12).
- **Cupones vigentes de un cliente** (para `AplicarPromocionVenta.tsx` en caja): `SELECT` sobre
  `cupon` con `id_cliente = ? AND estado = 'generado' AND CURRENT_DATE BETWEEN valido_desde AND
  valido_hasta`, más `oferta_recompra` con `id_cliente = ? AND desenlace = 'pendiente' AND
  estado_reserva = 'vigente'`.
- **Población elegible del experimento**: `SELECT id_cliente, id_senal_fuga` de `senal_fuga` de
  `002` con `estado = 'activa'`, excluyendo los clientes ya presentes en una
  `asignacion_experimento` de un `experimento_reactivacion` con `veredicto = 'en_curso'`.
- **Tasa de retorno por grupo** (al cerrar): para cada `grupo`,
  `COUNT(*) FILTER (WHERE retorno) / COUNT(*)` sobre `asignacion_experimento` del experimento. El
  `retorno` de cada fila se fija comprobando si existe una `visita` de `002` de ese `id_cliente`
  con `instante` en `[instante_asignacion, instante_asignacion + ventana_medicion_dias]`.

## Migración

`backend/migraciones/versions/0005_promociones_inteligentes.py` — crea las seis tablas y sus
índices:

- `redencion_promocion`: `(id_sucursal, periodo)` para `marca-activa`; `(id_venta)`; los tres
  índices únicos parciales sobre los `id_*` de origen.
- `cupon`: `UNIQUE (id_cliente, fecha_objetivo)`; `(estado, valido_hasta)` para el barrido de
  vencimiento.
- `oferta_recompra`: `UNIQUE (id_cliente, id_producto) WHERE desenlace = 'pendiente'`;
  `(estado_reserva, reserva_hasta)`.
- `experimento_reactivacion`: `(id_campania)`.
- `asignacion_experimento`: `UNIQUE (id_experimento_reactivacion, id_cliente)`; `(id_cliente)`.
- `campania`: `(tipo)`.

`downgrade` elimina las seis tablas en orden inverso de dependencia
(`redencion_promocion` → `asignacion_experimento` → `experimento_reactivacion` → `oferta_recompra`
→ `cupon` → `campania`). Ningún cambio de esquema sobre tablas de `001`–`004`.
