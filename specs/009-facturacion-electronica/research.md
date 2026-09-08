# Research — 009-facturacion-electronica

## 1. Simulación honesta, no integración fallida

**Decisión**: 009 produce un documento con la **forma** de una factura electrónica ecuatoriana
—estructura de datos, secuencial, IVA, "Consumidor Final"— y **declara en cada superficie** que
es un comprobante de demostración sin validez tributaria. No hay cliente HTTP al SRI, no hay
firmado con certificado, no hay generación de XML según el esquema del ente regulador, no hay
"clave de acceso" de 49 dígitos válida.

**Razón**: mismo criterio que 007 aplicó a "sin pasarela de pago real" y que la propia
constitución exige ("Ámbito acotado", "una limitación de alcance honesta"). Publicar como real un
documento que no lo es sería engañoso; declarar la simulación en el mismo lugar donde se muestra
el documento (FR-001, FR-019) mantiene la honestidad. El valor de demostración —"así se vería la
factura del cliente"— se obtiene igual.

**Alternativas descartadas**: (a) integración real con el SRI (ambiente de pruebas) — requiere
certificado digital, RUC real habilitado, y una dependencia externa que el Principio II quiere
mantener fuera del camino del cobro; fuera de alcance de un proyecto de demostración. (b) generar
un XML "casi válido" — invita a confundirlo con uno real; peor que un documento claramente
simulado.

## 2. Generación después del cobro, sin bloquearlo (Principio II)

**Decisión**: el frontend, en `Venta.tsx` función `cobrar`, después de que `registrarVenta`
devuelve la venta confirmada, llama a `generarFactura(venta.id_venta)` **con `.catch`** que sólo
registra un aviso —exactamente el patrón que ya usan `registrarVisita` y `registrarRedencion`
ahí mismo—. La pantalla de "venta registrada" muestra `<FacturaSimulada>` si la llamada
respondió, o un botón "Generar factura" si falló. El backend `POST /facturas` es una operación
independiente de `POST /ventas`.

**Razón**: FR-005, Principio II. La factura es un subproducto del cobro, no parte de él. Si el
servicio de 009 está caído, la caja sigue cobrando y registrando; sólo se pospone la factura.

**Alternativas descartadas**: (a) generar la factura dentro de `servicios/ventas.py` de 001 en la
misma transacción del cobro — acopla 001 a 009, hace que un fallo de 009 revierta un cobro
(prohibido), y viola la propiedad de datos (001 no debe conocer `factura_simulada`). (b) un job
en segundo plano que genere facturas pendientes — introduce trabajo programado que el proyecto no
tiene y demora la factura que el cliente espera ahora.

## 3. Secuencial: correlativo por (establecimiento, punto), sin huecos, idempotente por venta

**Decisión**: `factura_simulada` tiene `establecimiento` y `punto` (de la sucursal del turno, por
defecto `001`/`001` configurables) y `numero` (INTEGER). `UNIQUE (establecimiento, punto, numero,
tipo)` y `UNIQUE (id_venta)`. Al generar: dentro de la transacción, `SELECT COALESCE(MAX(numero),
0) + 1 FROM factura_simulada WHERE establecimiento=? AND punto=? AND tipo=? FOR UPDATE` (o una
secuencia de PostgreSQL por combinación). El `UNIQUE (id_venta)` hace que un segundo intento para
la misma venta devuelva la fila existente (idempotencia, FR-007, FR-012, SC-004). El secuencial
formateado `EEE-PPP-NNNNNNNNN` es una función pura de dominio.

**Razón**: SC-003 exige correlativo sin huecos; el `MAX+1` con bloqueo lo garantiza bajo
concurrencia (dos cajas de la misma sucursal). La idempotencia por `id_venta` refleja "una venta,
una factura".

**Alternativas descartadas**: (a) `BIGSERIAL` global — mezcla los correlativos de las dos
sucursales, contra la forma de una factura por establecimiento. (b) generar el número en el
frontend — no hay forma de garantizar unicidad ni orden desde el cliente.

## 4. Todo snapshot; una factura emitida no cambia

**Decisión**: `factura_simulada` guarda en columnas propias (o un `JSONB` de "cuerpo") el emisor
(razón social, RUC, dirección del momento), el comprador (nombre, identificador, o "Consumidor
Final"), los renglones (descripción, cantidad, precio, importe), el subtotal, la tarifa y el
monto de IVA, y el total. **Nada se recalcula al leer**: `GET /facturas/venta/{id}` devuelve lo
guardado.

**Razón**: FR-013, Edge Cases. Un documento fiscal (aunque simulado) es inmutable una vez
emitido; si la venta se anula o el RUC de configuración cambia, la factura ya emitida sigue
mostrando lo que mostraba. La corrección es anular + regenerar de la venta corregida (US3), no
editar.

## 5. Enganche de la anulación sin tocar 001

**Decisión**: `servicios/ventas.py::anular_venta` de 001 **no cambia**. 009 se entera de la
anulación por el **frontend**: `Venta.tsx`, tras llamar a `anularVenta` (001), llama a
`emitirNotaCredito(venta.id_venta)` (009) — mismo patrón "llamada posterior que no bloquea". El
backend `POST /facturas/nota-credito/{id_venta}` de 009: si la venta está anulada en 001 y tiene
factura `emitida`, la marca `anulada` y crea una `nota_credito` que la referencia; si no hay
factura, no hace nada (FR-016); idempotente (FR-017).

**Razón**: Propiedad de Datos — 001 no debe conocer 009. El frontend ya orquesta varias llamadas
post-venta (visita, redención); una más encaja. Un `xfail`/pendiente si se quisiera que el
backend de 001 emitiera un evento — fuera de alcance, el proyecto no tiene bus de eventos.

**Alternativa descartada**: un trigger de base de datos sobre `anulacion_venta` que inserte en
`factura_simulada` — lógica de negocio escondida en el esquema, difícil de probar y contra el
estilo del proyecto (todo en servicios).

## 6. IVA: una tarifa, aritmética Decimal

**Decisión**: `subtotal = Σ importe de renglón` (los importes de renglón ya vienen redondeados a
2 decimales de 001); `iva = round(subtotal * TARIFA_IVA, 2, ROUND_HALF_UP)`; `total = subtotal +
iva`. `TARIFA_IVA` de configuración, por defecto `0.15`. `dominio/factura.py` es función pura.

**Razón**: FR-008. Reutiliza el criterio de redondeo de 001 (`totales.py`), sin librería.
Productos con tarifa 0 %/exentos: fuera de alcance (Assumption) — requeriría un atributo de
tarifa en `producto` de 001, cambio de esquema de otro módulo.

**Nota sobre el total pagado**: en 001, la venta se cobra por `venta.total` (suma de importes de
renglón, **sin IVA** hoy). La factura de 009 muestra `subtotal + IVA`, que difiere de
`venta.total` por el monto de IVA. Esto se documenta como característica de la simulación: la
factura ilustra la descomposición fiscal; si se quisiera que el cliente pague el total con IVA,
sería un cambio en el cobro de 001, fuera de alcance de 009. **Alternativa**: interpretar
`venta.total` como precio final con IVA incluido y descomponer hacia atrás
(`subtotal = total / (1 + tarifa)`). **Decisión**: se adopta esta segunda (IVA incluido en el
precio de venta), que es lo habitual en el comercio al detalle ecuatoriano y hace que
`factura.total == venta.total`. Se fija en `dominio/factura.py` y se prueba (test unidad).

## 7. Presentación: un documento formal que DESIGN.md no tiene

**Decisión**: `<FacturaSimulada>` es un bloque de documento con su propio tratamiento —encabezado
del emisor, tabla de renglones densa, totales alineados a la derecha, y un **aviso de
simulación** destacado (no una nota al pie gris)—. Registro de Operación. `<DocumentoImprimible>`
envuelve ese bloque para `window.print()` ("Ver como documento", FR-014). Se añade a DESIGN.md
una regla "Presentación de documento formal" como enmienda MENOR de DESIGN.md al construir US1.

**Razón**: una factura no es una "Tabla de Operación" ni encaja en los componentes actuales; y el
aviso de simulación es un requisito funcional (FR-019) que necesita un tratamiento visual
definido para no perderse.

## 8. Sin migración de datos

**Decisión**: `0013` crea la tabla vacía. Las ventas ya cobradas antes de 009 no tienen factura;
se puede generar bajo demanda (`POST /facturas {id_venta}`) para cualquiera de ellas. `downgrade`
elimina la tabla — no se pierde ningún dato de negocio (la factura es derivada de la venta).

## 9. `medio_pago`: etiqueta derivada de la venta, nunca un dato de instrumento (análisis BAJO #1)

**Decisión**: `medio_pago` se deriva de `venta.referencia_terminal_pago` con una heurística
binaria: **referencia nula → `"efectivo"`; referencia no nula → `"tarjeta"`**. Es una **etiqueta
de categoría**, nunca un dato del instrumento (ni PAN, ni "últimos 4", ni token — FR-020,
Principio IV). Se calcula en `facturacion._medio_pago(venta)` en el momento de generar la
factura y se congela como snapshot en la fila.

**Razón**: 001 no tiene hoy un campo explícito de "método de pago" en `venta`; lo único que
distingue una venta con datáfono de una en efectivo es la presencia de
`referencia_terminal_pago` (que 007 usa para su bitácora). La factura ecuatoriana lista un medio
de pago, así que 009 necesita *algún* valor; esta heurística es la inferencia más conservadora
con lo que 001 ya guarda, y su error máximo (una venta con datáfono sin referencia capturada
saldría como "efectivo") no afecta ningún total ni ningún flujo — es un rótulo informativo en un
documento declarado de demostración. No se añade ningún campo a `venta` (sería un cambio de
esquema de otro módulo, fuera de alcance y contra Propiedad de Datos).

**Alternativa descartada**: dejar `medio_pago` en `null` cuando no hay certeza. Se descartó
porque la factura siempre muestra la fila y un "—" permanente comunica menos que la mejor
inferencia disponible; el `null` queda reservado para notas de crédito heredando el valor de su
factura de origen.
