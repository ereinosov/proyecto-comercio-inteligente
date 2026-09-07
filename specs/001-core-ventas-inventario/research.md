# Research: Core de Ventas e Inventario

**Fase 0** · 2026-09-04 · Plan: [plan.md](./plan.md)

Las ocho decisiones que el plan debía resolver explícitamente, más las que se derivaron de ellas.
No queda ningún `NEEDS CLARIFICATION` abierto.

---

## 1. Tipos numéricos: dinero y peso

**Decisión**: importes en `NUMERIC(12,2)`; precios por unidad de medida en `NUMERIC(12,4)` para
admitir precio por kilo con cuatro decimales sin arrastrar error; pesos siempre en `INTEGER` de
gramos. Ningún tipo de coma flotante aparece en el esquema ni en el código de cálculo; en Python los
importes se manejan con `Decimal`, nunca con `float`.

El importe de un renglón a granel se calcula como
`ROUND(cantidad_gramos * precio_por_kg / 1000, 2)`, con redondeo de mitad hacia arriba, que es el
comportamiento de `NUMERIC` en PostgreSQL y el de `Decimal` con `ROUND_HALF_UP` en Python. El total
de la venta es la suma de los importes ya redondeados de cada renglón, no el redondeo de la suma:
así el ticket cuadra con lo que el cliente ve línea por línea.

**Razón**: es la exigencia literal de la constitución, y es el motivo declarado por el que SQLite
está prohibido. La precisión de 2 decimales cubre USD; la de 4 en el precio evita que un precio por
kilo de tres decimales se pierda antes de multiplicar.

**Alternativas descartadas**: enteros en centavos para todo —funciona, pero obliga a convertir en
cada frontera y hace ilegibles las consultas de auditoría—; `NUMERIC` sin escala fija —permite que
dos filas guarden distinta precisión para el mismo concepto—.

---

## 2. Idempotencia de venta

**Decisión**: `venta.clave_idempotencia TEXT NOT NULL UNIQUE`, generada por el cliente (punto de
venta) antes del primer intento y reutilizada en cada reintento del mismo cobro. El registro de la
venta, sus renglones y sus movimientos de inventario ocurren en **una sola transacción**. Ante un
reintento, el `INSERT` viola la restricción única, la transacción se descarta completa y el servicio
devuelve la venta original con `200`, no un error.

**Razón**: la atomicidad de la transacción es lo que hace que la unicidad de la venta implique
unicidad de los movimientos. Sin ella podría existir una venta única con movimientos duplicados,
que es justo lo que el Principio II prohíbe.

**Alternativas descartadas**: deduplicación por comparación de contenido (misma sucursal, mismos
renglones, ventana de tiempo) —rechaza ventas legítimamente idénticas, que en un minimarket son
frecuentes—; tabla aparte de claves consumidas —añade una escritura y una fuente de verdad
adicional sin ganar nada sobre la restricción única—.

---

## 3. Saldo de existencia: derivado pero consultable

**Decisión**: `movimiento_inventario` es la única fuente de verdad. La tabla `existencia`
(`id_sucursal`, `id_producto`, `id_lote`, `cantidad`) es una **agregación derivada** que se
actualiza en la misma transacción que inserta el movimiento, mediante `INSERT ... ON CONFLICT DO
UPDATE SET cantidad = existencia.cantidad + EXCLUDED.cantidad`. Nunca se escribe una cantidad
absoluta: solo se le suma el delta del movimiento, de modo que no existe forma de sobrescribir un
saldo sin un movimiento que lo origine.

`existencia` **no es autoritativa**. Ante cualquier discrepancia gana la recomputación desde
`movimiento_inventario`, y la prueba obligatoria n.º 4 verifica la igualdad.

**Razón**: la constitución exige reconstruibilidad; el plan exige consulta barata. La suma de deltas
en la misma transacción da las dos cosas sin disparadores ocultos.

**Alternativas descartadas**: vista con `SUM` sobre movimientos —más simple y **suficiente al
volumen declarado**; se descarta por el requisito explícito de no recorrer el histórico, y esa
concesión queda registrada en la tabla de complejidad del plan—; disparadores de base de datos
—esconden el flujo de control fuera del código de aplicación y complican la depuración—; vista
materializada con refresco periódico —introduce una ventana en la que el saldo mostrado en caja
está desactualizado—.

---

## 4. Selección de lote: caducidad primero, entrada como desempate

**Decisión**: al descontar existencias se ordenan los lotes disponibles de la sucursal con
`ORDER BY fecha_caducidad ASC NULLS LAST, fecha_entrada ASC, id_lote ASC` y se consumen en ese orden
hasta cubrir la cantidad, generando **un movimiento por lote tocado**. La selección se hace con
`SELECT ... FOR UPDATE` sobre las filas de lote implicadas, para que dos cajas simultáneas no
consuman dos veces el mismo remanente.

`NULLS LAST` es lo que implementa la regla acordada: un producto sin caducidad nunca se adelanta a
uno que sí caduca, y entre productos sin caducidad decide la entrada más antigua.

**Razón**: es la aclaración registrada en la sesión de clarificación. El criterio efectivo es FEFO
con FIFO como desempate, no FIFO puro.

**Alternativas descartadas**: FIFO estricto por fecha de entrada —provoca merma que el propio
sistema habría causado al mandar vender el lote equivocado—; selección manual del lote por el
cajero —añade un paso a la caja, que es el flujo que no puede entorpecerse—.

---

## 5. Saldo negativo

**Corrección 2026-09-07 — bloqueo duro.** Lo que sigue describía el diseño original ("no bloquear,
imputar el exceso al último lote FEFO, dejar el saldo negativo"). Ese diseño se **revierte**: una
venta o un traspaso que excede la existencia disponible se **rechaza** con
`existencia_insuficiente` (409), validando la operación completa antes de escribir ningún
movimiento (`registrar_venta` / `despachar_traspaso` en `backend/rasero/servicios/`). La cita del
Principio II era incorrecta: ese principio cubre la caída de servicios EXTERNOS como camino
crítico de un cobro, no una consulta determinista contra la propia base. `existencia.cantidad`
**conserva** la ausencia de restricción de no negatividad a nivel de esquema, porque un saldo
negativo **histórico** (anterior a esta corrección) sigue siendo un dato válido, reconstruible y
visible — sólo se prohíbe **crear** uno nuevo. El texto original queda abajo como registro.

---

**Decisión original (revertida)**: ni `existencia.cantidad` ni el saldo por lote llevan restricción
de no negatividad. El esquema admite valores negativos y las consultas los muestran como tales.

Cuando una venta excede el saldo, el remanente que ningún lote cubre **se imputa al último lote
seleccionado por el criterio de caducidad**, que queda en negativo. Si el producto no tiene ningún
lote en esa sucursal, el movimiento se registra con `id_lote` nulo.

**Razón**: la primera regla es la decisión registrada del usuario. La segunda es una **decisión de
plan** que esa aclaración no cubría: había que decidir a qué lote se imputa el exceso. Imputarlo al
lote seleccionado preserva dos invariantes valiosas —todo movimiento de salida referencia un lote, y
la existencia sigue siendo exactamente la suma de los movimientos tanto por producto como por lote—
y el negativo en ese lote es en sí mismo la señal de que allí hay algo que contar.

**Alternativas descartadas**: limitar el saldo a cero y anotar el exceso aparte —rompe la igualdad
entre saldo y suma de movimientos, que es el fundamento del Principio IV—; registrar todo el exceso
sin lote —deja movimientos huérfanos y complica el costeo—; bloquear la venta —prohibido por el
Principio II—. *(Nota 2026-09-07: esta última alternativa es la que finalmente se adoptó; la
prohibición citada estaba mal fundada.)*

---

## 6. Traspaso entre sucursales

**Decisión**: entidad `traspaso` (origen, destino, estado, instantes) con `traspaso_renglon` por
producto y cantidad. En el despacho se inserta **un movimiento de salida** en la sucursal de origen
con `id_traspaso`; en la confirmación se inserta **un movimiento de entrada** en la de destino con el
mismo `id_traspaso`. Los dos asientos quedan enlazados por esa clave.

Mientras `traspaso.estado = 'en_transito'`, la mercancía pertenece al traspaso. La invariante del
sistema es:

```text
inventario_total = Σ existencia.cantidad + Σ cantidad de traspaso_renglon en tránsito
```

y esa suma no cambia al despachar. La prueba obligatoria n.º 5 la verifica.

El lote viaja: el movimiento de entrada en destino crea o alimenta un lote que conserva el costo y
la caducidad del lote de origen, para no perder el dato que 003 y 006 necesitan.

**Razón**: es la exigencia del Principio IV, que prohíbe expresamente registrar el traspaso como dos
ajustes independientes porque la mercancía en tránsito se evaporaría del recuento.

**Alternativas descartadas**: una "sucursal virtual de tránsito" —hace que el tránsito contamine
todas las consultas por sucursal y viola la cardinalidad real del dominio—; mover la existencia en
un solo paso al despachar —niega la existencia del tránsito y hace imposible detectar una
discrepancia de recepción—.

---

## 7. Cola de reconciliación offline

**Decisión**: tabla `operacion_pendiente` con `id`, `tipo_operacion`, `carga` (`JSONB` con el cuerpo
original de la petición), `recurso_afectado` (identificador textual del recurso sobre el que la
operación actúa), `marca_tiempo_origen` (`TIMESTAMPTZ`, reportada por el dispositivo),
`instante_recepcion` (`TIMESTAMPTZ`, puesto por el servidor), `estado`
(`pendiente_de_sincronizar` | `sincronizada` | `conflicto_resuelto`) e
`id_operacion_prevaleciente` (autorreferencia).

El endpoint de sincronización recibe un lote, lo ordena por `marca_tiempo_origen` ascendente y lo
aplica en ese orden. Ante dos operaciones sobre el mismo `recurso_afectado`, prevalece la de marca
más antigua, **en las dos direcciones**:

- si la que llega es más nueva que una ya aplicada, la que llega queda `conflicto_resuelto`;
- si la que llega es más antigua que una ya aplicada, se aplica ella y la ya aplicada pasa a
  `conflicto_resuelto`.

En ambos casos se rellena `id_operacion_prevaleciente`. Ninguna fila se borra ni se oculta.

Se conservan las dos marcas de tiempo por separado, de modo que un reloj de dispositivo desviado sea
detectable comparándolas en lugar de silencioso.

**Razón**: es la implementación mínima que fija la constitución v2.0.2, incluida la visibilidad
obligatoria de la operación desplazada.

**Nota de alcance**: las ventas son hechos de solo-añadir, así que entre ventas no hay conflicto
posible: los reintentos los resuelve la clave de idempotencia. El desempate por marca de tiempo
aplica a operaciones que mutan un mismo recurso —resolución de un conteo, confirmación de un
traspaso, corrección de una observación de precio—. Conviene decirlo porque un lector puede esperar
conflictos entre ventas que por construcción no existen.

**Alternativas descartadas**: última escritura gana —contradice la regla constitucional
explícita—; fusión automática campo a campo —el propio texto constitucional la declara mejora
futura y no requisito—; descartar en silencio la operación desplazada —PROHIBIDO—.

---

## 8. Zona horaria

**Decisión**: todos los instantes en `TIMESTAMPTZ`, que PostgreSQL normaliza a UTC.
`sucursal.zona_horaria` guarda un identificador IANA (`America/Guayaquil` para ambas sucursales del
juego de datos). Toda agregación por día usa
`(m.instante AT TIME ZONE s.zona_horaria)::date`, nunca `::date` sobre el instante crudo.

Un informe que abarque varias sucursales declara qué criterio de día aplica, como exige la
constitución.

**Razón**: exigencia constitucional. El identificador IANA, y no un desplazamiento fijo, es lo que
hace que el cambio de horario de verano no descuadre un cierre de caja.

**Alternativas descartadas**: guardar hora local sin zona —imposible de agregar entre sucursales—;
desplazamiento fijo en horas —se rompe con cualquier cambio de política horaria del país—.

---

## 9. Convención de endpoints

**Decisión**: sustantivos en plural y `kebab-case`, con las acciones que no son CRUD modeladas como
subrecurso: `POST /ventas`, `POST /ventas/{id_venta}/anulacion`, `POST /entradas-inventario`,
`POST /traspasos`, `POST /traspasos/{id_traspaso}/recepcion`, `POST /consultas-no-atendidas`,
`POST /observaciones-precio`, `GET /productos/{id_producto}/comparacion-precios`,
`POST /conteos-fisicos`, `POST /conteos-fisicos/{id_conteo}/resolucion`, `GET /capital-inmovilizado`,
`POST /operaciones-pendientes/sincronizacion`, `POST /turnos`, `POST /turnos/{id_turno}/cierre`.

**Razón**: es la convención pedida, y el subrecurso evita verbos en la ruta manteniendo cada acción
como un hecho registrable, coherente con un módulo cuyo dominio son hechos.

---

## 10. Frontend sin librería de componentes

**Decisión**: React 18 con Vite y componentes propios sobre variables CSS definidas en
`frontend/src/estilos/tokens.css`. Ninguna librería de componentes de terceros.

**Razón**: la constitución define un sistema de diseño propio con dos registros visuales, paleta
anclada, tipografía por registro y regla de tres portadores. Una librería de terceros traería sus
propios tokens, sus radios y su lenguaje de animación, que es exactamente lo que la sección de
sistema de diseño existe para evitar.

**Alternativas descartadas**: Material UI o shadcn con tema personalizado —el tema tapa los valores
por defecto pero no los elimina, y la deriva reaparece en cada componente nuevo—; Tailwind —no es
librería de componentes y sería admisible, pero duplicaría la escala de tokens ya definida en la
constitución—.

---

## 11. "Lote sin costo" del capital inmovilizado — centinela `0.00`, no `NULL`

**Decisión** (interpretación registrada durante la implementación del Bloque B, no retroactiva
sobre entradas anteriores): FR-035 y el esquema `CapitalInmovilizado` del contrato exigen un
estado "lote sin costo registrado → `valor_calculable: false`, `valor_inmovilizado: null`, nunca
cero". Pero `lote.costo_unitario` es `NUMERIC(12,4) NOT NULL` en `data-model.md` y en la migración
`0001`. Se resuelve tratando **`costo_unitario = 0.0000` como el centinela de "sin costo
registrado"**: el listado de capital inmovilizado devuelve `valor_calculable: false` y
`valor_inmovilizado: null` para esos lotes.

**Razón**: introducir `NULL` en un campo financiero `NUMERIC(12,4)` obligaría a revisar cada
consumidor existente de `lote.costo_unitario` (`003-precios-margenes/servicios/margenes.py`,
`006-caja-mermas-fraude/servicios/mermas.py` y `.../deteccion_fraude.py`) para manejar el nuevo
`None`, sin ningún beneficio funcional sobre el centinela. En este negocio `0.00` nunca es un costo
de compra real —una compra a proveedor siempre tiene un costo—, así que no hay ambigüedad con un
costo genuinamente cero. La redacción de FR-035 ("nunca como cero") apunta justamente a que el
peligro a evitar es mostrar `$0.00` como valor inmovilizado.

**Alternativas descartadas**: migración `0008` que haga `costo_unitario` nulo —cambio de esquema y
revisión de 3 módulos por un caso de borde—; declarar `valor_calculable` siempre `true` y quitar el
caso de T080/quickstart —tocaría el contrato y el quickstart ya aprobados—.

---

## 12. Umbrales de antigüedad de una observación de competencia (`indicador_forma`)

**Decisión**: el paso de una observación de precio de `indicador_forma: "lleno"` (reciente) a
`"medio"` a `"hueco"` (vieja) usa umbrales en días, en `backend/rasero/config/competencia.py`,
sobrescribibles por variable de entorno (mismo patrón que `config/pronostico.py` de 004,
`config/promociones.py` de 005 y `config/caja.py` de 006). Valores de arranque:

- `lleno`: antigüedad ≤ **7** días
- `medio`: **8**–**21** días
- `hueco`: > **21** días

**Razón**: FR-002 de la User Story 4 fija el criterio cualitativo —"un precio de hace dos semanas no
puede pesar como uno de hoy"—; ningún artefacto daba cifras. El corte de `lleno` en 7 días y el de
`hueco` en 21 dejan una observación de "hace dos semanas" (14 días) ya fuera de `lleno` y todavía en
`medio`, coherente con ese enunciado. Es presentación pura: `indicador_forma` no entra en ningún
cálculo ni decisión del sistema (FR-028: el sistema no ajusta ningún precio).
