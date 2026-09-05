# Research: Promociones Inteligentes

**Fase 0** · 2026-09-05 · Plan: [plan.md](./plan.md)

Los dos `[NEEDS CLARIFICATION]` del borrador de `spec.md` (FR-010 mecanismo de reserva, FR-021
umbral de incrementalidad) se resolvieron en la sesión de clarificación del 2026-09-05 (ver
`## Clarifications` en spec.md): **reserva de precio, no de inventario**, y **prueba z de dos
proporciones con p < 0,05**. Este documento fija los **parámetros** que esas decisiones dejaron
"calibrables aquí" —en particular el **tamaño mínimo de muestra por grupo** y la **semilla y el
algoritmo de aleatorización**, los dos puntos más probables de pregunta en la defensa oral— y
resuelve las decisiones de diseño que el plan debía tomar por su cuenta.

---

## 1. Reutilización íntegra del stack de `001`–`004`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + TS + Vite, sin librería de componentes de terceros) que `001`–`004`, sobre la
misma base PostgreSQL 16 (puerto 5442).

**Razón**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función que
una ya presente, salvo justificación registrada. Ninguna característica de este módulo exige un
lenguaje, framework o motor distinto. La única tentación real —una librería estadística para la
prueba z y el cálculo de poder— se descarta por separado en #10.

**Alternativas descartadas**: ninguna evaluada seriamente para el stack base.

---

## 2. Propiedad de datos: revisión completa de la entrada de `005` y enmienda v2.2.5 antes de diseñar el esquema

**Decisión**: antes de escribir `data-model.md`, se revisó la entrada **completa** de
`005-promociones-inteligentes` en la tabla de "Propiedad de Datos y Nomenclatura" de la
constitución —`campania`, `envio_promocional`, `grupo_control`— contra la Lectura Crítica n.º 6 y
las fronteras de la propia sección, y se corrigió por enmienda **v2.2.5** (commit `a2bb668`,
2026-09-05).

**Lo que la revisión encontró**:

- **`envio_promocional` contradice de frente la Lectura Crítica n.º 6.** Esa lectura dice
  literalmente "implementarlas como un mecanismo único está PROHIBIDO". Una entidad genérica única
  llamada "envío de promoción" es **exactamente** ese mecanismo único: obligaría a que el cupón de
  cumpleaños, el empuje de recompra y el descuento de reactivación —que el spec trata en tres User
  Stories con lógica y exigencias distintas— compartieran tabla y se distinguieran por un campo
  `tipo`, disolviendo la separación que la constitución exige preservar. Se **retira** y se
  sustituye por una entidad por mecanismo: `cupon` (fecha fija) y `oferta_recompra` (empuje por
  recompra). El hecho **transversal** —que una promoción se redimió en una venta de `001`— se
  modela como `redencion_promocion`, más estrecha y mejor definida que "envío": no representa el
  acto de comunicar una promoción (que en este alcance es manual), sino el de **consumirla** en una
  venta concreta.
- **`grupo_control` a secas es demasiado gruesa** para lo que el spec exige del mecanismo 3. FR-016
  a FR-024 piden registrar: la **semilla** de aleatorización, el **algoritmo**, la **ventana de
  medición**, el **tamaño mínimo de muestra** aplicado, las **tasas de retorno por grupo**, la
  **incrementalidad**, el **estadístico z y el valor p**, y el **veredicto** — más, por cliente, su
  **grupo** y su **desenlace de retorno**. Una sola entidad "grupo de control" no tiene dónde poner
  nada de eso. Se **retira** y se precisa en dos: `experimento_reactivacion` (la corrida, con toda
  su parametrización y su resultado) y `asignacion_experimento` (una fila por cliente elegible con
  su grupo y su retorno). El grupo de control **sigue siendo obligatorio** para este mecanismo
  (Lectura Crítica n.º 6); esta enmienda no lo debilita, lo modela con la granularidad que la
  medición de incrementalidad necesita.
- **`campania` se conserva** sin cambios como paraguas de una corrida de promoción de un mecanismo
  dado.

**Entrada corregida de `005`**: `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`,
`asignacion_experimento`, `redencion_promocion` — seis entidades (antes tres).

**Razón del patrón "tabla propia, no atributo ajeno"**: idéntica a la de `rol_producto` en `003` y
`sustitucion_producto` en `004`. La constitución prohíbe alterar el esquema de una entidad ajena;
`cliente` es de `002`, `venta` y `producto` son de `001`. Cada entidad de `005` referencia esas
tablas por clave foránea de **sólo lectura** y modela su propia lógica en tabla propia.

**Alternativas descartadas**: mantener `envio_promocional` como tabla base con subtipos por `tipo`
—rechazada por la Lectura Crítica n.º 6—; conservar `grupo_control` y colgar el resto de columnas
de `campania` —rechazada porque una `campania` de reactivación puede, en el futuro, tener más de
una corrida experimental (re-ejecutar con otra semilla o otra ventana), y mezclar los parámetros
del experimento con los de la campaña lo impediría—; no enmendar y "documentar la discrepancia"
—rechazada porque la Puerta de propiedad de datos exige que el `data-model.md` y la tabla
constitucional no discrepen, y v2.2.3 / v2.2.4 ya establecieron el precedente de enmendar primero.

---

## 3. Una entidad por mecanismo: cómo el esquema hace cumplir la Lectura Crítica n.º 6

**Decisión**: no existe ninguna tabla "promoción" genérica. `cupon`, `oferta_recompra` y el par
`experimento_reactivacion` / `asignacion_experimento` son tablas independientes, cada una con las
columnas que **su** mecanismo necesita y ninguna que no:

| Mecanismo | Entidad | Lo que la distingue estructuralmente |
|---|---|---|
| 1 — fecha fija | `cupon` | `fecha_objetivo`, `valido_desde`/`valido_hasta`; **sin** columna de grupo, semilla ni medición. `UNIQUE (id_cliente, fecha_objetivo)` da la idempotencia de FR-007. |
| 2 — recompra | `oferta_recompra` | `id_producto`, `precio_garantizado`, `reserva_hasta`, `intervalo_esperado_dias_disparo`; **sin** grupo de control. `UNIQUE (id_cliente, id_producto) WHERE desenlace = 'pendiente'` da FR-014. |
| 3 — reactivación | `experimento_reactivacion` + `asignacion_experimento` | `semilla`, `algoritmo`, `ventana_medicion_dias`, `tamano_minimo_muestra`, tasas por grupo, `estadistico_z`, `valor_p`, `veredicto`; `asignacion_experimento.grupo` es `ENUM('tratamiento','control')` **sin tercer valor**. |

**Razón**: la constitución exige que el modelo de dominio (Principio I) refleje que "son tres
mecanismos, no uno". Si el esquema tuviera una tabla base con `tipo`, cualquier consulta o regla
futura podría tratarlos como intercambiables por descuido; con tres tablas, tratar la reactivación
como un cupón exige escribir código que claramente cruza dos entidades, y salta a la vista en
revisión.

**`asignacion_experimento.grupo` sin "sin_grupo"**: FR-023 dice que la ausencia de grupo de control
"invalida cualquier afirmación sobre la eficacia". Modelado como un `ENUM` de dos valores, es
**imposible** tener un cliente "en el experimento pero sin grupo": o está en `tratamiento`, o en
`control`, o no tiene fila de asignación (no está en el experimento). No hay un estado en el que se
pueda afirmar eficacia sin control.

---

## 4. `redencion_promocion`: entidad transversal que referencia una venta de `001` sin duplicarla

**Decisión**: `redencion_promocion` tiene una **clave foránea de sólo lectura** `id_venta` →
`venta` (`001`), exactamente como `visita.id_venta` de `002`. Registra que un `cupon`, una
`oferta_recompra` o una `asignacion_experimento` (tratamiento) se usó en esa venta. **No copia**
ningún dato de la venta —ni total, ni renglones, ni precios—: para conocerlos, se hace `JOIN` con
`venta` / `renglon_venta` de `001`.

**Excepción justificada — dos columnas denormalizadas**: `redencion_promocion` sí guarda
`id_sucursal` y `periodo` (día local), **derivados** de la venta (`venta → turno → sucursal`;
`(venta.instante AT TIME ZONE sucursal.zona_horaria)::date`). Motivo: la consulta de
`marca-activa` que `004` consume (#5) es una agregación por `(id_producto, id_sucursal, periodo)`
sobre potencialmente miles de redenciones y una ventana de 90 días; resolver `id_sucursal` y
`periodo` con un triple `JOIN` a `turno` y `sucursal` en cada lectura la haría un orden de magnitud
más lenta, y ambos valores son **inmutables** una vez ocurrida la venta (una venta no cambia de
sucursal ni de instante). Es la misma clase de denormalización controlada que `visita.instante`
(copiado de `venta.instante`) en `002`. Se documenta aquí para que la revisión no lo lea como una
duplicación de datos de `001`.

**Cómo se entera `005` de una redención** (Principio II): **no** por participar en `POST /ventas`.
El cajero completa la venta en `001` con el `precio_aplicado` que decida (si honra un cupón, cobra
menos); **después**, una llamada aparte `POST /promociones/redenciones {id_venta, tipo_origen,
id_origen}` registra la redención. Idempotente por `UNIQUE (id_venta, tipo_origen, id_origen)`. Si
esa llamada falla o `005` está caído, la venta ya está cobrada y la redención se puede registrar
más tarde. Mismo patrón exacto que `registrar_visita` de `002`, cuyo docstring dice que "nunca
forma parte de la transacción de venta".

**Un solo endpoint, construido con el mecanismo 1**: `POST /promociones/redenciones` y el servicio
`registrar_redencion` se construyen en **US1** como parte de cerrar el ciclo del cupón — toda la
validación (coherencia `tipo_origen`↔`id_*`, ventana de vigencia del cupón, rechazo del grupo
`control`), la idempotencia y la denormalización viven ahí. **US2** añade una línea de efecto
(`oferta_recompra.desenlace = 'comprado'`); **US3** no añade nada; **US4** sólo lee. No hay una
tabla ni una ruta de redención por mecanismo — la Lectura Crítica n.º 6 exige tres mecanismos
distintos en la **generación** (cupón / oferta / experimento), no tres formas distintas de
registrar que uno se usó en una venta.

**Alternativas descartadas**: que `005` escuche un evento de `001` al cerrar la venta —`001` no
emite eventos y añadir un bus de eventos es la "segunda tecnología" del Principio I—; que
`redencion_promocion` copie los renglones de la venta para no depender de `001` en la consulta de
marca —duplica datos de `001`, prohibido, y desincroniza si la venta se anula—; resolver
`id_sucursal`/`periodo` por `JOIN` en cada lectura de marca —correcto pero lento a la escala de la
ventana de `004`, y sobre valores que nunca cambian.

---

## 5. La "marca de promoción activa" (FR-031 a FR-034): consulta derivada que cierra el contrato con `004`

**Decisión**: `marca_promocion_activa` **no es una tabla**. Es la consulta

```
GET /promociones/marca-activa?id_sucursal=&desde=&hasta=
  → [ { id_producto, id_sucursal, periodo, tipos: ["fecha_fija" | "recompra" | "reactivacion", ...] } ]
```

que agrupa `redencion_promocion` por `(id_producto, id_sucursal, periodo)` dentro de la ventana
pedida y lista los tipos de promoción que tocaron ese producto ese día en esa sucursal.

- **Expansión de `id_producto = NULL`**: un `cupon` de cumpleaños suele ser un descuento sobre
  **toda la compra**, no un producto. Su `redencion_promocion` se guarda con `id_producto = NULL`,
  y la consulta lo **expande** a todos los productos de esa venta vía `renglon_venta` de `001`. Una
  `oferta_recompra` sí tiene `id_producto` (el producto ofertado). Un descuento de reactivación
  también suele ser sobre toda la compra → `NULL` → misma expansión.
- **Qué hace `004` con esto**: FR-003 de `004` puebla `demanda_observada.con_promocion` por
  `(producto, sucursal, período)`. Hoy `004` fuerza `con_promocion = FALSE` para todo período
  (FR-030 de `004`, "hasta que `005` exista"). Con este endpoint, `004` lo pobla de verdad: un
  período con marca se **excluye o se marca** al construir la serie corregida (FR-029/FR-031 de
  `004`), para que las ventas promocionales no inflen la demanda a precio normal.
- **Contrato cerrado desde este lado**: el spec de `004` (Key Entities) esperaba "la marca de
  'promoción activa' por producto, sucursal y período (derivada de `campania`)". Este endpoint es
  esa marca. `005` la **posee y la deriva**; `004` la **lee**. Ninguna escritura de `005` en
  `demanda_observada` / `demanda_corregida` / `pronostico` (FR-033).

**Por qué derivada y no materializada**: a diferencia de `demanda_corregida` de `004` (que congela
anotaciones por período y por eso es tabla), la marca de promoción es una función pura de
`redencion_promocion`, que ya es un registro de hechos append-only. Materializarla añadiría una
tabla que hay que mantener sincronizada sin ninguna ganancia: la consulta agregada sobre
`redencion_promocion` indexada por `(id_sucursal, periodo)` es barata a esta escala.

**Alternativas descartadas**: materializar la marca en una tabla `periodo_promocion` —sincronización
sin ganancia—; que `004` consulte directamente `redencion_promocion` —acoplaría `004` al esquema
interno de `005` en vez de a un contrato estable, justo lo que la frontera de propiedad evita.

---

## 6. Cupón por fecha fija (FR-001 a FR-007): ventana de generación y frontera con `002`

**Decisión**:

- La generación se dispara por `POST /promociones/cupones/generacion {desde, hasta}` (o por la
  tarea `python -m rasero.tareas.generacion_cupones`, mismo patrón que
  `tareas/mantenimiento_clientes.py` de `002`). Para cada cliente que **`002` devuelve** en
  `GET /clientes/cumpleanos?desde=&hasta=`, se crea un `cupon` con `fecha_objetivo` = el cumpleaños
  de este año, `valido_desde` = `fecha_objetivo − ANTELACION_GENERACION_CUPON_DIAS`, `valido_hasta`
  = `fecha_objetivo + VALIDEZ_CUPON_DIAS`.
- **Frontera con `002` (FR-002, FR-027)**: `005` **nunca** lee `cliente.fecha_nacimiento` ni
  reimplementa el filtro por día/mes. Usa el endpoint de `002`, que además ya excluye a los
  clientes anonimizados (`Cliente.anonimizado = FALSE AND fecha_nacimiento IS NOT NULL`,
  verificado en `servicios/clientes.py::clientes_con_cumpleanos`). FR-003 se cumple por
  construcción: un anonimizado no aparece en la respuesta de `002`.
- **Idempotencia (FR-007)**: `UNIQUE (id_cliente, fecha_objetivo)`. Ejecutar la generación dos
  veces para el mismo rango, o para rangos solapados, no crea un segundo cupón por la misma fecha
  objetivo del mismo cliente. La generación captura y descarta la violación de unicidad por fila
  (mismo patrón que `registrar_visita` de `002` con `id_venta UNIQUE`).

**Valores por defecto** (parámetros de `config/promociones.py`, calibrables sin reabrir el
mecanismo):

| Parámetro | Valor de arranque | Razón |
|---|---|---|
| `ANTELACION_GENERACION_CUPON_DIAS` | **7** | El cupón llega la semana previa al cumpleaños: tiempo para que el cliente lo vea y planee una visita, sin generarlo con tanta antelación que lo olvide. |
| `VALIDEZ_CUPON_DIAS` | **14** | Una semana antes + una semana después. Cubre el fin de semana anterior y el posterior al cumpleaños, los dos momentos naturales de compra. |
| `DESCUENTO_CUPON_CUMPLEANOS_PCT` | **10,00** | Parámetro de negocio; suficiente para motivar una visita sin canibalizar margen de forma grave. Se ajusta con datos reales. |

**Alternativas descartadas**: generar el cupón el día exacto del cumpleaños —no da margen de
reacción—; ventana de validez de un mes —diluye la asociación con la fecha y complica la marca de
promoción activa de `004`; que `005` mantenga su propia copia de las fechas de nacimiento para no
llamar a `002` en cada generación —duplica un dato personal de `002`, contra la frontera de
propiedad y contra la minimización de datos de la constitución.

---

## 7. Empuje por recompra (FR-008, FR-009): elegibilidad y selección del producto

**Decisión**:

- **Cliente elegible (FR-008)**: `intervalo_compra.estado = 'calculado'` (de `002`; implica
  `visitas_consideradas >= 3`) **y** `dias_desde_ultima_visita` en el rango
  `[ intervalo_esperado_dias × (1 − MARGEN_ANTICIPACION_RECOMPRA), intervalo_esperado_dias ]` — es
  decir, el cliente **se acerca** a su intervalo pero aún no lo supera (superarlo es territorio de
  la `senal_fuga` de `002`, no de la recompra). `005` **consulta** `intervalo_compra`, nunca lo
  recalcula.
- **Producto que "suele recomprar" (FR-009)**: de las compras identificadas del cliente
  (`visita → venta → renglon_venta` de `001`) en los últimos `VENTANA_HISTORIAL_RECOMPRA_DIAS`, se
  toma el producto con **mayor número de compras distintas** (número de `venta` distintas que lo
  incluyen), con al menos `MIN_COMPRAS_PRODUCTO_RECOMPRA` compras; desempate por compra más
  reciente. La `justificacion` (JSONB) guarda la lista de `id_venta` que sustentan la elección,
  para que la oferta sea explicable (FR-009, Principio V).
- **No hay inferencia entre clientes** (FR-009, Assumptions): la selección mira **sólo** el
  historial del propio cliente, nunca correlación con lo que compran otros. Mismo criterio que la
  asignación manual de `rol_producto` en `003` y la relación de sustitución de `004`: `005` no
  infiere gustos, observa compras.

**Valores por defecto**:

| Parámetro | Valor de arranque | Razón |
|---|---|---|
| `MARGEN_ANTICIPACION_RECOMPRA` | **0,20** | La oferta se emite cuando el cliente lleva ≥ 80 % de su intervalo esperado sin comprar: suficientemente cerca para que la recompra sea inminente, con margen para que el código llegue antes de que compre por su cuenta. |
| `VENTANA_HISTORIAL_RECOMPRA_DIAS` | **180** | Seis meses de historial identificado: suficiente para que un patrón de recompra real aparezca varias veces, sin arrastrar preferencias viejas. |
| `MIN_COMPRAS_PRODUCTO_RECOMPRA` | **3** | Tres compras del mismo producto en la ventana es el mínimo para hablar de "patrón" y no de coincidencia — mismo umbral que `002` usa (3 visitas) para pasar de `datos_insuficientes` a `calculado`. |

**Alternativas descartadas**: elegir el producto de mayor gasto acumulado —premia un único
producto caro comprado una vez, no un patrón—; elegir por frecuencia relativa a la categoría
—sobreingeniería sin dato que lo pida—; ofrecer varios productos a la vez —FR-013 modela una oferta
= un producto; varios sería otra entidad.

---

## 8. "Cliente inactivo elegible" para la reactivación (FR-015): reutiliza `senal_fuga` de `002`

**Decisión**: la población elegible del experimento son los clientes con una `senal_fuga` de `002`
en estado **`activa`** (no `confirmada`, no `resuelta`), que no estén ya asignados a un experimento
de reactivación en curso.

**Por qué `activa` y no `confirmada`** (Assumptions del spec, confirmado aquí): el propio `002`
(FR-014 de `002` y `dominio/fuga_cliente.py`) describe la señal `activa` como la que "solo alimenta
una posible reactivación en `005`, reversible y sin costo si el cliente vuelve", y reserva
`confirmada` para el punto en que va a **anonimizar** los datos personales del cliente (a 5× el
intervalo esperado o 12 meses, el mayor). Un cliente `confirmada` está a días de perder su
`fecha_nacimiento` y su contacto; incluirlo en un experimento cuyo tratamiento es "enviarle una
comunicación con un descuento" no tiene sentido operativo. `005` toma la ventana en la que la
reactivación todavía puede funcionar.

**`005` no crea ningún criterio de inactividad nuevo** (FR-015, Lectura Crítica n.º 5): no define
"X días sin comprar". Lee `senal_fuga.estado` y `senal_fuga.id_senal_fuga`, y guarda esa `id` en
`asignacion_experimento` para trazabilidad. `002` sigue siendo el dueño de la detección y de la
máquina de estados; `005` **nunca** modifica una `senal_fuga` (FR-028) — ni siquiera la marca como
resuelta cuando el cliente vuelve: eso lo hace `002` en `registrar_visita`, y `005` lo **observa**.

**Alternativas descartadas**: incluir `confirmada` con una regla "sólo si faltan > 30 días para la
purga" —añade una dependencia frágil al calendario de anonimización de `002`—; que `005` derive su
propia noción de inactividad de `visita` —prohibido por FR-015 y por la Lectura Crítica n.º 5, que
exige un intervalo por cliente, que `002` ya calcula.

---

## 9. Aleatorización real con semilla fija (FR-016, FR-017) — el algoritmo

**Decisión**: la asignación a tratamiento / control se hace con
**`random.Random(semilla)`** de la biblioteca estándar de Python (generador **Mersenne Twister**,
`MT19937`), así:

```python
# dominio/experimento.py — función pura, sin acceso a base de datos
def asignar_grupos(ids_elegibles: list[int], *, semilla: int,
                   proporcion_tratamiento: Decimal) -> dict[int, str]:
    rng = random.Random(semilla)                      # estado inicial fijado por la semilla
    ordenados = sorted(ids_elegibles)                 # orden de entrada determinista
    rng.shuffle(ordenados)                            # Fisher–Yates sobre el flujo del PRNG
    corte = round(len(ordenados) * float(proporcion_tratamiento))
    tratamiento = set(ordenados[:corte])
    return {id_: ("tratamiento" if id_ in tratamiento else "control") for id_ in ids_elegibles}
```

**Por qué esto es aleatorización genuina y no un reparto determinista** (la pregunta de la defensa):

1. **`random.shuffle` es Fisher–Yates** consumiendo el flujo de números del PRNG. El resultado es
   una permutación **uniformemente distribuida** sobre las `n!` permutaciones posibles, a la
   calidad de MT19937 (período `2^19937 − 1`, equidistribución probada en 623 dimensiones). No hay
   ningún sesgo estructural: cada cliente tiene probabilidad `corte / n` de caer en tratamiento,
   **independiente de su `id_cliente`, de su nombre, de su antigüedad de alta y de cualquier otro
   atributo**.
2. **La semilla sólo fija el punto de partida del PRNG**, no *qué* cliente va a *qué* grupo en
   relación con sus atributos. Cambiar la semilla produce otra permutación igualmente válida y
   uniforme. "Mismo dato + misma semilla → mismos grupos" es **reproducibilidad**, no determinismo
   sesgado: es la misma propiedad que hace que un experimento científico registre su semilla para
   que un tercero pueda re-verificar el resultado.
3. **El `sorted()` previo** existe para que la **entrada** al shuffle sea determinista (el orden en
   que la base de datos devuelve las filas no está garantizado). Ordenar por `id_cliente` y luego
   barajar con semilla fija es lo que da reproducibilidad **total** (mismos elegibles → mismos
   grupos en cualquier máquina). El `sorted` **no** introduce sesgo: sólo fija el arreglo inicial
   que el shuffle transforma en una permutación uniforme.

**Contraste explícito con lo PROHIBIDO por FR-016**:

| Método prohibido | Por qué invalida la incrementalidad |
|---|---|
| `id_cliente % 2` | El grupo queda correlacionado con el `id`, y el `id` es un autoincremento → correlaciona con la **antigüedad de alta** → correlaciona con la lealtad y el patrón de compra. El grupo control y el tratamiento tendrían perfiles de cliente distintos *antes* del tratamiento, y la diferencia de retorno mezclaría el efecto del descuento con esa diferencia de base. |
| Orden alfabético / por fecha de última compra, y cortar por la mitad | Mismo problema: cualquier criterio de corte sobre un atributo ordenable crea dos grupos que difieren en ese atributo. |
| "Los primeros N que respondan van a tratamiento" | Autoselección: los que responden rápido son los más enganchados. |

**Semilla por defecto**: `SEMILLA_ALEATORIZACION = 20260905` (fija, en `config/promociones.py`).
Cada experimento **guarda su semilla** en `experimento_reactivacion.semilla` y su algoritmo en
`experimento_reactivacion.algoritmo` (`"random.Random / MT19937 (biblioteca estándar de Python)"`),
de modo que el resultado sea reproducible aunque el default cambie después. Para la demo, correr el
mismo `POST /promociones/experimentos` con los mismos elegibles y la misma semilla da byte a byte
los mismos grupos (SC-005).

**`PROPORCION_TRATAMIENTO = 0,5`** (50/50): reparto equilibrado, que **maximiza el poder
estadístico** de la prueba z para un total de elegibles dado (el poder es máximo cuando
`n_tratamiento = n_control`). Un reparto desequilibrado (p. ej. 70/30 "para tratar a más gente")
tiraría poder y exigiría más elegibles para el mismo MDE.

**Alternativas descartadas**: `secrets` / `os.urandom` —criptográficamente fuerte pero **no
reproducible**, que es justo lo que la demo necesita—; `numpy.random` —introduce `numpy` como
dependencia sólo para esto (Principio I), y su `default_rng` (PCG64) no aporta nada sobre MT19937 a
esta escala—; aleatorización por bloques o estratificada por sucursal/antigüedad —más sofisticada,
reduce varianza, pero el spec no la pide y añade complejidad que habría que justificar; con
`n ≈ 120` por grupo la aleatorización simple ya equilibra los atributos de base en expectativa.

---

## 10. Umbral estadístico de incrementalidad (FR-021): prueba z de dos proporciones + tamaño mínimo de muestra

### 10a. La prueba z de dos proporciones — sin librería

**Decisión**: al cerrar el experimento se calcula

```
p_t = retornos_tratamiento / n_tratamiento          # proporción de retorno del tratamiento
p_c = retornos_control      / n_control              # proporción de retorno del control
incrementalidad = p_t − p_c                          # FR-020

p_agrupada = (retornos_tratamiento + retornos_control) / (n_tratamiento + n_control)
error_estandar = sqrt( p_agrupada · (1 − p_agrupada) · (1/n_tratamiento + 1/n_control) )
z = (p_t − p_c) / error_estandar
valor_p = 1 − erf( |z| / sqrt(2) )                   # prueba de dos colas; erf ∈ math (biblioteca estándar)
```

`veredicto = 'efectivo'` **si y sólo si** `incrementalidad > 0` **y** `valor_p < ALFA_SIGNIFICANCIA`
(0,05). Una incrementalidad negativa (el control retornó más) nunca es `efectivo`, aunque sea
"significativa" — se registra como `no_efectivo` y la interfaz la muestra como contraproducente
(Edge Case del spec).

**Por qué sin `scipy` / `statsmodels`** (Principio I, Principio V "explicable"): la prueba z de dos
proporciones es la fórmula de arriba —cinco líneas de aritmética—; el valor p es la cola de la
normal estándar, que es `math.erf` de la biblioteca estándar (`Φ(z) = ½(1 + erf(z/√2))`). No hay
ninguna función que una librería aporte y que el autor no pueda derivar en la pizarra. Es la misma
disciplina que `004` aplicó al suavizado exponencial ("la recurrencia es una línea de aritmética;
una librería de ARIMA metería decenas de parámetros que nadie puede defender línea por línea").

**Por qué la prueba z y no otra**: con `n ≈ 120` por grupo y proporciones lejos de 0 y 1, la
aproximación normal a la binomial es holgadamente válida (regla habitual `n·p > 5` y `n·(1−p) > 5`:
`120 · 0,15 = 18`). La prueba exacta de Fisher daría prácticamente el mismo p a este tamaño y
exige iterar la distribución hipergeométrica —más código, sin ganancia—. Un test χ² de
independencia 2×2 es **algebraicamente equivalente** a esta z (χ² = z²) para dos colas; se elige la
z porque expone directamente el **signo** de la incrementalidad, que el negocio necesita ver.

### 10b. Tamaño mínimo de muestra por grupo (el cálculo de la defensa oral)

**Decisión**: antes de asignar grupos, el sistema calcula el **tamaño mínimo de muestra por grupo**
`n*` para detectar el efecto que el negocio considera relevante con poder estadístico razonable, y
si la población de elegibles no lo alcanza, marca el experimento `muestra_insuficiente` (FR-025) —
no asigna grupos ni envía tratamiento.

**Fórmula** (dos proporciones, dos colas, grupos iguales):

```
n* por grupo = ( z_{α/2}·√(2·p̄·(1−p̄))  +  z_β·√( p_c·(1−p_c) + p_t·(1−p_t) ) )²  /  (p_t − p_c)²
```

con `p̄ = (p_c + p_t) / 2`, `z_{α/2}` el cuantil normal de `1 − α/2` y `z_β` el de `poder`.

**Parámetros de arranque y su justificación**:

| Parámetro | Valor | Justificación |
|---|---|---|
| `α` (`ALFA_SIGNIFICANCIA`) | **0,05**, dos colas → `z_{α/2} = 1,959964` | Convención estándar. Dos colas porque la incrementalidad puede salir negativa (el descuento podría ser contraproducente) y eso también interesa detectarlo. |
| `poder` (`PODER_ESTADISTICO`) | **0,80** → `z_β = 0,841621` | Convención estándar (Cohen). Aceptamos un 20 % de probabilidad de no detectar un efecto real de tamaño `MDE`. |
| `p_c` (`TASA_RETORNO_BASE_ESPERADA`) | **0,15** | Tasa a la que se estima que un cliente con `senal_fuga` activa vuelve a comprar **por su cuenta**, sin ningún incentivo, dentro de la ventana de medición. Es un valor de **planificación**, no medido: se re-estima con la tasa real del grupo control tras el primer experimento y se recalibra el parámetro. Un cliente con señal activa ha superado 1× su intervalo esperado pero no 5×; que ~1 de cada 7 vuelva solo en las semanas siguientes es plausible para un minimarket de barrio. |
| `MDE` (`MDE_REACTIVACION_PP`) | **15 puntos porcentuales** → `p_t = 0,30` | El **efecto mínimo que haría que valga la pena** gastar el margen del descuento. Por debajo de +15 pp de retorno incremental, el margen canibalizado en los clientes que habrían vuelto igual supera el valor recuperado de los que no habrían vuelto. Es un parámetro de **negocio**: se fija con el dueño, no aquí; 15 pp es el arranque documentado. |

**Cálculo con los valores de arranque** (`p_c = 0,15`, `p_t = 0,30`, `p̄ = 0,225`):

```
z_{α/2}·√(2·0,225·0,775) = 1,959964 · √0,348750 = 1,959964 · 0,590551 = 1,157466
z_β·√(0,15·0,85 + 0,30·0,70) = 0,841621 · √(0,1275 + 0,2100) = 0,841621 · 0,580948 = 0,488940
n* = (1,157466 + 0,488940)² / (0,30 − 0,15)²  =  1,646406² / 0,0225  =  2,710651 / 0,0225  ≈  120,5
```

**`n* = 121 por grupo` ⇒ se necesitan ≥ 242 clientes con `senal_fuga` activa** para correr el
experimento con estos parámetros.

**Análisis de sensibilidad** (para la conversación con el dueño sobre qué MDE es aceptable):

| `p_c` | `MDE` (pp) | `p_t` | `n*` por grupo | elegibles mínimos |
|---|---|---|---|---|
| 0,15 | 10 | 0,25 | **250** | 500 |
| 0,15 | **15** | 0,30 | **121** | **242** |
| 0,15 | 20 | 0,35 | **73** | 146 |
| 0,10 | 15 | 0,25 | **100** | 200 |
| 0,20 | 15 | 0,35 | **138** | 276 |

**Limitación conocida y no bloqueante** (para la defensa oral): en un minimarket de barrio, la
población de clientes con `senal_fuga` activa en un momento dado puede ser **menor que 242**. En
ese caso el sistema marca el experimento `muestra_insuficiente` y **no emite ningún veredicto de
eficacia** — es la respuesta honesta, no un fallo. Las salidas cuando esto ocurre:

1. **Aceptar un MDE mayor** (detectar sólo efectos grandes): con MDE = 20 pp bastan 146 elegibles.
2. **Alargar la ventana de reclutamiento**: acumular clientes que van entrando en `senal_fuga`
   activa a lo largo de varias semanas antes de cerrar la asignación (varias `campania` que
   alimentan un mismo `experimento_reactivacion`, o experimentos sucesivos cuyos resultados se
   agregan — fuera del alcance de esta versión, anotado como evolución).
3. **Reportar el resultado como exploratorio**, con su intervalo de confianza ancho y sin declarar
   "efectivo".

`config/promociones.py` expone `n*` calculado y los cuatro parámetros que lo determinan, de modo
que la interfaz pueda mostrar "muestra insuficiente: 84 elegibles, mínimo 242 (MDE 15 pp)" —
explicable, no un "no" sin motivo (Principio V).

**Alternativas descartadas**: fijar `n*` como una constante ("siempre 100 por grupo") —esconde de
qué MDE y qué poder depende, justo lo que el Principio V "acotada" exige documentar—; usar un
umbral de incrementalidad fijo en puntos porcentuales sin prueba de significancia —lo que FR-021
descarta explícitamente: una diferencia de +12 pp con 15 clientes por grupo es ruido, con 200 es
señal, y sólo la prueba lo distingue—; corrección de continuidad de Yates en la z —efecto
despreciable a `n ≈ 120`, añade una fórmula más que explicar.

### 10c. Datos sintéticos para la demostración del examen (no es un supuesto del modelo)

**Decisión**: el juego de datos de demostración incluye **325 clientes** de "Despensa Los Ríos"
con `senal_fuga` activa — punto medio del rango 300–350, elegido como **margen operativo** sobre el
mínimo real `n* = 242` que el diseño experimental exige (#10b). El margen existe para que el
experimento de reactivación pueda mostrar un **veredicto real** (`efectivo` o `no_efectivo`) en la
defensa oral, y no sólo `muestra_insuficiente`.

Las visitas de retorno de la ventana de medición se **simulan** con una tasa base de
**~15 % en el grupo control** y **~29 % en el grupo tratamiento** (una incrementalidad de ~14 pp,
justo por debajo del MDE de 15 pp de #10b), de modo que la prueba z arroje `veredicto = 'efectivo'`
de forma **reproducible** con `SEMILLA_ALEATORIZACION = 20260905`: con ~162 clientes por grupo,
`p_c ≈ 0,15` y `p_t ≈ 0,29`, el estadístico z ronda 3,1 y el valor p queda holgadamente por debajo
de 0,05 (ver `quickstart.md` escenario 7, con el cálculo a mano).

**Esto es dato de demostración, no un parámetro del modelo ni un supuesto de diseño**:

- El **mínimo real exigido** por el diseño experimental es `n* = 242` (`2 × 121`), derivado del
  cálculo de poder de #10b con `p_c = 0,15`, `MDE = 15 pp`, `α = 0,05`, poder `0,80`. Ese número
  **no cambia** por elegir 325 para la demo.
- Los 325 clientes y las tasas de retorno simuladas (15 % / 29 %) son un **artefacto de la
  presentación**. En producción, `p_c` se re-estima con la tasa real del grupo control tras el
  primer experimento, y las tasas de tratamiento y control **se miden**, nunca se fijan.
- La utilidad que carga estos datos (tarea T042 de `tasks.md`, `rasero/semilla_reactivacion.py`)
  los rotula explícitamente como datos de demo y crea los clientes a través de los **servicios
  públicos de `002` y `001`** (`registrar_cliente`, `registrar_visita`, ventas de `001`), dejando
  que la propia `evaluar_fugas_pendientes` de `002` les asigne la `senal_fuga`. `005` **nunca**
  escribe directamente en `senal_fuga` ni en `visita` (frontera de propiedad de datos, FR-028).

**Guion de la defensa oral**: "el diseño exige **242** clientes elegibles como mínimo para detectar
un efecto de 15 puntos porcentuales con 80 % de poder; la demo usa **325** como margen operativo, y
con las tasas simuladas el veredicto sale `efectivo` de forma reproducible con la semilla fija —
pero el mecanismo es el mismo con la población real, y si ésta fuera menor que 242 el sistema
respondería `muestra_insuficiente` en vez de inventar una conclusión".

---

## 11. "Retorno a compra" (FR-019): definición, ventana y el sesgo de identificación

**Decisión**:

- Un cliente **retorna** si registra al menos una **`visita`** (de `002`) con `instante` dentro de
  la ventana `[instante_asignacion, instante_asignacion + VENTANA_MEDICION_REACTIVACION_DIAS]`, en
  cualquier sucursal. Se guarda `asignacion_experimento.id_venta_retorno` y `instante_retorno` de
  la primera visita en la ventana.
- **Por qué `visita` y no `venta` directa**: `005` no puede saber que un cliente concreto compró si
  no fue identificado en caja. La `visita` de `002` es la única señal observable que vincula una
  venta con un cliente. Además, `002` ya resuelve la `senal_fuga` de ese cliente en
  `registrar_visita` — el "retorno" que mide `005` y la "resolución de fuga" de `002` miran el
  mismo hecho, sin que `005` toque la señal.

**`VENTANA_MEDICION_REACTIVACION_DIAS = 42`** (6 semanas) por defecto:

- Debe ser lo bastante larga para que un cliente reactivado tenga una ocasión natural de compra
  (varias semanas), y lo bastante corta para que el efecto medido sea atribuible al descuento y no
  a estacionalidad o a otra causa que actúe a los dos o tres meses.
- 6 semanas ≈ el intervalo esperado típico de un cliente de minimarket multiplicado por ~1,5:
  cubre el ciclo de compra que el cliente "se saltó" más un margen.
- Calibrable; podría atarse a `mediana(intervalo_esperado_dias)` de la población del experimento en
  una versión futura.

**Sesgo de identificación — limitación conocida, declarada (Principio V "acotada")**: los clientes
de **tratamiento** tienen un incentivo (el descuento) para **identificarse** en caja al volver →
su visita se registra. Los de **control** que vuelven por su cuenta **pueden no identificarse** →
su visita se pierde → la tasa de retorno del control se **subestima** → la incrementalidad se
**sobrestima**. Mitigaciones y honestidad sobre el límite:

1. En el juego de datos de demostración, los clientes se identifican de forma consistente, así que
   el sesgo no distorsiona la demo.
2. En producción, la recomendación es **pedir identificación a todo cliente en caja durante la
   ventana del experimento** (una instrucción operativa, no una regla de software), o interpretar
   la incrementalidad medida como una **cota superior** del efecto real.
3. Este límite se documenta junto al resultado del experimento en la interfaz, no se esconde.

**Alternativas descartadas**: medir el retorno por cualquier `venta` de la sucursal en la ventana
sin vincular al cliente —imposible atribuirla a tratamiento o control—; exigir identificación
obligatoria en caja —viola el Principio II y la decisión de `002` de que identificar al cliente
nunca es bloqueante.

---

## 12. Ciclo de vida de las entidades: append + estado, no recompute-on-read

**Decisión**: a diferencia de `margen_calculado` de `003` y `demanda_corregida` de `004` (que se
**recomputan** al leer porque son funciones de datos de `001` que cambian), las entidades de `005`
son **hechos con máquina de estados**:

- `cupon`: `generado → redimido` (al registrarse su redención) o `generado → vencido` (al pasar
  `valido_hasta` sin redención). El paso a `vencido` lo hace la misma tarea `generacion_cupones` en
  cada corrida, o se calcula al leer comparando `valido_hasta` con la fecha actual (barato, no
  necesita tabla nueva).
- `oferta_recompra`: `desenlace pendiente → comprado | no_comprado | reserva_vencida`.
- `experimento_reactivacion`: `veredicto en_curso → efectivo | no_efectivo` (al cerrar) o
  directamente `muestra_insuficiente` (al crear).
- `asignacion_experimento`: `retorno FALSE → TRUE` (cuando se detecta la visita en la ventana).
- `redencion_promocion`: inmutable una vez creada (registro de hecho).

Ninguna se recomputa; ninguna se borra (Principio IV). El único cálculo derivado del módulo es la
consulta de `marca-activa` (#5).

**Razón**: los insumos de estas entidades son **decisiones y eventos de `005`** (generar un cupón,
crear un experimento, registrar una redención), no datos de `001`/`002` que cambien por debajo. No
hay nada que recomputar. El cierre de un experimento (`POST /promociones/experimentos/{id}/cierre`)
es una transición de estado explícita y única, no un recálculo.

---

## 13. Parámetros de configuración fijados en esta fase (resumen)

Todos en `backend/rasero/config/promociones.py` — un único lugar de verdad, sobrescribibles por
variable de entorno (mismo patrón que `config/pronostico.py` de `004`).

| Parámetro | Valor de arranque | Dónde se usa | Referencia |
|---|---|---|---|
| `ANTELACION_GENERACION_CUPON_DIAS` | 7 | Ventana de validez del cupón de cumpleaños | #6 |
| `VALIDEZ_CUPON_DIAS` | 14 | Ventana de validez del cupón | #6 |
| `DESCUENTO_CUPON_CUMPLEANOS_PCT` | 10,00 | Valor del cupón | #6 |
| `MARGEN_ANTICIPACION_RECOMPRA` | 0,20 | Rango de elegibilidad de la oferta de recompra | #7 |
| `VENTANA_HISTORIAL_RECOMPRA_DIAS` | 180 | Selección del producto de recompra | #7 |
| `MIN_COMPRAS_PRODUCTO_RECOMPRA` | 3 | Umbral de "patrón" de recompra | #7 |
| `DESCUENTO_RECOMPRA_PCT` | 8,00 | Valor de la reserva de precio | #7 |
| `VENTANA_RESERVA_RECOMPRA_DIAS` | 21 | Vigencia de la reserva de precio | #7 |
| `SEMILLA_ALEATORIZACION` | 20260905 | Asignación de grupos del experimento | #9 |
| `PROPORCION_TRATAMIENTO` | 0,5 | Reparto tratamiento/control | #9 |
| `ALFA_SIGNIFICANCIA` | 0,05 | Prueba z de dos proporciones | #10a |
| `PODER_ESTADISTICO` | 0,80 | Cálculo del tamaño mínimo de muestra | #10b |
| `TASA_RETORNO_BASE_ESPERADA` | 0,15 | Cálculo del tamaño mínimo de muestra (`p_c`) | #10b |
| `MDE_REACTIVACION_PP` | 15 | Cálculo del tamaño mínimo de muestra (efecto mínimo detectable) | #10b |
| `DESCUENTO_REACTIVACION_PCT` | 15,00 | Valor del descuento de reactivación | #10b |
| `VENTANA_MEDICION_REACTIVACION_DIAS` | 42 | Ventana de observación del retorno | #11 |

Todos son parámetros de **calibración dentro de las decisiones ya fijadas** (reserva de precio,
prueba z, aleatorización con semilla): ajustarlos no reabre FR-010 ni FR-021. Los que tienen
carácter de **política de negocio** (`MDE_REACTIVACION_PP`, `TASA_RETORNO_BASE_ESPERADA`, los tres
`DESCUENTO_*_PCT`) se confirman con el dueño del comercio y se re-estiman con datos reales tras el
primer experimento.

---

## 14. Convención de endpoints

**Decisión**: se reutiliza la convención de `001`–`004` — sustantivos, `kebab-case`, acciones
no-CRUD como subrecurso, un prefijo `/promociones` para todo el módulo:

- `POST /promociones/cupones/generacion` — genera los cupones de un rango de fechas (idempotente).
- `GET /promociones/cupones?id_cliente=&estado=&vigentes=` — lista cupones (`estado` filtra por
  `cupon.estado`: `generado` / `redimido` / `vencido`).
- `POST /promociones/ofertas-recompra/deteccion` — detecta y propone ofertas para una sucursal.
- `GET /promociones/ofertas-recompra?id_cliente=&desenlace=` — lista ofertas (`desenlace` es el
  campo real de `oferta_recompra`: `pendiente` / `comprado` / `no_comprado` / `reserva_vencida`;
  `estado_reserva` no se expone como filtro).
- `POST /promociones/experimentos` — crea un experimento de reactivación (asigna grupos, o marca
  `muestra_insuficiente`); `400` por parámetros inválidos, `409` si ya hay uno `en_curso`.
- `GET /promociones/experimentos/{id_experimento_reactivacion}` — detalle con tasas y prueba z.
- `GET /promociones/experimentos/{id_experimento_reactivacion}/asignaciones` — asignaciones por
  cliente (auditoría, SC-007).
- `POST /promociones/experimentos/{id_experimento_reactivacion}/cierre` — cierra la ventana,
  calcula retorno + prueba z + veredicto.
- `POST /promociones/redenciones` — registra una redención vinculada a una venta (idempotente).
  Construido con el **mecanismo 1** (US1) y **reutilizado** por los otros dos y por la marca de
  `004`, sin una tabla ni una ruta por mecanismo (ver #4).
- `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` — la marca agregada que `004` consume
  (única aportación propia de US4).
- **No se expone ninguna ruta de lectura de campañas**: `campania` es agrupación interna, alcanzada
  por el `id_campania` de sus mecanismos hijos (Assumption en spec.md).

**Razón**: consistencia con el contrato ya publicado; no hay ninguna razón de este dominio para
desviarse. Formato de error `{codigo, mensaje}` unificado en `001`–`004` (nunca `{detalle}`).

---

## 15. Estado de dependencias (verificado contra el repositorio)

Ver plan.md, "Estado de implementación por historia". Resumen: **`002` está completo** (checkpoint
`2fd6381`), **`001` User Story 1 está completa** (checkpoint `873228d`), y **`004` está completo**
(`41ad08c`) y ya espera la marca de `005`. Todas las lecturas que `005` necesita están disponibles.
La nota cautelar del checklist del spec ("`002` User Story 3 aún no implementada") era incorrecta y
queda corregida en el plan: `senal_fuga`, `evaluar_fugas_pendientes` y `GET /clientes/cumpleanos`
están entregados. **Ninguna historia de `005` está bloqueada.**
