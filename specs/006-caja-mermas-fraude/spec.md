# Feature Specification: Caja, Mermas y Fraude

**Feature Branch**: `006-caja-mermas-fraude` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-05

**Status**: Draft

**Input**: Detectar y atribuir las pérdidas de valor que un cuadre diario deja escapar. La tesis del
enunciado es que las mermas y las diferencias entre lo cobrado y lo que debería haberse cobrado solo
son visibles con un cuadre **frecuente** —por cierre de turno y por arqueo periódico—, no con un
único cierre al final del día: un cuadre diario no las captura a tiempo ni con resolución suficiente
para atribuirlas a un turno u operador concreto. La observación crítica que este módulo existe para
resolver, y que la constitución ya fijó (Lectura Crítica n.º 1): **el cuadre de caja NO detecta el
fraude de "cobrar 5, registrar 3"**. Cuando el operador cobra el monto real pero registra una venta
menor y se queda la diferencia, el efectivo en caja coincide exactamente con lo que el sistema
registró como vendido —el fraude ocurre al registrar la venta, no después—, así que ningún arqueo de
efectivo lo puede encontrar. La única forma de detectarlo es cruzar la existencia física (lo que
realmente salió del inventario, revelado en un conteo) contra las ventas registradas y las
cancelaciones, **desagregado por operador y por turno**. Este módulo distingue tres fenómenos con
lógica de detección distinta —merma física, diferencia caja-cobrado y fraude por sub-registro— y no
los trata como una sola entidad genérica. Consulta, sin reimplementar, la existencia, los
movimientos de inventario, las ventas, las cancelaciones, los turnos, los operadores, los lotes (con
su caducidad y su costo) y los conteos físicos de `001-core-ventas-inventario`; posee el arqueo de
caja por turno, la clasificación de mermas y el registro de anomalías de caja. La inteligencia de
este módulo es consultiva: el sistema detecta, atribuye y explica; la persona clasifica lo que el
sistema no puede explicar y decide qué hacer (Principio V de la constitución).

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-05

Ninguna pregunta quedó abierta. Las dos decisiones de alcance mayor que un lector podría esperar como
`NEEDS CLARIFICATION` se resolvieron con una decisión razonable documentada, por indicación explícita
del encargo:

- **Cadencia del cruce inventario-ventas para detectar el sub-registro**: no puede ejecutarse en
  cada venta (inviable para un minimarket de barrio) ni tiene sentido diario (un conteo físico
  diario de todo el catálogo no es realista). Se decide: el **arqueo de caja** se ejecuta a cada
  **cierre de turno** (contar efectivo es barato); el **cruce inventario-ventas por operador** se
  ejecuta a cada **conteo físico periódico** de `001` —que el negocio programa por categoría en una
  rotación semanal, con los frescos con más frecuencia (Assumptions)— y, además, bajo demanda cuando
  un indicador por operador (tasa de anulaciones, concentración de ventas bajo precio de lista) se
  dispara. Ver FR-018 a FR-021 y Assumptions.
- **Diferencia detectada que no se explica por ningún motivo conocido**: se registra como
  `anomalia_caja` en estado `sin_explicacion`, pendiente de revisión manual. El sistema **nunca
  fuerza** una clasificación ni la recorta a cero. Ver FR-027 a FR-031 y Assumptions.

El resto de ambigüedades menores de redacción se resolvió con defaults documentados en la sección
**Assumptions**.

## User Scenarios & Testing *(mandatory)*

<!-- Historias ordenadas por dependencia real, no por número de fenómeno. El arqueo de caja por
turno va primero: es el cuadre más barato y frecuente, el que el enunciado pone como punto de
entrada, depende solo de `turno` y `venta` de `001` (ya implementadas) y establece el registro de
primera clase (`arqueo`) sobre el que se apoya el lado de efectivo de la detección de anomalías. La
clasificación de mermas va segunda: toma la diferencia bruta que `001` ya expone en un conteo físico
y le asigna causa y valoración; una diferencia física tiene que compararse contra la merma declarada
ANTES de poder llamarse anomalía. El cruce inventario-ventas por operador (el sub-registro) va
tercero: es el mecanismo más complejo y de mayor riesgo, hereda el arqueo y la clasificación de
merma de las dos anteriores, y es la única señal válida del fraude que el arqueo no ve. La gestión de
anomalías sin explicación va última porque es el residuo: lo que queda después de descontar merma
declarada, error de cambio y cancelación fuera de turno. -->

### User Story 1 - Arquear la caja al cierre de cada turno (Priority: P1)

El encargado (o el propio operador al cerrar su turno) cuenta el efectivo y los comprobantes de otros
medios de pago que quedan en la caja y los compara contra lo que el sistema registró como cobrado en
ese turno. El sistema muestra la diferencia —sobrante o faltante— atribuida al turno y a su operador,
con el día local de la sucursal ya resuelto. Es el cuadre frecuente que un cierre diario no permite:
al hacerlo por turno, una diferencia queda atada a un operador concreto y a una franja de pocas
horas, no diluida en la jornada de toda la sucursal.

**Why this priority**: es el mecanismo más simple —contar efectivo y restar lo registrado— y el
punto de entrada del módulo. Depende únicamente de `turno` y `venta` de `001`, ya implementadas, así
que no está bloqueado. Establece la pieza compartida que los otros fenómenos reutilizan: el registro
`arqueo`, que fija el instante de cierre, el operador responsable y el día local, y que es la base
del lado de efectivo de una `anomalia_caja`. Construir la detección de fraude (la más compleja) antes
de esta base obligaría a inventar esa pieza dos veces. Además, esta historia demuestra en la práctica
por qué el arqueo, por sí solo, no basta: su diferencia es cero exactamente en el caso de fraude por
sub-registro (ver User Story 3).

**Independent Test**: para un turno cerrado con un conjunto conocido de ventas registradas, se puede
verificar que el sistema calcula "lo esperado en caja" como la suma de los cobros de ese turno, que
la diferencia contra el efectivo contado se muestra con su signo (sobrante o faltante), que queda
atribuida al operador del turno y al día local de la sucursal, y que un turno sin ninguna venta
produce un arqueo con esperado cero, no un error.

**Acceptance Scenarios**:

1. **Given** un turno cerrado con ventas registradas por un total conocido, **When** el encargado
   registra el efectivo y los comprobantes contados al cierre, **Then** el sistema muestra la
   diferencia entre lo contado y lo registrado como cobrado en ese turno, con su signo, atribuida al
   operador del turno y fechada por el día local de la sucursal.
2. **Given** un turno cuyo efectivo contado coincide exactamente con lo registrado como cobrado,
   **When** se cierra el arqueo, **Then** la diferencia es cero y el arqueo queda registrado como
   cuadrado, sin generar ninguna anomalía.
3. **Given** un turno con un faltante de efectivo, **When** se cierra el arqueo, **Then** el sistema
   registra el faltante y permite anotar un motivo conocido (por ejemplo, "mal dado el cambio",
   "pago no registrado"); si no hay motivo, la diferencia queda disponible para revisión como posible
   anomalía (User Story 4).
4. **Given** un turno ya arqueado, **When** se intenta volver a arquearlo, **Then** el sistema no
   crea un segundo arqueo para el mismo turno (idempotencia); una corrección se registra como
   ajuste del arqueo existente, sin borrar el conteo anterior.
5. **Given** un arqueo cerrado, **When** se consulta, **Then** NO modifica ninguna `venta`, ningún
   `total` ni ningún dato propiedad de `001`: el arqueo es un hecho propio de este módulo que solo
   observa las ventas del turno.
6. **Given** una consulta de arqueos de varias sucursales, **When** se presenta el resultado,
   **Then** cada arqueo se identifica por su sucursal; agregar el descuadre de varias sucursales sin
   discriminar la de origen está PROHIBIDO.

---

### User Story 2 - Clasificar la causa de una diferencia de conteo físico como merma (Priority: P2)

El encargado revisa las diferencias que un conteo físico de `001` dejó expuestas —por producto y por
lote, en bruto y sin causa— y clasifica cada una: merma física por vencimiento, por daño, por robo
externo, o por error de conteo; o la deja pendiente si no puede decidir. El sistema valora la pérdida
usando el costo del lote y la deja atribuida a la sucursal y al período entre conteos. También
permite declarar una merma fuera de un conteo (una botella que se rompió, un lote que venció en
estantería) y alerta de los lotes cuya caducidad se acerca antes de que se conviertan en merma.

**Why this priority**: es el segundo insumo indispensable. Una diferencia física negativa que no se
clasifica como merma declarada no puede distinguirse de una sustracción; la detección de fraude por
sub-registro (User Story 3) necesita saber qué parte del faltante de inventario ya está explicada por
merma antes de señalar el resto. Depende del conteo físico de `001` (`conteo_fisico`,
`conteo_renglon`), especificado pero aún no implementado (ver Dependencias entre módulos). La alerta
de caducidad y la declaración de merma fuera de conteo sí pueden operar solo con `lote` de `001`.

**Independent Test**: para un `conteo_renglon` de `001` con una diferencia negativa conocida sobre un
producto con costo de lote conocido, se puede verificar que el sistema permite clasificar esa
diferencia con una de las causas de merma, que calcula el valor de la pérdida como cantidad por costo
del lote, que la deja atribuida a la sucursal y al intervalo desde el conteo anterior, y que la
diferencia bruta de `001` no se altera.

**Acceptance Scenarios**:

1. **Given** un conteo físico de `001` resuelto con una diferencia de −3 unidades en un producto,
   **When** el encargado la clasifica como merma por daño, **Then** el sistema registra una merma de
   3 unidades con causa "daño", valorada al costo del lote correspondiente, atribuida a la sucursal
   y al período del conteo, sin modificar la diferencia bruta que `001` expone.
2. **Given** un producto a granel cuyo peso contado es menor que el peso descontado de sus lotes
   (diferencia de granel que `001` expone sin clasificar, FR-016 de `001`), **When** el encargado la
   clasifica, **Then** puede asignarle causa "deshidratación / merma de corte" y el valor se calcula
   sobre los gramos faltantes al costo por kilogramo del lote.
3. **Given** una diferencia de conteo que el encargado no puede explicar, **When** la revisa,
   **Then** puede dejarla como merma "pendiente de clasificar" o escalarla a `anomalia_caja` (User
   Story 4); el sistema no le impone una causa por defecto.
4. **Given** un lote perecedero cuya fecha de caducidad entra en la ventana de alerta configurada,
   **When** el encargado consulta las alertas de caducidad, **Then** el sistema lista ese lote con su
   existencia restante y su valor en riesgo, para que el encargado actúe antes de que sea merma; el
   sistema no da de baja ni descuenta nada por su cuenta.
5. **Given** una unidad que se rompió en estantería fuera de cualquier conteo, **When** el encargado
   declara la merma directamente, **Then** el sistema la registra con su causa, su cantidad y su
   valor, y señala que esa merma deberá conciliarse con el próximo conteo físico de `001` (este
   módulo no ajusta la existencia; ese ajuste pertenece a `001`).
6. **Given** una merma ya registrada y valorada, **When** se consulta el total de mermas de un
   período, **Then** se puede desglosar por causa, por producto y por sucursal, y nunca se agrega
   entre sucursales sin discriminar la de origen.

---

### User Story 3 - Detectar el sub-registro cruzando inventario contra ventas por operador (Priority: P3)

El analista del negocio revisa, por operador y por turno, las señales del fraude de "cobrar 5,
registrar 3": la existencia física que faltó en el último conteo y que no está explicada por merma
declarada ni por cancelación fuera de turno, la tasa de anulaciones de venta de cada operador, y la
concentración de ventas registradas por debajo del precio de lista en sus turnos. El sistema cruza
estos datos —todos derivados de `001`— desagregados por operador, y marca los patrones que el arqueo
de caja, por diseño, no puede ver: en este fraude el efectivo cuadra con lo registrado.

**Why this priority**: es el propósito central del módulo y el más complejo y de mayor riesgo —añade
el cruce por operador sobre la base del arqueo (User Story 1) y de la clasificación de merma (User
Story 2)—. La constitución (Lectura Crítica n.º 1) es explícita: este fraude NO produce descuadre de
caja y NO se detecta con un arqueo; su única señal es la discrepancia entre salida de inventario y
venta registrada, la tasa de anulaciones por cajero y la concentración de ventas bajo precio de lista
en un turno. Va después de las dos primeras historias porque necesita descontar del faltante de
inventario lo que ya se explicó como merma (User Story 2) y como diferencia de efectivo con motivo
(User Story 1). La parte que depende del conteo físico real está bloqueada por `001`; la parte de
anulaciones y precios sí puede construirse ya (ver Dependencias entre módulos).

**Independent Test**: para un conjunto conocido de ventas, anulaciones y —cuando exista— un conteo
físico con faltante, todo atribuido a operadores concretos vía `turno`, se puede verificar que el
sistema calcula por operador la tasa de anulaciones, la proporción de ventas por debajo del precio de
lista y el faltante de inventario no explicado por merma, y que señala al operador cuyo patrón se
desvía del resto sin afirmar por sí solo que hubo fraude —la señal es para revisión humana—.

**Acceptance Scenarios**:

1. **Given** dos operadores con volumen de ventas comparable y uno de ellos con una tasa de
   anulaciones de venta muy superior, **When** se calcula el cruce por operador, **Then** el sistema
   señala a ese operador con su tasa de anulaciones y el período considerado, como indicador de
   posible sub-registro, sin bloquear ni sancionar nada.
2. **Given** un turno de un operador con una concentración de renglones de venta registrados por
   debajo del precio de lista vigente muy por encima de la de los demás turnos del mismo producto y
   sucursal, **When** se calcula el cruce, **Then** ese turno queda marcado como patrón atípico de
   precio, con los renglones que lo sustentan enumerados (explicable, Principio V).
3. **Given** un conteo físico de `001` con un faltante de inventario en un producto, del cual una
   parte está explicada por merma declarada (User Story 2), **When** se cruza el resto contra las
   ventas registradas y las anulaciones del período, **Then** el faltante no explicado se atribuye
   proporcionalmente a los turnos y operadores que manejaron ese producto en el período, y se
   registra como `anomalia_caja` de origen inventario.
4. **Given** un turno cuyo arqueo de efectivo cuadró exactamente (diferencia cero) pero cuyo operador
   presenta faltante de inventario no explicado y tasa de anulaciones atípica, **When** se revisa,
   **Then** el sistema muestra explícitamente que el arqueo cuadrado NO descarta el fraude, y prioriza
   la señal del cruce de inventario sobre la del arqueo.
5. **Given** un faltante de inventario que coincide en magnitud y momento con una merma ya declarada
   y clasificada, **When** se ejecuta el cruce, **Then** ese faltante se considera explicado y NO
   genera una señal de fraude ni una anomalía.
6. **Given** cualquier señal del cruce por operador, **When** se consulta, **Then** el sistema nunca
   la presenta como conclusión de fraude: la presenta como patrón que se desvía de una línea base
   (el comportamiento del resto de operadores y turnos), con los datos que la sustentan, para
   revisión de una persona.
7. **Given** un cruce por operador, **When** se presenta, **Then** cada señal se identifica por
   sucursal, operador y período; agregar señales de varias sucursales sin discriminar la de origen
   está PROHIBIDO.

---

### User Story 4 - Gestionar las anomalías de caja sin explicación (Priority: P4)

El encargado trabaja una lista de anomalías: cada diferencia detectada —de efectivo en un arqueo o de
inventario en un cruce— que no se explica por ninguna causa conocida (ni merma declarada, ni error de
cambio anotado, ni cancelación registrada fuera de turno) queda como `anomalia_caja` en estado "sin
explicación", pendiente de que una persona la revise y le asigne una resolución. El sistema no fuerza
ninguna clasificación ni cierra la anomalía por su cuenta.

**Why this priority**: es el residuo de las tres historias anteriores —lo que queda sin explicar
después de descontar merma, error de cambio y cancelaciones— y por eso va última: sin las tres
primeras no hay nada que dejar pendiente. Tiene valor independiente: convierte "algo no cuadra" en
una cola de trabajo concreta, atribuida y fechada, que alguien resuelve. Es también la garantía de
que el sistema nunca inventa una explicación: si no hay causa conocida, lo dice.

**Independent Test**: dada una diferencia de arqueo sin motivo anotado y un faltante de inventario no
explicado por merma, se puede verificar que ambos aparecen como `anomalia_caja` en estado "sin
explicación" con su origen (efectivo o inventario), su sucursal, su operador o turno y su período,
que una persona puede asignarles una resolución (por ejemplo, "error operativo confirmado",
"escalado a fraude", "ajuste aceptado") y que el sistema nunca cambia ese estado sin la acción de una
persona.

**Acceptance Scenarios**:

1. **Given** un arqueo con un faltante de efectivo sin motivo conocido anotado, **When** se cierra el
   arqueo, **Then** el sistema crea una `anomalia_caja` de origen efectivo en estado "sin
   explicación", atribuida al turno y operador, con el monto y el día local.
2. **Given** un faltante de inventario que el cruce por operador (User Story 3) no pudo explicar por
   merma declarada, **When** se ejecuta el cruce, **Then** se crea una `anomalia_caja` de origen
   inventario en estado "sin explicación", con el producto, la magnitud, los turnos y operadores
   implicados y el período del conteo.
3. **Given** una `anomalia_caja` en estado "sin explicación", **When** una persona la revisa y le
   asigna una resolución, **Then** el sistema guarda la resolución, quién la asignó y cuándo, y
   conserva el estado anterior en el historial de la anomalía.
4. **Given** una `anomalia_caja` abierta, **When** transcurre cualquier plazo, **Then** el sistema NO
   la cierra, NO la reclasifica y NO la oculta automáticamente: permanece visible hasta que una
   persona la resuelve.
5. **Given** una diferencia detectada que sí se explica por completo (merma declarada, error de
   cambio anotado o cancelación fuera de turno registrada), **When** se evalúa, **Then** NO se crea
   ninguna `anomalia_caja`: la anomalía es, por definición, lo que no tiene explicación conocida.
6. **Given** una consulta de anomalías de varias sucursales, **When** se presenta, **Then** cada
   anomalía se identifica por su sucursal; agregar sin discriminar la de origen está PROHIBIDO.

---

### Edge Cases

- **Turno cerrado sin ninguna venta**: su arqueo tiene "esperado en caja" igual a cero; si el
  efectivo contado también es cero, cuadra; cualquier sobrante contado sobre cero es una diferencia a
  revisar, no un error del sistema.
- **Sobrante de efectivo (no faltante)**: se registra igual que un faltante, con signo positivo. Un
  sobrante recurrente en los turnos de un mismo operador es tan señalable como un faltante (puede
  indicar cobros no registrados que luego se "cuadran" con la siguiente venta).
- **Fraude de "cobrar 5, registrar 3" con caja perfectamente cuadrada**: el arqueo da diferencia
  cero; el sistema NO concluye "sin novedad": el cruce de inventario por operador (User Story 3) es
  la única vía de detección y se ejecuta con independencia de que el arqueo haya cuadrado.
- **Faltante de inventario en un producto que varios operadores manejaron en el período**: el
  faltante no explicado se reparte entre los turnos que registraron movimiento de ese producto,
  proporcional a su participación; ningún operador queda señalado de forma exclusiva solo por eso —es
  un indicador, no una acusación—.
- **Merma declarada mayor que el faltante del conteo**: se registra la merma tal como se declaró y la
  discrepancia (merma declarada por encima de lo que el conteo respalda) se marca como anomalía de
  inventario de signo contrario, para revisión —una merma inflada puede encubrir una sustracción—.
- **Diferencia de conteo positiva (sobra inventario)**: no es merma; se registra como anomalía de
  inventario "sobrante" para revisión (suele ser un error de registro de entrada o de conteo previo).
- **Cancelación de una venta de un turno ya cerrado, hecha por un encargado (FR-049 de `001`)**: la
  anulación cuenta en la tasa de anulaciones del encargado que la ejecutó, no del operador de la
  venta original; el cruce por operador respeta esa atribución de `001`.
- **Operador con PIN reasignado a mitad de turno (Edge Case de `001`)**: las ventas y anulaciones del
  turno conservan la atribución al operador original; el cruce por operador usa esa atribución y no
  la del PIN nuevo.
- **Conteo físico parcial (`alcance` de `conteo_fisico` de `001` acotado a unos productos)**: el
  cruce de inventario solo se ejecuta sobre los productos incluidos en ese conteo; los no contados
  quedan sin cruzar hasta el siguiente conteo que los cubra, y eso se marca, no se oculta.
- **Producto sin costo de lote registrado**: la merma o la anomalía de inventario se registra con
  cantidad pero con valor "no calculable", nunca con valor cero (mismo criterio que `001` para
  capital inmovilizado).
- **Reloj del dispositivo desviado al cerrar un arqueo offline**: el arqueo hereda el tratamiento de
  reconciliación de `001` —marca de tiempo de origen conservada junto al instante de recepción— y su
  día local se resuelve cuando sincroniza.
- **Dos arqueos del mismo turno por reintento de sincronización**: la clave de idempotencia por turno
  impide el duplicado (Principio II); prevalece el primero por marca de tiempo de origen.

## Requirements *(mandatory)*

### Functional Requirements

**Fenómeno 2 — Arqueo de caja y diferencia caja-cobrado (User Story 1)**

- **FR-001**: El sistema DEBE permitir registrar un arqueo de caja asociado a un `turno` cerrado de
  `001`, con el efectivo y los comprobantes de otros medios de pago contados al cierre.
- **FR-002**: El sistema DEBE calcular "lo esperado en caja" de un turno como la suma de los cobros
  de las `venta` registradas en ese turno (consultando `venta` y su `id_turno` de `001`), sin
  modificar ninguna venta ni ningún total.
- **FR-003**: El arqueo DEBE registrar la diferencia entre lo contado y lo esperado, con su signo
  (sobrante o faltante), atribuida al operador del turno (derivado de `turno.id_operador` de `001`) y
  fechada por el **día local de la sucursal** (zona horaria de la sucursal, no día UTC).
- **FR-004**: El sistema DEBE permitir anotar, para una diferencia de arqueo, un motivo conocido
  (por ejemplo, "mal dado el cambio", "pago no registrado"). Una diferencia con motivo conocido
  anotado NO genera anomalía; una sin motivo queda disponible como posible `anomalia_caja` de origen
  efectivo (FR-027).
- **FR-005**: El sistema NO DEBE crear más de un arqueo por el mismo turno. Un reintento con la misma
  clave de idempotencia DEBE devolver el arqueo existente; una corrección se registra como ajuste del
  mismo arqueo, conservando visible el conteo anterior (Principio II).
- **FR-006**: El arqueo DEBE completarse aunque los servicios de inteligencia o analítica no
  respondan, y DEBE poder ejecutarse sin conectividad y reconciliarse con la regla de `001` (gana la
  marca de tiempo de origen más antigua sobre el mismo recurso).
- **FR-007**: El sistema DEBE dejar el arqueo de un turno sin ninguna venta con "esperado en caja"
  igual a cero, no como un error.
- **FR-008**: El arqueo de efectivo, por sí solo, NO DEBE usarse como señal de fraude por
  sub-registro. Una diferencia de arqueo igual a cero NO DEBE presentarse como evidencia de ausencia
  de fraude (Lectura Crítica n.º 1 de la constitución). La detección de ese fraude es competencia
  exclusiva del cruce inventario-ventas (FR-018 a FR-026).

**Fenómeno 1 — Merma física y su clasificación (User Story 2)**

- **FR-009**: El sistema DEBE permitir clasificar la causa de una diferencia de conteo físico que
  `001` ya expone en bruto (`conteo_renglon.diferencia`), con una de estas causas: vencimiento,
  daño, robo externo, error de conteo. El sistema NO DEBE reimplementar el conteo ni recalcular la
  diferencia bruta de `001`.
- **FR-010**: Cada merma clasificada DEBE valorarse como la cantidad faltante multiplicada por el
  costo del lote correspondiente (`lote.costo_unitario` de `001`; por kilogramo si el producto es
  granel). Un producto sin costo de lote registrado DEBE mostrar valor "no calculable", nunca cero.
- **FR-011**: Cada merma DEBE quedar atribuida a la sucursal y al período entre el conteo que la
  reveló y el conteo anterior del mismo alcance; NO DEBE atribuirse a un operador concreto por el
  solo hecho de ser merma (una merma física no es una sustracción).
- **FR-012**: El sistema DEBE permitir declarar una merma fuera de un conteo físico (rotura,
  vencimiento en estantería), con su producto, lote, cantidad, causa y valor, y DEBE señalar que esa
  merma se conciliará con el próximo conteo físico de `001`. Este módulo NO DEBE ajustar `existencia`
  ni `movimiento_inventario` de `001`.
- **FR-013**: El sistema DEBE permitir dejar una diferencia de conteo como merma "pendiente de
  clasificar" cuando el encargado no puede decidir la causa; NO DEBE imponer una causa por defecto.
- **FR-014**: El sistema DEBE exponer una alerta de caducidad para los `lote` de `001` cuya
  `fecha_caducidad` entra en una ventana de anticipación configurable, con la existencia restante del
  lote y su valor en riesgo. La alerta es informativa: el sistema NO DEBE dar de baja, descontar ni
  traspasar nada.
- **FR-015**: La diferencia de un producto a granel que `001` expone (peso vendido más peso restante
  menor que el peso que entró, FR-016 de `001`) DEBE poder clasificarse como merma de granel
  (deshidratación, merma de corte) con su valor sobre los gramos faltantes.
- **FR-016**: El sistema DEBE permitir desglosar el total de mermas de un período por causa, por
  producto y por sucursal, sin agregar entre sucursales sin discriminar la de origen.
- **FR-017**: La clasificación de merma es la política de contabilización de la pérdida que la
  constitución asigna a este módulo; la fecha de caducidad y la diferencia bruta del conteo siguen
  siendo propiedad de `001` y este módulo solo las consulta.

**Fenómeno 3 — Fraude por sub-registro: cruce inventario-ventas por operador (User Story 3)**

- **FR-018**: El sistema DEBE calcular, por operador y por turno, la **tasa de anulaciones de venta**
  (anulaciones sobre ventas del período), consultando `venta` y `anulacion_venta` de `001` y su
  atribución de operador (`anulacion_venta.id_operador` para quien anula, `turno.id_operador` para
  quien vendió).
- **FR-019**: El sistema DEBE calcular, por operador y por turno, la **concentración de renglones de
  venta registrados por debajo del precio de lista vigente**, comparando `renglon_venta.precio_aplicado`
  contra el precio efectivo del producto en esa sucursal (`producto.precio_vigente` o su override
  `producto_precio_sucursal`, FR-050 de `001`).
- **FR-020**: El sistema DEBE cruzar el **faltante de inventario** de un conteo físico de `001`, una
  vez descontada la merma declarada y clasificada (FR-009 a FR-013) y las cancelaciones registradas,
  contra las ventas registradas del mismo producto, sucursal y período, y atribuir el faltante no
  explicado a los turnos y operadores que manejaron ese producto en el período, de forma
  proporcional a su participación en el movimiento.
- **FR-021**: El cruce inventario-ventas por operador DEBE ejecutarse a cada **conteo físico
  periódico** de `001` y, además, bajo demanda cuando un indicador de FR-018 o FR-019 se desvía de
  su línea base. NO DEBE ejecutarse en cada venta ni exigir un conteo físico diario del catálogo
  completo (cadencia justificada en Assumptions).
- **FR-022**: Cada señal del cruce DEBE ser **explicable**: DEBE enumerar los datos que la sustentan
  (qué anulaciones, qué renglones bajo precio de lista, qué faltante de qué conteo) y el período
  considerado (Principio V).
- **FR-023**: El sistema DEBE presentar cada señal del cruce como una **desviación respecto de una
  línea base** —el comportamiento del resto de operadores y turnos comparables en la misma sucursal—
  y NUNCA como una conclusión de fraude. La resolución es de una persona.
- **FR-024**: El sistema NO DEBE bloquear, suspender ni sancionar a ningún operador de forma
  automática a partir de una señal del cruce (Principio V: consultiva por defecto; Principio II: la
  caja no se bloquea).
- **FR-025**: Un faltante de inventario que coincide en magnitud y momento con una merma ya declarada
  y clasificada, o con una cancelación registrada, DEBE considerarse explicado y NO DEBE generar
  señal de fraude ni anomalía.
- **FR-026**: El sistema DEBE dejar constancia de que un arqueo de efectivo cuadrado (diferencia
  cero) NO descarta un sub-registro, y DEBE priorizar la señal del cruce de inventario sobre la del
  arqueo cuando ambas difieren para el mismo operador y período.

**Fenómeno transversal — Anomalías de caja sin explicación (User Story 4)**

- **FR-027**: El sistema DEBE registrar como `anomalia_caja` toda diferencia detectada —de efectivo
  en un arqueo (FR-004) o de inventario en un cruce (FR-020)— que no se explique por ninguna causa
  conocida: ni merma declarada, ni error de cambio anotado, ni cancelación registrada fuera de turno.
- **FR-028**: Cada `anomalia_caja` DEBE registrar su **origen** (efectivo o inventario), su
  **estado** (por defecto `sin_explicacion`), su sucursal, el turno u operador implicado, el período
  y el monto o magnitud; y el producto, cuando el origen es inventario.
- **FR-029**: El sistema NO DEBE forzar una clasificación de una `anomalia_caja`, NO DEBE recortar su
  magnitud a cero y NO DEBE cerrarla ni ocultarla automáticamente por el paso del tiempo. Permanece
  visible hasta que una persona la resuelve (mismo criterio que la operación desplazada por conflicto
  de `001`, que nunca se oculta).
- **FR-030**: El sistema DEBE permitir que una persona asigne una resolución a una `anomalia_caja`
  (por ejemplo, "error operativo confirmado", "escalado a fraude", "ajuste aceptado"), registrando
  quién la asignó y cuándo, y conservando el estado anterior en el historial de la anomalía.
- **FR-031**: Una diferencia que sí se explica por completo por una causa conocida NO DEBE generar
  ninguna `anomalia_caja`: la anomalía es, por definición, lo que carece de explicación conocida.

**Frontera con `001-core-ventas-inventario` (propiedad de datos)**

- **FR-032**: El sistema NO DEBE registrar, modificar ni recalcular `venta`, `renglon_venta`,
  `anulacion_venta`, `existencia`, `movimiento_inventario`, `lote`, `conteo_fisico`,
  `conteo_renglon`, `turno`, `operador` ni ningún precio; todos son propiedad de `001` y este módulo
  solo los consulta.
- **FR-033**: El sistema NO DEBE ejecutar conteos físicos; la ejecución del conteo y la exposición de
  la diferencia bruta pertenecen a `001` (FR-029 a FR-032 de `001`). Este módulo consume esa
  diferencia y le asigna causa.
- **FR-034**: El sistema NO DEBE ajustar la existencia como consecuencia de una merma declarada fuera
  de conteo (FR-012); ese ajuste solo ocurre en `001` cuando el próximo conteo físico lo resuelve.
- **FR-035**: La atribución por operador DEBE apoyarse exclusivamente en los datos que `001` ya
  registra —`venta.id_turno` → `turno.id_operador`, `anulacion_venta.id_operador`— sin reimplementar
  la identificación por PIN ni acceder a `operador.pin_hash`. Este módulo no autentica a nadie.
- **FR-036**: Cuando `001` recomiende, a partir de una señal del cruce (FR-021), un conteo físico
  dirigido a unos productos, esa recomendación es **consultiva**: el encargado la ejecuta en `001` (o
  la descarta). Este módulo no inicia el conteo.

**Común a los tres fenómenos**

- **FR-037**: Los tres fenómenos —merma física, diferencia caja-cobrado y fraude por sub-registro—
  DEBEN modelarse como fenómenos distintos, con su propia lógica de detección y su propia entidad o
  registro. Tratarlos como una sola entidad genérica de "descuadre" está PROHIBIDO.
- **FR-038**: Toda detección, arqueo, merma y anomalía DEBE identificarse por sucursal. Agregar
  descuadres, mermas o señales de varias sucursales sin discriminar la de origen está PROHIBIDO
  (Principio IV y restricción multi-sucursal de la constitución).
- **FR-039**: Toda salida de este módulo —diferencia de arqueo, valor de merma, señal de cruce,
  anomalía— DEBE ser reconstruible a partir del registro: qué datos de `001` la originaron, qué
  período cubrió y qué cálculo se aplicó (Principio V: explicable, con línea base).
- **FR-040**: La inteligencia de este módulo es consultiva: detecta, atribuye y explica, pero NO
  ejecuta ajustes de inventario, bloqueos de operador ni sanciones de forma automática. La acción
  correctiva la decide una persona (Principio V).
- **FR-041**: El sistema DEBE permitir operar y demostrar cada fenómeno por separado; ninguno depende
  de la existencia de otro para funcionar, más allá de que la detección de fraude por sub-registro
  (FR-020) necesita las mermas ya clasificadas (FR-009) para descontarlas del faltante.

### Key Entities *(include if feature involves data)*

- **arqueo**: cuadre de una caja al cierre de un `turno` de `001`. Registra el efectivo y los
  comprobantes contados, "lo esperado en caja" (suma de los cobros del turno, consultada a `001`), la
  diferencia con su signo, el motivo conocido si se anotó, el operador del turno, la sucursal, el día
  local y la clave de idempotencia. Es NUEVA en este módulo: `001` tiene conteo físico de inventario
  (`conteo_fisico`) pero ninguna noción de arqueo de efectivo. Propiedad de este módulo.
- **merma**: pérdida de producto sin venta asociada, clasificada por causa (vencimiento, daño, robo
  externo, error de conteo, deshidratación / merma de corte para granel, o "pendiente de
  clasificar"). Referencia el `conteo_renglon` de `001` que la reveló —o ninguno, si se declaró fuera
  de conteo—, con su cantidad, su lote, su valor (cantidad × `lote.costo_unitario` de `001`, o "no
  calculable"), su sucursal y el período entre conteos. Es la política de contabilización de la
  pérdida que la constitución asigna a este módulo. Propiedad de este módulo.
- **anomalia_caja**: diferencia detectada —de efectivo o de inventario— que ninguna causa conocida
  explica. Registra su origen (efectivo / inventario), su estado (`sin_explicacion` por defecto, y
  las resoluciones que una persona le asigne), su sucursal, el turno u operador implicado, el
  período, el monto o magnitud, el producto cuando aplica, y el historial de cambios de estado con
  quién y cuándo. Se **calcula consultando** `movimiento_inventario`, `venta` y `anulacion_venta` de
  `001` (la constitución declara expresamente legítima esa consulta) y es la forma en que la Lectura
  Crítica n.º 1 exige detectar el fraude de "cobrar 5, registrar 3". Propiedad de este módulo.

Consultas derivadas de este módulo que NO son necesariamente tablas (su forma se decide en
`plan.md`): los **indicadores por operador** de FR-018 y FR-019 (tasa de anulaciones, concentración
de ventas bajo precio de lista) y el **cruce inventario-ventas** de FR-020. Se calculan a partir de
`001` en el momento de la consulta; si `plan.md` determina que necesitan materializarse en una tabla
propia para rendimiento o para conservar su historia, esa tabla sería una entidad nueva de este
módulo y exigiría la enmienda constitucional que se señala al final de este documento.

Entidades de `001` que este módulo consulta pero no posee (frontera de propiedad de datos):
`venta`, `renglon_venta` (`precio_aplicado`, `cantidad`), `anulacion_venta` (`id_operador`),
`turno` (`id_operador`, `instante_apertura`, `instante_cierre`), `operador` (solo `id_operador` y
`es_encargado`; **nunca** `pin_hash`), `sucursal` (`zona_horaria`, para el día local), `producto`
(`precio_vigente`, `es_granel`), `producto_precio_sucursal` (override, FR-050 de `001`), `lote`
(`costo_unitario`, `fecha_caducidad`), `existencia`, `movimiento_inventario` (`tipo`, `cantidad`),
`conteo_fisico` (`alcance`, `estado`), `conteo_renglon` (`diferencia`, `cantidad_contada`,
`cantidad_esperada`).

## Dependencias entre módulos

Esta sección es de lectura obligatoria antes de `/speckit-plan`: fija qué se puede construir ahora,
qué queda bloqueado, qué contratos se consumen y qué enmienda constitucional respalda —o no— las
entidades de este módulo. No debe quedar oculta en `plan.md`.

**Lo que este módulo consulta y no reimplementa** (mismo patrón que `003`, `004` y `005` frente a
`001`):

- De `001-core-ventas-inventario`: `venta` y su `id_turno` (para "lo esperado en caja" de un arqueo y
  para el volumen de ventas por operador), `anulacion_venta` con su `id_operador` (para la tasa de
  anulaciones), `renglon_venta.precio_aplicado` y el precio efectivo por sucursal
  (`producto.precio_vigente` / `producto_precio_sucursal`, FR-050) (para la concentración de ventas
  bajo precio de lista), `movimiento_inventario` y `existencia` (para el faltante de inventario),
  `conteo_fisico` y `conteo_renglon.diferencia` (para clasificar mermas y para el cruce),
  `lote.costo_unitario` (para valorar mermas y anomalías) y `lote.fecha_caducidad` (para la alerta de
  caducidad), `turno` y `operador` (para la atribución), `sucursal.zona_horaria` (para el día local).

**Verificaciones exigidas por el encargo — resueltas antes de escribir los FR**:

1. **Campos y tablas de `001` que ya existen para esto** (verificado contra
   `001/data-model.md`, constitución v2.2.6): `existencia` (agregación derivada, sin restricción de
   no negatividad), `movimiento_inventario` (con `tipo` ∈ {`entrada_compra`, `salida_venta`,
   `entrada_anulacion`, `salida_traspaso`, `entrada_traspaso`, `ajuste_conteo`} y `cantidad` con
   signo), `venta` (con `id_turno`, del que se derivan operador, sucursal y caja) y `renglon_venta`
   (`precio_aplicado` copiado al vender, `cantidad_unidades` / `cantidad_gramos`),
   `anulacion_venta` (con `id_operador` de quien anula, que puede no ser quien vendió, FR-049 de
   `001`), `lote` (`costo_unitario`, `fecha_caducidad DATE NULL`, `instante_entrada`),
   `operador` (`pin_hash`, `es_encargado`) y `turno` (`id_operador`, apertura y cierre).
   **Conclusión**: `006` consulta estas tablas, no las reimplementa; sigue el mismo patrón de
   frontera que `003`/`004`/`005`.
2. **¿`001` ya tiene "arqueo" o "conteo físico" parcial, o lo introduce `006`?** `001` **sí** tiene
   conteo físico de inventario —`conteo_fisico` con `alcance JSONB` (subconjunto de productos o
   categorías; nulo ⇒ toda la sucursal), `estado` ∈ {`abierto`, `resuelto`}, y `conteo_renglon` con
   `diferencia` como columna generada (contada − esperada)—, y ese conteo **ya es parcial**. `001`
   **NO** tiene ninguna noción de **arqueo de caja / cuadre de efectivo por turno**. Por tanto:
   `006` **introduce `arqueo` por primera vez** y **reutiliza** `conteo_fisico` de `001` para el lado
   de inventario, sin ejecutar conteos (la constitución ya declara esa frontera: "el conteo físico y
   la diferencia bruta pertenecen a `001`; la clasificación de la causa pertenece a `006`, que no
   ejecuta conteos").
3. **Atribución por operador sin reimplementar autenticación**: confirmado. Cada `venta` lleva
   `id_turno` y cada `turno` lleva `id_operador`; cada `anulacion_venta` lleva `id_operador`. `006`
   obtiene la atribución con un `JOIN` sobre datos que `001` ya registra en cada venta y cada
   cancelación. El PIN de 4 dígitos (`operador.pin_hash`) es el mecanismo de identificación de `001`
   y `006` **no lo necesita ni lo consulta**: no autentica a nadie (FR-035).
4. **Diferencia detectada que no se explica por ningún motivo conocido**: se registra como
   `anomalia_caja` en estado `sin_explicacion`, pendiente de revisión manual (FR-027 a FR-031). El
   sistema **no fuerza** ninguna clasificación. Decisión tomada, no `NEEDS CLARIFICATION` (mismo
   criterio que `001` con la operación desplazada por conflicto: permanece visible, nunca se oculta).

**BLOQUEO explícito de implementación (no oculto)** — mismo tipo de bloqueo que `004` declara frente
a `consulta_no_atendida`:

- El último checkpoint del proyecto cubre `001` Setup + Foundational + User Story 1. `turno`,
  `venta`, `renglon_venta` y `anulacion_venta` están implementadas; **`conteo_fisico` y
  `conteo_renglon` (User Story 5 de `001`) están especificadas pero no implementadas**.
- En consecuencia:
  - **User Story 1 de `006` (arqueo de caja)**: NO bloqueada. Solo necesita `turno` y `venta`.
  - **User Story 2 de `006` (clasificar mermas)**: la clasificación de diferencias de conteo está
    **bloqueada** hasta que `001` implemente su User Story 5. La **alerta de caducidad** (FR-014) y
    la **declaración de merma fuera de conteo** (FR-012) solo necesitan `lote` y no están bloqueadas.
  - **User Story 3 de `006` (cruce por operador)**: la **tasa de anulaciones** (FR-018) y la
    **concentración de ventas bajo precio de lista** (FR-019) solo necesitan `venta`,
    `anulacion_venta` y `renglon_venta`, ya disponibles → NO bloqueadas. El **cruce contra el
    faltante de inventario** (FR-020) necesita `conteo_fisico` → **bloqueado** hasta `001` User
    Story 5.
  - **User Story 4 de `006` (anomalías)**: parcialmente operable (anomalías de origen efectivo desde
    US1); las de origen inventario esperan al desbloqueo de US2/US3.
- **Este spec se puede escribir y aprobar ahora.** El bloqueo es de implementación y se marca en
  `plan.md`, igual que en `004`.

**Contrato con `005-promociones-inteligentes`**: ninguno directo. `005` expone una marca de
"promoción activa" que consume `004`; `006` no la consume. Una venta bajo promoción registrada por
`001` con `precio_aplicado` por debajo del precio de lista podría, en principio, inflar el indicador
de FR-019; `plan.md` decide si el indicador excluye los períodos con promoción activa de `005` cuando
`005` exista (refinamiento, no bloqueo — hasta entonces todos los períodos se tratan sin promoción,
igual que hace `004`).

**Propiedad de datos — estado frente a la constitución (v2.2.6)**: la tabla de Propiedad de Datos
lista para `006-caja-mermas-fraude` tres entidades: `arqueo`, `merma`, `anomalia_caja`. **Este spec
usa exactamente esas tres y ninguna más.** A diferencia de `003` (v2.2.3, `costo_producto` →
`sugerencia_precio`), `004` (v2.2.4, + `sustitucion_producto`) y `005` (v2.2.5, de 3 a 6 entidades),
**este spec NO requiere enmienda constitucional para ser escrito, aprobado ni implementado en el
alcance aquí definido**. La constitución ya previó, además, que `anomalia_caja` "se calcula
consultando `movimiento_inventario`, `venta` y `anulacion_venta`" y que esa es "la forma en que la
Lectura Crítica n.º 1 exige detectar el fraude" — es decir, los indicadores por operador y el cruce
de FR-018 a FR-020 son **cálculo derivado dentro de `anomalia_caja`**, no entidades separadas.

**Punto pendiente de verificación en `/speckit-plan` (posible enmienda, NO hecha aquí)**: si
`data-model.md` concluye que los indicadores por operador (FR-018, FR-019) o el cruce (FR-020) deben
**materializarse en una tabla propia** —para conservar su historia, para rendimiento, o para que una
`anomalia_caja` de origen inventario referencie una fila estable en vez de recalcularse— esa tabla
(candidata: `senal_fraude_operador` o `indicador_operador`) sería una **cuarta entidad nueva de
`006`** y exigiría una enmienda de la tabla de Propiedad de Datos **antes** de `/speckit-plan`, del
mismo tipo que v2.2.3/v2.2.4/v2.2.5. La expectativa a día de hoy es que **no haga falta** (el cálculo
derivado sobre `001` basta y la constitución así lo anticipa), pero la decisión final es de
`data-model.md`, igual que ocurrió con `003`, `004` y `005`. Lo mismo aplica, con menor
probabilidad, a un eventual `conteo_efectivo` (líneas del arqueo desglosadas por medio de pago) si
`plan.md` decide desglosar el efectivo contado por medio de pago en vez de un total único — hoy se
modela como campos de `arqueo` y se difiere el desglose por medio de pago a cuando exista
`007-pagos-seguridad` (dueño de `medio_pago`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los turnos cerrados puede arquearse, y el arqueo atribuye la diferencia al
  operador del turno y al día local de la sucursal en el 100% de los casos.
- **SC-002**: El 100% de los arqueos calcula "lo esperado en caja" como la suma de los cobros del
  turno sin modificar ninguna `venta` ni ningún `total` de `001` (0% de escrituras sobre datos de
  `001`).
- **SC-003**: Ante reintentos del cierre de un mismo arqueo con la misma clave de idempotencia, se
  registra exactamente un arqueo por turno (0% de duplicados).
- **SC-004**: Un arqueo de efectivo con diferencia cero nunca se presenta como evidencia de ausencia
  de fraude por sub-registro (0% de los casos): la detección de ese fraude siempre pasa por el cruce
  inventario-ventas.
- **SC-005**: El 100% de las mermas clasificadas queda valorado al costo del lote correspondiente, o
  marcado como "no calculable" cuando falta el costo; ninguna merma se valora en cero por falta de
  costo.
- **SC-006**: El 100% de las mermas y anomalías se puede filtrar y desglosar por sucursal, causa y
  producto; ninguna vista agrega varias sucursales sin discriminar la de origen.
- **SC-007**: El 100% de las señales del cruce por operador es explicable: enumera las anulaciones,
  los renglones bajo precio de lista y el faltante de conteo que la sustentan, y el período
  considerado.
- **SC-008**: Ninguna señal del cruce por operador se presenta como conclusión de fraude ni provoca
  bloqueo, suspensión o sanción automática de un operador (0% de acciones automáticas sobre
  personas).
- **SC-009**: El 100% de las diferencias detectadas sin explicación conocida queda registrada como
  `anomalia_caja` en estado `sin_explicacion`; 0% de anomalías cerradas, reclasificadas u ocultadas
  por el sistema sin la acción de una persona.
- **SC-010**: El 100% de las diferencias que sí tienen explicación completa (merma declarada, error
  de cambio anotado, cancelación registrada) NO genera ninguna `anomalia_caja`.
- **SC-011**: 0% de operaciones de `006` que registran, modifican o recalculan `venta`, `existencia`,
  `movimiento_inventario`, `lote`, `conteo_fisico`, `conteo_renglon`, `turno`, `operador` o cualquier
  precio de `001`.
- **SC-012**: El faltante de inventario de un conteo que coincide con una merma ya declarada y
  clasificada se marca como explicado en el 100% de los casos y no genera señal de fraude ni anomalía
  duplicada.

## Assumptions

- **Cadencia del arqueo de caja**: por **cierre de turno**, no por día. Un turno es una franja de
  pocas horas atribuida a un operador (`turno` de `001`), así que arquear por turno es lo que ata una
  diferencia a un responsable y a una ventana estrecha —exactamente lo que el enunciado dice que un
  cierre diario no permite—. Contar efectivo al cierre de turno es una operación barata y ya habitual
  en un minimarket; no introduce carga operativa nueva significativa.
- **Cadencia del cruce inventario-ventas (fenómeno 3)**: se ejecuta a cada **conteo físico
  periódico** de `001` y, además, bajo demanda cuando un indicador por operador se desvía. NO en cada
  venta (inviable), NO diario sobre el catálogo completo (irreal para un comercio de barrio). Se
  asume que el negocio programa los conteos de `001` en una **rotación semanal por categoría**, con
  los frescos y los productos de alto valor/alta rotación contados con más frecuencia; el valor
  exacto del calendario lo fija el negocio al operar, no este spec. Esta cadencia captura el
  sub-registro en cuestión de días y lo mantiene atribuible a los turnos —y por tanto a los
  operadores— que trabajaron en ese intervalo, porque los turnos quedan registrados en `001`.
- **"Lo esperado en caja" de un turno**: suma de los `venta.total` de las ventas de ese turno. En
  esta versión no se desglosa por medio de pago (efectivo vs. tarjeta vs. transferencia) porque
  `001` solo guarda una `referencia_terminal_pago` opaca y el catálogo de medios de pago
  (`medio_pago`) es propiedad de `007-pagos-seguridad`, aún no construido. Cuando `007` exista, el
  desglose por medio de pago será un refinamiento aditivo. Hasta entonces, el arqueo compara el total
  contado (efectivo + comprobantes) contra el total registrado.
- **Valoración de la merma y de la anomalía de inventario**: cantidad faltante × `lote.costo_unitario`
  del lote correspondiente (el que la política FEFO de `001` —caducidad primero, entrada como
  desempate— habría consumido). No se promedia el costo entre lotes. Un producto sin costo de lote se
  muestra "no calculable", nunca cero (mismo criterio que `001` para capital inmovilizado).
- **Ventana de alerta de caducidad**: configurable, por categoría, con un valor global de respaldo
  —mismo patrón que el umbral de capital inmovilizado de `001` (`categoria.dias_umbral_inmovilizado`
  con umbral global de respaldo)—. El valor concreto lo fija el negocio; `plan.md` decide si reutiliza
  el umbral de inmovilizado o define uno propio para caducidad.
- **Atribución del faltante de inventario no explicado**: se reparte entre los turnos que registraron
  movimiento del producto en el período, proporcional a las unidades que cada turno movió. Es un
  indicador para revisión, no una imputación individual: ningún operador queda señalado en exclusiva
  solo por haber trabajado en el período. El método exacto de reparto (proporcional simple u otro) se
  afina en `plan.md` dentro de este criterio.
- **Línea base del cruce por operador**: el comportamiento del resto de operadores y turnos
  comparables de la misma sucursal en el mismo período. Una señal se emite cuando un operador se
  desvía de esa línea base por encima de un margen que `plan.md` fija y calibra; la familia de
  comparación (desviación respecto de la mediana o media de pares comparables) ya está decidida y no
  se reabre.
- **Anomalía sin explicación**: una diferencia que no encaja en merma declarada, error de cambio
  anotado ni cancelación registrada se registra como `anomalia_caja` estado `sin_explicacion`,
  pendiente de revisión manual. El sistema nunca fuerza una clasificación ni cierra la anomalía por
  el paso del tiempo. Ajustar esta decisión en el futuro es una enmienda de este spec.
- **`006` no ejecuta conteos ni ajusta existencia**: la ejecución del conteo físico y el ajuste de
  `existencia` pertenecen a `001` (frontera ya escrita en la constitución). Una merma declarada fuera
  de conteo (FR-012) queda pendiente de conciliarse con el próximo conteo de `001`; `006` solo la
  registra y la valora.
- **Recomendación de conteo dirigido**: cuando una señal del cruce sugiere contar unos productos,
  `006` **recomienda**; el encargado inicia el conteo en `001` o lo descarta. `006` no tiene un
  contrato que dispare conteos en `001` (Principio V: consultiva por defecto).
- **Datos personales**: `006` no captura ningún dato de cliente. Solo consulta el `id_operador` y su
  condición de encargado; nunca el PIN ni el hash del PIN. Los rastros de este módulo no contienen
  datos de pago completos (constitución, Principio IV).
- **Constitución vigente citada**: v2.2.6. Este módulo **no motivó ninguna enmienda** (v2.2.6, sobre
  la entrada de `007-pagos-seguridad`, es posterior y sin efecto sobre este módulo): sus tres
  entidades (`arqueo`, `merma`, `anomalia_caja`) coinciden con la tabla de Propiedad de Datos desde
  la ratificación. El único punto que podría motivar una (una cuarta entidad para materializar los
  indicadores por operador) se decide en `data-model.md` y se ha señalado explícitamente en
  "Dependencias entre módulos", sin resolverlo aquí.
- **Decisiones de alcance mayor, todas resueltas — ninguna quedó con default silencioso**: la
  cadencia del cruce (FR-021) y el tratamiento de la diferencia sin explicación (FR-027 a FR-031) se
  fijaron con una decisión razonable documentada, por indicación explícita del encargo. Ajustar
  cualquiera de ellas en el futuro es una enmienda de este spec, no una decisión libre de `plan.md`.
