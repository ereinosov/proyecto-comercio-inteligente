# Feature Specification: Pagos y Seguridad

**Feature Branch**: `007-pagos-seguridad` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-05

**Status**: Draft

**Input**: Cerrar el flanco de pagos de un minimarket sin convertirse en un procesador de pagos. El
enunciado del curso plantea cuatro preocupaciones concretas y acotadas alrededor del cobro con
tarjeta y del abanico de medios de pago, y este módulo las cubre exactamente, sin ampliarlas:
(1) **tokenización de los datos de pago** — que el sistema nunca retenga el número completo de una
tarjeta, solo un identificador sustituto y los últimos dígitos, tal como la constitución ya exige
en "Datos de pago"; (2) **firmware del datáfono / terminal de pago** — llevar registro de qué
terminal hay en cada sucursal, su versión de firmware, si está al día y su exposición conocida a
clonación (skimming), como señal de riesgo para revisión humana; (3) **bitácora de auditoría de la
actividad de pagos** — un rastro estructurado y consultable de los hechos de pago (un token se
emitió, una tarjeta se rechazó por política, un firmware se actualizó, un medio de pago se activó o
se desactivó en una sucursal), conforme al Principio IV; (4) **cobertura de medios de pago aceptados
por sucursal** — qué medios acepta cada sucursal y qué cuota de intención de compra queda sin
atender cuando un cliente no puede pagar como quería, tratada como métrica de cobertura y no como
faltante de inventario (Lectura Crítica n.º 4 de la constitución). **NO hay pasarela de pago real,
NO se procesan transacciones financieras reales, NO se hace settlement ni autorización con ningún
adquirente**: Rasero es un sistema de comercio inteligente para un minimarket, no un procesador de
pagos. Este módulo consulta, sin reimplementar, la `venta`, el `turno`, la `sucursal` y la
`referencia_terminal_pago` opaca de `001-core-ventas-inventario`; posee el catálogo de medios de
pago, el registro de terminales y su firmware, la métrica de cobertura por sucursal y la bitácora de
auditoría de pagos. La inteligencia de este módulo es consultiva: detecta y explica la exposición
(firmware desactualizado, terminal marcada como vulnerable, PAN rechazado); la persona decide qué
hacer.

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-05

Ninguna pregunta quedó abierta. Las decisiones que un lector podría esperar como `NEEDS
CLARIFICATION` se resolvieron con una decisión razonable documentada, con el mismo criterio que
`003`, `004`, `005` y `006` (decisión documentada en vez de pregunta abierta):

- **Alcance de la "tokenización"**: este módulo NO integra ninguna pasarela ni bóveda de un tercero.
  "Tokenizar" aquí significa que, cuando una venta de `001` se cobró con tarjeta, este módulo
  conserva únicamente un **identificador sustituto opaco** (el token), los **últimos cuatro
  dígitos**, la **marca** (Visa, Mastercard, …) y el **tipo** (débito / crédito), y **nunca** el
  número completo (PAN), el CVV ni la banda/chip. El PAN entra en el flujo de captura y sale
  tokenizado; el sistema no lo persiste en ningún punto (constitución, "Datos de pago" y Principio
  IV). Ver FR-009 a FR-015.
- **Dónde vive el token**: `research.md #1` concluyó que el conjunto {token, últimos dígitos, marca,
  tipo, terminal de captura, referencia de venta, clave de idempotencia} es un registro autoritativo
  que necesita **tabla propia** (`token_pago`) y no cabe en las cuatro entidades ratificadas. La
  **enmienda constitucional v2.2.6** (2026-09-05) la añadió a la tabla de Propiedad de Datos, mismo
  procedimiento que `003`/`004`/`005`. Su forma detallada se fija en `data-model.md`. Ver
  "Dependencias entre módulos".
- **Evaluación de "exposición a clonación"**: es un **indicador derivado y consultivo**, no un
  veredicto. Se calcula cruzando la versión de firmware y el estado de actualización de la terminal
  contra una **lista de versiones/modelos con vulnerabilidad conocida** que el negocio mantiene como
  configuración (mismo patrón que la ventana de alerta de caducidad de `006` o el umbral de
  inmovilizado de `001`). El sistema señala; nunca deshabilita una terminal por su cuenta
  (Principio V; Principio II: la caja no se bloquea). Ver FR-016 a FR-021.
- **Venta perdida por medio de pago no aceptado**: se registra como **métrica de cobertura de medios
  de pago por sucursal**, no como venta perdida en el sentido de faltante de inventario ni como
  `consulta_no_atendida` de `001` (esa es "no hay producto"; esta es "no puedo pagar así").
  Constitución, Lectura Crítica n.º 4. Ver FR-022 a FR-027.

## User Scenarios & Testing *(mandatory)*

<!-- Historias ordenadas por dependencia real y por valor de MVP, no por el orden en que el enunciado
lista las cuatro preocupaciones. La cobertura de medios de pago va primero: es la más simple, solo
necesita `sucursal` de `001` (ya implementada), no está bloqueada por nada, y es la que la
constitución nombra explícitamente como métrica (Lectura Crítica n.º 4). El registro de terminales y
la vigilancia de firmware va segunda: introduce `terminal_pago` —la pieza de primera clase que la
tokenización también necesita para saber qué terminal capturó cada cobro— y aporta valor de
seguridad por sí sola. La tokenización va tercera: se apoya en `terminal_pago` (segunda historia) y
en `venta` de `001`, y hace cumplir la regla constitucional de no retener el PAN en cada cobro con
tarjeta. La bitácora de auditoría de pagos va última: es el rastro transversal de los hechos que las
tres historias anteriores producen; sin ellas no hay nada que registrar. -->

### User Story 1 - Conocer y mantener la cobertura de medios de pago por sucursal (Priority: P1)

El encargado define, por sucursal, qué medios de pago acepta (efectivo, tarjeta de débito, tarjeta de
crédito, transferencia, billetera móvil) y registra los casos en que un cliente no pudo completar la
compra porque su medio de pago preferido no estaba disponible en esa sucursal. El sistema muestra,
por sucursal y período, la cobertura de medios de pago y la cuota de intención de compra no atendida
por esta causa, para que el negocio decida si habilitar un medio nuevo. Es una métrica de cobertura,
no un faltante de inventario: no hay transacción que registrar porque la venta nunca llegó a
ocurrir.

**Why this priority**: es el mecanismo más simple del módulo —un catálogo por sucursal y un contador
de intención no atendida— y el punto de entrada. Depende únicamente de `sucursal` de `001`, ya
implementada, así que no está bloqueado. Es además la preocupación que la constitución nombra de
forma literal (Lectura Crítica n.º 4: "un cliente que no entra porque el comercio no acepta su medio
de pago preferido … se trata como métrica de cobertura de medios de pago por sucursal"). Entrega
valor por sí sola: convierte una queja difusa ("perdemos clientes por no tener datáfono en Buena Fe")
en un número atribuido a una sucursal y un período.

**Independent Test**: para una sucursal con un conjunto conocido de medios de pago habilitados y un
conjunto conocido de eventos de "no pudo pagar así", se puede verificar que el sistema lista los
medios aceptados de esa sucursal, calcula la cobertura y la cuota de intención no atendida del
período, atribuye cada evento a su sucursal, y nunca agrega la métrica de varias sucursales sin
discriminar la de origen.

**Acceptance Scenarios**:

1. **Given** una sucursal sin tarjeta de crédito habilitada, **When** el encargado consulta su
   cobertura de medios de pago, **Then** el sistema muestra los medios aceptados de esa sucursal y
   marca la tarjeta de crédito como no cubierta.
2. **Given** un cliente que quería pagar con transferencia en una sucursal que no la acepta, **When**
   el operador registra el evento de intención no atendida con el medio deseado, **Then** el sistema
   lo contabiliza para esa sucursal y ese período, sin crear ninguna venta ni ningún movimiento de
   inventario.
3. **Given** varios eventos de intención no atendida en un período, **When** el encargado consulta la
   métrica, **Then** el sistema muestra la cuota de intención no atendida desglosada por medio de
   pago deseado y por sucursal, y nunca como faltante de inventario ni como `consulta_no_atendida`
   de `001`.
4. **Given** una consulta de cobertura de varias sucursales, **When** se presenta el resultado,
   **Then** cada dato se identifica por su sucursal; agregar la cobertura o la intención no atendida
   de varias sucursales sin discriminar la de origen está PROHIBIDO.
5. **Given** un medio de pago que el negocio habilita en una sucursal a partir de cierta fecha,
   **When** se consulta un período anterior a esa fecha, **Then** la métrica de ese período refleja
   que el medio no estaba disponible entonces (el catálogo por sucursal es histórico, no solo el
   estado actual).

---

### User Story 2 - Registrar las terminales de pago y vigilar su firmware y su exposición a clonación (Priority: P2)

El encargado registra cada terminal de pago (datáfono) física del negocio: su identificador, el
modelo, la sucursal donde está instalada, su versión de firmware y la fecha de la última
actualización. El sistema compara esa versión contra la última versión disponible y contra una lista
de versiones y modelos con vulnerabilidad de clonación conocida que el negocio mantiene, y señala las
terminales desactualizadas o expuestas, con la explicación de por qué. Es una señal para que el
encargado gestione la actualización o el reemplazo; el sistema nunca deshabilita una terminal.

**Why this priority**: introduce `terminal_pago`, la entidad de primera clase que la tokenización
(User Story 3) también necesita —cada cobro con tarjeta se captura en una terminal concreta y el
token debe poder decir en cuál—. Aporta valor de seguridad independiente: una terminal con firmware
viejo es la vía más común de clonación de tarjetas en el comercio físico, y hoy el negocio no tiene
forma de saber cuáles de sus datáfonos están en riesgo. Solo necesita su propio registro y la
configuración de versiones vulnerables; no está bloqueada por `001` más allá de `sucursal`, ya
disponible.

**Independent Test**: para un conjunto conocido de terminales con versiones de firmware conocidas y
una lista conocida de versiones vulnerables y de la última versión disponible, se puede verificar que
el sistema marca como desactualizada cada terminal por debajo de la última versión, como expuesta
cada terminal cuya versión o modelo está en la lista de vulnerabilidad, que enumera el motivo de cada
señal, que atribuye cada terminal a su sucursal, y que ninguna señal deshabilita ni bloquea la
terminal.

**Acceptance Scenarios**:

1. **Given** una terminal con una versión de firmware anterior a la última disponible, **When** el
   encargado consulta el estado de las terminales, **Then** el sistema la marca como desactualizada,
   indica la versión actual y la última disponible, y la diferencia de antigüedad.
2. **Given** una terminal cuya versión de firmware figura en la lista de versiones con
   vulnerabilidad de clonación conocida, **When** se evalúa su exposición, **Then** el sistema la
   marca como expuesta a clonación, con la referencia de la vulnerabilidad que lo motiva
   (explicable, Principio V).
3. **Given** una terminal al día y sin vulnerabilidad conocida, **When** se evalúa, **Then** el
   sistema la muestra como sin exposición conocida, sin generar ninguna señal.
4. **Given** una terminal marcada como expuesta, **When** se consulta, **Then** el sistema NO la
   deshabilita, NO impide su uso y NO bloquea cobros: la acción correctiva (actualizar, aislar o
   reemplazar) la decide una persona (Principio V; Principio II).
5. **Given** que el encargado registra una actualización de firmware de una terminal, **When** la
   nueva versión ya no está en la lista de vulnerabilidad y alcanza la última disponible, **Then**
   la terminal deja de aparecer como desactualizada y como expuesta, y el cambio queda en la
   bitácora (User Story 4).
6. **Given** una consulta del estado de terminales de varias sucursales, **When** se presenta,
   **Then** cada terminal se identifica por su sucursal; agregar el estado de varias sucursales sin
   discriminar la de origen está PROHIBIDO.

---

### User Story 3 - Tokenizar los datos de pago de cada cobro con tarjeta (Priority: P3)

Cuando una venta de `001` se cobra con tarjeta, el flujo de captura entrega el número de tarjeta a
este módulo, que devuelve de inmediato un identificador sustituto opaco (token) y conserva
únicamente ese token, los últimos cuatro dígitos, la marca y el tipo de tarjeta, junto con la
terminal en que se capturó y la referencia de la venta. El número completo, el CVV y los datos de
banda o chip nunca se guardan, ni en la base de datos, ni en registros, ni en la bitácora. Cualquier
intento de persistir un PAN completo se rechaza. El encargado puede consultar, para una venta, el
token y los últimos dígitos, nunca el número completo.

**Why this priority**: es el cumplimiento directo de una regla constitucional nombrada ("Datos de
pago": los datos completos de tarjeta NO se almacenan, registran ni transmiten; se conservan
únicamente identificadores y últimos dígitos). Toca cada cobro con tarjeta. Va después de User Story
2 porque el token necesita apuntar a la `terminal_pago` que capturó el cobro, y después de que `001`
tenga `venta` (ya implementada). No integra ninguna pasarela: la "captura" es el punto del flujo de
venta donde hoy `001` guarda una `referencia_terminal_pago` opaca; este módulo es quien rellena esa
referencia con un token y su metadato mínimo.

**Independent Test**: para una venta de `001` cobrada con tarjeta, se puede verificar que el módulo
devuelve un token opaco, que persiste solo token + últimos cuatro dígitos + marca + tipo + terminal
+ referencia de venta, que un intento de guardar un PAN completo (más de cuatro dígitos consecutivos
en el campo de últimos dígitos, o un campo de número completo) se rechaza, que la consulta de una
venta nunca devuelve el número completo, y que la bitácora del evento de tokenización no contiene el
PAN.

**Acceptance Scenarios**:

1. **Given** una venta de `001` que se cobra con una tarjeta, **When** el flujo de captura entrega
   el número a este módulo, **Then** el módulo devuelve un token opaco y persiste únicamente ese
   token, los últimos cuatro dígitos, la marca y el tipo, con la terminal y la referencia de la
   venta.
2. **Given** un token ya emitido para una venta, **When** se consulta esa venta, **Then** el sistema
   muestra el token y los últimos cuatro dígitos y NUNCA el número completo, el CVV ni datos de
   banda o chip.
3. **Given** un intento —por error de integración o de carga de datos— de persistir un número de
   tarjeta completo en cualquier campo de este módulo, **When** se procesa, **Then** el sistema lo
   rechaza y registra el rechazo en la bitácora sin incluir el número (FR-013).
4. **Given** un cobro con tarjeta cuya captura falla o se cancela, **When** no se llega a emitir
   token, **Then** la venta de `001` se completa igualmente con su comportamiento base (Principio
   II: ninguna función de pago o seguridad es camino crítico de un cobro) y el módulo registra que
   no hubo tokenización.
5. **Given** un reintento del mismo cobro con la misma clave de idempotencia, **When** se procesa,
   **Then** el sistema devuelve el token ya emitido y no crea un segundo registro de token
   (Principio II).
6. **Given** una consulta de la bitácora o de cualquier reporte de este módulo, **When** se
   presenta, **Then** en ningún punto aparece un número de tarjeta completo, un CVV ni un dato
   personal más allá del identificador mínimo necesario (Principio IV).

---

### User Story 4 - Auditar la actividad de pagos en una bitácora consultable (Priority: P4)

El analista del negocio consulta una bitácora estructurada de los hechos de pago del sistema: qué
token se emitió y para qué venta, qué PAN se rechazó por política y cuándo, qué firmware se actualizó
en qué terminal, qué medio de pago se activó o desactivó en qué sucursal, qué terminal se marcó como
expuesta a clonación. Cada entrada dice qué pasó, cuándo, en qué sucursal y terminal, iniciada por
qué operador o proceso, y con qué resultado. La bitácora es de solo anexado: una entrada no se
modifica ni se borra.

**Why this priority**: es el rastro transversal que el Principio IV exige para "toda operación que
mueva dinero" y para el resto de la actividad de pagos, y es el residuo de las tres historias
anteriores: sin catálogo de medios, sin terminales y sin tokenización no hay hechos que registrar.
Tiene valor independiente: convierte la actividad dispersa de pagos en un histórico consultable por
sucursal, terminal y tipo de evento, que es la base de cualquier investigación posterior.

**Independent Test**: para una secuencia conocida de hechos de pago (una emisión de token, un rechazo
de PAN, una actualización de firmware, un cambio de cobertura), se puede verificar que cada uno queda
en la bitácora con su tipo, su instante en el día local de la sucursal, su sucursal y terminal
cuando aplica, su iniciador y su resultado, que ninguna entrada contiene datos de pago completos ni
datos personales más allá del identificador mínimo, que las entradas se pueden filtrar por sucursal,
terminal y tipo, y que una entrada existente no puede modificarse ni borrarse.

**Acceptance Scenarios**:

1. **Given** cualquier hecho de pago de las User Stories 1 a 3, **When** ocurre, **Then** el sistema
   anexa una entrada a la bitácora con el tipo de evento, el instante en el día local de la
   sucursal, la sucursal, la terminal cuando aplica, el iniciador (operador o proceso) y el
   resultado.
2. **Given** una entrada de bitácora de una emisión de token, **When** se consulta, **Then** la
   entrada referencia el token y la venta pero NO contiene el número de tarjeta, el CVV ni ningún
   dato de banda o chip.
3. **Given** una entrada de bitácora ya escrita, **When** se intenta modificarla o borrarla, **Then**
   el sistema lo impide: la bitácora es de solo anexado (Principio IV: el estado debe ser
   reconstruible; sobrescribir sin registrar el cambio está PROHIBIDO).
4. **Given** una consulta de la bitácora, **When** se filtra, **Then** el sistema permite filtrar
   por sucursal, por terminal y por tipo de evento, y presenta cada entrada con su día local; una
   consulta multi-sucursal declara el criterio de día que aplica.
5. **Given** una entrada de bitácora de un rechazo de PAN, **When** se consulta, **Then** indica que
   hubo un intento rechazado y su motivo, sin incluir ningún dígito del número más allá de los
   últimos cuatro que la política permite conservar.
6. **Given** la bitácora de auditoría, **When** se consulta su antigüedad, **Then** las entradas se
   conservan al menos por el período de retención documentado (Assumptions) y no se purgan antes.

---

### Edge Cases

- **Venta en efectivo**: no genera token ni entrada de tokenización; sí puede contar para la
  cobertura de medios de pago (el efectivo es un medio aceptado). El módulo no crea registros de pago
  con tarjeta para cobros que no fueron con tarjeta.
- **Cliente que se va sin comprar por no aceptarse su medio de pago**: no hay `venta`, no hay
  `consulta_no_atendida` de `001` (eso es falta de producto); se registra solo como evento de
  intención no atendida de cobertura (User Story 1).
- **Terminal compartida temporalmente entre sucursales o movida de sucursal**: cada terminal tiene
  una sucursal actual y su historia de ubicación; una señal de firmware se atribuye a la sucursal
  donde estaba la terminal en el momento evaluado, no siempre a la actual.
- **Lista de versiones vulnerables vacía o no configurada**: ninguna terminal se marca como expuesta
  por vulnerabilidad conocida; las desactualizadas sí se siguen marcando por diferencia de versión.
  El sistema no inventa vulnerabilidades.
- **Última versión de firmware desconocida para un modelo**: la terminal no se marca como
  desactualizada por diferencia de versión (no hay contra qué comparar), pero sí se marca "versión de
  referencia desconocida" para que el encargado la complete; nunca se asume que está al día.
- **PAN con menos de 13 o más de 19 dígitos, o que no pasa la validación de Luhn**: el flujo de
  captura lo rechaza antes de tokenizar; se registra el rechazo sin el número.
- **Intento de tokenizar dos veces la misma tarjeta en ventas distintas**: cada venta obtiene su
  propio token; el módulo no deduplica tarjetas entre ventas (no mantiene un índice de tarjetas, solo
  de tokens por venta) para no reconstruir un identificador estable de tarjeta.
- **Cobro con tarjeta sin conectividad**: la venta de `001` se completa con su comportamiento base y
  se encola; la tokenización se resuelve al reconciliar, con la marca de tiempo de origen, igual que
  el resto de operaciones offline de `001`.
- **Reintento de sincronización de un evento de bitácora ya anexado**: la clave de idempotencia del
  evento impide la entrada duplicada.
- **Operador no encargado intenta cambiar la cobertura de medios de pago de una sucursal o la lista
  de versiones vulnerables**: son cambios de configuración reservados al encargado; el intento se
  rechaza y se registra en la bitácora.
- **Consulta de cobertura de un período en el que una sucursal no existía todavía**: la métrica no
  incluye esa sucursal en ese período; no se reporta cobertura cero, se reporta "sucursal inexistente
  en el período".

## Requirements *(mandatory)*

### Functional Requirements

**Preocupación 4 — Cobertura de medios de pago aceptados por sucursal (User Story 1)**

- **FR-001**: El sistema DEBE mantener un catálogo de medios de pago (al menos: efectivo, tarjeta de
  débito, tarjeta de crédito, transferencia, billetera móvil), extensible sin cambio estructural.
- **FR-002**: El sistema DEBE permitir declarar, por sucursal, qué medios de pago acepta, con la
  fecha desde la que cada uno está disponible, de modo que la cobertura de un período pasado refleje
  el estado de entonces y no solo el actual.
- **FR-003**: El sistema DEBE permitir registrar un evento de **intención de compra no atendida por
  medio de pago**: un cliente no completó la compra porque su medio de pago preferido no estaba
  disponible en esa sucursal. El evento registra el medio deseado, la sucursal, el instante en día
  local y, opcionalmente, una nota; NO crea ninguna `venta` ni ningún movimiento de inventario.
- **FR-004**: El sistema DEBE calcular, por sucursal y período, la **cobertura de medios de pago**
  (qué medios acepta sobre el catálogo) y la **cuota de intención de compra no atendida** por esta
  causa, desglosable por medio deseado.
- **FR-005**: El sistema NO DEBE tratar la intención no atendida por medio de pago como venta perdida
  por faltante de inventario ni como `consulta_no_atendida` de `001`. Son fenómenos distintos:
  `consulta_no_atendida` es "no hay producto"; esto es "no puedo pagar así" (Lectura Crítica n.º 4).
- **FR-006**: Toda métrica de cobertura DEBE identificarse por sucursal. Agregar la cobertura o la
  intención no atendida de varias sucursales sin discriminar la de origen está PROHIBIDO (Principio
  IV y restricción multi-sucursal).
- **FR-007**: Cambiar el catálogo de medios de pago o la cobertura de una sucursal DEBE estar
  reservado al encargado y DEBE quedar registrado en la bitácora de auditoría (FR-028).

**Preocupación 2 — Registro de terminales de pago y vigilancia de firmware (User Story 2)**

- **FR-008**: El sistema DEBE mantener un registro de las **terminales de pago** físicas del negocio,
  cada una con su identificador, modelo, sucursal actual, historia de ubicación, versión de firmware
  y fecha de la última actualización de firmware.
- **FR-009**: El sistema DEBE mantener, como configuración que el negocio actualiza, la **última
  versión de firmware disponible por modelo** y una **lista de versiones y modelos con vulnerabilidad
  de clonación conocida**, cada entrada con una referencia identificable de la vulnerabilidad.
- **FR-010**: El sistema DEBE marcar una terminal como **desactualizada** cuando su versión de
  firmware es anterior a la última disponible para su modelo, indicando ambas versiones y la
  antigüedad de la diferencia. Si no hay última versión de referencia conocida para el modelo, la
  terminal se marca "versión de referencia desconocida", nunca "al día".
- **FR-011**: El sistema DEBE marcar una terminal como **expuesta a clonación** cuando su versión de
  firmware o su modelo figura en la lista de vulnerabilidad conocida, enumerando la referencia de la
  vulnerabilidad que lo motiva (explicable, Principio V).
- **FR-012**: El sistema NO DEBE deshabilitar, bloquear ni impedir el uso de una terminal marcada
  como desactualizada o expuesta. La señal es consultiva; la acción correctiva la decide una persona
  (Principio V; Principio II: la caja no se bloquea).
- **FR-013**: El sistema DEBE permitir registrar una **actualización de firmware** de una terminal
  (nueva versión, fecha); tras registrarla, la terminal se reevalúa contra FR-010 y FR-011 y el
  cambio queda en la bitácora (FR-028).
- **FR-014**: Toda señal de firmware DEBE atribuirse a la **sucursal donde estaba la terminal en el
  momento evaluado** (historia de ubicación), no siempre a la actual. Agregar el estado de terminales
  de varias sucursales sin discriminar la de origen está PROHIBIDO.
- **FR-015**: Registrar o modificar terminales, versiones de referencia o la lista de vulnerabilidad
  DEBE estar reservado al encargado y DEBE quedar en la bitácora.

**Preocupación 1 — Tokenización de los datos de pago (User Story 3)**

- **FR-016**: Cuando una `venta` de `001` se cobra con tarjeta, el sistema DEBE recibir el número de
  tarjeta del flujo de captura, devolver un **identificador sustituto opaco (token)** y persistir
  únicamente: el token, los **últimos cuatro dígitos**, la **marca**, el **tipo** (débito / crédito),
  la **terminal** de captura (FR-008) y la **referencia de la venta**.
- **FR-017**: El sistema NO DEBE almacenar, registrar ni transmitir por sistemas propios el número de
  tarjeta completo (PAN), el CVV ni ningún dato de banda magnética o chip, en ningún punto: base de
  datos, archivos de registro, bitácora de auditoría, respuestas de consulta o reportes
  (constitución, "Datos de pago"; Principio IV).
- **FR-018**: El sistema DEBE **rechazar** cualquier intento de persistir un número de tarjeta
  completo en cualquiera de sus campos, y DEBE registrar el rechazo en la bitácora **sin** incluir el
  número.
- **FR-019**: La consulta del pago de una venta DEBE devolver el token y los últimos cuatro dígitos y
  NUNCA el número completo. El token DEBE ser opaco: no DEBE permitir derivar de él el número de
  tarjeta ni un identificador estable de la tarjeta entre ventas distintas.
- **FR-020**: La tokenización NO DEBE ser camino crítico de un cobro. Si la captura o la tokenización
  falla, la `venta` de `001` DEBE completarse igualmente con su comportamiento base, y el sistema
  DEBE registrar que esa venta quedó sin tokenización (Principio II).
- **FR-021**: La emisión de token DEBE ser **idempotente**: un reintento con la misma clave de
  idempotencia DEBE devolver el token ya emitido, sin crear un segundo registro (Principio II).
- **FR-022**: Un cobro con tarjeta ejecutado sin conectividad DEBE completarse en `001` con su
  comportamiento base y encolarse; la tokenización se resuelve al reconciliar, con la marca de tiempo
  de origen y la regla de conflicto de `001`.

**Preocupación 3 — Bitácora de auditoría de la actividad de pagos (User Story 4)**

- **FR-023**: El sistema DEBE anexar a una **bitácora de auditoría** una entrada por cada hecho de
  pago: emisión de token, rechazo de PAN, actualización de firmware, detección de terminal
  desactualizada o expuesta, alta o baja de un medio de pago en una sucursal, cambio de cobertura,
  registro de intención no atendida.
- **FR-024**: Cada entrada de la bitácora DEBE registrar: el **tipo de evento**, el **instante** en
  el **día local de la sucursal**, la **sucursal**, la **terminal** cuando aplica, el **iniciador**
  (operador o proceso), el **resultado** y una referencia al recurso afectado (token, venta,
  terminal, medio de pago).
- **FR-025**: La bitácora DEBE ser de **solo anexado**: una entrada existente NO DEBE poder
  modificarse ni borrarse (Principio IV).
- **FR-026**: Ninguna entrada de la bitácora DEBE contener datos de pago completos, CVV, datos de
  banda o chip, ni datos personales más allá del identificador mínimo necesario (Principio IV).
- **FR-027**: La bitácora DEBE poder consultarse y filtrarse por **sucursal**, por **terminal** y por
  **tipo de evento**; una consulta que abarque varias sucursales DEBE declarar qué criterio de día
  local aplica.
- **FR-028**: Todo cambio de configuración de este módulo (catálogo y cobertura de medios de pago,
  registro de terminales, versiones de referencia, lista de vulnerabilidad) DEBE dejar entrada en la
  bitácora con quién lo hizo y cuándo.

**Frontera con `001-core-ventas-inventario` (propiedad de datos)**

- **FR-029**: El sistema NO DEBE registrar, modificar ni recalcular `venta`, `renglon_venta`,
  `turno`, `operador`, `sucursal` ni ningún dato propiedad de `001`; todos se consultan.
- **FR-030**: El sistema es quien da contenido a la `referencia_terminal_pago` **opaca** que `001`
  ya reserva en cada `venta` ([`001/data-model.md`], campo `TEXT NULL`): `001` guarda la referencia
  sin interpretarla; `007` la resuelve como token + terminal. `007` NO DEBE cambiar el tipo ni la
  semántica de ese campo en el esquema de `001`.
- **FR-031**: La atribución de sucursal y de operador de un hecho de pago DEBE apoyarse en los datos
  que `001` ya registra (`venta.id_turno` → `turno.id_operador` y `turno` → sucursal), sin
  reimplementar la identificación por PIN ni acceder a `operador.pin_hash`.
- **FR-032**: El día local de una sucursal DEBE resolverse con `sucursal.zona_horaria` de `001`; las
  agregaciones de cobertura y de bitácora se calculan sobre el día local de la sucursal, no sobre el
  día UTC (constitución, "Tiempo").

**Común a las cuatro preocupaciones**

- **FR-033**: Las cuatro preocupaciones —cobertura de medios, firmware de terminal, tokenización y
  bitácora— DEBEN modelarse como fenómenos distintos con su propia lógica; tratarlas como una sola
  entidad genérica de "pago" está PROHIBIDO.
- **FR-034**: Toda salida de este módulo —métrica de cobertura, señal de firmware, token, entrada de
  bitácora— DEBE identificarse por sucursal y ser reconstruible a partir del registro: qué dato la
  originó, qué período cubrió y qué regla se aplicó (Principio IV; Principio V: explicable).
- **FR-035**: La inteligencia de este módulo es **consultiva**: detecta y explica exposición
  (firmware, vulnerabilidad, PAN rechazado) pero NO deshabilita terminales, NO bloquea cobros y NO
  sanciona a nadie de forma automática. La acción correctiva la decide una persona (Principio V).
- **FR-036**: El sistema NO DEBE integrar ninguna pasarela de pago, adquirente o procesador real, NO
  DEBE ejecutar autorización, captura financiera ni settlement, y NO DEBE mover dinero real. El
  alcance es el registro y la seguridad de los datos de pago de un minimarket, no el procesamiento de
  transacciones.
- **FR-037**: Toda operación de este módulo que altere configuración o emita un token DEBE aceptar
  una clave de idempotencia y ser segura ante reintentos (Principio II).

### Key Entities *(include if feature involves data)*

Las cinco entidades que la constitución (v2.2.6) asigna a `007-pagos-seguridad` en su tabla de
Propiedad de Datos son `terminal_pago`, `medio_pago`, `cobertura_pago`, `bitacora_auditoria` y
`token_pago`. Este spec las usa con ese nombre. `token_pago` se añadió por la enmienda **v2.2.6**
(2026-09-05), a raíz de `research.md #1` de este módulo — ver "Dependencias entre módulos".

- **medio_pago**: un medio de pago del catálogo (efectivo, tarjeta de débito, tarjeta de crédito,
  transferencia, billetera móvil, …). Atributos: nombre, si requiere terminal de pago, si admite
  tokenización. Es el catálogo global; la aceptación por sucursal la lleva `cobertura_pago`.
  Propiedad de este módulo.
- **terminal_pago**: una terminal de pago (datáfono) física. Atributos: identificador, modelo,
  sucursal actual, historia de ubicación (sucursal y período), versión de firmware, fecha de la
  última actualización de firmware, y los indicadores derivados "desactualizada" y "expuesta a
  clonación" con su motivo. Referenciada por el token como la terminal de captura. Es NUEVA en este
  módulo; `001` solo guarda una `referencia_terminal_pago` opaca. Propiedad de este módulo.
- **cobertura_pago**: la aceptación de un `medio_pago` en una `sucursal`, con la fecha desde la que
  está disponible (histórico, no solo estado actual), y la métrica derivada de intención de compra no
  atendida por sucursal, período y medio deseado. Es la métrica que la Lectura Crítica n.º 4 nombra.
  Propiedad de este módulo.
- **bitacora_auditoria**: rastro de solo anexado de los hechos de pago. Cada entrada: tipo de evento,
  instante en día local, sucursal, terminal cuando aplica, iniciador (operador o proceso), resultado,
  referencia al recurso afectado. Nunca contiene PAN, CVV, datos de banda o chip, ni datos personales
  más allá del identificador mínimo. Propiedad de este módulo.

- **token_pago** *(añadida por la enmienda **v2.2.6**)*: el registro **autoritativo** de un cobro con
  tarjeta tokenizado — token opaco (`UNIQUE`), últimos cuatro dígitos, marca, tipo, terminal de
  captura, referencia de la venta de `001` (`UNIQUE`, un token por cobro), clave de idempotencia
  (FR-021). **Ningún** campo de PAN, CVV ni banda/chip. `research.md #1` concluyó que este registro
  no cabe en las otras cuatro entidades —no es un catálogo (`medio_pago`), no es el dispositivo
  (`terminal_pago`), no es la métrica agregada (`cobertura_pago`) y no es un evento de solo anexado
  (`bitacora_auditoria`)—; la enmienda **v2.2.6** (2026-09-05) lo añadió a la tabla de Propiedad de
  Datos, mismo patrón que v2.2.3 (`003`), v2.2.4 (`004`) y v2.2.5 (`005`). Consulta `venta` de `001`
  sin poseerla y rellena su `referencia_terminal_pago` opaca. Propiedad de este módulo. Su forma
  detallada se fija en `data-model.md`.

Entidades de `001` que este módulo consulta pero no posee (frontera de propiedad de datos):
`venta` (`id_turno`, `referencia_terminal_pago` opaca, `total`), `turno` (`id_operador`, sucursal),
`operador` (solo `id_operador` y `es_encargado`; **nunca** `pin_hash`), `sucursal` (`zona_horaria`,
para el día local; existencia en el período para la métrica de cobertura).

## Dependencias entre módulos

Esta sección es de lectura obligatoria antes de `/speckit-plan`: fija qué se puede construir ahora,
qué contratos se consumen de `001`, y qué entidad motivó la enmienda constitucional **v2.2.6**. No
debe quedar oculta en `plan.md`.

**Lo que este módulo consulta y no reimplementa** (mismo patrón que `003`, `004`, `005` y `006`
frente a `001`):

- De `001-core-ventas-inventario`: `venta` y su `referencia_terminal_pago` opaca (que `007` rellena
  con un token, FR-030) y su `id_turno` (para atribuir sucursal y operador de un cobro), `turno`
  (`id_operador`, sucursal), `sucursal` (`zona_horaria` para el día local; su existencia en el
  período para la métrica de cobertura). **No** consulta `existencia`, `movimiento_inventario`,
  `lote` ni `conteo_fisico`: este módulo no toca inventario.

**Verificaciones exigidas por el encargo — resueltas antes de escribir los FR**:

1. **Qué reserva ya `001` para el pago** (verificado contra `001/data-model.md`, `001/spec.md`
   FR-007 y su Lectura Crítica n.º 3, constitución v2.2.6): `001` guarda en cada `venta` un campo
   `referencia_terminal_pago` de tipo `TEXT NULL` descrito explícitamente como **referencia opaca**,
   y `001/spec.md` declara que "`terminal_pago` sigue siendo propiedad de `007-pagos-seguridad` y
   este módulo solo guarda una referencia". `001` **no** tiene catálogo de medios de pago, ni
   registro de terminales, ni bitácora de pagos, ni métrica de cobertura, ni registro de tokens.
   **Conclusión**: `007` introduce las cinco por primera vez y rellena la referencia opaca de `001`
   sin alterar su esquema (FR-030).
2. **`001` no guarda el medio de pago de una venta**: `venta` de `001` solo tiene la referencia de
   terminal opaca y el `total`; no hay columna de "método de pago". Por tanto la cobertura de medios
   (`cobertura_pago`) y el catálogo (`medio_pago`) son enteramente de `007`; no hay dato de `001`
   que duplicar. `006` ya lo anticipó al diferir el desglose del arqueo por medio de pago "a cuando
   exista `007-pagos-seguridad` (dueño de `medio_pago`)".
3. **Lectura Crítica n.º 4 — venta perdida antes de que exista transacción**: la constitución ya
   decidió que "un cliente que no entra porque el comercio no acepta su medio de pago preferido … se
   trata como métrica de cobertura de medios de pago por sucursal, no como venta perdida en el
   sentido de faltante de inventario". `007` implementa exactamente eso (FR-003 a FR-005); no lo
   modela como `consulta_no_atendida` de `001` (que es falta de producto). Decisión tomada, no
   `NEEDS CLARIFICATION`.
4. **"Datos de pago" de la constitución**: la sección "Restricciones Técnicas y de Datos → Datos de
   pago" ya exige que "los datos completos de tarjeta NO se almacenan, registran ni transmiten por
   sistemas propios" y que se conserven "únicamente identificadores y últimos dígitos". `007` no
   introduce una regla nueva: la hace cumplir en cada cobro con tarjeta (FR-016 a FR-019). El
   Principio IV refuerza que los rastros "NO DEBEN contener datos de pago completos". Decisión
   tomada, no `NEEDS CLARIFICATION`.

**BLOQUEO explícito de implementación (no oculto)** — mismo tipo de declaración que `004` frente a
`consulta_no_atendida` y `006` frente a `conteo_fisico`:

- El último checkpoint del proyecto cubre `001` Setup + Foundational + User Story 1. `venta`,
  `turno` y `sucursal` (con `zona_horaria`) están implementadas; la `referencia_terminal_pago` opaca
  existe en el esquema de `venta` desde Foundational.
- En consecuencia, **ninguna User Story de `007` está bloqueada por datos de `001` que falten**:
  - **User Story 1 (cobertura de medios de pago)**: solo necesita `sucursal`. NO bloqueada.
  - **User Story 2 (terminales y firmware)**: solo necesita su propio registro y `sucursal`. NO
    bloqueada.
  - **User Story 3 (tokenización)**: necesita `venta` y su `referencia_terminal_pago` opaca, ambas
    disponibles. NO bloqueada. El único punto de integración es el flujo de captura de pago del
    servicio de venta de `001`; `plan.md` define si `007` expone un contrato que `001` invoca al
    cobrar con tarjeta, o si `007` procesa la referencia de forma diferida. En ambos casos la venta
    de `001` no depende de que `007` responda (FR-020, Principio II).
  - **User Story 4 (bitácora)**: transversal a las tres anteriores. NO bloqueada.
- **Este spec se puede escribir, aprobar e implementar ahora.** La decisión de entidad del punto
  siguiente ya está resuelta: la enmienda **v2.2.6** que añade `token_pago` fue aprobada y aplicada
  el 2026-09-05.

**Contrato con `006-caja-mermas-fraude`**: `006` difirió explícitamente el **desglose del arqueo por
medio de pago** a "cuando exista `007-pagos-seguridad` (dueño de `medio_pago`)", modelando por ahora
"lo esperado en caja" como un total único (`006/spec.md`, Assumptions). Cuando `007` exista, ese
desglose por medio de pago será un **refinamiento aditivo de `006`**, no un cambio de contrato:
`007` es el dueño de `medio_pago` y `006` lo consultará, igual que consulta el resto de `001`. `007`
no consume nada de `006`.

**Propiedad de datos — estado frente a la constitución (v2.2.6)**: tras la enmienda **v2.2.6**
(2026-09-05), la tabla de Propiedad de Datos lista para `007-pagos-seguridad` **cinco** entidades:
`terminal_pago`, `medio_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`. **Este spec usa
exactamente esas cinco.** Tres de las cuatro preocupaciones del encargo caían ya en las cuatro
entidades ratificadas (firmware de terminal → `terminal_pago`; cobertura de medios → `medio_pago` +
`cobertura_pago`; log de actividad → `bitacora_auditoria`); la cuarta —**la persistencia del token de
un cobro con tarjeta**— no tenía entidad anticipada:

- `research.md #1` concluyó que el conjunto {token, últimos dígitos, marca, tipo, terminal de
  captura, referencia de venta, clave de idempotencia} es el **registro autoritativo** de la relación
  venta↔token, con `UNIQUE` por cobro e idempotencia (FR-021), y **no cabe** en `bitacora_auditoria`
  (rastro de solo anexado, FR-025) ni en ninguna de las otras tres entidades sin forzar su semántica.
- Es una **quinta entidad nueva de `007`** (`token_pago`), añadida por la **enmienda v2.2.6**, del
  mismo tipo y con la misma justificación que v2.2.3 sobre `003` (`sugerencia_precio`), v2.2.4 sobre
  `004` (`sustitucion_producto`) y v2.2.5 sobre `005` (los tres mecanismos de promoción): la lista
  original de `007` se ratificó en v2.0.0 antes de que existiera este spec.

La enmienda **v2.2.6** fue aprobada y aplicada el 2026-09-05, con su informe de impacto en el
encabezado de `constitution.md` y la sincronización de las citas de "versión vigente" en `001`–`006`
(puerta de sincronización de enmiendas, v2.2.0). `data-model.md` de `007` se escribe sobre esa base.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las sucursales tiene su cobertura de medios de pago consultable, con la
  fecha desde la que cada medio está disponible; la métrica de un período pasado refleja el estado
  de entonces en el 100% de los casos.
- **SC-002**: El 100% de los eventos de intención de compra no atendida por medio de pago queda
  atribuido a una sucursal y un período, y 0% se registra como `venta`, movimiento de inventario o
  `consulta_no_atendida` de `001`.
- **SC-003**: Ninguna vista de cobertura, firmware o bitácora agrega datos de varias sucursales sin
  discriminar la de origen (0% de agregaciones sin sucursal).
- **SC-004**: El 100% de las terminales registradas se evalúa contra la última versión de firmware y
  la lista de vulnerabilidad conocida; cada señal de "desactualizada" o "expuesta a clonación"
  enumera su motivo en el 100% de los casos.
- **SC-005**: 0% de terminales deshabilitadas, bloqueadas o impedidas de uso por el sistema a partir
  de una señal de firmware: la acción correctiva siempre la decide una persona.
- **SC-006**: 0% de números de tarjeta completos (PAN), CVV o datos de banda/chip almacenados,
  registrados o devueltos por el módulo, en cualquier campo, archivo de registro, bitácora o
  respuesta de consulta.
- **SC-007**: El 100% de los cobros con tarjeta que se tokenizan conserva exactamente {token,
  últimos cuatro dígitos, marca, tipo, terminal, referencia de venta} y nada más.
- **SC-008**: El 100% de los intentos de persistir un PAN completo se rechaza y se registra en la
  bitácora sin el número.
- **SC-009**: Ante reintentos de emisión de token con la misma clave de idempotencia, se registra
  exactamente un token por cobro (0% de duplicados).
- **SC-010**: El 100% de los cobros con tarjeta cuya tokenización falla no impide que la `venta` de
  `001` se complete (0% de cobros bloqueados por el módulo de pagos).
- **SC-011**: El 100% de los hechos de pago (emisión de token, rechazo de PAN, actualización de
  firmware, cambio de cobertura, intención no atendida) genera una entrada de bitácora con tipo,
  día local, sucursal, iniciador y resultado.
- **SC-012**: 0% de entradas de bitácora modificadas o borradas tras su escritura (solo anexado).
- **SC-013**: 0% de operaciones de `007` que registran, modifican o recalculan `venta`, `turno`,
  `operador`, `sucursal` o cualquier otro dato propiedad de `001`; la `referencia_terminal_pago`
  opaca de `001` se rellena sin cambiar su tipo ni su semántica en el esquema de `001`.
- **SC-014**: 0% de integraciones con pasarelas, adquirentes o procesadores de pago reales; 0% de
  movimiento de dinero real.

## Assumptions

- **Sin pasarela de pago real**: este módulo no integra ningún adquirente, procesador ni bóveda de
  terceros, no ejecuta autorización ni settlement y no mueve dinero. "Tokenizar" es una operación
  local: recibir el PAN en el flujo de captura, devolver un token opaco y descartar el PAN. El
  alcance es la seguridad y el registro de los datos de pago de un minimarket. Ampliar esto a un
  procesador de pagos es un módulo nuevo, no una enmienda de este spec.
- **Origen del PAN en el flujo de captura**: se asume que el punto de venta de `001` entrega el
  número de tarjeta a `007` en el momento del cobro con tarjeta (entrada manual o lectura de la
  terminal) y que `007` responde con el token que `001` guarda como `referencia_terminal_pago`. El
  mecanismo exacto de esa entrega (contrato síncrono que `001` invoca, o cola que `007` consume) lo
  decide `plan.md`; en cualquier caso la venta de `001` no se bloquea si `007` no responde (FR-020).
- **Token opaco**: el token es un identificador sustituto sin relación derivable con el número de
  tarjeta y sin estabilidad entre ventas (una misma tarjeta usada en dos ventas produce dos tokens
  distintos). El módulo no mantiene un índice de tarjetas, solo de tokens por venta, para no
  reconstruir un identificador persistente de tarjeta ni de titular.
- **Últimos dígitos y marca**: se conservan los últimos cuatro dígitos y la marca porque son el
  identificador mínimo que un encargado necesita para conciliar un cobro con el comprobante físico
  del cliente, y es exactamente lo que la constitución permite conservar ("identificadores y últimos
  dígitos").
- **Lista de versiones de firmware vulnerables**: es configuración que el negocio mantiene, con una
  referencia identificable por entrada (un boletín del fabricante, un CVE, una nota interna). El
  sistema no descubre vulnerabilidades por su cuenta ni consulta fuentes externas; si la lista está
  vacía, ninguna terminal se marca expuesta por vulnerabilidad conocida (solo por desactualización).
- **Última versión de firmware por modelo**: también configuración del negocio. Si falta para un
  modelo, sus terminales se marcan "versión de referencia desconocida", nunca "al día".
- **Exposición a clonación como indicador consultivo**: el sistema señala terminales desactualizadas
  o vulnerables como riesgo para revisión; la decisión de actualizar, aislar o reemplazar es de una
  persona (Principio V). El sistema nunca deshabilita una terminal (Principio II: la caja no se
  bloquea).
- **Retención de la bitácora de auditoría**: las entradas se conservan al menos por el año fiscal en
  curso más el anterior (mínimo dos cierres anuales), alineado con la trazabilidad que exige el
  Principio IV; `plan.md` puede extenderlo pero no reducirlo por debajo de ese mínimo. Las entradas
  no se purgan antes de ese plazo.
- **Retención del token**: el token y su metadato mínimo viven mientras la `venta` asociada sea
  consultable; como el PAN nunca se almacena, no hay dato sensible que caduque. `plan.md` define si
  el token se purga junto con el archivado de ventas antiguas de `001`.
- **Día local**: todas las agregaciones de cobertura y todas las marcas de tiempo de la bitácora se
  calculan sobre el día local de la sucursal (`sucursal.zona_horaria` de `001`), no sobre el día
  UTC (constitución, "Tiempo"). Un reporte multi-sucursal declara su criterio de día.
- **Datos personales**: `007` no captura datos de cliente. De la tarjeta conserva solo marca, tipo y
  últimos cuatro dígitos; del operador, solo `id_operador` y su condición de encargado, nunca el PIN
  ni su hash. La bitácora no contiene datos personales más allá del identificador mínimo (Principio
  IV).
- **Reservas al encargado**: cambiar el catálogo o la cobertura de medios de pago, registrar o mover
  terminales, y editar las listas de versiones de referencia y de vulnerabilidad son acciones
  reservadas al encargado (`operador.es_encargado` de `001`), y todas quedan en la bitácora.
- **Constitución vigente citada**: v2.2.6. Este módulo **motivó la enmienda v2.2.6** (2026-09-05),
  que añadió `token_pago` a su entrada en la tabla de Propiedad de Datos (de 4 a 5 entidades) tras
  `research.md #1`. Las otras cuatro entidades (`terminal_pago`, `medio_pago`, `cobertura_pago`,
  `bitacora_auditoria`) estaban desde la ratificación. La enmienda está aprobada y aplicada.
- **Decisiones de alcance mayor, todas resueltas — ninguna quedó con default silencioso**: el
  alcance de la tokenización (local, sin pasarela), el tratamiento de la venta perdida por medio de
  pago (métrica de cobertura, no faltante) y la evaluación de exposición a clonación (indicador
  consultivo contra lista configurable) se fijaron con una decisión razonable documentada, con el
  mismo criterio que `003`–`006`. Ajustar cualquiera es una enmienda de este spec, no una decisión
  libre de `plan.md`.
