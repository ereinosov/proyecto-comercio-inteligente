# Feature Specification: Promociones Inteligentes

**Feature Branch**: `005-promociones-inteligentes` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-05

**Status**: Draft

**Input**: Decidir, generar y medir promociones dirigidas a clientes, partiendo de una tesis del
enunciado: un descuento a un cliente inactivo puede recuperar valor real o simplemente canibalizar
margen que ya se iba a dar de todas formas — si el cliente habría vuelto igual, el descuento
destruye el margen que pretendía proteger. Por eso la decisión de aplicar (o no) la promoción de
reactivación DEBE basarse en un umbral estadístico de efecto incremental medido contra un grupo de
control, no en una regla fija arbitraria. El módulo cubre **tres** mecanismos de promoción
distintos, con lógica y exigencias diferentes, que la constitución (Lectura Crítica n.º 6) prohíbe
tratar como una sola entidad genérica: (1) **cupón por fecha fija** (cumpleaños), regla simple sin
inferencia ni medición; (2) **empuje por patrón de recompra con reserva de precio**, que ofrece
proactivamente a un cliente en su intervalo de compra esperado un producto que suele recomprar, con
un código que le garantiza el precio (no el stock) dentro de una ventana; (3) **reactivación de
cliente inactivo**, el único de los tres que exige grupo de control e incrementalidad. Este módulo consulta, sin reimplementar, la detección de fuga
silenciosa y el intervalo de compra esperado de `002-clientes-fidelizacion`, la fecha de nacimiento
del cliente de `002` (a través de la consulta de cumpleañeros que `002` ya expone), y el historial
de compras y los contratos de venta de `001-core-ventas-inventario`; posee los cupones, las ofertas
de recompra, los experimentos de reactivación (grupo asignado, resultado de retorno, semilla usada)
y el registro de redenciones. La generación de promociones es consultiva: el sistema propone y
mide; la persona decide y ejecuta (Principio V de la constitución).

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-05

- Q: ¿Cuál es el mecanismo exacto de la "reserva" en el empuje por recompra (FR-010) — apartado
  temporal de unidades físicas del stock de `001`, compromiso de precio sin afectar la existencia, o
  marca consultiva de producto pre-asignado? → A: **Reserva de precio, no de inventario**. El sistema
  emite un código o registro que garantiza el precio ofertado si el cliente vuelve a comprar dentro
  de la ventana definida. No aparta stock físico ni escribe contra ninguna tabla de inventario de
  `001`. Si al momento de redimir no hay existencia suficiente, el cliente recibe el mismo
  tratamiento que cualquier comprador sin oferta activa: la reserva garantiza el precio, nunca la
  disponibilidad. Se descartó la reserva de inventario para mantener intacta la frontera "`005`
  consulta pero no reimplementa `001`" y seguir el patrón "sugiere, no aplica" ya establecido en
  FR-028 de `001` y usado en `003` (ver Assumptions).
- Q: ¿Cuál es el valor exacto del umbral mínimo de incrementalidad para considerar efectiva la
  promoción de reactivación (FR-021)? → A: El umbral es **estadístico, no un número fijo arbitrario**:
  la diferencia de proporciones entre el % de retorno del grupo tratamiento y el del grupo control
  debe ser **estadísticamente significativa mediante una prueba z de dos proporciones (p < 0,05)**
  para considerar la campaña efectiva. Limitación conocida y no bloqueante: la prueba pierde poder
  con muestras pequeñas por grupo; el tamaño mínimo de muestra recomendado se calcula y documenta en
  `plan.md`/`research.md` de `005` cuando se conozca el volumen real de clientes elegibles (ver
  Assumptions y FR-025). El **mecanismo** de la medición (grupo de control + aleatorización con
  semilla fija + comparación de tasas de retorno) ya estaba decidido y no se reabrió; esta
  resolución solo fija cómo se juzga la diferencia.

El resto de ambigüedades menores de redacción se resolvió con defaults documentados en la sección
**Assumptions**.

## User Scenarios & Testing *(mandatory)*

<!-- Historias ordenadas por dependencia real, no por número de mecanismo de promoción. El cupón por
fecha fija va primero porque es la regla más simple y establece la base compartida (registro de
envío, registro de redención, exposición de la marca de promoción activa) que los otros dos
mecanismos reutilizan. El empuje por recompra va segundo: añade detección de patrón pero sigue sin
diseño experimental. La reactivación va última por ser el único mecanismo con grupo de control,
aleatorización y medición de incrementalidad — el más complejo y de mayor riesgo. La exposición de
la marca de promoción activa hacia `004` va al final porque se deriva de los registros que producen
los tres mecanismos anteriores. -->

### User Story 1 - Generar el cupón por fecha fija (cumpleaños) (Priority: P1)

El encargado consulta qué cupones de cumpleaños se generaron para el período próximo: cuando la
fecha de cumpleaños de un cliente registrado entra en la ventana de generación, el sistema emite un
cupón para ese cliente, con su ventana de validez y su estado. Es la regla más simple de las tres —
fecha llega, cupón se genera— y no requiere grupo de control ni medición de incrementalidad.

**Why this priority**: es el mecanismo más simple y el cimiento operativo del módulo. Establece las
piezas compartidas que los otros dos mecanismos reutilizan tal cual —el registro de que se emitió
una promoción a un cliente, el registro de que esa promoción se redimió en una venta de `001`, y la
marca de "promoción activa" que `004` consumirá—. Construir la reactivación (la más compleja) antes
de esta base obligaría a inventar esas piezas dos veces.

**Independent Test**: para un cliente con fecha de nacimiento conocida y una ventana de generación
que la cubre, se puede verificar que el sistema emite exactamente un cupón, con su ventana de
validez y su estado inicial, obtenido a través de la consulta de cumpleañeros de `002` (FR-012 de
`002`) y no por acceso directo a `cliente.fecha_nacimiento`; y que un cliente anonimizado (sin fecha
de nacimiento) no recibe cupón.

**Acceptance Scenarios**:

1. **Given** un cliente registrado cuya fecha de cumpleaños cae dentro de la ventana de generación,
   **When** el encargado consulta los cupones del período, **Then** el sistema muestra un cupón para
   ese cliente, con su motivo ("fecha fija — cumpleaños"), su ventana de validez y su estado
   "generado".
2. **Given** el mismo cliente y la misma fecha de cumpleaños ya procesada este año, **When** la
   generación se vuelve a ejecutar, **Then** el sistema NO emite un segundo cupón por la misma fecha
   objetivo del mismo cliente en el mismo año.
3. **Given** un cliente cuya fuga fue confirmada y sus datos personales ya fueron anonimizados por
   `002` (ya no tiene `fecha_nacimiento`), **When** se ejecuta la generación de cupones, **Then**
   ese cliente no aparece —`002` ya lo excluye de la consulta de cumpleañeros— y el sistema no
   genera un cupón "sin fecha".
4. **Given** un cupón generado y vigente, **When** el cliente lo usa en una venta registrada por
   `001`, **Then** el sistema registra la redención vinculada a esa venta y marca el cupón como
   "redimido", sin modificar la venta ni el precio (propiedad de `001`).
5. **Given** un cupón generado cuya ventana de validez vence sin uso, **When** vence, **Then** el
   sistema marca el cupón como "vencido" y no lo cuenta como redimido.

---

### User Story 2 - Empujar la recompra con reserva de precio a un cliente en su intervalo esperado (Priority: P2)

El encargado revisa las ofertas de recompra que el sistema propone: a un cliente cuyo tiempo desde
la última compra se acerca a su intervalo de compra esperado (derivado por `002` a partir de su
propio historial), el sistema le ofrece proactivamente un producto que ese cliente suele recomprar,
con una reserva de precio (un código que le garantiza el precio ofertado dentro de una ventana, sin
apartar stock). No requiere grupo de control.

**Why this priority**: añade detección de patrón sobre la base de la User Story 1 —qué producto
recompra el cliente, si el cliente está en su ventana de recompra—, pero sigue sin diseño
experimental: es una oferta dirigida, no una medición de efecto. Depende del registro de envío y
redención de la User Story 1 y del intervalo de compra esperado de `002`. Es más compleja que el
cupón por fecha fija y menos que la reactivación.

**Independent Test**: para un cliente con `intervalo_compra.estado = 'calculado'` en `002` y un
historial de compras con al menos un producto claramente recomprado, se puede verificar que, al
acercarse el cliente a su intervalo esperado, el sistema propone una oferta de ese producto con su
reserva de precio, sin escritura alguna contra el inventario de `001`; y que un cliente en
`datos_insuficientes` no recibe oferta.

**Acceptance Scenarios**:

1. **Given** un cliente con intervalo de compra esperado calculado por `002` y un producto que ha
   comprado repetidamente, **When** el tiempo desde su última compra se acerca a ese intervalo,
   **Then** el sistema propone una oferta de recompra de ese producto para ese cliente, con el
   intervalo esperado que la disparó registrado como su justificación.
2. **Given** un cliente cuyo `intervalo_compra.estado` en `002` es `datos_insuficientes`, **When**
   se ejecuta la detección de recompra, **Then** el sistema no genera oferta para ese cliente —no
   hay intervalo esperado del que partir—, igual que `002` lo excluye de su detección de fuga.
3. **Given** una oferta de recompra propuesta, **When** el encargado la revisa, **Then** el sistema
   NO ha apartado inventario ni escrito contra ninguna tabla de `001`; la reserva es solo de precio,
   y el envío de la oferta requiere la acción del encargado.
4. **Given** una oferta de recompra activa para un cliente y un producto, **When** se vuelve a
   ejecutar la detección, **Then** el sistema no genera una segunda oferta activa para el mismo
   cliente y el mismo producto.
5. **Given** una oferta de recompra cuya reserva de precio vence sin que el cliente compre, **When**
   vence, **Then** la oferta se cierra con desenlace "reserva vencida" y el cliente pierde la
   garantía de precio; no hay stock que liberar porque la reserva nunca apartó inventario.
6. **Given** una oferta de recompra vigente que el cliente decide redimir cuando no hay existencia
   suficiente del producto, **When** intenta comprar, **Then** recibe el mismo tratamiento que
   cualquier comprador sin oferta activa (sin garantía de disponibilidad); la reserva solo cubría el
   precio.

---

### User Story 3 - Medir la reactivación de clientes inactivos contra un grupo de control (Priority: P3)

El analista del negocio corre un experimento de reactivación: toma los clientes inactivos elegibles
(los que `002` ya detectó con señal de fuga), los reparte por aleatorización real con semilla fija
en grupo tratamiento y grupo control, ofrece el descuento solo al tratamiento, y mide el % de
clientes que vuelven a comprar en cada grupo. La incrementalidad es la diferencia entre esas dos
tasas; la promoción se considera efectiva solo si esa diferencia es estadísticamente significativa
(prueba z de dos proporciones, p < 0,05), no si supera un número fijo arbitrario. Es el único de los
tres mecanismos que exige grupo de control.

**Why this priority**: es el propósito analítico central del módulo y el más complejo — añade
aleatorización, grupo de control y medición de incrementalidad sobre la base de envío y retorno de
las historias anteriores. La constitución (Lectura Crítica n.º 6) hace el grupo de control
obligatorio para este tipo: sin él, cualquier afirmación sobre la eficacia de la campaña es
inválida. Va última porque hereda toda la maquinaria de las dos primeras y aporta la parte de mayor
riesgo si se construye mal.

**Independent Test**: para una población de clientes inactivos elegibles conocida, se puede
verificar que la asignación a tratamiento/control es reproducible con la misma semilla (mismos datos
+ misma semilla → mismos grupos), que no es predecible a partir de la paridad del id ni de ningún
atributo no aleatorio, que solo el tratamiento recibe el descuento, y que el resultado de
incrementalidad es reconstruible a partir del registro.

**Acceptance Scenarios**:

1. **Given** una población de clientes inactivos elegibles (con señal de fuga de `002`), **When** se
   crea el experimento de reactivación, **Then** cada cliente queda asignado a grupo tratamiento o
   grupo control por aleatorización real, y la semilla usada queda registrada junto con el
   experimento.
2. **Given** el mismo conjunto de clientes elegibles y la misma semilla, **When** el experimento se
   vuelve a generar, **Then** la asignación de grupos es idéntica a la anterior (reproducibilidad de
   la demostración).
3. **Given** un experimento con grupos asignados, **When** se revisa qué clientes recibieron
   comunicación, **Then** solo los del grupo tratamiento recibieron el descuento de reactivación; el
   grupo control no recibió ninguna comunicación ni descuento.
4. **Given** un experimento en curso y su ventana de medición, **When** vence la ventana, **Then**
   el sistema calcula el % de clientes que retornaron a comprar en el grupo tratamiento y el % en el
   grupo control, y la incrementalidad como la diferencia entre ambos.
5. **Given** una incrementalidad medida, **When** se evalúa la efectividad, **Then** el sistema
   marca la promoción de reactivación como efectiva si y solo si la diferencia de tasas de retorno
   entre tratamiento y control es estadísticamente significativa (prueba z de dos proporciones,
   p < 0,05); si no lo es —incluida una incrementalidad negativa (el control retornó más que el
   tratamiento)—, la marca como no efectiva y conserva el resultado, sin ocultarlo.
6. **Given** una población de clientes elegibles demasiado pequeña para que la prueba z tenga poder
   estadístico, **When** se crea el experimento, **Then** el sistema lo marca como "muestra
   insuficiente" en vez de forzar una conclusión de incrementalidad.
7. **Given** un cliente del grupo control que vuelve a comprar por su cuenta durante la ventana de
   medición, **When** `002` resuelve su señal de fuga, **Then** el sistema cuenta ese retorno para
   la tasa de su grupo (control) y NO modifica la señal de fuga de `002` (solo la observa).

---

### User Story 4 - Exponer la marca de "promoción activa" para el pronóstico de demanda (Priority: P4)

El analista de `004-pronostico-demanda` consulta, por producto, sucursal y período, si hubo una
promoción activa que distorsione la demanda observada, para poder excluir o marcar ese período al
construir la serie corregida. `005` es el propietario de esa marca y la deriva de las redenciones y
aplicaciones de los tres mecanismos de promoción.

**Why this priority**: cierra el contrato que `004` dejó abierto (FR-029 a FR-031 y FR-039 de `004`,
que ya esperan consumir una "marca de promoción activa" de `005`). Va última porque la marca se
deriva de los registros que producen las User Stories 1 a 3; sin ellas no hay nada que exponer.
`004` ya tiene una línea base para cuando `005` no existe (trata todo período como sin promoción,
FR-030 de `004`), así que esta historia mejora el pronóstico, no lo desbloquea.

**Independent Test**: dada una redención de cupón o una oferta de recompra comprada sobre un producto
concreto en una sucursal y fecha, se puede verificar que la consulta de "promoción activa" de `005`
devuelve ese producto, sucursal y período marcados, con el tipo de promoción que lo afectó, y que un
producto sin ninguna promoción en ese período no aparece marcado.

**Acceptance Scenarios**:

1. **Given** un producto con una redención de promoción registrada en una sucursal y fecha, **When**
   `004` consulta la marca de promoción activa para ese producto, sucursal y período, **Then** `005`
   devuelve ese período marcado, indicando qué tipo de promoción (fecha fija, recompra o
   reactivación) lo afectó.
2. **Given** un producto sin ninguna promoción redimida ni aplicada en un período, **When** `004`
   consulta la marca, **Then** `005` devuelve ese período como sin promoción activa.
3. **Given** una consulta de marca de promoción activa, **When** `005` la resuelve, **Then** el
   resultado se identifica siempre por sucursal; agregar varias sucursales sin discriminar la de
   origen está PROHIBIDO.
4. **Given** que `005` todavía no está implementado, **When** `004` construye su serie corregida,
   **Then** `004` trata todos los períodos como sin promoción (su línea base, FR-030 de `004`) y el
   gancho de integración con `005` queda documentado, no oculto.

---

### User Story 5 - Visualizar el resultado del experimento de reactivación (Priority: P5)

El encargado, tras cerrar la ventana de un experimento de reactivación, ve dos barras que
comparan el retorno observado del grupo de control con el del grupo de tratamiento, junto a la
lectura de la prueba (incrementalidad, z, p, veredicto) con sus portadores de forma. Así la
diferencia —o su ausencia— se ve de un vistazo, sin leer cuatro números.

**Why this priority**: es una lectura pura sobre el experimento que User Story 3 ya calcula. No
escribe ni recalcula nada, no cambia ningún contrato; es aditiva y no reabre el checkpoint de
User Stories 1–4.

**Independent Test**: para un experimento cerrado con muestra suficiente se verifica que el
gráfico muestra dos barras (control y tratamiento) con sus tasas, y que el texto de la inferencia
sigue mostrando z, p y veredicto con su forma; para un experimento con muestra insuficiente o en
curso se verifica que el gráfico NO dibuja barras ni fuerza un veredicto, sino que dice
explícitamente por qué no hay tasas.

**Acceptance Scenarios**:

1. **Given** un experimento cerrado con muestra suficiente, **When** el encargado abre su
   resultado, **Then** ve un gráfico de dos barras (retorno de control y de tratamiento) y, junto
   a él, el texto de la prueba con su portador de forma (▲/▬/◇) — el mismo patrón ya usado.
2. **Given** que las dos barras no tienen significado semántico entre sí, **When** se renderiza
   el gráfico, **Then** ambas usan el mismo color de serie (Estimado), nunca verde ni rojo.
3. **Given** un experimento cuya muestra activa es insuficiente (o sigue en curso), **When** se
   abre su resultado, **Then** el gráfico muestra un estado vacío que explica el motivo, sin
   dibujar barras ni afirmar un veredicto que los datos no sostienen.

---

### Edge Cases

- **Cliente sin `fecha_nacimiento`** (nunca se capturó, o se anonimizó tras fuga confirmada en
  `002`): no es elegible para el cupón de cumpleaños; el sistema lo omite explícitamente —vía la
  exclusión que `002` ya aplica en su consulta de cumpleañeros— y nunca genera un cupón "sin fecha".
- **Cliente en `intervalo_compra.estado = 'datos_insuficientes'`**: no es elegible para el empuje de
  recompra (no hay intervalo esperado del que partir), igual que `002` lo excluye de la detección de
  fuga y del cálculo de valor de cliente.
- **Cliente que califica a la vez para dos mecanismos** (por ejemplo, cumple años y además está
  inactivo): los tres mecanismos son independientes; recibir un cupón de cumpleaños no excluye a un
  cliente del experimento de reactivación. El registro DEBE permitir distinguir qué promoción
  influyó en un retorno concreto para no confundir la atribución (ver Assumptions).
- **Incrementalidad negativa** (el grupo control retornó en mayor proporción que el tratamiento): se
  registra tal cual y la promoción se marca como no efectiva o contraproducente; el resultado nunca
  se oculta ni se recorta a cero.
- **Población de inactivos elegibles demasiado pequeña**: el experimento se marca como "muestra
  insuficiente"; no se fuerza una conclusión de incrementalidad cuando la prueba z de dos
  proporciones no tiene poder estadístico (ver FR-021, FR-025).
- **Reserva de recompra que vence sin compra**: la oferta se cierra con desenlace "reserva
  vencida" y el cliente pierde la garantía de precio; no hay inventario que liberar porque la
  reserva es solo de precio y nunca apartó stock de `001`.
- **Redención de una oferta de recompra sin existencia suficiente del producto**: la reserva de
  precio no garantiza disponibilidad; el cliente recibe el mismo trato que cualquier comprador sin
  oferta activa.
- **Cliente del grupo tratamiento que compra antes de recibir el descuento**: su retorno cuenta para
  la tasa del grupo tratamiento (fue asignado a tratamiento); la ausencia de redención del descuento
  queda registrada y es parte de la explicación del resultado.
- **Promoción activa y quiebre de stock en el mismo período para un producto**: `005` solo expone la
  marca de promoción activa; cómo se combina con la descensura por quiebre es decisión de `004`
  (orden de correcciones ya fijado en `004`).
- **Redención de un cupón fuera de su ventana de validez**: se rechaza como redención; el cupón sigue
  su curso hacia "vencido" y no cuenta como redimido.

## Requirements *(mandatory)*

### Functional Requirements

**Mecanismo 1 — Cupón por fecha fija (cumpleaños)**

- **FR-001**: El sistema DEBE generar un cupón para un cliente cuando su fecha de cumpleaños entre
  en la ventana de generación configurada. La regla es directa —fecha objetivo dentro de la ventana
  → cupón— sin inferencia, sin grupo de control y sin medición de incrementalidad.
- **FR-002**: La identificación de qué clientes cumplen años en el rango DEBE obtenerse
  exclusivamente a través de la consulta de cumpleañeros que `002-clientes-fidelizacion` ya expone
  (FR-012 de `002`). El sistema NO DEBE reimplementar el filtro por día y mes de nacimiento ni
  acceder a `cliente.fecha_nacimiento` por otra vía.
- **FR-003**: El sistema NO DEBE generar un cupón de cumpleaños para un cliente anonimizado por
  `002` (que ya no conserva `fecha_nacimiento`); `002` ya lo excluye de la consulta de cumpleañeros
  y `005` respeta esa exclusión.
- **FR-004**: Cada cupón generado DEBE registrar el cliente, el motivo ("fecha fija — cumpleaños"),
  la ventana de validez y el estado (generado, redimido o vencido).
- **FR-005**: El sistema DEBE registrar la redención de un cupón cuando se usa en una venta de
  `001`, vinculada a esa venta, sin modificar la venta, el precio ni ningún dato propiedad de `001`.
  La redención es un hecho propio de `005`.
- **FR-006**: El cupón por fecha fija NO DEBE condicionar su generación ni su valor a ningún umbral
  estadístico ni a ningún grupo de control (contraste explícito con el mecanismo 3).
- **FR-007**: El sistema NO DEBE generar más de un cupón por la misma fecha objetivo del mismo
  cliente en el mismo año, aunque la generación se ejecute varias veces (idempotencia).

**Mecanismo 2 — Empuje por patrón de recompra con reserva**

- **FR-008**: El sistema DEBE identificar a los clientes cuyo tiempo desde la última compra se
  acerca a su intervalo de compra esperado, consultando `intervalo_compra.intervalo_esperado_dias`
  de `002` (solo para clientes con `estado = 'calculado'`) sin recalcularlo.
- **FR-009**: Para un cliente elegible, el sistema DEBE seleccionar un producto que ese cliente
  suele recomprar a partir de su historial de compras de `001` (`venta`, `renglon_venta`) y/o sus
  visitas de `002`. El criterio de selección por defecto se documenta en Assumptions y DEBE ser
  explicable (qué compras sustentan la elección).
- **FR-010**: El sistema DEBE ofrecer proactivamente ese producto al cliente con una **reserva de
  precio**: un código o registro que garantiza el precio ofertado si el cliente vuelve a comprar
  dentro de la ventana definida. La reserva NO aparta stock físico ni escribe contra ninguna tabla
  de inventario de `001`.
- **FR-011**: Si al momento de redimir la oferta el punto de venta de `001` no tiene existencia
  suficiente del producto, el cliente recibe el mismo tratamiento que cualquier comprador sin oferta
  activa (es `001` quien resuelve la venta): la reserva de precio garantiza el precio, nunca la
  disponibilidad. El sistema NO DEBE alterar `existencia` ni `movimiento_inventario` de `001` en
  ningún momento del ciclo de la oferta, y **no necesita leerlos**.
- **FR-012**: El empuje por recompra NO DEBE exigir grupo de control ni medición de incrementalidad.
- **FR-013**: Cada oferta de recompra DEBE registrar el cliente, el producto, el intervalo esperado
  que la disparó, el estado de la reserva de precio (vigente o vencida) y el desenlace (comprado, no
  comprado o reserva vencida).
- **FR-014**: El sistema NO DEBE mantener más de una oferta de recompra activa a la vez para el
  mismo cliente y el mismo producto.

**Mecanismo 3 — Reactivación de cliente inactivo (con grupo de control)**

- **FR-015**: El sistema DEBE definir "cliente inactivo elegible" reutilizando la detección de fuga
  silenciosa de `002` (`senal_fuga`), sin crear un criterio de inactividad nuevo ni paralelo. El
  estado exacto de la señal considerado elegible se documenta en Assumptions.
- **FR-016**: El sistema DEBE asignar los clientes inactivos elegibles a grupo tratamiento o grupo
  control mediante **aleatorización real** con **semilla fija**. Un reparto determinista por paridad
  del id del cliente, por orden alfabético, por antigüedad o por cualquier otro criterio no
  aleatorio está PROHIBIDO.
- **FR-017**: La semilla fija DEBE registrarse junto con el experimento y sirve **únicamente** para
  la reproducibilidad de la demostración (mismos datos de entrada + misma semilla → mismos grupos).
  Su existencia NO convierte la asignación en no-aleatoria: la aleatorización sigue siendo genuina.
- **FR-018**: Solo el grupo tratamiento DEBE recibir el descuento de reactivación. El grupo control
  NO DEBE recibir ninguna comunicación ni descuento durante el experimento.
- **FR-019**: El sistema DEBE medir, por grupo, el porcentaje de clientes que retornan a comprar
  dentro de la ventana de medición del experimento. La longitud de la ventana se documenta en
  Assumptions.
- **FR-020**: El sistema DEBE calcular la **incrementalidad** como la diferencia entre el porcentaje
  de retorno del grupo tratamiento y el porcentaje de retorno del grupo control.
- **FR-021**: El umbral de efectividad de la reactivación es **estadístico, no un número fijo
  arbitrario**: la diferencia de proporciones entre el % de retorno del grupo tratamiento y el del
  grupo control DEBE ser **estadísticamente significativa mediante una prueba z de dos proporciones
  (p < 0,05)** para que la campaña se considere efectiva. El **mecanismo** de la medición (grupo de
  control + aleatorización con semilla + comparación de tasas de retorno) ya estaba decidido y no se
  reabre; esta regla solo fija cómo se juzga la diferencia.
- **FR-022**: El sistema DEBE registrar el experimento de reactivación con: los clientes asignados y
  su grupo, la semilla usada, la ventana de medición, el porcentaje de retorno por grupo, la
  incrementalidad resultante y el resultado de la prueba z de dos proporciones (estadístico y valor
  p).
- **FR-023**: El sistema NO DEBE afirmar la eficacia de una campaña de reactivación que no tenga un
  grupo de control asignado; su ausencia invalida cualquier afirmación sobre la eficacia (Lectura
  Crítica n.º 6 de la constitución).
- **FR-024**: Cada resultado del experimento de reactivación DEBE ser reconstruible a partir del
  registro: qué clientes en cada grupo, qué proporción retornó en cada grupo, qué diferencia
  resultó y si esa diferencia fue estadísticamente significativa (Principio V: explicable).
- **FR-025**: Cuando la población de clientes inactivos elegibles sea demasiado pequeña para que la
  prueba z de FR-021 tenga poder estadístico, el sistema DEBE marcar el experimento como "muestra
  insuficiente" en vez de emitir una conclusión de incrementalidad. El tamaño mínimo de muestra por
  grupo se calcula y documenta en `plan.md`/`research.md` cuando se conozca el volumen real de
  clientes elegibles (ver Assumptions).

**Frontera con `002-clientes-fidelizacion` (propiedad de datos)**

- **FR-026**: El sistema NO DEBE reimplementar la detección de fuga silenciosa ni el cálculo del
  intervalo de compra esperado; `senal_fuga` e `intervalo_compra` son propiedad de `002` y este
  módulo solo los consulta.
- **FR-027**: El sistema NO DEBE acceder a `cliente.fecha_nacimiento` para la lógica de cumpleaños;
  DEBE usar la consulta de cumpleañeros que `002` ya expone (FR-012 de `002`).
- **FR-028**: El sistema NO DEBE modificar el estado de una `senal_fuga` ni marcar una fuga como
  resuelta; esa transición pertenece a `002`, que la resuelve cuando el cliente vuelve a comprar.
  `005` observa el retorno del cliente para su propia medición, sin tocar la señal.

**Frontera con `001-core-ventas-inventario` (propiedad de datos)**

- **FR-029**: El sistema NO DEBE registrar, modificar ni recalcular `venta`, `renglon_venta`,
  `existencia`, `movimiento_inventario`, `producto_precio_sucursal` ni ningún precio; consulta el
  historial de compras y aplica descuentos únicamente a través de los contratos de `001`.
- **FR-030**: La aplicación de un cupón o descuento en una venta DEBE registrarse como una redención
  propia de `005` vinculada a la venta de `001`, sin que `005` posea la venta.

**Frontera con `004-pronostico-demanda` (contrato de "promoción activa")**

- **FR-031**: El sistema DEBE exponer, por producto, sucursal y período, una marca de "promoción
  activa" derivada de las redenciones y aplicaciones de los tres mecanismos de promoción, para que
  `004` la consuma (FR-029 a FR-031 y FR-039 de `004`).
- **FR-032**: La marca de promoción activa DEBE indicar qué tipo de promoción (fecha fija, recompra
  o reactivación) afectó al producto en ese período, para que `004` decida si excluye o solo marca
  ese período.
- **FR-033**: El sistema NO DEBE escribir en `demanda_observada`, `demanda_corregida` ni
  `pronostico`; son propiedad de `004`. `005` solo provee la marca; `004` la aplica.
- **FR-034**: El contrato queda cerrado desde el lado de `005` con este spec. Mientras `005` no esté
  implementado, `004` trata todo período como sin promoción (su línea base, ya prevista en FR-030 de
  `004`); una vez implementado, la marca de FR-031 pasa a ser la fuente.

**Común a los tres mecanismos**

- **FR-035**: Toda promoción, cupón, oferta y experimento DEBE identificarse por sucursal cuando
  aplique. Agregar resultados de varias sucursales sin discriminar la de origen está PROHIBIDO
  (Principio IV y restricción multi-sucursal de la constitución).
- **FR-036**: La inteligencia de este módulo es consultiva: `005` genera cupones, ofertas y
  asignaciones de grupo, y mide resultados, pero NO ajusta precios ni inventario de forma
  automática. La aplicación de un descuento en el punto de venta requiere la acción del operador
  (Principio V: consultiva por defecto; Principio II: la caja no se bloquea).
- **FR-037**: La decisión de aplicar la promoción de reactivación DEBE basarse en el umbral
  estadístico de incrementalidad (FR-021), no en una regla fija arbitraria.
- **FR-038**: Los tres mecanismos de promoción DEBEN modelarse como mecanismos distintos, con su
  propia lógica y sus propias exigencias. Implementarlos como una sola entidad genérica está
  PROHIBIDO (Lectura Crítica n.º 6 de la constitución).
- **FR-039**: El sistema DEBE permitir operar y demostrar cada mecanismo por separado; ninguno
  depende de la existencia de otro para funcionar, más allá de la base compartida de registro de
  envío y de redención.

**Visualización del experimento (User Story 5)**

- **FR-040**: El sistema DEBE ofrecer, en el resultado de un experimento de reactivación, un
  gráfico de dos barras con el retorno observado del grupo de control y del grupo de tratamiento,
  junto al texto de la inferencia (incrementalidad, z, p, veredicto) que ya existe.
- **FR-041**: Las dos barras NO tienen significado semántico entre sí: DEBEN usar el mismo color
  de serie (Estimado, #1F5673) y distinguirse por su etiqueta. Usar verde, rojo o una paleta
  decorativa está PROHIBIDO.
- **FR-042**: Cuando el experimento no tiene tasas de retorno medibles (muestra insuficiente o
  ventana en curso), el gráfico NO DEBE dibujar barras ni afirmar un veredicto: DEBE mostrar un
  estado vacío que explique el motivo, con la misma honestidad que el texto de la inferencia
  (FR-020, FR-021).

### Key Entities *(include if feature involves data)*

- **campania**: una corrida de promoción de un mecanismo dado (fecha fija, recompra o reactivación),
  con su tipo, la sucursal o sucursales que cubre y su ventana temporal. Es el paraguas bajo el que
  se agrupan los envíos y, para la reactivación, el experimento. Propiedad de este módulo.
- **cupon**: cupón generado para un cliente por una fecha fija (cumpleaños), con su motivo, su
  ventana de validez y su estado (generado, redimido, vencido). No requiere grupo de control.
  Propiedad de este módulo.
- **oferta_recompra**: oferta proactiva de un producto que un cliente suele recomprar, disparada por
  su intervalo de compra esperado (consultado a `002`), con el producto ofrecido, la justificación
  (qué compras la sustentan), el precio garantizado y la ventana de la **reserva de precio** (no de
  inventario: no aparta stock de `001`), su estado (vigente o vencida) y el desenlace. Propiedad de
  este módulo.
- **experimento_reactivacion**: experimento de reactivación de clientes inactivos, con la población
  elegible (derivada de `senal_fuga` de `002`), la semilla de aleatorización usada, la ventana de
  medición, las tasas de retorno por grupo, la incrementalidad resultante, el resultado de la prueba
  z de dos proporciones (estadístico y valor p) y el veredicto (efectivo, no efectivo o "muestra
  insuficiente"). Propiedad de este módulo.
- **asignacion_experimento**: una fila por cliente inactivo elegible, con su grupo asignado
  (tratamiento o control) y su resultado de retorno a compra dentro de la ventana de medición. Es la
  materialización del grupo de control obligatorio para el mecanismo 3. Propiedad de este módulo.
- **redencion_promocion**: el hecho de que un cupón, una oferta de recompra o un descuento de
  reactivación se usó en una venta de `001`; vincula el envío con la venta (propiedad de `001`) sin
  poseer la venta. Es la base de la que se deriva la marca de "promoción activa" que consume `004`.
  Propiedad de este módulo.
- **marca_promocion_activa**: consulta derivada (no necesariamente una tabla), por producto,
  sucursal y período, que indica si hubo promoción activa y de qué tipo; se calcula a partir de
  `redencion_promocion` y de las aplicaciones registradas. Es el contrato que `004` consume. Su
  forma concreta se decide en `plan.md`.

Entidades de `002` que este módulo consulta pero no posee (frontera de propiedad de datos):
`cliente` (a través de la consulta de cumpleañeros de FR-012 de `002`), `intervalo_compra`
(`intervalo_esperado_dias`, `estado`), `senal_fuga` (estado y su historia), `visita`. Entidades de
`001` que este módulo consulta (solo lectura) pero no posee: `producto`, `sucursal`, `venta`,
`renglon_venta`, `producto_precio_sucursal`, `turno`. `005` **no lee ni escribe** `existencia` ni
`movimiento_inventario` de `001`: la reserva del empuje por recompra es de precio, no de inventario,
y la disponibilidad al vender la resuelve `001` (FR-011). Entidades de `004` hacia las que este
módulo expone la marca de promoción activa (sin escribir en ellas): `demanda_observada`,
`demanda_corregida`.

## Dependencias entre módulos

Esta sección es de lectura obligatoria antes de `/speckit-plan`: fija qué se puede construir ahora,
qué contratos se cierran y qué enmienda constitucional respalda las entidades de este módulo. No
debe quedar oculta en `plan.md`.

**Lo que este módulo consulta y no reimplementa** (mismo patrón que `003` y `004` frente a `001` y
`002`):

- De `002-clientes-fidelizacion`: la consulta de cumpleañeros (FR-012 de `002`, que ya excluye
  clientes anonimizados) para el mecanismo 1; `intervalo_compra.intervalo_esperado_dias` y su
  `estado` para el mecanismo 2; `senal_fuga` y su estado para definir "cliente inactivo elegible" en
  el mecanismo 3; `visita` como contexto de historial de compra del cliente.
- De `001-core-ventas-inventario`: `venta` y `renglon_venta` (historial de compras del cliente para
  elegir el producto de recompra y para detectar retornos), `producto`, `sucursal` y `turno`
  (para resolver la sucursal y el día local de una venta con redención),
  `producto_precio_sucursal` (precio vigente sobre el que se fija la reserva de precio o se aplica
  un descuento). **No** consulta `existencia` ni `movimiento_inventario`: la disponibilidad al
  vender la resuelve `001` (FR-011).

**Verificación exigida por el enunciado — `cliente.fecha_nacimiento`**: el enunciado pedía
confirmar que ese campo exista antes de apoyar el cupón de cumpleaños en él. **Verificado**:
`cliente.fecha_nacimiento` existe en `002` (FR-001 de `002`, y `data-model.md` de `002`,
`DATE NULL`, obligatoria al registrar), y `002` la documenta explícitamente como "la única base del
cupón de cumpleaños que decide y emite `005`". **No hay bloqueo** por este lado. La única cautela es
operativa y ya resuelta por `002`: un cliente anonimizado pierde `fecha_nacimiento` y queda fuera de
la consulta de cumpleañeros (FR-003 de este spec).

**Contrato que este spec cierra hacia `004-pronostico-demanda`**: `004` ya especificó (FR-029 a
FR-031, FR-039 y sus Key Entities) que consumirá de `005` una "marca de promoción activa" por
producto, sucursal y período, derivada de `campania`. Este spec cierra ese contrato desde el lado de
`005` (FR-031 a FR-034): `005` es el propietario de la marca, la deriva de `redencion_promocion` y
la expone con el tipo de promoción. Hasta que `005` se implemente, `004` mantiene su línea base
(todo período sin promoción), tal como ya previó.

**La detección pertenece a `002`, la decisión a `005`** (frontera ya escrita en la constitución):
`002` detecta el riesgo de fuga; `005` decide si ofrecer un descuento de reactivación y —a
diferencia de los otros dos mecanismos— lo condiciona a un experimento con grupo de control. `005`
no toca `senal_fuga`; `002` la resuelve cuando el cliente vuelve.

**Enmienda constitucional que respalda estas entidades (ya aplicada — v2.2.5)**: la tabla de
Propiedad de Datos de la constitución listaba para `005-promociones-inteligentes` tres entidades
(`campania`, `envio_promocional`, `grupo_control`), escritas antes de que existiera este spec. La
enmienda **v2.2.5** (2026-09-05) retiró `envio_promocional` y `grupo_control` —la primera contradice
la Lectura Crítica n.º 6 al modelar las promociones como un mecanismo único; la segunda es demasiado
gruesa para la medición de incrementalidad— y añadió `cupon`, `oferta_recompra`,
`experimento_reactivacion`, `asignacion_experimento` y `redencion_promocion`. Lista vigente de
`005`: `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`,
`redencion_promocion` (6 entidades). Mismo patrón que la enmienda **v2.2.3** para `003`
(`sugerencia_precio`) y **v2.2.4** para `004` (`sustitucion_producto`); ver el informe de impacto de
sincronización al inicio de `constitution.md`.

**Nada bloquea escribir, aprobar e implementar este spec**: las dos decisiones de alcance mayor que
quedaban abiertas (mecanismo de reserva, umbral de incrementalidad) se resolvieron en la sesión de
clarificación del 2026-09-05 (ver `## Clarifications`) — reserva de precio y umbral estadístico por
prueba z. `002` está implementado hasta su User Story 1
en el último checkpoint, pero `cliente`, `visita`, `intervalo_compra` y `senal_fuga` están
especificados y son consultables conforme `002` avance; la parte de este módulo que depende de datos
reales de fuga (mecanismo 3) espera a que `002` implemente su User Story 3, y así debe marcarse en
`plan.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los cupones de cumpleaños generados corresponde a un cliente cuya fecha de
  cumpleaños cayó dentro de la ventana de generación, obtenido a través de la consulta de
  cumpleañeros de `002`; 0% generados por acceso directo a `cliente.fecha_nacimiento`.
- **SC-002**: Ningún cliente anonimizado por `002` recibe un cupón de cumpleaños (0%).
- **SC-003**: El 100% de las redenciones de cupón o de oferta queda vinculado a una venta de `001`
  sin que `005` haya modificado esa venta, su precio ni ningún otro dato propiedad de `001`.
- **SC-004**: El 100% de los experimentos de reactivación tiene un grupo de control asignado por
  aleatorización real; 0% de afirmaciones de eficacia de una campaña de reactivación sin grupo de
  control.
- **SC-005**: Dados los mismos datos de entrada y la misma semilla, la asignación de grupos del
  experimento es idéntica entre corridas en el 100% de los casos (reproducibilidad de la
  demostración).
- **SC-006**: La asignación a tratamiento o control no es predecible a partir de la paridad del id
  del cliente, su orden alfabético ni ningún otro atributo no aleatorio — verificable
  estadísticamente sobre la población asignada.
- **SC-007**: El 100% de los resultados de incrementalidad es reconstruible a partir del registro:
  qué clientes en cada grupo, qué proporción retornó en cada grupo, qué diferencia resultó y el
  resultado de la prueba z de dos proporciones (estadístico y valor p).
- **SC-008**: La promoción de reactivación se marca como efectiva si y solo si la diferencia de
  tasas de retorno entre tratamiento y control es estadísticamente significativa (prueba z de dos
  proporciones, p < 0,05), en el 100% de los casos (coherencia con FR-021); una incrementalidad
  negativa o no significativa nunca se presenta como éxito.
- **SC-009**: El 100% de las marcas de "promoción activa" expuestas a `004` identifica producto,
  sucursal, período y tipo de promoción.
- **SC-010**: 0% de operaciones de `005` que registran, modifican o recalculan `venta`,
  `existencia`, `movimiento_inventario`, precio, `senal_fuga` o `intervalo_compra`.
- **SC-011**: Los tres mecanismos de promoción son operables y demostrables por separado; ninguno
  requiere la existencia de otro para funcionar, más allá de la base compartida de registro de envío
  y redención.

## Assumptions

- **`cliente.fecha_nacimiento` existe y no es un bloqueo**: verificado contra `002` (FR-001 y su
  `data-model.md`). `002` ya la trata como la única base del cupón de cumpleaños de `005` y ya
  excluye a los clientes anonimizados de su consulta de cumpleañeros; `005` no necesita nada más de
  `002` para el mecanismo 1.
- **Ventana de generación del cupón de cumpleaños**: el sistema genera el cupón con antelación
  configurable a la fecha de cumpleaños (por ejemplo, la semana previa), no exactamente el día. El
  valor concreto de esa antelación y de la ventana de validez del cupón se decide en `plan.md`; no
  cambia el mecanismo (fecha llega → cupón).
- **Selección del producto de recompra (FR-009)**: el default es el producto que el cliente ha
  comprado con mayor frecuencia y de forma más regular en su historial reciente de `001`/`002` (el
  candidato más claro a "producto que suele recomprar"). El criterio exacto y la ventana de
  historial se afinan en `plan.md`; la elección DEBE quedar registrada y ser explicable. No se
  infiere un producto por correlación con otros clientes.
- **Reserva de precio, no de inventario (FR-010, resuelto en Clarifications 2026-09-05)**: la
  "reserva" del empuje por recompra garantiza el precio ofertado dentro de una ventana, no la
  disponibilidad del producto. Se descartó la reserva de inventario (apartar unidades físicas del
  stock de `001`) por dos razones: mantiene intacta la frontera "`005` consulta pero no reimplementa
  `001`" —apartar stock exigiría que `005` escribiera contra `existencia`/`movimiento_inventario` o
  dependiera de un contrato de bloqueo de inventario que `001` no expone— y sigue el patrón
  "sugiere, no aplica" ya establecido en FR-028 de `001` ("el sistema NO DEBE ajustar ningún precio
  de forma automática") y usado en `003`. Si al redimir no hay stock, el cliente recibe el trato de
  cualquier comprador sin oferta (FR-011). La Lectura Crítica n.º 6 de la constitución describe este
  mecanismo como "empuje por patrón de recompra detectado, con reserva del producto"; este spec
  interpreta esa "reserva" como reserva de precio por las razones anteriores, y esa interpretación
  es la justificación que la propia constitución exige de toda especificación que matice una de sus
  lecturas críticas.
- **Estado de `senal_fuga` elegible para el mecanismo 3**: el default es la señal en estado
  `activa` — el estado que la propia `002` describe (FR-014 de `002`) como el que "solo alimenta una
  posible reactivación en `005`, reversible y sin costo si el cliente vuelve". Un cliente en estado
  `confirmada` está a punto de que `002` anonimice sus datos personales, por lo que queda fuera de
  la población elegible por defecto. Ajustar esta frontera es una decisión de `plan.md` dentro del
  criterio ya fijado (reutilizar la detección de `002`, no crear una nueva).
- **Ventana de medición del experimento de reactivación (FR-019)**: se fija en `plan.md`. Un punto
  de partida razonable es un múltiplo del intervalo de compra esperado de los clientes de la
  población, o un plazo absoluto del orden de 4 a 8 semanas; no reabre el mecanismo, solo lo
  parametriza.
- **"Retorno a compra"**: un cliente cuenta como retornado si registra al menos una venta (con o sin
  redención del descuento) dentro de la ventana de medición, en cualquier sucursal de la campaña.
  Refinable en `plan.md`.
- **Umbral estadístico de incrementalidad (FR-021, resuelto en Clarifications 2026-09-05)**: la
  campaña de reactivación se considera efectiva solo si la diferencia entre la tasa de retorno del
  grupo tratamiento y la del grupo control es estadísticamente significativa mediante una prueba z
  de dos proporciones con p < 0,05 — un umbral estadístico, no un número fijo arbitrario, como pide
  el enunciado del docente.
- **Poder estadístico de la prueba z (limitación conocida, no bloqueante)**: la prueba z de dos
  proporciones pierde poder con muestras pequeñas por grupo, y la población de clientes elegibles
  para reactivación en un minimarket de barrio puede ser pequeña. El tamaño mínimo de muestra por
  grupo para un poder razonable se calcula y documenta en `plan.md`/`research.md` de `005` cuando se
  conozca el volumen real de clientes elegibles; por debajo de ese tamaño el experimento se marca
  "muestra insuficiente" (FR-025) en vez de emitir un veredicto de efectividad.
- **Atribución cuando un cliente recibe más de una promoción**: el registro de cada redención y de
  cada retorno indica qué envío y qué mecanismo lo originó, de modo que un retorno pueda atribuirse
  a la promoción correcta. No se intenta repartir el crédito de un retorno entre varias promociones
  simultáneas; se registra cuál se redimió.
- **Valor del descuento de cada mecanismo** (porcentaje o monto del cupón, del empuje de recompra y
  del descuento de reactivación): son parámetros de negocio que se fijan en `plan.md`, no decisiones
  de alcance de este spec.
- **Aleatorización con semilla fija**: la semilla se registra por experimento y existe solo para que
  la demostración sea reproducible (mismos datos + misma semilla → mismos grupos). No es un reparto
  determinista: el generador es genuinamente aleatorio y la semilla solo fija su punto de partida.
  El tamaño relativo de los grupos tratamiento y control (por ejemplo 50/50) se decide en `plan.md`.
- **`campania` no tiene endpoint de lectura propio** (decisión intencional): el contrato de `005`
  no expone ninguna ruta para listar o consultar campañas. `campania` es la agrupación interna de
  una corrida de un mecanismo (de cupones, de ofertas de recompra o de un experimento);
  ningún escenario de aceptación de las cuatro historias de este spec requiere listar campañas de
  forma independiente de sus mecanismos, y cada `cupon`, `oferta_recompra` y `experimento_reactivacion`
  ya lleva su `id_campania`. Si una versión futura necesitara una vista de "todas las campañas",
  añadir ese endpoint sería trabajo aditivo sin cambio de esquema.
- **`005` no lee `existencia` ni `movimiento_inventario` de `001`**: la reserva del empuje por
  recompra es de precio, no de inventario (FR-010), y si al redimir falta stock es `001` quien
  resuelve la venta (FR-011). Las únicas lecturas de esas dos tablas ocurren en las **pruebas de
  frontera**, que cuentan filas antes y después para confirmar que `005` nunca escribió.
- **Constitución vigente citada**: v2.2.6. La enmienda que esta funcionalidad motivó es la
  **v2.2.5** (2026-09-05); v2.2.6 es una corrección posterior sobre la entrada de
  `007-pagos-seguridad`, sin efecto sobre este módulo. La enmienda **v2.2.5** reconcilió la lista
  de entidades de `005` en la tabla de Propiedad de Datos (`campania`, `envio_promocional`,
  `grupo_control` → `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`,
  `asignacion_experimento`, `redencion_promocion`), mismo patrón que v2.2.3 (`003`) y v2.2.4
  (`004`). Ya está aplicada; ver "Dependencias entre módulos" y el informe de impacto al inicio de
  `constitution.md`.
- **Decisiones de alcance mayor, todas resueltas — ninguna quedó con default silencioso**: FR-010
  (reserva de precio, no de inventario) y FR-021 (umbral estadístico por prueba z de dos
  proporciones, p < 0,05) se resolvieron en la sesión de clarificación del 2026-09-05 (ver
  `## Clarifications`). El mecanismo de medición de la reactivación (grupo de control +
  aleatorización con semilla + comparación de tasas de retorno) nunca fue una decisión abierta: ya
  estaba decidido y no se reabrió. Ajustar cualquiera de estas decisiones en el futuro es una
  enmienda de este spec, no una decisión libre de `plan.md`.
