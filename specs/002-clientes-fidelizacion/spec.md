# Feature Specification: Clientes y Fidelización

**Feature Branch**: `002-clientes-fidelizacion` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-04

**Status**: Draft

**Input**: Medir el valor real de cada cliente (no solo su gasto total, sino combinando frecuencia
de compra y margen de los productos que compra) y detectar señales de fuga silenciosa derivando,
para cada cliente, un intervalo de compra esperado a partir de su propio historial — nunca un
umbral global de inactividad aplicado a todos por igual. La entidad cliente incluye fecha de
nacimiento porque el enunciado exige un cupón de cumpleaños, aunque decidir y emitir ese cupón (y
cualquier otra promoción) pertenece a `005-promociones-inteligentes`; esta funcionalidad solo mide
valor y detecta fuga, y expone esas señales para que otra funcionalidad decida sobre ellas.

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-04

- Q: ¿Qué finalidad y periodo de retención tienen los datos personales del cliente (fecha de
  nacimiento y contacto)? → A: la finalidad es exclusivamente el análisis de valor de cliente y
  detección de fuga de esta funcionalidad; ningún otro uso. El periodo de retención no es un plazo
  fijo global: se ata al propio intervalo de compra esperado del cliente. Cuando el tiempo sin
  visita alcanza 5 veces ese intervalo — con un piso de 12 meses, para que un cliente muy frecuente
  no se anonimice tras una ausencia corta en términos absolutos aunque grande en relación con su
  propio ritmo — la fuga se considera confirmada. A partir de ahí se conserva el dato 90 días más y
  luego se anonimiza automáticamente, conservando solo métricas agregadas que no identifican a la
  persona (ver FR-002, FR-014, FR-015).
- Q: ¿Es obligatorio identificar al cliente en el punto de venta? → A: no. Es opcional, a criterio
  del cajero, por la misma razón que ninguna otra validación en `001-core-ventas-inventario` es
  bloqueante: el Principio II de la constitución exige que la caja no se detenga y prohíbe que
  cualquier función de analítica o fidelización sea camino crítico de un cobro. Forzar la
  identificación introduciría exactamente el tipo de bloqueo que ese principio prohíbe (ver
  FR-003).
- Q: ¿Cómo se presenta el valor de cliente — puntuación única, desglose de sus tres dimensiones, o
  ambos? → A: ambos, mapeados a los dos registros visuales que la constitución ya define. La
  puntuación compuesta, como resumen, vive en el registro de Operación — visible al identificar al
  cliente durante una venta, sin interrumpir el cobro. El desglose de frecuencia, monto y margen
  vive en el registro de Análisis, donde el negocio revisa el detalle con calma (ver FR-011).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mantener el catálogo de clientes y su historial de visitas (Priority: P1)

El personal de tienda registra clientes con su nombre y fecha de nacimiento, y cada vez que un
cliente registrado se identifica al completar una compra, esa compra queda anotada como una visita
en su historial. Sin este historial acumulado, ni el valor de cliente ni la detección de fuga
tienen datos sobre los que calcularse.

**Why this priority**: Es la base de datos de la que dependen las otras dos historias. Sin clientes
registrados y sin visitas vinculadas a sus ventas no hay nada que medir ni que vigilar.

**Independent Test**: Se puede probar registrando un cliente nuevo y completando una venta
identificándolo; el historial de ese cliente debe reflejar la visita sin necesidad de que exista
todavía ningún cálculo de valor o de fuga.

**Acceptance Scenarios**:

1. **Given** que un cliente no está registrado, **When** se registra con nombre y fecha de
   nacimiento, **Then** queda disponible para ser identificado en ventas futuras.
2. **Given** un cliente ya registrado, **When** se completa una venta identificándolo, **Then** se
   crea una visita vinculada a esa venta, con su fecha, monto total y margen total.
3. **Given** una venta que no identifica a ningún cliente, **When** se completa, **Then** no se crea
   ninguna visita ni se altera el historial de ningún cliente registrado.
4. **Given** un cajero cobrando con clientes esperando, **When** decide no identificar al cliente
   para no demorar el cobro, **Then** la venta se completa igual de rápido que si lo hubiera
   identificado; identificarlo nunca añade un paso obligatorio ni bloqueante.

---

### User Story 2 - Medir el valor real de cada cliente (Priority: P2)

El negocio consulta un listado de clientes en el que el valor de cada uno combina cuánto compra,
con qué frecuencia y qué margen dejan los productos que elige — no solo cuánto ha gastado en total
— para poder distinguir a quién realmente conviene prestar atención preferente.

**Why this priority**: Es el primer análisis diferenciador que el negocio pidió explícitamente
frente al criterio de "gasto total" que hoy usa por impresión. Depende de que existan visitas
(User Story 1), pero es demostrable en cuanto hay un conjunto mínimo de datos.

**Independent Test**: Con un conjunto de clientes de prueba que combinen distintas proporciones de
monto, frecuencia y margen, se puede verificar que el orden resultante no coincide con un ranking
por monto total simple, y que la misma puntuación aparece como resumen en un contexto y como
desglose en otro.

**Acceptance Scenarios**:

1. **Given** dos clientes con el mismo monto total acumulado pero distinta frecuencia de visitas o
   distinto margen, **When** se consulta su valor, **Then** el sistema los distingue y no los
   presenta como equivalentes.
2. **Given** un cliente cuyo historial de visitas todavía es insuficiente, **When** se consulta su
   valor, **Then** el sistema lo distingue explícitamente en vez de asignarle un valor por defecto
   o de omitirlo silenciosamente.
3. **Given** un cliente identificado durante una venta en curso, **When** el cajero lo visualiza en
   el registro de Operación, **Then** ve únicamente la puntuación compuesta de su valor, sin el
   desglose completo, para no interrumpir el flujo de cobro.
4. **Given** el negocio revisando el listado de clientes en el registro de Análisis, **When** abre
   el detalle de un cliente, **Then** ve el desglose de frecuencia, monto y margen que sustenta esa
   puntuación.

---

### User Story 3 - Detectar señales de fuga silenciosa por cliente (Priority: P3)

El negocio consulta qué clientes muestran señales de posible abandono, calculadas contra el propio
ritmo histórico de compra de cada uno — nunca contra un número fijo de días aplicado a toda la
base de clientes por igual.

**Why this priority**: Es valiosa pero depende de tener historial acumulado (User Story 1) y
complementa, sin bloquear, la medición de valor (User Story 2). Es la última en construirse porque
su señal solo es confiable cuando ya hay suficiente historial de visitas.

**Independent Test**: Con historiales de visitas de prueba variados por cliente, se puede verificar
que la señal se activa según el patrón propio de cada cliente y no según un umbral compartido con
otros clientes.

**Acceptance Scenarios**:

1. **Given** un cliente con un intervalo de compra esperado derivado de su propio historial,
   **When** transcurre más tiempo que ese intervalo desde su última visita sin una nueva, **Then**
   se genera una señal de fuga para ese cliente.
2. **Given** un cliente con una señal de fuga activa, **When** el cliente registra una nueva
   visita, **Then** la señal se marca como resuelta y su histórico se conserva.
3. **Given** dos clientes con ritmos históricos de compra distintos, **When** ambos llevan la misma
   cantidad de días sin comprar, **Then** el sistema puede marcar a uno en riesgo y al otro no,
   según el historial propio de cada uno.
4. **Given** un cliente cuyo tiempo sin visita alcanza 5 veces su propio intervalo esperado (o 12
   meses, lo que sea mayor), **When** se cumple ese umbral, **Then** su fuga se marca como
   confirmada y comienza el periodo de retención breve de sus datos personales.
5. **Given** un cliente con la fuga confirmada dentro del periodo de retención de 90 días, **When**
   el cliente vuelve a comprar antes de que ese periodo venza, **Then** la anonimización programada
   se cancela y la señal se resuelve igual que cualquier otra reactivación.

---

### Edge Cases

- ¿Qué pasa con un cliente cuyo historial de visitas todavía es demasiado corto para calcular un
  intervalo confiable? Queda en un estado explícito de "datos insuficientes"; nunca se le asigna un
  intervalo por defecto ni se le clasifica como "en riesgo" o "sin riesgo" (ver FR-007).
- ¿Qué pasa si el margen de un producto cambia en `003-precios-margenes` después de que ya se
  registró una visita que lo incluía? El margen de esa visita ya registrada no se recalcula
  retroactivamente; queda fijado al momento en que ocurrió la visita.
- ¿Qué pasa con una venta que no identifica a ningún cliente? No genera visita ni afecta el valor o
  la fuga de ningún cliente (ver FR-004).
- ¿Qué pasa cuando un cliente readmitido tras una señal de fuga resuelta vuelve a cambiar su ritmo
  de compra? El intervalo esperado se recalcula con cada nueva visita, reflejando siempre el
  patrón más reciente de ese cliente, no el que tenía al momento del registro.
- ¿Qué pasa si dos clientes distintos comparten nombre o datos de contacto? La deduplicación de
  identidad está fuera de alcance de esta funcionalidad; se asume que cada registro de cliente
  corresponde a una persona distinta.
- ¿Qué pasa con un cliente muy frecuente (por ejemplo, intervalo esperado de 7 días) que deja de
  comprar? Su señal de fuga se detecta pronto (FR-008), pero sus datos personales no se anonimizan
  hasta que pasen al menos 12 meses sin compra — el piso de FR-014 —, no 5 veces su intervalo corto,
  para no borrar prematuramente a alguien con una ausencia todavía breve en términos absolutos.
- ¿Qué pasa si un cliente con la fuga confirmada y en periodo de retención vuelve a comprar? Se
  cancela la anonimización programada y la señal se resuelve como cualquier otra (ver Acceptance
  Scenario 5 de User Story 3 y FR-015).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar un cliente con al menos nombre y fecha de
  nacimiento; los datos de contacto (teléfono o correo) son opcionales.
- **FR-002**: El sistema DEBE conservar los datos personales del cliente (fecha de nacimiento y
  contacto, cuando exista) exclusivamente con la finalidad de calcular su valor y detectar su fuga
  en esta funcionalidad, y por el periodo variable que define FR-014 y FR-015 — nunca por un plazo
  fijo igual para todos los clientes ni para ninguna otra finalidad.
- **FR-003**: El sistema DEBE permitir identificar a un cliente ya registrado al momento de una
  venta, a criterio del cajero, vinculando esa venta como una visita de ese cliente. Identificar al
  cliente NO DEBE ser nunca un paso obligatorio ni bloqueante para completar la venta: forzarlo
  violaría el Principio II de la constitución (Fiabilidad Operativa en el Punto de Venta), que
  prohíbe que cualquier función de analítica o fidelización sea camino crítico de un cobro.
- **FR-004**: Una venta que no identifica cliente NO DEBE generar ninguna visita ni afectar el
  cálculo de valor o de fuga de ningún cliente.
- **FR-005**: Cada visita DEBE registrar la fecha, el monto total y el margen total de la venta que
  la originó, consultando el margen ya calculado por la funcionalidad de márgenes
  (`003-precios-margenes`) al momento en que ocurre la visita.
- **FR-006**: El sistema DEBE calcular, para cada cliente con historial suficiente, un intervalo de
  compra esperado derivado exclusivamente del propio historial de visitas de ese cliente. Aplicar
  el mismo intervalo o el mismo umbral de inactividad a todos los clientes por igual está
  PROHIBIDO.
- **FR-007**: Un cliente cuyo historial de visitas no alcance el mínimo necesario para calcular un
  intervalo confiable DEBE distinguirse explícitamente con un estado de "datos insuficientes",
  nunca con un intervalo por defecto ni con una clasificación de riesgo.
- **FR-008**: El sistema DEBE generar una señal de fuga para un cliente cuando este supere su
  propio intervalo de compra esperado sin registrar una nueva visita.
- **FR-009**: El sistema DEBE marcar como resuelta una señal de fuga activa cuando el cliente
  correspondiente registre una nueva visita, conservando el histórico de la señal en vez de
  eliminarlo.
- **FR-010**: El sistema DEBE calcular un valor de cliente que combine frecuencia de visitas, monto
  total y margen total de sus compras, de forma que dos clientes con el mismo monto total pero
  distinta frecuencia o margen puedan quedar clasificados de forma distinta.
- **FR-011**: El sistema DEBE presentar el valor de cliente en dos niveles, mapeados a los dos
  registros visuales de la constitución: (a) una puntuación compuesta, como resumen, en el registro
  de Operación — por ejemplo al identificar al cliente durante una venta —, para una lectura rápida
  que no interrumpe el cobro; y (b) el desglose de las tres dimensiones (frecuencia, monto, margen)
  en el registro de Análisis, donde el negocio revisa el detalle.
- **FR-012**: El sistema DEBE exponer qué clientes registrados cumplen años en una fecha o rango de
  fechas dado, para que otra funcionalidad pueda consumir ese dato.
- **FR-013**: El sistema NO DEBE crear, aplicar, recomendar ni decidir ningún cupón, descuento o
  acción promocional. El valor de cliente, la fecha de cumpleaños y las señales de fuga se exponen
  únicamente como datos para que `005-promociones-inteligentes` decida sobre ellos.
- **FR-014**: El sistema DEBE considerar la fuga de un cliente como confirmada — a efectos
  únicamente de retención de datos personales, un estado distinto y posterior al de "activa" que ya
  dispara FR-008 — cuando el tiempo transcurrido desde su última visita alcance o supere el mayor
  entre: cinco veces (5×) su propio intervalo de compra esperado, o 12 meses sin visita.

  **Razón de 5×**: la señal "activa" de FR-008 ya se dispara a 1× el intervalo esperado, y es
  barata de equivocar — solo alimenta una posible reactivación en `005`, reversible y sin costo si
  el cliente vuelve. La confirmación de FR-014, en cambio, dispara un acto irreversible: la
  anonimización de FR-015 borra el dato antes de que `005` pueda siquiera evaluar una reactivación
  informada. El múltiplo debe separar con margen amplio "quizás saltó un ciclo de compra" (todavía
  útil para `005`) de "ya no cabe esperar retorno con estos datos". Un múltiplo bajo (2×-3×) sigue
  disparando sobre variación normal de un cliente irregular; uno muy alto (15×-20×) retiene datos
  personales mucho más allá de cualquier finalidad activa, en contra del principio de minimización
  de datos que exige la constitución. 5× es la elección de partida en ese punto medio: un orden de
  magnitud por encima de la señal reversible, sin llegar a la retención indefinida.

  **Razón del piso de 12 meses**: ancla el umbral a un ciclo estacional completo (un año
  calendario) con independencia del intervalo propio del cliente. Sin este piso, un cliente muy
  frecuente (ej. intervalo esperado de 7 días) se anonimizaría tras apenas 35 días de ausencia
  (5×7), un plazo demasiado corto en términos absolutos —cubre ni siquiera una temporada— para
  concluir que no va a volver, aunque sea grande en relación con su propio ritmo. Doce meses
  garantiza que ningún cliente se anonimice antes de haber tenido, como mínimo, una oportunidad de
  volver en cada época del año en que suele comprar.

  **Estado de la decisión**: 5× y 12 meses son una política de arranque razonada, no un valor
  calibrado con datos de producción — ese ajuste estadístico no es posible antes de tener historial
  real de clientes. Se documentan aquí como los valores vigentes; ajustarlos a la luz de datos
  reales es una enmienda de este spec, no una decisión libre de implementación (ver Assumptions).
- **FR-015**: Tras confirmarse la fuga de un cliente según FR-014, el sistema DEBE conservar sus
  datos personales (fecha de nacimiento y contacto) durante un periodo de retención adicional de 90
  días, y anonimizarlos automáticamente al vencer ese periodo sin que el cliente haya vuelto a
  comprar. Si el cliente registra una nueva visita en cualquier momento antes de vencer ese periodo,
  el sistema DEBE cancelar la anonimización programada.
- **FR-016**: Al anonimizar los datos personales de un cliente, el sistema DEBE conservar
  únicamente las métricas agregadas de valor y de fuga ya calculadas, sin ningún dato que permita
  reidentificar a la persona.

### Key Entities *(include if feature involves data)*

- **Cliente**: persona identificada del comercio; nombre, fecha de nacimiento (única base del
  cupón de cumpleaños que decide y emite `005`), datos de contacto opcionales, fecha de alta. Tras
  la anonimización de FR-015/FR-016, conserva solo un identificador técnico y sus métricas
  agregadas, sin nombre, fecha de nacimiento ni contacto. Propiedad de esta funcionalidad.
- **Visita**: registro de que un cliente identificado realizó una compra; referencia a la venta de
  origen (propiedad de `001-core-ventas-inventario`), fecha, monto total y margen total de esa
  compra (margen consultado en `003-precios-margenes` al momento de la visita, no recalculado
  después). Propiedad de esta funcionalidad.
- **Intervalo de compra**: por cliente, el ritmo de compra esperado derivado exclusivamente de su
  propio historial de visitas; incluye un estado explícito de "datos insuficientes" cuando el
  historial no alcanza el mínimo necesario. Es también la base de los umbrales de FR-008 (fuga
  activa) y FR-014 (fuga confirmada, a 5× este intervalo o 12 meses). Propiedad de esta
  funcionalidad.
- **Señal de fuga**: marca que un cliente superó su propio intervalo de compra esperado sin una
  nueva visita. Distingue tres estados: activa (recién detectada, consumible por `005` para
  evaluar una posible reactivación), confirmada (superó el umbral de FR-014 y dispara la retención
  breve de FR-015) y resuelta (el cliente volvió a comprar, en cualquiera de los dos estados
  anteriores). Conserva cuándo se detectó y, si aplica, cuándo se resolvió. Propiedad de esta
  funcionalidad. La detección pertenece aquí; la decisión de ofrecer un descuento de reactivación
  pertenece a `005-promociones-inteligentes`, que la consume.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los clientes con dos o más visitas registradas cuenta con un intervalo de
  compra esperado calculado exclusivamente a partir de su propio historial, sin compartir ese
  cálculo con ningún otro cliente.
- **SC-002**: Un cliente de alto gasto total pero baja frecuencia y bajo margen puede quedar
  clasificado por debajo de un cliente de menor gasto pero mayor frecuencia y margen, demostrando
  que el valor no se basa solo en el monto acumulado.
- **SC-003**: El personal puede determinar si un cliente específico muestra señal de fuga
  silenciosa, y desde cuándo, consultando una sola vista de ese cliente.
- **SC-004**: Ningún cliente con historial por debajo del mínimo necesario aparece clasificado como
  "en riesgo" ni como "sin riesgo": aparece explícitamente como "datos insuficientes".
- **SC-005**: El 100% de las señales de fuga y de los valores de cliente calculados quedan
  disponibles para que `005-promociones-inteligentes` los consulte, sin que esta funcionalidad
  dispare, aplique o recomiende ninguna acción promocional por sí misma.
- **SC-006**: Identificar a un cliente durante una venta no añade tiempo perceptible al cobro
  frente a una venta sin cliente identificado.
- **SC-007**: El 100% de los clientes cuya fuga permanece confirmada más de 90 días sin una nueva
  visita quedan anonimizados automáticamente, sin intervención manual, y sin que ningún dato
  personal sobreviva a ese proceso.

## Assumptions

- El margen de una visita se fija en el momento en que esta ocurre (consultando
  `003-precios-margenes`) y no se recalcula retroactivamente si el margen del producto cambia
  después.
- **Refactor pendiente (registrado en la Clarification de `003-precios-margenes` del
  2026-09-05, FR-022)**: `resolver_margen_visita` (`margen_resolver.py`) implementa hoy una fórmula
  de margen propia y provisional (ver research.md #2 de este módulo) porque `003-precios-margenes`
  todavía no existía al construir esta funcionalidad. `003` ya decidió que esta función DEBE migrar
  a consumir su definición de margen real en vez de mantener la fórmula propia — es trabajo de
  implementación pendiente para la fase de planificación/tareas de `003`, no un cambio de alcance
  de este spec: FR-005, FR-010 y la Assumption anterior ya asumían esa consulta a `003` desde que se
  escribieron.
- El número mínimo de visitas necesario para considerar confiable el intervalo de compra de un
  cliente es un parámetro que se decide en `plan.md`, no en esta especificación; hasta alcanzarlo,
  el cliente permanece en el estado "datos insuficientes" (ver FR-007).
- La fecha de nacimiento es obligatoria al registrar un cliente, porque es la única base de datos
  que necesita el cupón de cumpleaños de `005`; sin ella, el cliente simplemente no será elegible
  para ese cupón cuando `005` lo evalúe.
- El teléfono y el correo del cliente son opcionales y no son la base de ningún cálculo de valor ni
  de fuga en esta funcionalidad.
- Una venta puede completarse sin identificar cliente (cliente no registrado o que no desea
  identificarse); ese caso no genera visita ni afecta ningún cálculo (ver FR-004).
- Los multiplicadores y plazos concretos de FR-014 y FR-015 (5×, piso de 12 meses, retención de 90
  días) son la política de esta funcionalidad tal como fue decidida y documentada aquí; ajustarlos
  en el futuro es una enmienda de este spec, no una decisión libre de `plan.md`.
