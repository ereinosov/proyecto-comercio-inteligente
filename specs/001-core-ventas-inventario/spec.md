# Feature Specification: Core de Ventas e Inventario

**Feature Branch**: `n/a` — el proyecto no es un repositorio git todavía; no se creó rama.

**Created**: 2026-09-04

**Status**: Draft

**Input**: Módulo base de Rasero para un minimarket de barrio con sección de frescos a peso y dos
sucursales. Registra los hechos de venta e inventario de los que dependen los otros seis módulos:
venta a peso, entradas por compra en lotes, traspasos entre sucursales, consultas no atendidas,
observaciones de precio de competencia, conteo físico, capital inmovilizado y reconciliación de
operaciones ejecutadas sin conectividad. Registra hechos; no decide acciones.

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura literal
> de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en español,
> conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-04

- Q: ¿Se implementa la devolución de mercancía con reingreso a inventario y reembolso, o solo la
  anulación de una venta? → A: Solo anulación. La anulación la exige la detección de fraude de
  `006-caja-mermas-fraude` (tasa de anulaciones por operador); ninguna de las siete funcionalidades
  definidas requiere devolución, así que queda fuera de alcance de este módulo.
- Q: ¿Qué criterio sigue el consumo de lotes al descontar existencias? → A: FIFO, primero en entrar
  primero en salir, como criterio base; es coherente con el cálculo de capital inmovilizado, que
  detecta antes los lotes antiguos sin salida. Refinado en la cuarta aclaración de esta sesión para
  el caso de los productos con caducidad.
- Q: ¿Debe el sistema bloquear una venta cuya cantidad excede el saldo de existencia calculado? →
  A: No. Advierte al operador, registra la venta y deja la diferencia expuesta para el siguiente
  conteo físico. Bloquear el cobro violaría el Principio II de la constitución: ninguna validación
  puede ser camino crítico de un cobro.
- Q: Con FIFO, ¿qué ocurre cuando un lote que entró después caduca antes que otro más antiguo? →
  A: manda la caducidad. Entre los lotes disponibles, sale primero el de caducidad más próxima; si
  el producto no tiene caducidad, o dos lotes caducan el mismo día, decide la entrada más antigua.
  El criterio efectivo es por tanto caducidad primero y entrada como desempate, no FIFO puro: es lo
  que evita mermas que el propio sistema habría provocado al mandar vender el lote equivocado.
- Q: Cuando una venta excede el saldo, ¿cómo queda representado el exceso? → A: la existencia queda
  en negativo y visible hasta el siguiente conteo físico. Es la única representación que mantiene
  el inventario reconstruible exactamente a partir de sus movimientos, como exige el Principio IV,
  y un saldo negativo en pantalla es además la señal de que ese producto necesita conteo.
- Q: ¿Qué límite tiene anular una venta? → A: el operador puede anular las ventas de su turno en
  curso; una venta de un turno ya cerrado solo la anula un encargado. Reutiliza la figura de
  encargado que ya existe para reasignar PIN, sin introducir un sistema de roles, y evita que la
  anulación sin límite se convierta en el vector del fraude que 006 debe detectar.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar una venta en caja (Priority: P1)

El cajero abre turno, se identifica con su PIN y cobra. La venta puede mezclar productos por unidad
(una lata de atún) y productos a peso (700 g de queso pesados en báscula). Al cerrar la venta, el
sistema descuenta las existencias, deja constancia de qué operador la ejecutó y por qué terminal de
pago se cobró, y no duplica nada si el cobro se reintenta.

**Why this priority**: es el hecho económico del que dependen todos los demás módulos. Sin venta
atribuida no hay margen que calcular, ni demanda que pronosticar, ni tasa de anulaciones por cajero
que vigilar. Es también el único flujo que no puede detenerse nunca.

**Independent Test**: con un catálogo y existencias precargadas, un evaluador puede abrir turno,
cobrar una venta mixta y verificar el descuento de existencias, la atribución a operador y terminal,
y que un reintento con la misma clave no genera una segunda venta. Entrega valor por sí solo: es un
punto de venta funcional.

**Acceptance Scenarios**:

1. **Given** un operador con turno abierto y PIN confirmado, y un producto por unidad con saldo 10,
   **When** registra una venta de 3 unidades, **Then** la venta queda registrada con su operador y
   terminal, el saldo pasa a 7 y se genera un movimiento de salida trazable a esa venta.
2. **Given** un producto marcado como granel con 5 000 g en lote, **When** el operador registra un
   renglón de 0,7 kg leído de báscula, **Then** el renglón se guarda con cantidad decimal, el
   inventario descuenta 700 g y la interfaz muestra la cantidad en kg.
3. **Given** una venta ya registrada con una clave de idempotencia, **When** el mismo cobro se
   reintenta con esa misma clave, **Then** el sistema devuelve la venta original y NO crea una
   segunda venta ni un segundo movimiento de inventario.
4. **Given** un servicio no crítico caído (pronóstico, analítica o telemetría), **When** el operador
   cobra, **Then** la venta se completa igualmente con el comportamiento base.
5. **Given** una venta registrada por error, **When** el operador la anula, **Then** la anulación
   queda registrada como hecho propio atribuido a ese operador, las existencias se reponen y la
   venta original permanece visible, nunca borrada.

---

### User Story 2 - Recibir mercancía del proveedor en lotes (Priority: P2)

El encargado recibe una compra y la ingresa al sistema: qué producto, qué cantidad, a qué costo y —
si es perecedero — con qué fecha de caducidad. Cada recepción alimenta o crea un lote en la sucursal
que la recibe.

**Why this priority**: sin entradas no hay existencias que vender ni costo que registrar. El costo
es el insumo que el módulo de márgenes necesita, y la caducidad es el insumo que el módulo de mermas
necesita.

**Independent Test**: registrar una compra de tres productos, uno de ellos perecedero, y verificar
que se crean los lotes con su costo y caducidad, que las existencias suben y que el movimiento de
entrada queda trazable a la recepción.

**Acceptance Scenarios**:

1. **Given** un producto no perecedero, **When** el encargado registra una entrada de 24 unidades a
   costo unitario conocido, **Then** se crea un lote con esa cantidad y ese costo, sin caducidad.
2. **Given** un producto granel perecedero, **When** se registra una entrada de 12,5 kg con fecha de
   caducidad, **Then** el lote guarda 12 500 g y su caducidad queda disponible para el módulo de
   mermas.
3. **Given** una entrada registrada, **When** se consulta el lote, **Then** muestra su costo, pero el
   sistema NO presenta ningún margen calculado en este módulo.

---

### User Story 3 - Registrar una consulta no atendida (Priority: P3)

Un cliente pregunta por un producto, no lo hay, y se va. Hoy eso no lo registra nadie. El cajero
marca la consulta en dos toques desde la propia pantalla de venta, sin pedir dato alguno al cliente
y sin abandonar el flujo de cobro.

**Why this priority**: es el dato más barato de capturar y el único que revela la demanda que nunca
llegó a ser venta. Sin él, el módulo de pronóstico solo ve demanda censurada por el agotamiento y
sistemáticamente pedirá de menos.

**Independent Test**: desde la pantalla de venta, marcar una consulta no atendida sobre un producto
agotado y verificar que queda registrada con producto, sucursal e instante, y que la caja sigue
operativa.

**Acceptance Scenarios**:

1. **Given** el cajero en la pantalla de venta, **When** marca un producto como consultado y no
   atendido, **Then** la consulta queda registrada en dos toques con producto, sucursal, instante y
   operador, sin solicitar ningún dato del cliente.
2. **Given** una consulta registrada, **When** se revisa el registro, **Then** incluye el saldo que
   el sistema tenía de ese producto en ese instante, de modo que el módulo de pronóstico pueda
   distinguir un agotamiento real de un producto que estaba pero no se localizó.

---

### User Story 4 - Comparar el precio propio contra la competencia (Priority: P4)

El encargado captura precios que observó en otros comercios y luego consulta, producto por producto,
cómo está su precio frente a esas observaciones, viendo con claridad de cuándo es cada dato. El
sistema le muestra la comparación; la decisión de mover el precio es suya.

**Why this priority**: el caso de negocio parte de que el cliente compara precios en segundos. Pero
la comparación solo sirve si el operador ve la antigüedad del dato: un precio de hace dos semanas no
puede pesar como uno de hoy.

**Independent Test**: capturar tres observaciones de canales distintos, una de ellas de otra
presentación, y verificar que la vista de comparación muestra el precio propio, cada observación
normalizada a la misma unidad de medida, y la antigüedad de cada una.

**Acceptance Scenarios**:

1. **Given** un producto propio de 1 kg, **When** se captura una observación de un competidor que lo
   vende en presentación de 500 g, **Then** la observación guarda la presentación observada tal cual
   y la comparación se muestra normalizada a precio por unidad de medida.
2. **Given** observaciones capturadas en distintas fechas, **When** el operador abre la comparación,
   **Then** cada observación muestra su antigüedad calculada en el momento de la lectura, con color,
   indicador de forma y texto explícito, y ninguna antigüedad se muestra solo por color.
3. **Given** un canal de competencia que aún no existe, **When** el operador lo nombra al capturar,
   **Then** el canal se añade al catálogo abierto y queda disponible para futuras capturas, sin
   crear un duplicado si ya existía con el mismo nombre normalizado.
4. **Given** una comparación desfavorable, **When** el operador la consulta, **Then** el sistema NO
   ajusta ningún precio por su cuenta.
5. **Given** un producto con precio base de $10 y un override de $9 declarado solo en Buena Fe,
   **When** se abre la comparación de precios para Quevedo Centro y, por separado, para Buena Fe,
   **Then** Quevedo Centro compara contra $10 y Buena Fe compara contra $9, cada una resuelta para
   la sucursal indicada (FR-050).

---

### User Story 5 - Cuadrar el inventario con un conteo físico (Priority: P5)

El encargado programa un conteo, cuenta lo que hay en estantería y bodega, y el sistema le muestra
en qué se diferencia lo contado del saldo que él mismo calculó a partir de los movimientos. La
diferencia se expone por producto y por lote; clasificar su causa no es tarea de este módulo.

**Why this priority**: el sistema no puede asumir que su propio saldo es correcto. Sin conteo, todo
lo que el resto de módulos construya encima descansa sobre un número no verificado.

**Independent Test**: iniciar un conteo sobre un subconjunto de productos, capturar cantidades
contadas distintas de las esperadas y verificar que el sistema expone la diferencia por producto y
lote y genera un ajuste trazable al conteo que lo originó.

**Acceptance Scenarios**:

1. **Given** un producto con saldo calculado de 40 unidades, **When** el conteo registra 37,
   **Then** el sistema expone una diferencia de −3 asociada a ese conteo, sin clasificar su causa.
2. **Given** un producto granel, **When** lo contado difiere de lo descontado de los lotes,
   **Then** la diferencia se registra como diferencia de granel, disponible para que el módulo de
   mermas la clasifique como corte o deshidratación.
3. **Given** un conteo resuelto, **When** se consulta el histórico de movimientos, **Then** el
   ajuste resultante es trazable al conteo que lo originó y el saldo anterior sigue siendo
   reconstruible.

---

### User Story 6 - Traspasar mercancía entre las dos sucursales (Priority: P6)

La sucursal de origen despacha mercancía a la otra. Mientras viaja, esa mercancía no está disponible
en ninguna de las dos, pero tampoco desaparece: pertenece a la operación de traspaso. La sucursal de
destino confirma la recepción.

**Why this priority**: con dos sucursales el traspaso es una operación cotidiana, y es el escenario
donde el inventario total se descuadra con más facilidad si se registra mal.

**Independent Test**: despachar un traspaso, verificar que el inventario total del sistema no cambia
mientras está en tránsito, y confirmar la recepción comprobando que la mercancía aparece en destino.

**Acceptance Scenarios**:

1. **Given** 20 unidades en la sucursal de origen, **When** se despacha un traspaso de 8, **Then**
   el origen queda con 12 disponibles, el destino sigue igual, y 8 constan en tránsito asociadas a
   la operación de traspaso.
2. **Given** un traspaso en tránsito, **When** se consulta el inventario total del sistema, **Then**
   el total incluye la mercancía en tránsito y coincide exactamente con el total previo al despacho.
3. **Given** un traspaso en tránsito de 8 unidades, **When** el destino confirma la recepción de 8,
   **Then** las 8 pasan a disponibles en destino y el tránsito queda en cero.
4. **Given** un traspaso de 8 unidades, **When** el destino confirma la recepción de solo 7,
   **Then** el sistema expone una discrepancia de 1 asociada a esa operación de traspaso y no la
   clasifica ni la absorbe en silencio.

---

### User Story 7 - Ver el capital inmovilizado (Priority: P7)

El dueño abre un listado de los lotes que llevan demasiado tiempo sin salir, con cuánto dinero
representa cada uno. El sistema se lo enseña; qué hacer con esa mercancía lo decide él.

**Why this priority**: convierte una intuición ("creo que ese estante no rota") en una cifra. Depende
de que existan lotes y movimientos, por eso va después de las historias que los producen.

**Independent Test**: con lotes de distintas categorías y antigüedades de última salida, verificar
que el listado señala exactamente los que superan el umbral de su categoría y calcula su valor como
cantidad restante por costo.

**Acceptance Scenarios**:

1. **Given** un lote de una categoría de frescos cuyo umbral es corto y cuya última salida excede
   ese umbral, **When** se consulta el listado, **Then** el lote aparece señalado con su valor
   inmovilizado.
2. **Given** un lote de no perecedero con la misma antigüedad pero un umbral más largo, **When** se
   consulta el listado, **Then** ese lote NO aparece señalado.
3. **Given** una categoría sin umbral propio definido, **When** se evalúan sus lotes, **Then** se
   aplica el umbral global de respaldo.
4. **Given** un lote señalado, **When** el dueño lo revisa, **Then** el sistema no propone ni ejecuta
   ninguna acción automática de descuento, traspaso o baja.

---

### User Story 8 - Sincronizar lo trabajado sin conexión (Priority: P8)

La caja siguió cobrando mientras no había internet. Al volver la conexión, lo trabajado sube al
servidor en el orden en que ocurrió de verdad, y si algo choca con otra operación sobre el mismo
recurso, el conflicto queda a la vista de una persona en lugar de resolverse a escondidas.

**Why this priority**: es la última historia en secuencia porque necesita que existan operaciones que
sincronizar, pero **no es opcional**: el Principio II de la constitución exige que la caja no se
detenga. Mientras esta historia no esté entregada, el sistema solo puede demostrarse con
conectividad continua, y esa limitación DEBE declararse en cualquier demostración.

**Independent Test**: desconectar la red, registrar varias operaciones, reconectar y verificar que
suben en orden de marca de tiempo de origen y que ninguna se pierde.

**Acceptance Scenarios**:

1. **Given** la caja sin conectividad, **When** el operador registra ventas y consultas no
   atendidas, **Then** cada operación se guarda localmente como pendiente de sincronizar con su
   marca de tiempo de origen y la caja sigue cobrando.
2. **Given** operaciones pendientes con marcas de tiempo distintas, **When** vuelve la conectividad,
   **Then** se envían al servidor en orden de marca de tiempo de origen.
3. **Given** dos operaciones en conflicto sobre el mismo recurso, **When** se sincronizan, **Then**
   prevalece la de marca de tiempo más antigua y la desplazada queda marcada como conflicto resuelto
   con referencia a la que prevaleció.
4. **Given** una operación desplazada por conflicto, **When** una persona revisa el histórico,
   **Then** la operación sigue siendo visible y no fue eliminada ni ocultada.

---

### User Story 9 - Corregir el carrito antes de cobrar (Priority: P9)

El cajero agregó un renglón con la cantidad equivocada, o el cliente cambió de opinión sobre un
producto antes de pagar. El cajero corrige la cantidad de ese renglón o lo quita del carrito sin
tener que empezar la venta de cero, y el total se actualiza al instante.

**Why this priority**: es una historia aditiva descubierta en auditoría de uso, estrictamente
**anterior** a confirmar el cobro. No cambia nada de lo ya certificado en US1 (idempotencia,
saldo negativo visible, FEFO): el carrito, hasta el momento de "Cobrar", es un borrador que solo
vive en la pantalla. Se numera P9 porque depende de que exista el flujo de venta de US1.

**Independent Test**: con un carrito de varios renglones sin cobrar, editar la cantidad de uno y
eliminar otro; verificar que el total refleja de inmediato ambos cambios y que al cobrar la venta
registrada contiene exactamente los renglones y cantidades resultantes.

**Acceptance Scenarios**:

1. **Given** un carrito con dos o más renglones sin cobrar, **When** el cajero pulsa el control de
   eliminar de un renglón, **Then** ese renglón desaparece del carrito y el total se recalcula sin
   pedir confirmación adicional.
2. **Given** un renglón en el carrito, **When** el cajero cambia su cantidad o peso en el propio
   renglón, **Then** el importe del renglón y el total del carrito se actualizan de inmediato sin
   volver a elegir el producto.
3. **Given** un carrito editado (renglones eliminados y cantidades cambiadas), **When** el cajero
   confirma el cobro, **Then** la venta registrada contiene exactamente los renglones y cantidades
   que quedaban en pantalla.
4. **Given** un carrito con un solo renglón, **When** el cajero lo elimina, **Then** el carrito
   queda vacío y la acción de cobrar no está disponible hasta que se agregue al menos un renglón.

---

### User Story 10 - Roles de operador, sucursal fija y autorización centralizada (Priority: P10)

Hoy un `operador` es global (sin sucursal asignada) y su única distinción de capacidad es el
booleano `es_encargado`, cuyo chequeo está copiado en tres servicios distintos. Esta historia
convierte eso en un modelo de autorización real: cada operador pertenece a una sucursal fija y
tiene uno de tres roles (`cajero` < `encargado` < `admin`); la verificación de rol vive en un
único mecanismo de backend y un único hook de frontend; y la interfaz **oculta** —no
deshabilita— lo que el rol activo no puede hacer. Un rol nuevo, `admin`, gana en exclusiva la
gestión de operadores.

Esto ejerce el **Principio VI** de la constitución (enmienda **v2.3.0**), que también cambia el
esquema de la entidad `operador` de este módulo. Es **autorización**, no autenticación: el PIN
+ hash (FR-006) no cambia, no se introduce JWT ni sesión de servidor, y `id_operador` sigue
viajando explícito.

**Why this priority**: es un cambio de arquitectura sobre `operador` y `turno`, entidades ya
certificadas de US1. Se numera P10 porque depende de que exista el flujo de turno (US1) y toca
datos de sesión ya en producción; su migración de datos debe correr contra el esquema vivo. No
altera ningún cálculo de dinero, existencias ni el contrato de `POST /ventas`.

**Independent Test**: crear un operador `cajero` atado a la sucursal A; iniciar sesión con él y
verificar que (a) la apertura de turno se resuelve a la sucursal A sin selector, (b) los ítems
de nav de encargado/admin no aparecen, (c) un intento directo por API de una acción de
encargado se rechaza con `{codigo, mensaje}`. Repetir con un `admin` y verificar que ve el
selector de sucursal, la pestaña de gestión de operadores, y puede crear/editar operadores.

**Acceptance Scenarios**:

1. **Given** un operador con rol `cajero` y sucursal asignada A, **When** abre turno, **Then**
   el turno se crea en la sucursal A sin que se le muestre ningún selector de sucursal.
2. **Given** ese mismo `cajero`, **When** por API directa intenta abrir turno en la sucursal B,
   **Then** el backend lo rechaza con `{codigo: "turno_sucursal_no_asignada", mensaje: "Este
   operador está asignado a [A], no puede abrir turno en otra sucursal."}` y no se crea turno.
3. **Given** un operador con rol `admin`, **When** abre turno, **Then** se le muestra el
   selector de sucursal y puede elegir cualquiera de las sucursales activas.
4. **Given** un turno abierto por un `cajero`, **When** carga cualquier pantalla, **Then** el
   ítem de nav "Administración", el atajo "+ Crear producto nuevo" y todo botón de
   Editar/Desactivar de listas administrables **no se renderizan** (no aparecen deshabilitados).
5. **Given** un turno abierto por un `encargado`, **When** entra a Administración, **Then** ve
   las 5 pestañas de datos maestros y sus acciones de crear/editar/desactivar, pero **no** la
   pestaña de gestión de operadores.
6. **Given** un turno abierto por un `admin`, **When** entra a Administración, **Then** ve una
   6.ª pestaña "Operadores" donde puede dar de alta un operador (con sucursal y rol
   obligatorios), cambiar el rol o la sucursal de otro, y desactivarlo.
7. **Given** un `encargado`, **When** por API directa intenta cambiar el rol de otro operador a
   `encargado` o `admin`, **Then** el backend lo rechaza: ascender operadores es exclusivo de
   `admin`.
8. **Given** cualquier operador (incluido `cajero`), **When** edita un `cliente`, **Then** la
   acción se permite: la edición de cliente sigue sin restricción de rol.
9. **Given** la base de datos anterior a esta historia, **When** corre la migración, **Then**
   cada operador con `es_encargado=false` queda con `rol='cajero'`, cada uno con
   `es_encargado=true` queda con `rol='encargado'`, ninguno queda como `admin`, y cada uno
   recibe una `id_sucursal` no nula.

---

### User Story 11 - Sesión de turno con token verificable (Priority: P11)

La User Story 10 centralizó la verificación de **rol** (`requiere_rol`), pero la **identidad**
del operador seguía resolviéndose leyendo el `id_operador` que el propio cliente envía en el
cuerpo de cada petición, sin comprobar que quien llama sea de verdad ese operador. Con la consola
de red abierta, cualquiera cambia ese valor y actúa como cualquier rol —`admin` incluido— sin
conocer ningún PIN. Ese patrón (`id_operador` en el cuerpo, sin sesión) es anterior a US10:
viene de `007-pagos-seguridad`. US10 no lo introdujo, sólo lo volvió más grave al añadir una
jerarquía real que suplantar.

Esta historia cierra esa brecha. Al abrir turno, tras validar el PIN, el backend emite un **token
de sesión de turno** (JWT firmado con clave simétrica, HS256) con los claims mínimos
`id_operador`, `id_turno`, `rol` y `exp`. El frontend lo guarda en memoria junto al turno y lo
adjunta como `Authorization: Bearer <token>` en toda petición sujeta a rol. El backend deriva la
identidad **exclusivamente** de ese token; el `id_operador` del cuerpo queda ignorado para
autorización y se retira de esos cuerpos. El token se invalida por expiración de tiempo (12 h),
por cierre del turno, o si el operador se desactiva.

Esto ejerce la sub-sección **"Identidad de sesión"** del **Principio VI** (enmienda
constitucional **v2.4.0**). Es **identidad de sesión**, no una credencial nueva: el PIN + hash
(FR-006) sigue siendo lo único que se presenta; el token es la consecuencia de presentarlo. **No
cambia ningún esquema** (la invalidación por cierre reutiliza `turno.instante_cierre`).

**Why this priority**: es una corrección de seguridad sobre el mecanismo central de
autorización, transversal a todos los routers que hoy verifican rol. Se numera P11 porque
depende de que exista el flujo de turno (US1) y la verificación de rol centralizada (US10). No
altera ningún cálculo de dinero ni de existencias, ni el contrato de `POST /ventas`.

**Independent Test**: autenticado como `cajero` (turno abierto, token en mano), enviar un
`id_operador` de `admin` en el cuerpo de una acción que requiere `admin` (p. ej.
`POST /operadores`): el backend responde `403 rol_insuficiente` —el cuerpo no tuvo ningún
efecto—. Sin token: `401`. Con el token de un turno ya cerrado: `401`. Con el token de un
operador desactivado tras la emisión: `401`.

**Acceptance Scenarios**:

1. **Given** un operador abre turno con PIN correcto, **When** el turno se crea, **Then** la
   respuesta incluye un campo `token` (JWT) además de los datos del turno.
2. **Given** un `cajero` con turno abierto y su token, **When** hace `POST /operadores`
   (acción de `admin`) con un `id_operador` de `admin` en el cuerpo, **Then** el backend lo
   rechaza con `{codigo: "rol_insuficiente"}` (403): la identidad salió del token, no del cuerpo.
3. **Given** cualquier petición a un endpoint sujeto a rol **sin** header `Authorization`,
   **When** llega al backend, **Then** se rechaza con `401` y `{codigo: "sesion_invalida",
   mensaje: "Tu turno expiró o fue cerrado. Abre turno de nuevo."}`, sin traza técnica.
4. **Given** un token cuyo `exp` ya pasó, **When** se usa en un endpoint sujeto a rol, **Then**
   el backend responde `401` con `{codigo: "sesion_expirada"}`.
5. **Given** un token válido por tiempo pero cuyo turno fue cerrado (`POST /turnos/{id}/cierre`),
   **When** se usa, **Then** el backend responde `401 sesion_invalida` aunque no haya expirado.
6. **Given** un token de un operador que un `admin` desactivó después de la emisión, **When** se
   usa, **Then** el backend responde `401` de inmediato, sin esperar a que expire.
7. **Given** un `encargado` con turno abierto y su token, **When** hace una acción de
   `encargado` (crear una categoría), **Then** la acción se ejecuta con `201` y la identidad
   registrada es la del token.
8. **Given** el frontend con la sesión activa, **When** una petición devuelve `401` por sesión
   expirada o cerrada, **Then** la interfaz muestra "Tu turno expiró o fue cerrado. Abre turno
   de nuevo." y vuelve a la pantalla de apertura de turno, no un error genérico.
9. **Given** el código tras esta historia, **When** se hace `grep -rn "id_operador" backend/rasero/api/`
   sobre los cuerpos de escritura sujetos a rol, **Then** ninguno declara `id_operador` /
   `id_operador_solicitante` como campo del cuerpo para autorización.

---

### Edge Cases

- **Peso cero o negativo en báscula**: un renglón de granel con cantidad menor o igual a cero se
  rechaza antes de cerrar la venta.
- **Venta que excede el saldo**: el sistema advierte al operador y le permite continuar registrando
  la venta física que ya ocurrió; la existencia queda en saldo negativo, visible, hasta el
  siguiente conteo, porque impedir el cobro detendría la caja.
- **Lote posterior que caduca antes**: el sistema consume primero el de caducidad más próxima
  aunque haya entrado después; el orden de entrada solo decide entre lotes sin caducidad o con la
  misma fecha.
- **Anulación de una venta de un turno ya cerrado**: el operador no puede hacerlo; requiere a un
  encargado, y la anulación queda atribuida al encargado, no al operador de la venta original.
- **Producto sin costo registrado**: aparece en el listado de capital inmovilizado con valor no
  calculable, nunca con valor cero, para no fingir una cifra.
- **Lote agotado durante un traspaso en tránsito**: la mercancía en tránsito nunca se consume desde
  el origen; el saldo disponible en origen ya la excluyó al despachar.
- **Traspaso nunca confirmado**: la mercancía permanece en tránsito y visible como tal
  indefinidamente; el sistema no la reabsorbe automáticamente pasado ningún plazo.
- **Reloj del dispositivo desviado**: la marca de tiempo de origen se registra tal como la reportó
  el dispositivo y se conserva junto al instante de recepción en el servidor, de modo que un desvío
  sea detectable en lugar de silencioso.
- **Observación de competencia de presentación no convertible** (el competidor vende un combinado
  sin unidad de medida comparable): se guarda la observación pero se excluye de la comparación
  normalizada y se marca como no comparable.
- **PIN olvidado a mitad de turno**: un encargado reasigna el PIN; el turno en curso y sus ventas
  conservan la atribución al operador original.
- **Dos operadores en la misma caja**: cada venta se atribuye al operador con turno abierto en el
  momento de registrarla; cerrar turno y abrir otro no reatribuye ventas ya registradas.
- **Consulta no atendida sobre un producto con saldo positivo**: se permite registrarla; el saldo
  del instante queda guardado para distinguir agotamiento de producto no localizado.
- **Cantidad de un renglón editada a cero o vacía**: el renglón no se elimina solo; queda con el
  importe en cero y el cajero decide si lo quita o corrige. Cobrar con un renglón en cero se trata
  igual que hoy trata US1 una cantidad no válida.
- **Editar el único renglón del carrito hasta dejarlo inválido**: no se borra el carrito; la acción
  de cobrar simplemente no está disponible mientras no haya un renglón válido.
- **Operador existente sin turnos previos al migrar**: recibe como `id_sucursal` la primera
  sucursal activa por orden de `id_sucursal`; queda anotado para que un `admin` lo revise, nunca
  se deja nulo.
- **`admin` que abre turno sin elegir sucursal**: el selector no tiene valor por defecto; el
  turno no se abre hasta que elige una. Su `operador.id_sucursal` no se usa como valor
  preseleccionado para no sugerir una restricción que no existe.
- **Desactivar al único `admin`**: la gestión de operadores no lo impide, pero muestra una
  advertencia de que quedará sin ningún operador capaz de gestionar operadores; la decisión es
  del `admin` que la ejecuta (mismo criterio que el resto de desactivaciones: informar con datos
  reales, nunca bloquear).
- **Cambiar la sucursal de un operador con turno abierto**: se permite; el turno en curso
  conserva su `id_sucursal` original (las ventas ya atribuidas no se reatribuyen), y la nueva
  sucursal aplica a partir del siguiente turno.
- **Frontend que oculta una opción y backend que igual la recibe**: defensa en profundidad. Que
  el nav no ofrezca una acción no exime al backend de rechazarla con `{codigo, mensaje}` si
  llega por API directa.
- **Token expirado a mitad de una operación larga** (User Story 11): la petición que lo detecta
  se rechaza con `401`; el frontend lleva al operador a abrir turno de nuevo. No hay refresco
  silencioso de token —la sesión de turno no se renueva sola— pero 12 h cubren cualquier turno
  real de caja con margen.
- **Turno cerrado por otro proceso mientras el token sigue "vivo" por tiempo** (User Story 11):
  la siguiente petición con ese token se rechaza con `401 sesion_invalida`; la invalidación por
  cierre gana sobre la validez por tiempo.
- **Operador desactivado mientras su turno sigue abierto** (User Story 11): su token se rechaza
  de inmediato en la siguiente petición (`401`), sin esperar a `exp` ni al cierre de turno.
  Criterio conservador: quitarle el acceso a un operador desactivado no puede depender de que
  alguien cierre su turno.
- **`id_operador` en el cuerpo distinto del operador del token** (User Story 11): el backend
  **ignora** el del cuerpo por completo; no compara, no rechaza por discrepancia. Una sola
  fuente de verdad. El campo se retira de esos cuerpos.
- **Petición a un endpoint que hoy no verifica identidad** (entradas de inventario, traspasos,
  conteos, sincronización, la mayoría de precios/pronóstico/promociones): fuera del alcance de
  User Story 11. Siguen aceptando peticiones sin token, igual que hoy. Se anotan como candidatos
  a una historia futura de identidad de sesión ampliada.

## Requirements *(mandatory)*

### Functional Requirements

**Venta y atribución**

- **FR-001**: El sistema DEBE permitir registrar una venta con uno o más renglones, cada uno
  referido a un producto y una cantidad.
- **FR-002**: El sistema DEBE aceptar cantidad entera para productos no marcados como granel y
  cantidad decimal para productos marcados como granel.
- **FR-003**: El sistema DEBE llevar el inventario de productos granel en gramos como número entero
  y presentarlo al usuario en kilogramos.
- **FR-004**: El sistema DEBE atribuir cada venta a un operador identificado, y a la terminal de
  pago con la que se cobró.
- **FR-005**: El operador DEBE identificarse al abrir turno eligiéndose de una lista y confirmando
  un PIN numérico de cuatro dígitos; toda venta del turno se atribuye a ese operador.
- **FR-006**: Un encargado DEBE poder reasignar el PIN de un operador. El sistema NO ofrece
  recuperación de PIN por correo, expiración de sesión ni control de acceso a pantallas por rol.
- **FR-007**: El sistema DEBE guardar en cada venta la referencia a la terminal de pago empleada,
  como dato opaco; la definición y las reglas de seguridad de las terminales pertenecen al módulo
  de pagos y seguridad.
- **FR-008**: El sistema DEBE aceptar una clave de idempotencia por venta y devolver la venta
  original ante un reintento con la misma clave, sin crear duplicados de venta ni de movimiento de
  inventario.
- **FR-009**: El sistema DEBE registrar la anulación de una venta como hecho propio, atribuido al
  operador que la ejecuta y con su instante, reponiendo las existencias y conservando visible la
  venta anulada. El sistema NO DEBE implementar devolución de mercancía por parte del cliente, con
  reingreso a inventario y reembolso: eso queda fuera del alcance de este módulo.
- **FR-049**: Un operador DEBE poder anular únicamente ventas de su turno en curso. Anular una
  venta de un turno ya cerrado DEBE requerir a un encargado, y la anulación DEBE quedar atribuida a
  quien la ejecutó, no al operador de la venta original.
- **FR-010**: Cada renglón de venta DEBE generar un movimiento de salida de inventario trazable a
  esa venta.
- **FR-011**: La venta DEBE completarse aunque los servicios de pronóstico, analítica o telemetría
  no respondan.
- **FR-047**: El sistema DEBE permitir registrar una venta cuya cantidad excede el saldo de
  existencia calculado. DEBE advertir al operador antes de cerrarla, DEBE registrarla igualmente y
  DEBE dejar que la existencia quede en saldo negativo, visible como tal, hasta el siguiente conteo
  físico. Limitar el saldo a cero está PROHIBIDO, porque rompería la reconstrucción del inventario
  a partir de sus movimientos. Bloquear el cobro por esta causa está PROHIBIDO: ninguna validación
  de existencias puede ser camino crítico de un cobro.

**Entradas, lotes y costo**

- **FR-012**: El sistema DEBE permitir registrar una entrada de inventario por compra a proveedor,
  creando o alimentando un lote en la sucursal receptora.
- **FR-013**: Cada lote DEBE guardar su costo y, cuando el producto lo requiera, su fecha de
  caducidad.
- **FR-014**: El sistema NO DEBE calcular ni presentar margen en este módulo; solo registra el
  costo.
- **FR-015**: Cada lote DEBE pertenecer a exactamente una sucursal.
- **FR-048**: Al descontar existencias, el sistema DEBE consumir primero el lote de caducidad más
  próxima entre los disponibles en esa sucursal. Cuando el producto no lleva caducidad, o cuando
  dos lotes caducan el mismo día, DEBE consumir el de entrada más antigua. Cada movimiento de
  salida DEBE identificar de qué lote se descontó, para que el consumo sea auditable.

**Traspasos**

- **FR-017**: Un traspaso entre sucursales DEBE registrarse como una operación de traspaso
  identificable con dos asientos enlazados: salida en origen y entrada en destino.
- **FR-018**: Mientras un traspaso está en tránsito, la mercancía DEBE pertenecer a la operación de
  traspaso: no cuenta como disponible en ninguna de las dos sucursales y sigue contando en el
  inventario total del sistema.
- **FR-019**: El sistema DEBE exponer cualquier discrepancia entre lo despachado y lo confirmado en
  destino, asociada a la operación de traspaso, sin clasificarla ni absorberla.

**Consultas no atendidas**

- **FR-020**: El punto de venta DEBE exponer una acción de dos toques para registrar una consulta no
  atendida con producto, sucursal, instante y operador, sin solicitar dato alguno del cliente.
- **FR-021**: Cada consulta no atendida DEBE guardar el saldo que el sistema tenía de ese producto
  en ese instante.

**Precios de competencia**

- **FR-022**: El sistema DEBE registrar cada precio de competencia como una observación fechada con
  producto, canal, presentación observada, precio, fuente, instante de captura y operador.
- **FR-023**: El sistema DEBE normalizar las observaciones a precio por unidad de medida para
  compararlas contra el precio propio, conservando intacta la presentación observada.
- **FR-024**: La antigüedad de una observación DEBE calcularse en el momento de la lectura y NO
  almacenarse como campo.
- **FR-025**: El catálogo de canales de competencia DEBE ser una tabla abierta que el operador
  alimenta, evitando duplicados por nombre normalizado.
- **FR-026**: La captura de observaciones DEBE hacerse por carga manual o por archivo. La obtención
  automática desde sitios web de terceros está PROHIBIDA.
- **FR-027**: La vista de comparación DEBE mostrar el precio propio junto a las observaciones
  vigentes, cada una con su antigüedad expresada simultáneamente por color, indicador de forma y
  texto.
- **FR-028**: El sistema NO DEBE ajustar ningún precio de forma automática.
- **FR-050**: El sistema DEBE admitir que el precio de un producto difiera por sucursal mediante
  un override opcional; una sucursal sin override hereda el precio base del producto. La
  comparación de precio propio contra la competencia (FR-027) DEBE resolverse para la sucursal
  indicada, no contra un precio global.

**Conteo físico**

- **FR-029**: El sistema DEBE permitir iniciar un conteo físico programado, acotado a una sucursal y
  opcionalmente a un subconjunto de productos o categorías.
- **FR-030**: El sistema DEBE comparar lo contado contra el saldo calculado a partir de los
  movimientos y exponer la diferencia por producto y por lote.
- **FR-031**: El sistema NO DEBE clasificar la causa de la diferencia; esa clasificación pertenece
  al módulo de caja, mermas y fraude.
- **FR-032**: Al resolverse un conteo, el ajuste resultante DEBE registrarse como movimiento
  trazable al conteo que lo originó, conservando reconstruible el saldo anterior.
- **FR-016** *(reubicado desde "Granel y diferencias"; premisa corregida tras análisis)*: la merma
  de un producto a granel por corte o deshidratación NO se detecta en el momento de la venta —si
  se facturan 700 g, se descuentan 700 g del lote, sin diferencia estructural posible entre ambos—.
  Se revela en el conteo físico, cuando el peso vendido de un lote más su peso restante no suman
  el peso que entró originalmente. Esa diferencia es la misma diferencia bruta que expone FR-030
  para ese lote; el sistema NO DEBE clasificarla como corte, deshidratación u otra causa —esa
  clasificación pertenece a `006-caja-mermas-fraude`, igual que cualquier otra diferencia de
  conteo (FR-031).

**Capital inmovilizado**

- **FR-033**: El sistema DEBE señalar como capital inmovilizado todo lote cuya última salida exceda
  el umbral de días de su categoría.
- **FR-034**: El umbral DEBE definirse por categoría de producto; las categorías sin umbral propio
  DEBEN heredar un umbral global de respaldo configurable.
- **FR-035**: El valor inmovilizado de un lote DEBE calcularse como cantidad restante por costo del
  lote. Un lote sin costo registrado DEBE mostrarse como no calculable, nunca como cero.
  *(Nota de implementación — ver research.md §11: como `lote.costo_unitario` es `NUMERIC(12,4) NOT
  NULL`, "sin costo registrado" se implementa con el centinela `costo_unitario = 0.00`, no con
  `NULL`; para esos lotes el listado devuelve `valor_calculable: false` y `valor_inmovilizado:
  null`.)*
- **FR-036**: El sistema DEBE limitarse a hacer visible el capital inmovilizado, sin proponer ni
  ejecutar acción alguna sobre él.

**Operación sin conectividad**

- **FR-037**: Toda operación ejecutada sin conectividad DEBE persistirse localmente como pendiente
  de sincronizar, con su marca de tiempo de origen.
- **FR-038**: Al recuperarse la conectividad, las operaciones pendientes DEBEN enviarse en orden de
  marca de tiempo de origen.
- **FR-039**: Ante un conflicto sobre el mismo recurso DEBE prevalecer la operación de marca de
  tiempo más antigua.
- **FR-040**: La operación desplazada por un conflicto DEBE marcarse como conflicto resuelto con
  referencia a la que prevaleció, y permanecer visible para revisión humana. Eliminarla u ocultarla
  está PROHIBIDO.
- **FR-041**: El sistema DEBE conservar, junto a la marca de tiempo de origen, el instante en que el
  servidor recibió la operación.

**Transversales**

- **FR-042**: Toda operación que mueva dinero o existencias DEBE registrar operador, sucursal, caja
  cuando aplique, instante y resultado.
- **FR-043**: Los importes y las cantidades en gramos DEBEN representarse con precisión exacta; el
  uso de coma flotante binaria está PROHIBIDO.
- **FR-044**: Los instantes DEBEN almacenarse en tiempo universal y presentarse en la zona horaria
  de la sucursal de la operación; las agregaciones por día DEBEN usar el día local de la sucursal.
- **FR-045**: El sistema DEBE operar en una sola moneda (USD).
- **FR-046**: El sistema DEBE admitir un número no acotado de sucursales; codificar en cualquier
  parte que las sucursales son dos está PROHIBIDO.

**Corrección del carrito antes de cobrar (User Story 9)**

- **FR-051**: Antes de confirmar el cobro, cada renglón del carrito DEBE ofrecer un control visible
  para eliminarlo del carrito. Eliminar un renglón individual NO DEBE pedir confirmación adicional
  (es una acción de bajo riesgo, reversible agregando el producto de nuevo); esto NO altera el
  flujo de confirmación de anular una venta ya cobrada (FR-009), que se conserva.
- **FR-052**: Antes de confirmar el cobro, cada renglón DEBE permitir cambiar su cantidad (o su
  peso, si es granel) sin eliminar y volver a agregar el producto. El importe del renglón y el
  total del carrito DEBEN recalcularse de inmediato al editar o eliminar.
- **FR-053**: La corrección del carrito es estado local de la pantalla hasta el momento de
  "Cobrar"; NO DEBE introducir ningún endpoint nuevo ni persistir el carrito parcialmente. La venta
  registrada al cobrar DEBE contener exactamente los renglones y cantidades resultantes de la
  edición, sin efecto sobre FEFO (FR-048), el saldo negativo visible (FR-047) ni ningún otro
  requisito de US1.

**Roles de operador, sucursal fija y autorización centralizada (User Story 10 — Principio VI,
enmienda constitucional v2.3.0)**

- **FR-054**: Cada `operador` DEBE pertenecer a exactamente una `sucursal` (`operador.id_sucursal`,
  FK, NOT NULL). Es una relación uno-a-uno; una tabla de asociación operador↔sucursal está
  PROHIBIDA salvo caso de uso demostrado de rotación.
- **FR-055**: Cada `operador` DEBE tener exactamente un rol de un conjunto cerrado: `cajero`,
  `encargado` o `admin`. La columna booleana `es_encargado` se retira. La jerarquía es
  acumulativa: `cajero` < `encargado` < `admin`.
- **FR-056**: La migración de datos DEBE convertir `es_encargado=false → rol='cajero'` y
  `es_encargado=true → rol='encargado'`, sin promover ningún operador a `admin`. El script de
  migración DEBE llevar la regla de conversión como comentario explícito y su procedimiento de
  reversión. `id_sucursal` de cada operador existente se deriva de su último turno, o de la
  primera sucursal activa si no tiene turnos.
- **FR-057**: La verificación de rol DEBE realizarse en un único mecanismo de backend
  —`requiere_rol(sesion, id_operador, rol_minimo)` en `backend/rasero/seguridad.py`, expuesto
  además como dependency reutilizable de FastAPI parametrizable por rol mínimo—. Replicar el
  chequeo de rol por servicio, router o pantalla está PROHIBIDO. Las tres funciones
  `_encargado_o_error` actuales (`administracion.py`, `cobertura_pago.py`, `terminales_pago.py`)
  DEBEN eliminarse y reemplazarse por ese mecanismo. El código de error reutiliza los tipos ya
  existentes del sistema; no se introduce un tipo de error nuevo si uno cubre el caso.
- **FR-058**: Toda acción que hoy requiere `es_encargado` (administración de datos maestros,
  terminales de pago, cobertura de medios de pago) DEBE requerir rol `encargado` o superior —
  igual de accesible para `encargado` y `admin`.
- **FR-059**: La gestión de operadores —alta, edición, desactivación— y la asignación de rol y
  de sucursal de otros operadores DEBE ser exclusiva del rol `admin`. Ningún `encargado` puede
  ascender a otro operador a `encargado` ni a `admin`.
- **FR-060**: Al abrir turno, para un operador `cajero` o `encargado` la sucursal DEBE resolverse
  automáticamente a `operador.id_sucursal`, sin selector visible. Para `admin` el selector DEBE
  permanecer visible y permitir cualquier sucursal activa (su `id_sucursal` es dato de registro,
  no restricción).
- **FR-061**: El backend DEBE rechazar (defensa en profundidad) todo intento de que un `cajero`
  o `encargado` abra turno en una sucursal distinta a la asignada, con
  `{codigo: "turno_sucursal_no_asignada", mensaje: "Este operador está asignado a [sucursal], no
  puede abrir turno en otra sucursal."}` — mismo formato `{codigo, mensaje}` del resto del
  sistema. No se crea turno.
- **FR-062**: El frontend DEBE **ocultar** —no deshabilitar— toda opción de navegación y toda
  acción que el rol activo no pueda usar: el ítem "Administración", el atajo "+ Crear producto
  nuevo" desde Venta, los botones de Editar/Desactivar de listas administrables y la pestaña de
  gestión de operadores. El patrón es el ya establecido para el atajo de creación de producto:
  "nunca lleva a un error de permisos, simplemente no se ofrece". La lectura del rol DEBE
  centralizarse en un único hook de frontend (`useRol`) que reutiliza la fuente de verdad
  existente del operador del turno; leer `es_encargado` directamente en un componente está
  PROHIBIDO.
- **FR-063**: La edición de `cliente` NO tiene restricción de rol y esta historia NO la
  introduce: cualquier `cajero` puede editarla (decisión explícita ya documentada).
- **FR-064**: La User Story 10 es de **autorización de rol**, no de autenticación. El PIN + hash
  (FR-006) no cambia. *(La resolución de identidad de sesión que US10 dejaba en el `id_operador`
  del cuerpo la corrige la User Story 11 — ver FR-065.)*

**Identidad de sesión de turno (User Story 11 — Principio VI, sub-sección "Identidad de sesión",
enmienda constitucional v2.4.0)**

- **FR-065**: Al abrir turno (`POST /turnos`), y sólo tras validar el PIN (FR-005/FR-006), el
  sistema DEBE emitir un token de sesión de turno y devolverlo en la respuesta. El token es un
  JSON Web Token firmado con clave simétrica (HS256). Se emite un token por turno abierto.
- **FR-066**: El token DEBE llevar exactamente estos claims: `id_operador`, `id_turno`, `rol` y
  `exp` (expiración). El backend NUNCA DEBE usar el `rol` del claim para autorizar: `requiere_rol`
  sigue resolviendo el rol real desde la tabla `operador` en cada verificación. El claim `rol`
  existe sólo para la interfaz.
- **FR-067**: Toda petición a un endpoint que hoy verifica rol (`requiere_rol` / `exige_rol`)
  DEBE exigir el token en el header `Authorization: Bearer <token>`. La identidad del operador
  DEBE derivarse EXCLUSIVAMENTE de ese token. El campo `id_operador` (o `id_operador_solicitante`)
  del cuerpo de esas peticiones queda IGNORADO para autorización y DEBE retirarse del esquema del
  cuerpo. NO se valida cruce cuerpo-vs-token: una sola fuente de verdad, el token.
- **FR-068**: El backend DEBE rechazar con `401` toda petición sujeta a rol cuyo token: (a) falte
  o tenga firma inválida o malformada — `{codigo: "sesion_invalida"}`; (b) haya expirado por
  tiempo — `{codigo: "sesion_expirada"}`; (c) refiera un turno con `instante_cierre` no nulo —
  `{codigo: "sesion_invalida"}`; (d) refiera un operador con `activo = false` —
  `{codigo: "sesion_invalida"}`. Todos con mensaje orientado a la acción correctiva ("Tu turno
  expiró o fue cerrado. Abre turno de nuevo."), sin traza técnica (Principio IV). Los códigos
  `sesion_invalida` y `sesion_expirada` son nuevos y no colisionan con los de `errores.py`.
- **FR-069**: El `exp` del token DEBE ser un tiempo fijo de 12 horas desde la emisión. NO hay
  refresco ni renovación: al expirar, el operador abre turno de nuevo. El token NO se persiste en
  ninguna tabla; la invalidación por cierre de turno se comprueba contra `turno.instante_cierre`,
  que ya existe — sin tabla de revocación ni columna nueva.
- **FR-070**: El frontend DEBE guardar el token en memoria, en el mismo estado donde ya vive el
  turno abierto. Guardarlo en `localStorage`, `sessionStorage` o cualquier almacenamiento de
  navegador está PROHIBIDO. Perderlo al recargar la página es correcto (igual que hoy se pierde
  el turno). El cliente HTTP DEBE adjuntar el header `Authorization` automáticamente cuando hay
  sesión activa; ninguna pantalla lo hace a mano.
- **FR-071**: Ante un `401` de sesión (`sesion_invalida` / `sesion_expirada`) a mitad de sesión,
  el frontend DEBE mostrar "Tu turno expiró o fue cerrado. Abre turno de nuevo." y volver a la
  pantalla de apertura de turno — nunca el error genérico "Ocurrió un error".
- **FR-072**: La clave de firma del token DEBE inyectarse por entorno (`JWT_SECRET_KEY`), con un
  valor por defecto SÓLO para desarrollo, igual que `DATABASE_URL` en `configuracion.py`. Ningún
  secreto real en el repositorio.
- **FR-073**: Los endpoints que hoy NO verifican identidad alguna (entradas de inventario,
  traspasos, conteos físicos, sincronización de operaciones pendientes, y la mayoría de
  precios/pronóstico/promociones) quedan FUERA DEL ALCANCE de esta historia: no cambian y siguen
  aceptando peticiones sin token. Se anotan como candidatos a una historia futura.

### Key Entities

Entidades ya asignadas a este módulo por la constitución vigente:

- **sucursal**: local físico con su zona horaria. Cardinalidad no acotada.
- **producto**: artículo del catálogo. Indica si se vende a granel y a qué categoría pertenece.
- **categoria**: agrupación de productos; porta el umbral de días de capital inmovilizado.
- **zona_exhibicion**: zona física de exhibición dentro de una sucursal, con su grado de
  privilegio. Este módulo la cataloga; el módulo de precios y márgenes la usa para sugerir
  colocación.
- **lote**: cantidad recibida de un producto en una sucursal, con su costo y su caducidad opcional.
- **existencia**: saldo disponible de un producto en una sucursal, derivado de los movimientos.
- **movimiento_inventario**: hecho que altera existencias (entrada, salida por venta, salida y
  entrada por traspaso, ajuste por conteo). Referencia siempre el hecho que lo originó.
- **venta**: transacción de cobro con su operador, terminal, sucursal, instante y clave de
  idempotencia.
- **renglon_venta**: línea de una venta con producto, cantidad y precio aplicado.
- **consulta_no_atendida**: producto consultado y no vendido, con sucursal, instante, operador y
  saldo del momento.
- **observacion_precio**: precio de competencia observado, con canal, presentación, fuente e
  instante de captura.
- **canal_competencia**: origen de una observación. Catálogo abierto.

Entidades **incorporadas a este módulo por la enmienda v2.1.0** de la constitución, a raíz de esta
misma especificación — ver "Dependencias Constitucionales":

- **operador**: persona que ejecuta ventas y conteos, con su PIN. **Enmienda v2.3.0 (User Story
  10)**: gana `id_sucursal` (FK → `sucursal`, NOT NULL, uno-a-uno) y su booleano `es_encargado`
  se reemplaza por `rol` (ENUM cerrado `cajero` | `encargado` | `admin`). La autorización por rol
  es un mecanismo central (`requiere_rol`), no un chequeo por servicio. **Enmienda v2.4.0 (User
  Story 11)**: sin cambio de esquema — la identidad del operador en cada petición sujeta a rol se
  deriva ahora de un token de sesión de turno, no del `id_operador` del cuerpo.
- **turno**: periodo de trabajo de un operador en una caja y sucursal. **Enmienda v2.3.0**: para
  `cajero`/`encargado` la sucursal se resuelve a `operador.id_sucursal` (sin selector); `admin`
  elige libremente. **Enmienda v2.4.0 (User Story 11)**: la apertura devuelve además un `token`
  de sesión (JWT firmado, no persistido); el `instante_cierre` que ya existe es lo que invalida
  ese token al cerrarse el turno.
- **traspaso**: operación que enlaza la salida en origen con la entrada en destino y es dueña de la
  mercancía en tránsito.
- **conteo_fisico**: conteo programado y sus renglones contados, con la diferencia resultante.
- **operacion_pendiente**: operación ejecutada sin conectividad, con su estado de sincronización, su
  marca de tiempo de origen y, si fue desplazada, la referencia a la que prevaleció.
- **anulacion_venta**: hecho de anular una venta, con operador e instante.

Entidades **incorporadas a este módulo por las enmiendas v2.1.1 y v2.1.2** de la constitución,
detectadas al escribir `data-model.md` — ver "Dependencias Constitucionales":

- **conteo_renglon**: línea contada de un `conteo_fisico`, con su cantidad esperada, su cantidad
  contada y la diferencia entre ambas.
- **producto_precio_sucursal**: override opcional del precio base de `producto` por sucursal
  (FR-050); si una sucursal no declara override, hereda el precio base.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un cajero registra una venta de cinco renglones que incluye al menos un producto a
  peso en menos de 45 segundos desde el inicio del cobro.
- **SC-002**: Registrar una consulta no atendida toma dos toques y menos de 5 segundos, sin sacar al
  cajero del flujo de cobro.
- **SC-003**: El 100 % de las ventas registradas tiene operador y terminal de pago atribuidos; no
  existe ninguna venta sin atribución.
- **SC-004**: El inventario total del sistema es reconstruible a partir de sus movimientos en
  cualquier instante elegido, incluido un instante con traspaso en tránsito, y la reconstrucción
  coincide exactamente con el saldo del sistema.
- **SC-005**: Ante 10 reintentos del mismo cobro con la misma clave, se registra exactamente una
  venta y un solo juego de movimientos de inventario.
- **SC-006**: Tras 30 minutos sin conectividad con al menos 50 operaciones registradas, la
  reconexión sincroniza el 100 % de ellas sin pérdida, y toda operación desplazada por conflicto
  sigue siendo consultable.
- **SC-007**: El 100 % de las observaciones de competencia mostradas en la comparación exhibe su
  antigüedad mediante los tres portadores exigidos, y ninguna la comunica solo por color.
- **SC-008**: Un conteo físico de 200 productos se captura y resuelve en menos de 30 minutos, y
  produce la diferencia por producto y por lote sin intervención manual de cálculo.
- **SC-009**: Todo lote que cruza el umbral de su categoría aparece en el listado de capital
  inmovilizado, con su valor, en la siguiente consulta que se haga tras cruzarlo.
- **SC-010**: Un evaluador que desconoce el sistema completa el ciclo entrada → venta → conteo →
  diferencia sin asistencia, usando solo lo que la interfaz le muestra.
- **SC-011**: Un cajero que agregó un renglón equivocado corrige la cantidad o lo quita del carrito
  en menos de 10 segundos y sin reiniciar la venta; el total mostrado refleja el cambio de
  inmediato, y la venta cobrada coincide exactamente con lo que quedó en pantalla.
- **SC-012**: Tras la migración de la User Story 10, el 100 % de los operadores existentes tiene
  un rol (`cajero` o `encargado`, según su antiguo `es_encargado`) y una `id_sucursal` no nula,
  y **cero** operadores quedaron como `admin` sin haberse creado explícitamente.
- **SC-013**: La cadena de texto `es_encargado` no aparece en ningún archivo de `backend/` ni de
  `frontend/src/` tras la User Story 10 —ni como columna, ni como campo de respuesta, ni como
  lectura de componente— y la única vía de verificación de rol en el backend es `requiere_rol`.
- **SC-014**: Un `cajero` no ve en ninguna pantalla —ni deshabilitada— una sola opción que
  requiera `encargado` o `admin`; un intento por API directa de cualquiera de esas acciones se
  rechaza con `{codigo, mensaje}`.
- **SC-015**: Tras la User Story 11, enviar un `id_operador` de mayor rol en el cuerpo de una
  acción sujeta a rol, autenticado con el token de un rol menor, se rechaza con `403` en el
  100 % de los intentos: el cuerpo no tiene ningún efecto sobre la identidad resuelta. La prueba
  de regresión que reproduce el hallazgo original de la auditoría pasa.
- **SC-016**: El 100 % de las peticiones a endpoints sujetos a rol sin token válido (ausente,
  firma inválida, expirado, turno cerrado, operador desactivado) se rechaza con `401` y un
  `{codigo, mensaje}` orientado a la acción correctiva, sin traza técnica.
- **SC-017**: `grep -rn "id_operador\b" backend/rasero/api/` no devuelve ningún campo de cuerpo
  de escritura declarado para autorización, y la única fuente de identidad de operador en un
  endpoint sujeto a rol es la dependency `operador_de_sesion`.

## Dependencias Constitucionales

Esta especificación descansa sobre la constitución del proyecto (**v2.4.0**, versión vigente) y
hereda de ella sin repetirlas: la precisión monetaria exacta, el tratamiento del tiempo por
sucursal, la regla de reconciliación offline, la obligación de trazabilidad y la prohibición de
decisiones automáticas de precio o reposición.

La enmienda **v2.3.0** (Principio VI, "Autorización y Roles") cambia el **esquema** de la
entidad `operador` de este módulo: gana `id_sucursal` (FK → `sucursal`, NOT NULL, uno-a-uno) y
su columna booleana `es_encargado` se retira y se reemplaza por `rol` (ENUM cerrado
`cajero` | `encargado` | `admin`). El conteo de entidades de 001 no cambia (sigue en 20). La
enmienda **v2.4.0** amplía el Principio VI con la sub-sección "Identidad de sesión" (token JWT
de turno emitido en `POST /turnos`; el `id_operador` del cuerpo queda deprecado para
autorización) — **sin** cambio de esquema: `operador` y `turno` no ganan ni pierden columnas y
la invalidación por cierre de turno reutiliza `turno.instante_cierre`. Esa capacidad se
especifica como **User Story 11** de este módulo. La
capacidad de negocio que ejerce ese cambio —autorización centralizada, restricción de sucursal
en apertura de turno, gestión de operadores admin-only— se especifica como **User Story 10** de
este módulo (ver más abajo), ya que `operador` es entidad de 001.

**No hay discrepancia pendiente con la tabla de propiedad de datos.** La redacción de esta
especificación y de los artefactos de diseño derivados de ella (`data-model.md`,
`contracts/openapi.yaml`) fue destapando, en sucesivas revisiones, una entidad mal asignada y seis
entidades no contempladas en la ratificación original; las enmiendas **v2.1.0**, **v2.1.1** y
**v2.1.2** las resolvieron, en ese orden. Toda entidad que este módulo define —las 20 de
`data-model.md`— figura hoy como propiedad de `001-core-ventas-inventario`, y la puerta de
propiedad de datos del flujo de calidad no bloquea su fusión.

Lo resuelto, para trazabilidad de la revisión:

1. **`conteo_fisico` se movió de `006-caja-mermas-fraude` a `001-core-ventas-inventario`** (v2.1.0).
   La frontera quedó declarada en la propia constitución: este módulo ejecuta el conteo y expone la
   diferencia bruta sin interpretarla; 006 clasifica la causa —merma, robo, error de registro— y no
   ejecuta conteos.
2. **`operador`, `turno`, `traspaso`, `operacion_pendiente` y `anulacion_venta` se incorporaron a
   001** (v2.1.0). Ninguna figuraba en la tabla ratificada en v2.0.0 y ninguna pertenece
   naturalmente a otro módulo.
3. **`terminal_pago` sigue siendo propiedad de `007-pagos-seguridad`** y este módulo solo guarda una
   referencia opaca a ella. Eso es consulta entre funcionalidades, no redefinición: nunca requirió
   enmienda y se deja anotado para que la revisión no lo confunda con una invasión de propiedad.
4. **`anomalia_caja` es propiedad de 006 pero se calcula leyendo `movimiento_inventario`, `venta` y
   `anulacion_venta`,** que son de este módulo. La constitución lo declara expresamente legítimo
   desde v2.1.0. Es además la vía por la que la Lectura Crítica n.º 1 exige detectar el fraude de
   "cobrar 5, registrar 3", así que este módulo DEBE mantener esas tres entidades consultables por
   006.
5. **`conteo_renglon` se incorporó a 001** (v2.1.1). Es la línea contada de un `conteo_fisico`
   —producto, lote, cantidad contada, cantidad esperada, diferencia—, hija estructural de una
   entidad ya asignada a 001, detectada al escribir `data-model.md`.
6. **`producto_precio_sucursal` se incorporó a 001** (v2.1.2). Es el override opcional del precio
   base de `producto` por sucursal: si una sucursal no declara override, hereda el precio base. La
   política de cómo fijar cualquiera de los dos precios sigue perteneciendo a
   `003-precios-margenes`; 001 solo provee la capacidad de que el precio pueda diferir por
   sucursal y lo resuelve al vender y al comparar contra la competencia.

## Assumptions

- **Anulación sí, devolución no** (decidido, ver Clarifications): anular una venta registrada por
  error está dentro del alcance porque la tasa de anulaciones por operador es una de las señales con
  las que `006-caja-mermas-fraude` detecta el fraude descrito en la Lectura Crítica n.º 1. La
  devolución de mercancía por parte del cliente, con reingreso a inventario y reembolso, queda
  fuera de alcance: ninguna de las siete funcionalidades definidas la requiere.
- **Consumo de lotes: caducidad primero, entrada como desempate** (decidido, ver Clarifications):
  las existencias se descuentan del lote de caducidad más próxima; entre lotes sin caducidad, o con
  la misma fecha, sale primero el de entrada más antigua. El criterio base acordado fue FIFO y se
  refinó para no provocar mermas evitables en frescos; el efecto sobre el listado de capital
  inmovilizado se mantiene, porque los lotes viejos sin salida siguen aflorando antes.
- **Umbral global de respaldo**: se asume un valor configurable único, sin proponer aquí una cifra
  concreta; las cifras por categoría las define el negocio al cargar el catálogo.
- **PIN de cuatro dígitos**: se asume que no hay bloqueo por intentos fallidos ni caducidad de PIN,
  coherente con que la autenticación completa está fuera de alcance.
- **Token de sesión de turno** (User Story 11, decidido): JWT simétrico (HS256, librería `pyjwt`),
  no asimétrico ni OAuth — es una aplicación de un solo servidor, no un sistema multi-tenant. Sin
  refresco: el `exp` de 12 h cubre cualquier turno real y, al expirar, se abre turno de nuevo. La
  invalidación por cierre de turno se resuelve contra `turno.instante_cierre` (blocklist mínima
  sobre estado ya existente), no con una tabla nueva. Un operador desactivado a mitad de turno
  pierde el acceso de inmediato (criterio conservador). Los endpoints que hoy no verifican
  identidad quedan fuera de alcance.
- **Precio de venta**: el precio aplicado a un renglón es el precio vigente de la sucursal si esa
  sucursal declaró un override, y si no, el precio base del producto. El sistema admite que el
  precio difiera por sucursal —los competidores de Quevedo Centro no son los de Buena Fe, y un
  precio único haría imposible responder a la presión competitiva local que describe el caso de
  negocio— pero eso es capacidad, no obligación: una sucursal sin override sencillamente hereda el
  precio base. El precio resultante queda copiado en el renglón, para que una venta pasada siga
  siendo reconstruible cuando el precio cambie. La política de cómo se fija cualquiera de los dos
  precios pertenece al módulo de precios y márgenes; este módulo solo resuelve cuál aplica y lo
  registra.
- **Datos personales**: este módulo no captura ningún dato de cliente. La identificación de clientes
  pertenece al módulo de clientes y fidelización.
- **Alcance de demostración**: dos sucursales, "Quevedo Centro" y "Buena Fe", del juego de datos
  ficticio "Despensa Los Ríos". Ese nombre vive solo como dato de prueba y no aparece en ningún
  identificador técnico.
- **Báscula**: se asume captura manual del peso leído por el operador; la integración electrónica
  con una báscula no fue pedida y no se asume disponible.
