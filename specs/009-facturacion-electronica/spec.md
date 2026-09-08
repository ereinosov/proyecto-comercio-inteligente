# Feature Specification: Facturación Electrónica (Simulada)

**Feature Branch**: `009-facturacion-electronica` — se desarrolla sobre `master`; no se crea rama dedicada.

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Factura electrónica SIMULADA con la forma de datos de una factura
ecuatoriana (RUC, razón social, secuencial 001-001-000000123, subtotal, IVA 15 %, total, datos
del cliente o 'Consumidor Final'), sin conexión real al SRI. Consumidor de 001, nunca dueño de
la venta. Se genera automáticamente al confirmar el cobro, sin bloquearlo, y se muestra en
pantalla. Rol: cualquier cajero."

## Resumen

Hoy una venta se cobra y se registra, pero el cliente no se lleva **un comprobante con forma de
factura**. Esta funcionalidad añade, **después** de cada cobro confirmado, un documento con la
**forma de datos de una factura electrónica ecuatoriana** —encabezado con el RUC y la razón
social del comercio, un **secuencial** `establecimiento-punto-correlativo`, el detalle de
renglones, el **subtotal**, el **IVA** y el **total**, y los datos del comprador (nombre e
identificador si la venta se identificó, o "Consumidor Final" si no)— y lo muestra en pantalla al
cerrar la venta.

Es **simulada**, y el sistema lo dice: **no hay conexión al SRI**, no hay firma electrónica, no
se genera ningún XML válido para el ente regulador, y el secuencial no está autorizado por
nadie. Es exactamente la misma clase de limitación de alcance honesta que 007 declaró para "sin
pasarela real": el flujo tiene la forma correcta, sin la infraestructura regulatoria detrás.

009 es **consumidor** de 001 (`venta`, `renglon_venta`) y de 002 (nombre e identificador del
`cliente`, si se identificó). No modifica ninguna tabla de esos módulos. La factura se genera en
el mismo punto del flujo donde 002 registra la visita y 005 la redención —después de que la
venta ya está confirmada— y **nunca bloquea el cobro** (Principio II): si la generación falla, la
venta queda intacta y la factura se puede regenerar.

Cualquier **`cajero`** puede generarla y verla: es parte del flujo de venta que ya opera, no
requiere rol elevado.

## Clarifications

### Session 2026-09-07

- Q: ¿La factura tiene validez tributaria real? → A: **No.** Es simulada. No hay conexión al SRI,
  ni firma electrónica, ni XML autorizado, ni clave de acceso válida. El sistema **muestra un
  aviso visible** de que es un comprobante de demostración, no un documento tributario. El
  secuencial es un correlativo interno, no un rango autorizado.
- Q: ¿Se genera en el cobro o a demanda? → A: **Automáticamente al confirmar el cobro**, en el
  mismo punto donde 002 registra `visita` y 005 registra `redencion_promocion`: después de que
  `POST /ventas` devolvió la venta confirmada, con una llamada que **no bloquea** ese resultado.
  Si falla, la venta ya está registrada; la factura se puede **regenerar** desde la vista de la
  venta.
- Q: Si el cliente no se identificó, ¿qué datos de comprador lleva la factura? → A: **"Consumidor
  Final"**, sin RUC/cédula, sin dirección. Es la práctica estándar en Ecuador para una venta al
  detalle sin identificar al comprador. Decisión de negocio, no un placeholder técnico.
- Q: ¿La factura se puede anular o corregir? → A: Si la **venta** se anula (flujo de 001 ya
  existente), su factura simulada queda marcada como **anulada** (nota de crédito simulada
  mínima: misma forma, tipo distinto, referencia a la factura anulada). No hay edición de una
  factura ya emitida — se anula y, si hace falta, se regenera de la venta corregida. Coherente
  con "una venta ya cobrada no se edita, se anula" de 001.
- Q: ¿Impresión física o PDF? → A: **Pantalla es suficiente** para esta versión. Se ofrece
  además "Ver como documento" que abre una vista imprimible con el formato de factura (el
  navegador imprime o guarda como PDF); NO se genera un PDF en el servidor ni se envía por
  correo. Si más adelante se quiere un PDF real, reutilizará el patrón de generación de
  documentos que el proyecto adopte (hoy no existe ninguno).
- Q: ¿El secuencial es global o por punto de emisión? → A: **Correlativo por
  `(establecimiento, punto de emisión)`**, que en esta simulación se derivan de la **sucursal**
  del turno (una sucursal = un establecimiento, un punto de emisión por defecto). El correlativo
  arranca en 1 por combinación y no se reutiliza ni salta huecos: es idempotente por `id_venta`
  (una venta = una factura).
- Q: ¿El IVA se aplica a todos los renglones por igual, y va por encima o incluido en el precio?
  → A: Una única tarifa (configurable, por defecto 15 %), e **incluida en el precio de venta al
  detalle** (práctica habitual del comercio minorista ecuatoriano). Así el `total` de la factura
  es exactamente `venta.total` de 001 y 009 **no cambia lo que el cliente paga**: el `subtotal`
  se calcula descomponiendo hacia atrás. Productos con tarifa 0 %/exentos: **fuera de alcance**
  (los `producto` de 001 no llevan atributo de tarifa de IVA; añadirlo sería cambio de esquema
  de 001).

## Dependencias entre módulos

009 **sólo lee** de 001 y 002. No modifica ninguna de sus tablas.

| Origen | Qué consume | Cómo |
|---|---|---|
| 001 | `venta` (total, instante, turno), `renglon_venta` (producto, cantidad, precio, importe), `turno`→`sucursal`, `anulacion_venta` | detalle y totales de la factura; la sucursal define establecimiento/punto; una venta anulada marca su factura como anulada |
| 001 | `producto` (nombre, código) | descripción de cada renglón |
| 002 | `cliente` (nombre, identificador) **si la venta se identificó** vía `visita` | datos del comprador; sin `visita` identificada → "Consumidor Final" |
| 007 | `referencia_terminal_pago` de la `venta` / medio de pago | etiqueta del medio de pago en la factura ("efectivo" / "tarjeta"), **nunca** datos de tarjeta |

**Frontera de propiedad de datos.** 009 introduce **una** entidad propia, `factura_simulada`,
que la constitución declara en su sección "Propiedad de Datos y Nomenclatura" (enmienda
**v2.7.0**, ya hecha antes de este plan). 009 **consulta** `venta` de 001 sin poseerla —mismo
patrón que `redencion_promocion` (005) y `visita` (002)—. Nada de 009 alimenta de vuelta a
001/002.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recibir la factura simulada al terminar una venta (Priority: P1)

El cajero cobra una venta. Al confirmarse el cobro, la pantalla de "venta registrada" muestra,
además del total y las acciones ya existentes ("Nueva venta", "Anular"), la **factura simulada**
de esa venta: encabezado con la razón social y el RUC del comercio, el secuencial
(`001-001-000000042`), la fecha, los datos del comprador ("Consumidor Final" si no se
identificó), la tabla de renglones (descripción, cantidad, precio unitario, importe), el
subtotal, el IVA y el total, y un **aviso visible** de que es un comprobante de demostración sin
validez tributaria.

**Why this priority**: es el valor central —el cliente se lleva un comprobante con forma de
factura— y el flujo mínimo demostrable. Todo lo demás (regenerar, anular, ver como documento) es
alrededor de esto.

**Independent Test**: cobrar una venta de dos renglones; verificar que la pantalla de venta
registrada muestra una factura con el secuencial correcto, los renglones y totales que coinciden
con la venta, el comprador correcto y el aviso de simulación; verificar que la venta se registró
igual que antes (009 no cambió el cobro).

**Acceptance Scenarios**:

1. **Given** una venta de 2 latas a 1,75 y 700 g de queso por 5,13 (total cobrado 8,63), **When**
   el cajero confirma el cobro, **Then** la pantalla muestra una factura con esos dos renglones,
   y —con el IVA **incluido** en el precio de venta al detalle (decisión de research §6)— un
   **subtotal** de 7,50 (8,63 ÷ 1,15), un **IVA** de 1,13 y un **total** de 8,63 que coincide
   exactamente con lo que el cliente pagó. El cobro de 001 no cambia.
2. **Given** una venta sin cliente identificado, **When** se genera la factura, **Then** el
   bloque del comprador dice "Consumidor Final", sin RUC ni dirección.
3. **Given** una venta de un cliente identificado con cédula, **When** se genera la factura,
   **Then** el bloque del comprador lleva su nombre y su cédula/RUC.
4. **Given** cualquier factura simulada, **When** se renderiza, **Then** incluye un aviso visible
   de que es un comprobante de demostración sin validez tributaria; el sistema en ningún momento
   afirma lo contrario.
5. **Given** el punto del flujo donde falla la generación de la factura (servicio caído), **When**
   el cajero confirma el cobro, **Then** la venta se registra igual, la pantalla lo muestra, y
   ofrece "Generar factura" para reintentar — el cobro nunca se bloqueó ni se revirtió.
6. **Given** dos cobros seguidos en la misma sucursal, **When** se generan sus facturas, **Then**
   sus secuenciales son correlativos (`…041`, `…042`), sin huecos ni repeticiones.

---

### User Story 2 - Volver a ver o regenerar la factura de una venta (Priority: P2)

Desde el detalle de una venta ya cobrada (la pantalla de "venta registrada" mientras siga
abierta, o una consulta posterior de la venta), el cajero puede volver a ver su factura simulada.
Si la venta no tiene factura (porque la generación falló en su momento), puede generarla ahora;
la factura resultante es **idéntica** a la que se habría generado en el cobro (mismos datos,
mismo secuencial asignado a esa venta), porque es idempotente por `id_venta`.

**Why this priority**: cierra el hueco de "el cobro salió pero la factura no". Segundo porque
sólo aporta si US1 ya existe.

**Independent Test**: cobrar una venta con el servicio de factura desactivado (no se genera);
reactivarlo; pedir la factura de esa venta; verificar que se genera con el secuencial que le
tocaba y datos correctos; pedirla otra vez y verificar que no se crea una segunda.

**Acceptance Scenarios**:

1. **Given** una venta cobrada sin factura, **When** el cajero pulsa "Generar factura", **Then**
   se crea la factura de esa venta y se muestra.
2. **Given** una venta que ya tiene factura, **When** se pide generarla de nuevo, **Then** se
   devuelve la misma factura, no se crea una segunda (idempotente por `id_venta`).
3. **Given** una factura ya emitida, **When** el cajero la abre de nuevo, **Then** ve exactamente
   el mismo documento (secuencial, fecha, renglones, totales, comprador) — una factura emitida no
   cambia.

---

### User Story 3 - Anular la factura cuando se anula la venta (Priority: P3)

Cuando una venta se anula por el flujo ya existente de 001, su factura simulada queda marcada
como **anulada** y el sistema genera una **nota de crédito simulada** mínima: la misma forma de
documento, tipo "nota de crédito", que referencia la factura anulada y revierte sus totales. La
pantalla de la venta anulada muestra ambos documentos. No hay edición de una factura ya emitida.

**Why this priority**: coherencia con "una venta cobrada no se edita, se anula" de 001. Tercero
porque la anulación es un caso menos frecuente y US1/US2 ya entregan el flujo principal.

**Independent Test**: cobrar una venta (se genera su factura), anularla; verificar que la factura
queda marcada anulada y que aparece una nota de crédito simulada que la referencia y revierte los
totales; verificar que la venta y la anulación de 001 no cambiaron.

**Acceptance Scenarios**:

1. **Given** una venta con factura simulada, **When** la venta se anula (flujo de 001), **Then**
   su factura queda marcada como anulada y se crea una nota de crédito simulada que la
   referencia.
2. **Given** una nota de crédito simulada, **When** se renderiza, **Then** tiene la misma forma
   que la factura, tipo "nota de crédito", con los totales en negativo o marcados como reverso, y
   el mismo aviso de simulación.
3. **Given** una venta sin factura (falló la generación) que se anula, **When** se procesa la
   anulación, **Then** no se genera ninguna nota de crédito (no hay factura que revertir); la
   anulación de 001 procede igual.

---

### Edge Cases

- **Venta con total 0** (toda la mercancía a cantidad 0 tras editar el carrito — caso de 001): no
  se genera factura; una factura de total 0 no tiene sentido. Se documenta.
- **Cliente identificado sin identificador** (sólo nombre): la factura lleva el nombre y omite el
  bloque de cédula/RUC (Regla del Hueco que Enseña: no "N/A").
- **Regeneración tras cambiar el RUC/razón social de configuración**: una factura **ya emitida**
  conserva los datos con los que se emitió (snapshot); sólo una factura nueva usa la
  configuración actual.
- **Dos sucursales**: cada una es su propio establecimiento/punto de emisión con su propio
  correlativo; los secuenciales de una no afectan a los de la otra.
- **Reintento de cobro idempotente de 001** (misma `clave_idempotencia`): la segunda llamada
  devuelve la misma venta y NO genera una segunda factura.
- **Venta anulada y luego "nueva venta" con el mismo carrito**: es una venta nueva, con su propia
  factura y su propio secuencial; no reutiliza el de la anulada.
- **Descomposición del IVA con más de 2 decimales**: `subtotal = round(venta.total / 1,15; 2)` y
  `iva = venta.total - subtotal`, de modo que `subtotal + iva == venta.total` exactamente, sin
  céntimo perdido por redondeo. Mismo criterio de redondeo que 001 (medio hacia arriba).

## Requirements *(mandatory)*

### Functional Requirements

**Naturaleza y alcance**

- **FR-001**: La factura es **simulada**: el sistema NO se conecta al SRI, NO firma
  electrónicamente, NO genera XML válido para el ente regulador y NO obtiene autorización de
  ningún secuencial. Toda superficie que muestre una factura DEBE incluir un **aviso visible** de
  que es un comprobante de demostración sin validez tributaria.
- **FR-002**: 009 es de **solo lectura** respecto a 001 y 002: NO crea, modifica ni borra ninguna
  `venta`, `renglon_venta`, `cliente`, `visita` ni ninguna otra entidad de esos módulos. Su única
  escritura es sobre su propia entidad `factura_simulada`.
- **FR-003**: Generar y ver una factura simulada DEBE estar disponible para el rol **`cajero`** y
  superiores; NO requiere rol elevado.
- **FR-004**: El **RUC**, la **razón social** y la **tarifa de IVA** DEBEN venir de la
  configuración del despliegue (variables de entorno, con un valor de demostración por defecto),
  NUNCA como literal en código, identificador ni tabla — mismo patrón que `VITE_LOGO_COMERCIO`.

**Generación (User Story 1)**

- **FR-005**: Al confirmarse un cobro (después de que `POST /ventas` devolvió la venta
  confirmada), el sistema DEBE generar automáticamente la factura simulada de esa venta con una
  operación que **NO bloquea** ni revierte el cobro (Principio II): si falla, la venta queda
  registrada y la factura se puede generar después.
- **FR-006**: Una factura simulada DEBE contener: datos del emisor (razón social, RUC, dirección
  de la sucursal si la hay), **secuencial** `EEE-PPP-NNNNNNNNN`, fecha de emisión, datos del
  comprador (nombre e identificador, o "Consumidor Final"), la tabla de renglones (descripción,
  cantidad, precio unitario, importe), **subtotal**, **IVA** (tarifa y monto), **total**, y el
  aviso de simulación.
- **FR-007**: El **secuencial** DEBE ser un correlativo por `(establecimiento, punto de emisión)`
  —derivados de la sucursal del turno—, que arranca en 1, no reutiliza números ni deja huecos, y
  es **idempotente por `id_venta`**: una venta tiene como mucho una factura, con un secuencial
  fijo.
- **FR-008**: El **IVA** (tarifa única configurable, por defecto 15 %) va **incluido en el precio
  de venta**: `total` de la factura == `venta.total` de 001 (lo que el cliente pagó); el
  `subtotal` se obtiene descomponiendo hacia atrás (`venta.total / (1 + tarifa)`) y el monto de
  IVA es la diferencia, todo redondeado a 2 decimales con el criterio de 001. Así 009 **no
  cambia lo que el cliente paga** ni el cobro de 001. El modelado de tarifas 0 % / exentas queda
  fuera de alcance.
- **FR-009**: Los datos del comprador salen de la `visita` identificada de la venta (002): si hay
  cliente con identificador, se muestran nombre + cédula/RUC; si hay cliente sin identificador,
  sólo el nombre; si no hay cliente identificado, **"Consumidor Final"** sin ningún dato.
- **FR-010**: Una venta con **total 0** NO genera factura.

**Ver y regenerar (User Story 2)**

- **FR-011**: El cajero DEBE poder volver a ver la factura de una venta y, si no tiene, generarla;
  la factura generada después es **idéntica** a la que se habría generado en el cobro (mismos
  datos, mismo secuencial reservado para esa venta).
- **FR-012**: Pedir generar la factura de una venta que **ya tiene** una DEBE devolver la
  existente, nunca crear una segunda (idempotente por `id_venta`).
- **FR-013**: Una factura **ya emitida** NO se edita: sus datos (secuencial, fecha, renglones,
  totales, comprador, razón social/RUC del momento de emisión) son un **snapshot** inmutable.
- **FR-014**: El sistema DEBE ofrecer "Ver como documento": una vista imprimible con formato de
  factura que el navegador puede imprimir o guardar como PDF. NO se genera un PDF en el servidor
  ni se envía por ningún canal.

**Anulación (User Story 3)**

- **FR-015**: Cuando una `venta` se anula por el flujo de 001, su `factura_simulada` (si existe)
  DEBE marcarse como **anulada**, y el sistema DEBE generar una **nota de crédito simulada**: la
  misma forma de documento, tipo "nota de crédito", que referencia la factura anulada y revierte
  sus totales, con el mismo aviso de simulación.
- **FR-016**: Si la venta anulada no tenía factura, NO se genera nota de crédito; la anulación de
  001 procede igual.
- **FR-017**: La nota de crédito simulada también es **idempotente**: anular dos veces (caso ya
  imposible en 001) no crearía dos notas.

**Presentación**

- **FR-018**: La factura y la nota de crédito se muestran en la **pantalla de "venta
  registrada"** de Venta, ampliando esa vista ya existente; y en el detalle de una venta
  consultada después. Registro de **Operación** (es parte del flujo de caja).
- **FR-019**: El aviso de simulación (FR-001) DEBE estar en la misma superficie que el documento,
  legible, no ocultable — no una nota al pie en gris que se pierde.
- **FR-020**: Ningún dato de pago (PAN, CVV, banda/chip) aparece en una factura: a lo sumo el
  **medio** como etiqueta ("efectivo", "tarjeta"), coherente con Principio IV y las Restricciones
  Técnicas de datos de pago.
- **FR-021**: Ningún literal de la razón social real ("Despensa Los Ríos"), RUC real ni de las
  sucursales aparece en código, identificador ni tabla (FR-046 de 001, FR-004 de aquí).

### Key Entities *(include if feature involves data)*

- **Factura simulada** (`factura_simulada`): el documento con forma de factura ecuatoriana
  generado a partir de una venta confirmada. Atributos: referencia a la `venta` (única —
  idempotencia), tipo (`factura` | `nota_credito`), establecimiento y punto de emisión (de la
  sucursal), número correlativo, secuencial formateado, fecha de emisión, snapshot de emisor
  (razón social, RUC, dirección), snapshot de comprador (nombre, identificador, o "Consumidor
  Final"), snapshot de renglones (descripción, cantidad, precio, importe), subtotal, tarifa y
  monto de IVA, total, estado (`emitida` | `anulada`), referencia a la factura que revierte (para
  las notas de crédito), instante de generación. Todo snapshot: una factura emitida no cambia
  aunque cambien la venta, el cliente o la configuración.

Es propiedad de 009. `venta`, `renglon_venta`, `cliente` son propiedad de 001/002 y 009 sólo los
**consulta** en el momento de emitir; después la factura es autónoma.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El **100 %** de los cobros con total > 0 termina con una factura simulada visible en
  la pantalla de venta registrada (o, si su generación falló, con la opción de generarla y sin
  que el cobro se haya visto afectado).
- **SC-002**: El `total` de cada factura coincide, al centavo, con `venta.total` de 001 (el IVA va
  incluido en el precio); y `subtotal + IVA == total` con la tarifa configurada.
- **SC-003**: Los secuenciales de una sucursal son estrictamente correlativos: en una serie de N
  cobros consecutivos en una sucursal, los N secuenciales son `k, k+1, …, k+N-1` sin huecos ni
  repeticiones.
- **SC-004**: Generar la factura de una venta que ya la tiene **nunca** crea una segunda fila de
  `factura_simulada` para esa venta (idempotencia verificable).
- **SC-005**: Una auditoría del código de 009 encuentra **cero** sentencias de modificación sobre
  tablas de 001/002.
- **SC-006**: El **100 %** de las superficies que muestran una factura incluye el aviso de
  simulación; un evaluador que ve la pantalla entiende sin ayuda que no es un documento
  tributario real.
- **SC-007**: Un cobro cuya generación de factura falla se completa igual: la venta queda
  registrada y la pantalla lo confirma en el mismo tiempo que un cobro sin 009.
- **SC-008**: Al anular una venta con factura, su factura queda anulada y aparece una nota de
  crédito que la referencia — en el **100 %** de los casos con factura previa.

## Assumptions

- **Una sucursal = un establecimiento = un punto de emisión.** El secuencial se forma con
  `establecimiento` y `punto` derivados de la sucursal (por defecto `001` / `001` configurables);
  no se modela una tabla de puntos de emisión múltiples por tienda.
- **Tarifa de IVA única.** Una sola tarifa (por defecto 15 %, la vigente en Ecuador) sobre todo
  el subtotal. Productos con tarifa 0 % / exentos: fuera de alcance; los `producto` de 001 no
  tienen hoy un atributo de tarifa de IVA y añadirlo es cambio de esquema de 001, no de 009.
- **Datos del emisor por configuración.** `RUC_COMERCIO`, `RAZON_SOCIAL_COMERCIO`,
  `DIRECCION_COMERCIO` (opcional), `TARIFA_IVA`, `ESTABLECIMIENTO_SRI`, `PUNTO_EMISION_SRI` — con
  valores de demostración por defecto, nunca literales.
- **Sin envío ni almacenamiento externo.** No hay correo, no hay subida a un portal, no hay PDF
  en servidor. "Ver como documento" es una vista imprimible del navegador.
- **La generación en el cobro reutiliza el patrón de 002/005.** Igual que `registrarVisita` y
  `registrarRedencion` se llaman después de `registrarVenta` sin bloquearla, la generación de la
  factura es una llamada posterior que, si falla, sólo registra un aviso y deja un botón para
  reintentar.
- **Nota de crédito mínima.** Sólo la forma de documento y la reversión de totales; no se modela
  el ciclo completo de una nota de crédito tributaria (motivos codificados, sustento, etc.).
- **Zona horaria de la fecha de emisión.** La de la sucursal del turno (mismo criterio que 006
  para el día local).

## Dependencias Constitucionales

- **Enmienda v2.7.0 ya hecha ANTES de este plan** (patrón v2.2.3–v2.2.6): declara
  `factura_simulada` como propiedad de 009 en "Propiedad de Datos y Nomenclatura" y añade la
  frontera "009 consume `venta`/`renglon_venta` de 001 y datos de `cliente` de 002, sin poseer
  ninguno; la factura se genera tras el cobro y nunca lo bloquea; ningún dato de pago en la
  factura". Este plan no necesita otra enmienda.
- **Principio II** (fiabilidad en el punto de venta): 009 respeta explícitamente que la
  generación de la factura NO es camino crítico del cobro.
- **Principio IV** (trazabilidad) y **Restricciones Técnicas / Datos de pago**: una factura no
  contiene PAN/CVV/banda; a lo sumo el medio como etiqueta.
- **Constitución v2.5.0, "Autorización de pantalla"**: la factura es parte del flujo de caja →
  rol `cajero`. No entra en la tabla de pantallas de `encargado`.
- **`DESIGN.md`**: puede ganar, en el plan de 009, una regla nueva para la **presentación de un
  documento formal** (una factura no encaja en "Tabla de Operación" ni en los componentes
  actuales): un bloque de documento con su propio tratamiento tipográfico y el aviso de
  simulación destacado. Se decide en el plan, no en esta spec.
