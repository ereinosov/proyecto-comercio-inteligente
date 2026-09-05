# Research: Pronóstico de Demanda

**Fase 0** · 2026-09-05 · Plan: [plan.md](./plan.md)

Los tres `NEEDS CLARIFICATION` del borrador de `spec.md` (FR-009 método de censura, FR-019
horizonte/granularidad, FR-020 familia de método) se resolvieron en la sesión de clarificación del
2026-09-05 (ver `## Clarifications` en spec.md). Este documento fija los **parámetros** que esas
clarificaciones dejaron explícitamente "calibrables aquí" (N y α) y resuelve las decisiones de
diseño que el plan debía tomar por su cuenta.

---

## 1. Reutilización íntegra del stack de `001`/`002`/`003`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + TS + Vite, sin librería de componentes de terceros) que `001`/`002`/`003`,
sobre la misma base PostgreSQL 16 (puerto 5442).

**Razón**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función que
una ya presente, salvo justificación registrada. Ninguna característica de este módulo exige un
lenguaje, framework o motor distinto. La única tentación real —una librería de series temporales—
se descarta por separado en #7.

**Alternativas descartadas**: ninguna evaluada seriamente para el stack base.

---

## 2. Propiedad de datos: revisión completa de la entrada de `004` y enmienda v2.2.4 antes de diseñar el esquema

**Decisión**: antes de escribir `data-model.md`, se revisó la entrada **completa** de
`004-pronostico-demanda` en la tabla de "Propiedad de Datos y Nomenclatura" de la constitución
—no sólo se asumió que faltaba `sustitucion_producto`— y se corrigió por enmienda **v2.2.4**.

**Lo que la revisión encontró**:

- `demanda_observada`, `demanda_corregida` y `pronostico` (las tres entradas originales) **no
  contradicen ninguna frontera** declarada en la sección. A diferencia de `003` —donde v2.2.3
  detectó que `costo_producto` chocaba con la frontera "el costo pertenece a 001" dos líneas más
  abajo, y que faltaba `sugerencia_precio`—, aquí las tres son artefactos analíticos derivados
  (serie de ventas agregada y anotada; serie corregida por reglas de negocio; proyección),
  coherentes con la misma lógica que asigna `margen_calculado` a `003`: *el cálculo derivado con
  reglas de negocio pertenece al módulo que lo produce, no al dueño del dato de origen*. Se añadió
  además una viñeta de frontera explícita ("demanda observada = dato de ventas de 001; serie
  corregida y pronóstico = cálculo de 004") para dejarlo tan claro como la viñeta costo/margen.
- **Faltaba `sustitucion_producto`**: la relación declarada manualmente entre dos productos que el
  spec exige en FR-032 y User Story 6, y —tras `/speckit-clarify`— también en FR-009 (b), donde el
  ajuste cruzado de la descensura la consulta. La lista original se escribió antes de que
  existiera el spec de `004` (igual que pasó con `001` en v2.1.1/v2.1.2 y con `003` en v2.2.3).
- **Desliz de sincronización de v2.2.3**: el pie de `constitution.md` había quedado en
  "Versión: 2.2.2" cuando v2.2.3 ya regía en el cuerpo y en el informe de impacto. La enmienda
  v2.2.4 lo lleva a 2.2.4 y sincroniza las citas de "versión vigente" en los artefactos de `001`,
  `002` y `003` (las citas históricas —"la enmienda v2.2.3 que añadió `sugerencia_precio`"— no se
  barren, por la excepción explícita de la Puerta de sincronización de enmiendas).

**Entrada corregida de `004`**: `demanda_observada`, `demanda_corregida`, `pronostico`,
`sustitucion_producto` — cuatro entidades (antes tres).

**Razón del patrón `sustitucion_producto` como tabla propia y no como atributo de `producto`**:
idéntica a la de `rol_producto` en `003` (research.md #3 de `003`). La constitución prohíbe alterar
el esquema de una entidad ajena; `producto` es de `001`. Una tabla propia de `004` con dos FK hacia
`producto` (`id_producto`, `id_producto_sustituto`) logra el mismo resultado observable sin tocar
el esquema ajeno.

**Alternativas descartadas**: asumir que la tabla ya estaba bien y sólo añadir
`sustitucion_producto` sin revisar el resto — rechazada porque la Puerta de propiedad de datos
exige contrastar la entrada completa, y porque es exactamente el atajo que habría dejado pasar el
error de `costo_producto` en `003`; modelar la sustitución como una columna `id_sustituto` en
`producto` — rechazada por alterar esquema ajeno; no declarar `sustitucion_producto` y guardar las
parejas en un `JSONB` dentro de otra tabla de `004` — rechazada porque FR-032 la trata como una
entidad con su propio ciclo de vida (declarar, consultar) y FR-009 (b) la consulta por clave.

---

## 3. `demanda_observada` y `demanda_corregida`: tablas materializadas por recompute-on-read sobre ventana acotada

**Decisión**: ambas son tablas reales, con grano **día local de la sucursal**, una fila por
`(id_producto, id_sucursal, fecha_local)`. Se **materializan por upsert** cuando se solicita la
serie o el pronóstico de un producto, sobre la **ventana de días relevante** (por defecto los
últimos 90 días locales, parámetro) — no por disparador de base de datos ni por tarea de fondo
periódica. Igual patrón que `margen_calculado` de `003` (research.md #4 de `003`), con la misma
precisión sobre el volumen: la vista de una sucursal completa se resuelve con **una** consulta de
conjunto, nunca con un bucle que llame N veces al reconstructor de un solo producto (el patrón N+1
que `003` corrigió).

**Por qué tablas y no una vista sobre `venta`/`renglon_venta`**:

- FR-002 y FR-003 exigen anotar cada período con datos que hay que **congelar** con él: si tuvo
  quiebre de stock y su extensión, el precio vigente de ese período, y si hubo promoción activa.
  Una vista pura recalcularía esas anotaciones cada vez y no dejaría dónde registrar la
  procedencia de una corrección (FR-010).
- FR-004 dice que `demanda_observada` es "un registro de hechos y NO DEBE modificarse
  retroactivamente". Una tabla materializada con las anotaciones congeladas cumple esto; el
  recompute-on-read sólo rellena períodos aún no materializados o cuya ventana de origen cambió,
  no reescribe la historia ya fijada salvo corrección explícita.
- La constitución **lista** `demanda_observada` y `demanda_corregida` como entidades propias de
  `004` (a diferencia de "valor de cliente" de `002`, que nunca apareció en la tabla y por eso se
  dejó como consulta derivada). El mismo argumento que usó `003` para `margen_calculado`.

**Por qué recompute-on-read y no tarea de fondo**: los insumos (ventas nuevas, movimientos de
inventario, un período que se marca de promoción) ocurren por eventos de `001`/`005`, no de `004`.
Un disparador sobre tablas ajenas escondería el flujo de control fuera del código (misma razón por
la que `002` rechazó disparadores para `existencia`, research.md #6 de `002`, y `003` para
`margen_calculado`). Una tarea de fondo periódica podría servir un pronóstico obsoleto entre
ejecuciones. La ventana es **acotada** (≤ 90 días diarios por producto/sucursal — el pronóstico no
necesita años de historia), así que recalcularla en cada lectura es trivial a esta escala
(cientos de productos, dos sucursales).

**Tratamiento de la venta anulada** (decidido aquí, no cubierto por el spec): la demanda observada
de un período cuenta la cantidad neta que **salió y no volvió** — los movimientos `salida_venta`
menos los `entrada_anulacion` del mismo producto/sucursal/período. Una venta anulada no es demanda
satisfecha (la mercancía volvió al lote). Es la lectura más simple y defendible; si más adelante
se quisiera tratar la anulación como demanda real "que existió aunque se revirtió", sería una
enmienda de este spec, no una decisión libre de implementación.

**Orden fijo de aplicación de correcciones sobre `demanda_corregida`** (ya en Assumptions del
spec): (1) quiebre de stock → (2) precio → (3) promoción → (4) señal de sustitución. La descensura
por quiebre es la base sobre la que operan las demás; cada corrección posterior parte del valor
que dejó la anterior y registra su propio delta (FR-010).

**Alternativas descartadas**: vista SQL pura — rechazada por lo anterior (no hay dónde congelar
anotaciones ni procedencia); materialización total de toda la historia por tarea nocturna —
rechazada por servir datos obsoletos entre corridas y por no tener el spec una ventana de
tolerancia declarada (a diferencia de la anonimización de `002`, que sí la tiene); recompute por
bucle de un producto a la vez para el listado de sucursal — rechazada por el N+1 ya explicado.

---

## 4. Servicio de reconstrucción de serie: una función de conjunto, correcciones en orden

**Decisión**: `servicios/demanda.reconstruir_serie(sesion, *, id_sucursal, id_producto=None,
desde, hasta)` reconstruye y materializa la ventana pedida. Con `id_producto=None` resuelve la
sucursal completa en una sola consulta de conjunto (para la pantalla de listado). Internamente:

1. Agrega `movimiento_inventario` de tipo `salida_venta`/`entrada_anulacion` por día local
   (`AT TIME ZONE sucursal.zona_horaria`) → cantidad observada por período.
2. Reconstruye el saldo de existencia día a día replayando `movimiento_inventario` ordenado por
   `instante` (la tabla `existencia` de `001` es "derivada, no autoritativa" — ante discrepancia
   gana la recomputación desde movimientos, según el propio `data-model.md` de `001`) → marca de
   quiebre y su extensión por período (FR-002, FR-005).
3. Reconstruye el precio vigente por período de `renglon_venta.precio_aplicado` (#8).
4. Marca de promoción por período: de `005` cuando exista; hoy, siempre "sin promoción" (FR-030).
5. `upsert` masivo sobre `demanda_observada`.
6. Deriva `demanda_corregida` aplicando las cuatro correcciones en orden (#3) y `upsert` masivo.

**Razón**: una sola responsabilidad por función, una sola consulta de conjunto por
sucursal-ventana, y el orden de correcciones explícito en un único lugar auditable.

**Alternativas descartadas**: reutilizar el reconstructor de un producto en un bucle para el
listado (N+1); calcular la serie corregida en el frontend a partir de la observada (duplicaría la
lógica de negocio en TypeScript y la sacaría del alcance de las pruebas obligatorias de Python).

---

## 5. Método base de descensura por quiebre (FR-009 a) y el parámetro **N**

**Decisión**: para un período con quiebre de stock, la demanda corregida por este eje es el
**máximo** de la demanda observada del mismo producto y sucursal entre los **N períodos diarios
más recientes sin quiebre** (previos al inicio del intervalo de quiebre). Aritmética simple, sin
estimadores de máxima verosimilitud ni supuestos de distribución.

**Valor por defecto de N: 30 días** (parámetro de configuración, calibrable en implementación
contra la serie sintética de la User Story 2; su valor exacto es una decisión de `tasks.md`/código
dentro de este método ya fijado, no una reapertura de FR-009).

**Por qué 30 y no otro número**:

- **Cubre cuatro ciclos semanales completos.** La demanda de un minimarket tiene un patrón
  semanal fuerte (fines de semana ≠ martes). Con N = 30 la ventana contiene ~4 muestras de cada
  día de la semana, así que el máximo de la ventana captura el pico semanal real (p. ej. el
  sábado) sin depender de un único sábado que pudo ser atípico.
- **Una ventana más corta (7–14) es frágil.** Con 7 días hay una sola muestra por día de la
  semana: el máximo queda a merced de un único día raro (una fiesta local, un pedido mayorista
  puntual) y además puede **no** contener el día de mayor demanda si el quiebre empezó justo
  después de él.
- **Una ventana más larga (60–90) arrastra nivel obsoleto.** A 60–90 días la ventana incorpora
  demanda de antes de un cambio de precio, de surtido o de temporada reciente, y el máximo se
  ancla a un nivel que ya no aplica — justo lo contrario de la reactividad que el pronóstico
  necesita.
- **Coincide con el horizonte medio del pronóstico (FR-019, 30 días).** La ventana de "lo normal
  reciente" y la ventana de patrón intramensual del pronóstico son la misma, lo que hace el
  sistema más fácil de explicar: un solo número gobierna "cuánto pasado es relevante".

**Por qué el máximo y no la media o un percentil**: durante el quiebre la demanda latente es
inobservable. El objetivo declarado del módulo es **dejar de pedir de menos** ("sistemáticamente
pedirá de menos" es el fallo a evitar, spec). El máximo de los días normales recientes es un
estimador que (a) garantiza `corregida ≥ observada` (FR-006) por construcción y (b) yerra hacia no
subcorregir. Que no **sobrecorrija** sistemáticamente es precisamente lo que la validación
sintética de la User Story 2 comprueba (SC-002): si el máximo resultara demasiado agresivo en la
práctica, el ajuste es bajar de "máximo" a "percentil 90 de la ventana", dentro del mismo método.

**Censura total** (FR-012): si no hay **ningún** período sin quiebre en el histórico disponible y
tampoco hay `consulta_no_atendida`, no hay ventana de la cual tomar el máximo → estado "no
estimable por censura total", nunca cero.

**Alternativas descartadas**: imputación por tasa de venta previa al quiebre (ventas/hora de los
días inmediatamente anteriores, extrapolada a los días de quiebre) — rechazada porque la sesión
de `/speckit-clarify` ya fijó el método base como "máximo de N períodos recientes sin quiebre", no
como tasa horaria; regresión de Poisson censurada o modelo de supervivencia — rechazados por
`/speckit-clarify` (exigen librería estadística y supuestos de distribución, contra Principio I y
Principio V "explicable"); media de la ventana en vez del máximo — más conservadora pero
subcorrige por diseño, justo el sesgo a eliminar.

---

## 6. Ajuste cruzado por sustituto (FR-009 b)

**Decisión**: si el producto en quiebre `P` tiene uno o más sustitutos declarados en
`sustitucion_producto` (con `P` como `id_producto`), y un sustituto `S` registró durante el
intervalo de quiebre de `P` una demanda observada **por encima de su propia línea típica** (el
mismo máximo-de-N de #5 aplicado a `S`), entonces:

```
exceso_S            = max(0, demanda_observada_S_en_ventana_de_quiebre − maximo_N_de_S)
estimado_cruzado_P  = estimado_base_P + Σ_S exceso_S          (suma sobre todos los sustitutos de P)
demanda_corregida_P = estimado_cruzado_P                       (complementa el base, no lo reemplaza)
```

**Política de atribución por defecto: 100 % del exceso del sustituto** se atribuye a `P` (el
cliente que no pudo comprar `P` y compró `S` en su lugar). Es la atribución más simple y
defendible; su magnitud es un parámetro calibrable (como N y α). El spec prohíbe cuantificar la
canibalización "con precisión estadística" (FR-034, referido a la **señal** de User Story 6) —
esto es distinto: es el ajuste **de la descensura** (User Story 1, tratamiento profundo), no la
señal cualitativa de User Story 6, y sigue siendo aritmética de una línea.

**Por qué complementar y no reemplazar**: FR-009 (b) es explícito ("ajustar el estimado del método
base al alza, complementándolo, nunca reemplazándolo"). El método base ya captura la demanda
"normal" de `P`; el exceso del sustituto captura la porción **adicional** que se desvió por el
quiebre. Reemplazar perdería la demanda base de `P`.

**Interacción con User Story 6**: la señal de sustitución de FR-033 (marca cualitativa "demanda de
`S` potencialmente inflada por el quiebre de `P`") y este ajuste usan la **misma** relación
`sustitucion_producto` y la misma noción de "por encima de lo típico". La señal se anota en la
serie de `S`; el ajuste se aplica a la serie corregida de `P`. No se descuenta el exceso de la
serie de `S` (FR-034 lo prohíbe) — sólo se **marca** en `S` y se **suma** en `P`.

**Nivel (b) es opcional**: si `P` no tiene sustitutos declarados, `demanda_corregida_P` =
`estimado_base_P`. La ausencia de User Story 6 no bloquea User Story 1 (FR-009, plan.md "Estado de
implementación por historia").

**Alternativas descartadas**: atribuir una fracción fija < 100 % sin base declarada (¿de dónde
sale 60 %?); estimar la fracción por regresión entre las series de `P` y `S` (cuantificación
estadística, prohibida y contra Principio V); descontar el exceso de la serie de `S` además de
sumarlo en `P` (FR-034 lo prohíbe: la señal en `S` es cualitativa).

---

## 7. Familia de método de pronóstico (FR-020): suavizado exponencial simple, sin librería

**Decisión**: el pronóstico se calcula con **suavizado exponencial simple** (SES) sobre la serie
ya corregida por censura:

```
nivel_t     = α · demanda_corregida_t + (1 − α) · nivel_{t−1}
pronostico_{t+k} = nivel_t · multiplicador_de_tramo(t + k)        (para todo k en el horizonte)
```

El `multiplicador_de_tramo` viene de #8b. Todo se implementa en Python de biblioteca estándar y
SQL de agregación — **ninguna librería de series temporales** (statsmodels, Prophet,
scikit-learn, pmdarima).

**Razón**: la sesión de `/speckit-clarify` ya fijó "suavizado exponencial simple — no promedio
móvil plano, no ARIMA/Prophet/ML". El Principio I prohíbe una segunda tecnología para la misma
función salvo justificación registrada, y el Principio V exige que "una recomendación que el
encargado no puede justificar ante su gerente no se despliega": la recurrencia de SES es una línea
de aritmética, con un único parámetro (α) cuyo efecto se explica en una frase. Una librería de
ARIMA o Prophet metería decenas de parámetros y supuestos que nadie en el equipo puede defender
línea por línea, además de ser la "segunda tecnología" que el Principio I señala.

**Alternativas descartadas**: promedio móvil plano — es exactamente la **línea base determinista**
de FR-022 (research.md #8c), así que usarlo como método de pronóstico dejaría al módulo sin nada
que superar a su propia línea base; ARIMA / suavizado exponencial de Holt-Winters con
estacionalidad / Prophet / modelos ML — rechazados por `/speckit-clarify` y por Principio I + V;
suavizado exponencial doble (con tendencia) — no lo pide el spec y añade un segundo parámetro (β)
sin necesidad demostrada para un minimarket de barrio.

### El parámetro **α**

**Valor por defecto: α = 0,3** (parámetro de configuración, calibrable contra la línea base y la
serie sintética; su valor exacto es decisión de código dentro del método ya fijado).

**Por qué 0,3**:

- Con α = 0,3 el peso de una observación de hace `k` días es `0,3 · 0,7^k`. El peso acumulado de
  los últimos 7 días es `1 − 0,7^7 ≈ 0,92`: **el 92 % del pronóstico lo determina la última
  semana**. Es reactivo — un cambio real de nivel se refleja en pocos días — sin ser volátil.
- Un solo día atípico mueve el pronóstico en `0,3 ·` su desviación: ~30 %. Suficiente para no
  ignorar una señal real, poco para no perseguir ruido en una decisión de compra.
- **α = 0,5** dejaría que un único día raro moviera el pronóstico la mitad de su error — demasiado
  nervioso para pedir stock.
- **α = 0,1** tarda ~22 días (`0,9^k < 0,1` ⇒ `k ≈ 22`) en reflejar a la mitad un cambio de nivel
  real — demasiado lento cuando el surtido de un minimarket rota.
- 0,3 favorece la **reactividad a la demanda reciente** sobre la estabilidad, que es lo correcto
  cuando la serie ya viene descensurada (el ruido grande —los quiebres— ya se corrigió aguas
  arriba) y las decisiones son de reposición a días vista.

**Calibración**: se compara el error de SES(α) contra el de la línea base (FR-022) sobre la
historia disponible y sobre la serie sintética; se elige el α del conjunto {0,1, 0,2, 0,3, 0,4,
0,5} con menor error, con 0,3 como valor de arranque si no hay diferencia clara.

---

## 8. Los tres ejes que operan sobre la serie corregida

### 8a. Detección de intervalo de quiebre (FR-005)

**Decisión**: un día local cuenta como "en quiebre" para `(producto, sucursal)` **sólo si el saldo
de existencia reconstruido desde `movimiento_inventario` se mantuvo ≤ 0 durante TODO el día**. El
saldo se reconstruye por suma de deltas ordenada por `instante` (nunca se lee `existencia`, que no
es autoritativa — `data-model.md` de `001`); como el saldo sólo sube con entradas, el máximo
alcanzado en el día es `max(saldo al inicio del día, saldo tras cada movimiento del día)`, y basta
comprobar que ese máximo sea ≤ 0.

**Por qué el día completo y no "≤ 0 en algún momento"**: la granularidad de la serie ya está fijada
en diaria (FR-019, `/speckit-clarify`). Un día en el que el producto se agotó a media jornada
todavía tuvo capacidad de venta el resto, y descensurarlo inflaría la demanda corregida por horas
que sí vendieron. Representar quiebres **parciales** ("agotado 6 de 10 horas") exigiría una unidad
de tiempo más fina que el día — fuera del alcance de esta versión. Es una decisión conservadora a
propósito: sólo se corrige lo que el spec llama "no tuvo existencia durante X días". En el código
es la constante nombrada `SALDO_MAXIMO_EN_QUIEBRE` (`dominio/serie_demanda.py`); también quedó en
Assumptions de `spec.md` para no depender de la nota del código durante la defensa oral.

Con período base diario, `dias_en_quiebre` de FR-002 es por tanto 0 ó 1 por período; la fórmula
proporcional del método base se deja escrita para no romperse si el grano cambia en el futuro.

### 8b. Precio vigente por período (FR-003, FR-025 a FR-028) — sin dependencia de histórico de precio

**Decisión**: el precio vigente de un producto en un período histórico se reconstruye del
**`renglon_venta.precio_aplicado`** de `001`, que es un valor **copiado en cada venta** ("para que
la venta siga siendo reconstruible si el precio cambia", `data-model.md` de `001`). Por período se
toma el precio aplicado más frecuente (moda; media ponderada por cantidad como desempate).

- **`001` NO conserva un histórico de precio** (`producto.precio_vigente` y
  `producto_precio_sucursal.precio_vigente` son valores actuales, sin validez temporal). Pero **no
  hace falta**: `renglon_venta.precio_aplicado` ya lleva el precio de cada transacción histórica.
- Un período **sin ventas** no tiene precio reconstruible → se marca "sin corrección de precio"
  (FR-027), nunca se asume un precio retroactivo. Un período de quiebre no tiene ventas y su
  demanda ya se estima por #5 de todos modos.
- **Precio de referencia** hacia el que se normaliza (FR-025): el precio vigente **actual** del
  producto en la sucursal (`COALESCE(producto_precio_sucursal, producto.precio_vigente)`, la misma
  resolución que usa `001` al vender). El pronóstico responde a "cuánta demanda esperar al precio
  de hoy" (Assumptions del spec).
- **Normalización** (FR-025): para un período cuyo precio reconstruido `p_hist` difiere del precio
  de referencia `p_ref`, la demanda del período se ajusta por un factor de elasticidad simple
  `(p_hist / p_ref) ^ ε`, con `ε` (elasticidad-precio) como parámetro por defecto `ε = 1`
  (elasticidad unitaria: subir el precio un 10 % reduce la demanda ~10 %). `ε` es calibrable como
  N y α; documentado explícito para no esconder el supuesto. El efecto aplicado se registra (qué
  `p_hist`, qué `p_ref`, qué `ε`) para explicabilidad (FR-028).
- **Observaciones de competencia** (`observacion_precio`/`canal_competencia`): son un insumo de
  **contexto** para interpretar un cambio de demanda, no una entrada del cálculo de descensura.
  `001` User Story 4 (captura de competencia) tampoco está implementada; cuando lo esté, la vista
  de análisis puede mostrar la observación junto al período. No es un bloqueo (plan.md "Estado de
  implementación por historia").

### 8c. Línea base determinista (FR-022)

**Decisión**: la línea base es el **promedio móvil simple de la demanda observada sin corregir**
sobre la misma ventana N (#5). Es determinista, no usa la serie corregida y no usa α. Un
`pronostico` sólo se marca `vigente = TRUE` si su error retrospectivo (sobre los últimos días con
dato real) es **menor** que el de la línea base para el mismo tramo (SC-004). Si no lo supera, la
respuesta del endpoint devuelve el pronóstico calculado pero con `vigente = FALSE` y
`motivo_no_vigente = "no supera la linea base"`, y la interfaz muestra la línea base.

### 8d. Estacionalidad intramensual (FR-019, horizonte medio de 30 días)

**Decisión**: el mes se parte en **tramos fijos** y se calcula, por tramo, un multiplicador =
(media de la demanda corregida del producto en ese tramo, sobre el histórico) / (media global del
producto). El pronóstico a 30 días = `nivel_t` (SES) × multiplicador del tramo de cada día futuro.
**No** hay descomposición estacional formal, ni estacionalidad anual, ni festiva (límite
documentado, Assumptions del spec).

Tramos por defecto (parámetro): `[1–7]`, `[8–15]`, `[16–22]`, `[23–fin de mes]`, con marca
adicional de **quincena** para los días 14–16 y 29–31/1–2 (donde el enunciado sitúa los picos de
pago de sueldo). Un tramo con menos de un mínimo de observaciones históricas usa multiplicador
1,0 (sin ajuste) y se marca como tal.

**Alternativas descartadas**: descomposición STL / medias móviles centradas para aislar
estacionalidad — es "descomposición estacional formal", excluida por `/speckit-clarify`;
multiplicador por día del mes individual (1–31) — sobreajusta con el histórico corto de un
minimarket; ignorar la estacionalidad intramensual — contradice FR-019, que la pide explícitamente
para el horizonte medio.

---

## 9. Datos sintéticos con demanda latente conocida (FR-013 a FR-017, User Story 2)

**Decisión**: los datos sintéticos viven en las **mismas tablas** (`demanda_observada`,
`demanda_corregida`) para ejercer exactamente el mismo código de descensura, distinguidos por:

- una columna `es_sintetico BOOLEAN NOT NULL DEFAULT FALSE` en `demanda_observada` y
  `demanda_corregida`;
- una columna `demanda_latente_verdadera NUMERIC(14,4) NULL` en `demanda_observada`, poblada
  **sólo** para las filas sintéticas de períodos de quiebre (NULL en todo dato real y en períodos
  sintéticos sin quiebre).

`servicios/demanda_sintetica.cargar_serie(...)` inserta la serie generada (con su demanda latente
verdadera). `servicios/demanda_sintetica.reporte_error_descensura(...)` compara, para las filas
sintéticas, `demanda_corregida.valor` contra `demanda_observada.demanda_latente_verdadera` y
devuelve el error por período y el agregado, junto al mismo error calculado para
`demanda_observada.cantidad` (la referencia "no corregir nada") — que es lo que SC-002 exige
comparar.

**Aislamiento sintético/real** (FR-017): toda consulta de pronóstico de producción añade
`WHERE es_sintetico = FALSE` en la capa de servicio, y `servicios/pronostico.generar_pronostico`
rechaza con error explícito si se le pide un pronóstico "de producción" sobre un producto que sólo
tiene filas sintéticas. La prueba de contrato del arnés verifica que ninguna respuesta de
`GET /pronostico` incluye filas sintéticas.

**Generación de la serie sintética**: un guion de utilidad (`tests/` o `scripts/`, no en el
paquete de producción) produce una serie con: un nivel base, un patrón semanal, uno o más
intervalos de quiebre con demanda latente verdadera fijada, y —para el escenario de FR-016— un
conjunto de `consulta_no_atendida` sintéticas consistentes con esa demanda latente. Los datos
sintéticos **no** pertenecen a "Despensa Los Ríos" ni se cargan en el entorno de producción
(constitución: separación herramienta/datos).

**Alternativas descartadas**: tablas sintéticas separadas (`demanda_observada_sintetica`, …) —
duplican el esquema y arriesgan que el código de descensura de producción y el de validación
diverjan, que es justo lo que la validación existe para evitar; una base de datos aparte para
sintéticos — sobreingeniería para dos columnas discriminadoras; generar los sintéticos al vuelo
en cada prueba sin persistirlos — impide que `ValidacionDescensura.tsx` muestre el reporte y que
el error sea inspeccionable fuera de la corrida de pytest.

---

## 10. "Histórico suficiente" para pronosticar y "nivel típico" de un sustituto

**Decisión**:

- **"Nivel típico"** de un producto (para FR-033 y para el `maximo_N` de #5/#6): el máximo de la
  demanda observada entre sus N períodos recientes sin quiebre. Una sola definición, reutilizada
  en los tres sitios que la necesitan — coherencia y una cosa menos que explicar.
- **"Histórico suficiente"** para emitir un `pronostico` numérico (FR-023): al menos **N** períodos
  diarios con demanda observada registrada, de los cuales al menos **14** sin quiebre. Por debajo
  de ese umbral → estado "datos insuficientes", nunca un número. Un producto nuevo cae aquí por
  construcción.
- Ambos umbrales (N; el 14; el mínimo de observaciones por tramo de #8d) son parámetros de
  configuración calibrables, no constantes ocultas en el código (Principio V "acotada": los
  límites del modelo se documentan antes de implementar).

**Razón**: el spec (Assumptions) delega estos umbrales concretos a esta fase "dentro del método ya
fijado". Anclarlos todos a la misma N que gobierna la descensura y el pronóstico mantiene el
sistema explicable con un solo número rector.

---

## 11. Convención de endpoints

**Decisión**: se reutiliza la convención de `001`/`002`/`003` — sustantivos, `kebab-case`, vista
específica de un producto anidada bajo `/productos/{id_producto}`, acciones no-CRUD como
subrecurso:

- `GET /demanda?id_sucursal=&id_producto=&desde=&hasta=` — serie observada + corregida de un
  producto (o de la sucursal completa si se omite `id_producto`), con las anotaciones por período.
- `GET /productos/{id_producto}/pronostico?id_sucursal=&horizonte=corto|medio` — genera (append) y
  devuelve el pronóstico, con factores, período de datos, línea base y `vigente`.
- `GET /productos/{id_producto}/pronostico?solo_ultimo=true` — última generación sin crear otra
  (mismo patrón que `sugerencia-precio` de `003`).
- `GET /sustituciones` / `POST /sustituciones` / `DELETE /sustituciones/{id_sustitucion_producto}`
  — declarar y consultar relaciones (FR-032).
- `POST /demanda-sintetica` — cargar una serie sintética (FR-013).
- `GET /demanda-sintetica/validacion?id_sucursal=&id_producto=` — reporte de error de descensura
  (FR-014, FR-015).

**Razón**: consistencia con el contrato ya publicado; no hay ninguna razón de este dominio para
desviarse.

---

## Parámetros de configuración fijados en esta fase (resumen)

| Parámetro | Valor por defecto | Dónde se usa | Justificación |
|---|---|---|---|
| `N` | **30 días** | Método base de descensura (#5), `maximo_N` de sustituto (#6), ventana de línea base (#8c), umbral de histórico suficiente (#10) | Cubre 4 ciclos semanales; más corto es frágil ante días atípicos, más largo arrastra nivel obsoleto; coincide con el horizonte medio del pronóstico |
| `α` | **0,3** | Suavizado exponencial simple (#7) | 92 % del pronóstico lo fija la última semana: reactivo sin ser volátil; 0,5 persigue ruido, 0,1 tarda ~3 semanas en seguir un cambio real |
| `ε` (elasticidad-precio) | **1,0** | Normalización del eje de precio (#8b) | Elasticidad unitaria como supuesto neutro y explícito; calibrable; se registra en cada corrección |
| Ventana de materialización | **90 días** | recompute-on-read (#3) | El pronóstico no necesita más historia; acota el coste de recalcular en cada lectura |
| Tramos del mes | `[1–7] [8–15] [16–22] [23–fin]` + marca de quincena | Estacionalidad intramensual (#8d) | Capta picos de quincena/pago sin sobreajustar con histórico corto |
| Mínimo sin quiebre para pronosticar | **14 períodos** | Umbral "datos insuficientes" (#10) | Media quincena de demanda observable real antes de arriesgar un número |

Todos son parámetros de configuración con estos valores de arranque; ajustarlos es una decisión
de calibración **dentro** de los métodos ya fijados por `/speckit-clarify`, no una reapertura de
FR-009, FR-019 o FR-020.
