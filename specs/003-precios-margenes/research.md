# Research: Precios y Márgenes

**Fase 0** · 2026-09-05 · Plan: [plan.md](./plan.md)

No quedó ningún `NEEDS CLARIFICATION` en `spec.md` al llegar a esta fase (el único del borrador
inicial, FR-022, se resolvió en la sesión de clarificación de 2026-09-05, ver `## Clarifications`
en spec.md). Las decisiones siguientes son las que el plan debía resolver por su cuenta.

---

## 1. Reutilización íntegra del stack de `001`/`002`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + Vite, sin librería de componentes de terceros) que `001`/`002`, sobre la misma
base PostgreSQL 16.

**Razón**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función que
una ya presente, salvo justificación registrada. Ninguna característica de este módulo —una
fórmula de ratio, dos reglas de ranking, un formulario de clasificación— exige un lenguaje,
framework o motor distinto de los que ya sirven a `001` y `002`.

**Alternativas descartadas**: ninguna evaluada seriamente; no hay señal en el dominio que lo
justifique.

---

## 2. Propiedad de datos: corrección constitucional antes de diseñar el esquema

**Decisión**: antes de escribir `data-model.md`, se corrigió por enmienda (**v2.2.3**) la entrada
de `003-precios-margenes` en la tabla de "Propiedad de Datos y Nomenclatura" de la constitución. La
entrada original —`costo_producto`, `margen_calculado`, `rol_producto`, `sugerencia_colocacion`—
contradecía la propia frontera que la misma sección ya declaraba dos líneas más abajo ("el costo
del producto es dato de compra y pertenece a 001; el margen es cálculo derivado... y pertenece a
003") y no incluía `sugerencia_precio`, que el spec exige explícitamente (FR-008, FR-013, FR-014).
La entrada corregida es: `margen_calculado`, `rol_producto`, `sugerencia_precio`,
`sugerencia_colocacion` — cuatro entidades, mismo conteo, composición corregida.

**Razón**: la lista original se escribió antes de que existiera el spec real de `003` (como ya
ocurrió con `001`: `conteo_renglon` y `producto_precio_sucursal` se incorporaron por enmienda —
v2.1.1 y v2.1.2 — al escribir su `data-model.md`, no en la ratificación inicial). Diseñar el
esquema de este módulo alrededor de una `costo_producto` que la propia constitución dice que
pertenece a `001` habría duplicado esa entidad en dos lugares; omitir `sugerencia_precio` habría
dejado sin dónde persistir el registro de insumos que FR-014 exige. Corregir la tabla antes de
diseñar, en vez de diseñar alrededor del error, es lo que la "Puerta de propiedad de datos" de la
constitución exige: contrastar toda entidad nueva contra esa tabla.

**Alternativas descartadas**: mantener `costo_producto` como una tabla real de `003` que duplique
`lote.costo_unitario` de `001` — rechazada porque crea dos fuentes de verdad del costo (el mismo
problema de fondo que motivó la clarificación de FR-022 sobre el margen) y porque el costo vigente
de un producto ya es derivable de `lote`/`existencia` sin necesidad de copiarlo; no declarar
`sugerencia_precio` y tratar la sugerencia de precio como un valor puramente efímero, nunca
persistido — rechazada porque FR-013 exige "dejar registro de qué sugerencia" originó un override
aplicado, y FR-014 exige que la sugerencia sea explicable *después* de generada, no solo en el
instante de la llamada.

---

## 3. `rol_producto`: tabla propia, no columna de `producto`

**Decisión**: `rol_producto` se modela como su propia tabla, con `id_producto` como clave primaria
y foránea hacia `producto` (relación uno a lo sumo uno), no como una columna añadida a la tabla
`producto` de `001`.

**Razón**: la constitución prohíbe expresamente alterar el esquema de una entidad ajena ("un cambio
de esquema sobre una entidad ajena DEBE hacerse en la funcionalidad propietaria"). `producto` es
propiedad exclusiva de `001`; añadirle una columna `rol` sería un cambio de esquema hecho desde
`003`, prohibido con independencia de que el enunciado (Lectura Crítica n.º 2) hable del rol "del
producto" en lenguaje natural. Una tabla separada, propiedad de `003`, con FK hacia `producto`
logra el mismo resultado observable (cada producto tiene, o no, un rol) sin tocar el esquema ajeno.

**Alternativas descartadas**: columna `rol_producto` en `producto` — rechazada por lo anterior;
tabla `rol_producto` con historial completo de cada cambio (en vez de una fila por producto que se
sobrescribe) — rechazada por ahora: el spec (FR-006) solo exige registrar el instante del último
cambio, no un historial completo de reclasificaciones, y no hay necesidad demostrada de esa
complejidad todavía; puede añadirse después sin romper el contrato si aparece esa necesidad.

---

## 4. `margen_calculado`: recalculado en cada lectura, no por disparador ni tarea de fondo

**Decisión**: `margen_calculado` es una tabla que se **recalcula y sobrescribe (upsert) en cada
lectura** del margen de un producto — no se mantiene sincronizada por disparador de base de datos
ni se refresca por una tarea programada. El costo vigente usado es el del lote que la política de
salida de `001` (FEFO: caducidad más próxima, entrada como desempate) consumiría primero para esa
combinación de producto y sucursal — la misma aproximación de "costo vigente" que ya declara
`spec.md` en Assumptions, y el mismo criterio de selección que `001` ya usa para vender.

**Razón**: los dos insumos del margen (costo y precio) cambian por eventos que ocurren en `001`
(una nueva compra, un cambio de precio o de override), no en `003`. Un disparador de base de datos
sobre tablas ajenas para mantener `margen_calculado` sincronizado escondería el flujo de control
fuera del código de aplicación — la misma razón por la que `002` ya rechazó disparadores para
`existencia`/anonimización (research.md #6 de `002`). Una tarea de fondo periódica podría mostrar un
margen obsoleto entre ejecuciones, lo que violaría SC-001 ("el margen real mostrado coincide con...
en el 100% de los casos verificados"). Recalcular en cada lectura garantiza SC-001 exactamente, y
`margen_calculado` sigue sirviendo su propósito de tabla explicable y consultable (Principio IV):
guarda el costo y precio exactos que produjeron el último valor mostrado.

**Precisión sobre el volumen** (revisado tras revisión de `/speckit-plan`): "recalcular en cada
lectura" es trivial para `GET /productos/{id_producto}/margen` (un producto, un puñado de
consultas), pero `GET /margenes?id_sucursal=` (la vista que lista todos los productos de una
sucursal para la pantalla de sugerencia de precio, User Story 3) **NO** DEBE implementarse como un
bucle que llame N veces al resolver de un solo producto — eso sería un patrón N+1 (cada iteración
resuelve override de precio, costo FEFO y hace su propio upsert por separado), con cientos de
consultas por cada vez que se abre la pantalla. `GET /margenes` DEBE resolver la sucursal completa
con una única consulta de conjunto: un `SELECT` que una `producto` con `producto_precio_sucursal`
(vía `COALESCE`, igual que ya hace `resolver_precio_efectivo` de `001`) y con el costo del lote FEFO
de cada producto (una subconsulta lateral o una función de ventana que, por cada `id_producto`,
tome el `costo_unitario` del lote de `(id_sucursal, id_producto, fecha_caducidad NULLS LAST,
instante_entrada, id_lote)` más próximo — el mismo índice de selección FEFO que `data-model.md` de
`001` ya define), seguida de **un solo** `upsert` masivo (`INSERT ... SELECT ... ON CONFLICT DO
UPDATE`) sobre `margen_calculado`. Para el volumen de este dominio (cientos de productos por
sucursal, Scale/Scope) una consulta de conjunto sobre unas pocas centenas de filas es trivial para
PostgreSQL (muy por debajo del presupuesto de 300 ms p95 fijado en el plan); la misma consulta
implementada como cientos de llamadas individuales sí sería un problema de rendimiento real y
evitable, no una limitación aceptable del dominio — por eso esta distinción se deja explícita aquí
en vez de confiarla a que la implementación la descubra sola. `resolver_margen_producto`
(research.md #8, el contrato con `002`) sigue siendo la función de un solo producto —correcta para
su caso de uso, que nunca resuelve una sucursal completa a la vez— y no debe reutilizarse en un
bucle desde el endpoint de listado.

**Alternativas descartadas**: resolver `GET /margenes` iterando el resolver de un solo producto
una vez por fila (N consultas) — rechazada por el patrón N+1 ya explicado, evitable con una sola
consulta de conjunto sin perder la propiedad de "recalcular en cada lectura"; disparador de base de
datos sobre `lote`/`producto`/
`producto_precio_sucursal` — rechazado por la razón ya dada; tarea de fondo periódica (mismo patrón
que la anonimización de `002`) — rechazada porque el margen no tiene una ventana de tolerancia
declarada en el spec (a diferencia de la anonimización, que sí la tiene, FR-015 de `002`), y
recalcular en cada lectura no tiene costo de cómputo relevante a esta escala (Scale/Scope); no
persistir `margen_calculado` en absoluto y tratarlo como una consulta derivada (como `002` hace con
"valor de cliente") — rechazada porque la constitución ya lo declara como entidad propia de `003`
en la tabla de propiedad de datos (a diferencia de "valor de cliente", que nunca apareció ahí), y
porque `sugerencia_precio`/`sugerencia_colocacion` necesitan un valor de margen persistido y
fechado que puedan snapshot-ear al generarse (research.md #5, #6).

**Corrección de alcance (detectada durante implementación de T009-T011, no en `/speckit-clarify`)**:
el borrador inicial de `spec.md`, de este documento y de `data-model.md` afirmaba que el margen de
un producto a granel necesitaba "la misma conversión gramos/kg que aplica `001`" al costo y al
precio. Es falso, y se corrigió en los tres documentos junto con esta entrada.

`lote.costo_unitario` y `producto.precio_vigente` (ambos de `001`) ya están expresados en la misma
base de medida —por unidad, o por kilogramo si `producto.es_granel`— para cualquier producto
(data-model.md de `001`). `calcular_margen`/`resolver_margen_producto` (dominio/margenes.py,
servicios/margenes.py) solo dividen uno entre el otro; no hay ninguna cantidad vendida de por medio
que multiplicar, así que no hay nada que convertir. Aplicar una conversión aquí habría sido un
error real, no una precaución de más: habría escalado el costo por un factor de 1000 en un sentido
o en otro, corrompiendo el margen de todo producto a granel.

La confusión venía de una analogía incorrecta con `margen_relativo` de `002`
(`margen_resolver.py`, research.md #2 de `002`), que sí convierte — pero por una razón que no
aplica aquí: ese cálculo multiplica `costo_unitario` (por kg) por
`movimiento_inventario.cantidad` (una cantidad en **gramos**, la de una venta real ya ocurrida)
para obtener el costo total consumido en esa venta. Es un margen de **transacción**, con una
cantidad variable de por medio. El margen real de `003` es un margen de **catálogo** — precio de
lista contra costo vigente, sin ninguna cantidad vendida en el cálculo —, y por eso nunca necesitó
esa conversión: comparten el nombre "margen" y la forma del cociente `(x − costo) / x`, pero no son
el mismo cálculo, y confundirlos fue el origen del error. No cambió ninguna fórmula de código a
raíz de esta corrección — `dominio/margenes.py` y `servicios/margenes.py` ya estaban implementados
correctamente (sin conversión); el error vivía únicamente en la documentación.

---

## 5. Algoritmo de sugerencia de precio (Lectura Crítica n.º 2)

**Decisión**: la sugerencia de precio parte del precio vigente (base o su override) y se ajusta
según `rol_producto` y la observación de competencia normalizada más reciente y comparable, cuando
existe:

- **Gancho de tráfico**, con observación vigente: sugerir el menor entre el precio de competencia
  normalizado y el precio vigente — igualar o bajar para atraer tráfico —, nunca por debajo del
  costo vigente (piso de costo: este módulo jamás sugiere vender a pérdida, ni siquiera para un
  gancho de tráfico).
- **Generador de margen**, con observación vigente: si el precio vigente ya está por debajo del
  precio de competencia normalizado, sugerir subir hasta igualarlo (capturar margen que el mercado
  ya tolera); si el precio vigente ya es igual o mayor, sugerir mantenerlo — este rol no persigue
  igualar competencia a la baja.
- **Cualquier rol, sin observación vigente**: sugerir mantener el precio vigente; la sugerencia se
  marca explícitamente "sin referencia de competencia" (FR-010) — el valor informativo es mostrar
  el margen real y el rol, no proponer un número sin sustento.
- **Sin `rol_producto` asignado**: se genera igual (FR-008 no lo exige como requisito previo), pero
  se marca "sin clasificar" y no aplica ninguna de las dos reglas de dirección anteriores; el precio
  sugerido es el vigente sin ajuste.

**Razón**: la Lectura Crítica n.º 2 ya decidió que "bajar el precio de los productos más vendidos
(gancho de tráfico) y subirlo en los de nicho (generador de margen) no contradice decidir por
margen" — esta decisión traduce esa dirección a una regla verificable sin inventar un objetivo
numérico de margen por rol que el spec no exige (Assumptions de `spec.md` ya fija el margen real
como margen bruto simple, sin costeo de indirectos ni objetivos por categoría). El piso de costo es
la única restricción dura, y existe porque ninguna de las dos historias de usuario del spec exige
ni contempla vender a pérdida.

**Alternativas descartadas**: un objetivo numérico de margen por rol (por ejemplo, "gancho de
tráfico: margen objetivo 5-10%; generador de margen: 30-40%") — rechazado por no tener ninguna base
declarada en el spec ni en el enunciado, y por introducir una complejidad de calibración (¿de dónde
salen esos rangos?) que nadie pidió; modelar elasticidad de demanda o simulación de volumen —
rechazado por la misma razón, y porque el spec define margen real como margen bruto simple,
explícitamente sin este tipo de modelado; ignorar el rol y sugerir siempre igualar competencia —
rechazado porque contradice directamente la Lectura Crítica n.º 2.

**Corrección detectada durante implementación de T028-T029**: esta decisión da por hecho que
existe una "observación normalizada" (precio de competencia por unidad de medida) ya resuelta.
`001` declara esa normalización como su propio requisito (FR-023: "El sistema DEBE normalizar las
observaciones a precio por unidad de medida"), pero User Story 4 de `001` —captura y comparación
de precios de competencia— nunca se implementó: existe la tabla `observacion_precio`, pero ningún
servicio, endpoint ni prueba la escribe o la normaliza. `003` no puede esperar a que `001` termine
esa historia para generar sus propias sugerencias (User Story 3 de `003` no depende de esa historia
de `001` en el spec), así que `dominio/sugerencias.normalizar_precio_observado` implementa la
normalización mínima que `003` necesita —convertir a precio por unidad o por kilogramo, los dos
únicos casos que este dominio compara—, documentada explícitamente como una implementación que
`003` no debería tener que mantener: si `001` construye su propia normalización más adelante, esta
función debe migrar a consumirla, mismo patrón que ya resolvió FR-022 para el margen (research.md
#8). No es una decisión de alcance de `003`, es una función puente sobre un requisito ajeno
incumplido.

---

## 6. Algoritmo de sugerencia de colocación (Lectura Crítica n.º 3)

**Decisión**: para una sucursal, se ordenan los productos por `margen_calculado.margen`
descendente y las `zona_exhibicion` de esa sucursal por `grado_privilegio` descendente, y se
asignan por rango: el producto de mayor margen a la zona de mayor privilegio, y así sucesivamente,
repartiendo en franjas cuando hay más productos que zonas. `rol_producto` no altera este ranking;
se adjunta como parte de la explicación de la sugerencia (FR-015 exige usarlo como insumo, y la
propia correlación esperada —generador de margen tiende a margen alto, gancho de tráfico a margen
bajo— hace que el rol narre la misma decisión que el margen ya determina, no que la contradiga).

**Razón**: la Lectura Crítica n.º 3 fija la regla en términos de margen, literalmente: "el producto
de mayor margen va a zona de exhibición privilegiada y el de menor margen a zona relegada". Es una
decisión de análisis ya tomada, no una que este plan deba reinterpretar. Ordenar por margen y
mapear contra `grado_privilegio` es la traducción más directa de esa regla a un algoritmo
verificable, sin inventar una segunda dimensión de ranking que la propia Lectura no pide.

**Alternativas descartadas**: usar `rol_producto` como criterio primario de colocación (por
ejemplo, "gancho de tráfico siempre a zona relegada, para forzar el recorrido por el resto de la
tienda", una táctica real de layout de supermercado) — rechazada por contradecir la redacción
literal de la Lectura Crítica n.º 3, que ata la colocación al margen, no al rol; combinar margen y
rol en una puntuación ponderada — rechazada por la misma razón que `002` rechazó ponderaciones
arbitrarias para el valor de cliente (research.md #4 de `002`): no hay ninguna base declarada para
el peso relativo de cada factor, y el spec no la pide.

**Corrección detectada durante implementación de T039-T040**: `tasks.md` había escrito la firma de
la función pura de este algoritmo como `sugerir_colocacion(margen, zonas_ordenadas) -> id_zona`,
tomando el margen de un solo producto. Es incompatible con la decisión de arriba: un ranking
**relativo** ("el producto de mayor margen…") no puede resolverse conociendo el margen de un único
producto de forma aislada — hace falta saber dónde queda ese margen frente a los de los demás
productos de la misma sucursal. La firma correcta, ya implementada, es
`sugerir_colocacion(*, rango, total_con_margen, zonas_ordenadas) -> id_zona | None`, donde `rango`
es la posición 1-indexada del producto entre los que tienen margen calculable en esa sucursal
(`servicios/precios.generar_sugerencia_colocacion` calcula ese ranking reutilizando
`listar_margenes_sucursal`, ya libre de N+1 desde research.md #4, para conocer el margen de todos
los productos de la sucursal en una sola consulta). `tasks.md` se corrigió para reflejar esta firma.

**Edge case decidido, no cubierto por el spec**: un producto sin margen calculable no tiene con qué
rankear — `generar_sugerencia_colocacion` no genera sugerencia en ese caso (`404`, mismo trato que
FR-018 ya da a la ausencia de zonas), en vez de asignarle una posición arbitraria.

---

## 7. Aplicar una sugerencia de precio: vía una función de servicio de `001`, no ORM directo desde `003`

**Decisión** (revisada tras revisión de `/speckit-plan`): `001` gana una función nueva,
`fijar_precio_sucursal(sesion, *, id_producto, id_sucursal, precio_vigente) ->
ProductoPrecioSucursal`, en su propio `backend/rasero/servicios/catalogo.py` (junto a
`listar_catalogo`, que ya lee esta misma tabla). Esa función hace el `upsert`
(`INSERT ... ON CONFLICT (id_producto, id_sucursal) DO UPDATE`) sobre `producto_precio_sucursal`.
`servicios/precios.py` de `003`, al aplicar una sugerencia, **llama a esa función** — en proceso,
en la misma transacción en que marca la `sugerencia_precio` como aplicada — en vez de instanciar o
escribir directamente sobre el modelo ORM `ProductoPrecioSucursal`. No se crea un endpoint HTTP
nuevo en `001`; la función es de uso interno entre módulos del mismo backend.

**Razón (corregida respecto a la primera versión de esta decisión)**: la primera versión proponía
que `003` importara `ProductoPrecioSucursal` (`persistencia/modelos.py` de `001`) y escribiera
sobre él directamente. Aunque eso no altera el *esquema* de la tabla —la letra de la regla
constitucional de propiedad de datos—, sí rompe el aislamiento entre módulos en la práctica: si
`001` más adelante añade una invariante sobre esa tabla (una validación, una restricción, un
registro de auditoría de cambios de precio), cualquier escritor que la ignore por acceder al ORM
directamente queda desincronizado en silencio. Es una asimetría real frente a **leer** otra tabla
—que ya es una operación de bajo riesgo y sin este problema, como ya hace `002` con
`lote`/`movimiento_inventario`—: **escribir** sí compromete invariantes de negocio, y esas
invariantes son responsabilidad exclusiva del propietario del dato. Una función de una sola
responsabilidad, expuesta por `001` y consumida en proceso por `003`, da a `001` un lugar único
donde crecer esas reglas sin que cada consumidor tenga que enterarse y replicarlas. El costo de
esta función es mínimo (una función de una decena de líneas en un archivo que `001` ya tiene) frente
al riesgo que evita.

Esto no reabre el alcance de `001`: FR-050 de `001` ya declara la *capacidad* de que el precio
difiera por sucursal ("el sistema DEBE admitir..."), pero `001` nunca implementó ninguna escritura
sobre esa tabla porque ninguna de sus historias de usuario la necesitaba — la propia especificación
de `001` declina explícitamente la política de "cómo" fijar el precio. `fijar_precio_sucursal` es
la implementación, ahora sí necesaria, de una capacidad que `001` ya había prometido; no es un
requisito nuevo de `001` ni una decisión de negocio que le pertenezca a `003` imponerle.

**Alternativas descartadas**: `003` escribe directamente sobre el modelo ORM de `001` (versión
original de esta decisión) — descartada por la razón ya dada: funciona hoy porque `001` no tiene
invariantes propias sobre esa tabla, pero acopla a `003` a los detalles internos de otro módulo sin
ningún punto de control; un endpoint HTTP (`PUT /productos/{id}/precio-sucursal`) que `003` consuma
por red — rechazada por introducir latencia y una transacción distribuida entre dos módulos que
viven en el mismo proceso y la misma base de datos, sin ninguna ganancia de aislamiento que una
función en proceso no dé ya (ambos comparten conexión y transacción, así que "aplicar sugerencia" y
"marcar aplicada" siguen siendo atómicos); que `003` mantenga su propia copia de "precio efectivo"
en vez de escribir en la tabla de `001` — rechazada por crear la misma duplicación de fuente de
verdad que la clarificación de FR-022 ya identificó como indefendible para el margen, aplicada
ahora al precio.

**Consecuencia aceptada**: `003` depende de la firma de `fijar_precio_sucursal`, propiedad de
`001`; si `001` cambia esa firma, `003` debe actualizarse en el mismo cambio. Es una dependencia
mucho más angosta y estable que depender del modelo ORM completo, exactamente el punto de esta
corrección.

---

## 8. Contrato de migración con `002` (FR-022)

**Decisión**: `003` expone una función Python en proceso,
`resolver_margen_producto(sesion: Session, *, id_producto: int, id_sucursal: int) -> Decimal | None`,
en `backend/rasero/servicios/margenes.py`. Devuelve el `margen` vigente de `margen_calculado` para
esa combinación (recalculándolo si hace falta, research.md #4), o `None` si no es calculable
(FR-003: sin costo vigente disponible).

`002` migra `resolver_margen_visita` (`margen_resolver.py`) para que, por cada `renglon_venta` de la
venta, llame a esta función en vez de calcular su propio costo desde `movimiento_inventario`, y
combine los resultados con la misma fórmula de ponderación por monto que ya usa
(`Σ(importe_renglon × margen_producto) / venta.total`, research.md #4 de `002`) — esa fórmula de
agregación por venta sigue siendo propiedad de `002` porque combina varios productos de una misma
transacción, un concepto que no le pertenece a `003`. Cuando `resolver_margen_producto` devuelve
`None` para algún renglón, `002` conserva su tratamiento ya documentado para costo desconocido
("ese tramo del renglón se trata como costo cero, la aproximación más simple", research.md #2 de
`002`) — sin cambio de comportamiento en ese caso límite.

**Razón**: `002` y `003` viven en el mismo proceso de backend y la misma base de datos (Principio
I); una función en proceso evita una segunda tecnología (HTTP interno, cola de mensajes) para una
llamada que hoy ya se resuelve con una consulta SQL directa. Mantener la fórmula de ponderación por
venta en `002` respeta la propiedad de datos: `venta`/`renglon_venta` son de `001`, y "cómo combinar
el margen de varios productos de una misma venta" es una decisión de `002` (cómo mide valor de
cliente), no de `003` (que solo sabe de margen por producto y sucursal, nunca de "visita").

**Alternativas descartadas**: un endpoint HTTP (`GET /productos/{id}/margen`) consumido por `002`
en vez de una función en proceso — rechazada por la razón ya dada en research.md #7 (misma proceso,
misma base, sin ganancia de aislamiento) y porque además introduciría latencia de red en el camino
de creación de una `visita`, que hoy es una operación local; que `003` reciba una `venta` completa y
devuelva el margen ya ponderado — rechazada porque obligaría a `003` a conocer `venta`/
`renglon_venta` (propiedad de `001`) y a duplicar la lógica de ponderación por monto que ya es
propiedad declarada de `002`, mezclando fronteras de datos que hoy están limpias.

**Nota de migración** (mismo principio que ya declaró research.md #2 de `002`): `visita.margen_relativo`
ya calculado con la fórmula interina **no se recalcula retroactivamente** al desplegar este cambio;
solo las visitas nuevas, creadas después de la migración, consultan `resolver_margen_producto` de
`003`.

---

## 9. Convención de endpoints

**Decisión**: se reutiliza la convención ya fijada por `001`/`002` — sustantivos en plural,
`kebab-case`, acciones no CRUD como subrecurso, y el patrón ya usado por `001` de anidar bajo
`/productos/{id_producto}` una vista específica de ese producto (`comparacion-precios`):
`GET /margenes`, `GET /productos/{id_producto}/margen`, `PUT /productos/{id_producto}/rol`,
`GET /productos/{id_producto}/sugerencia-precio`, `POST
/productos/{id_producto}/sugerencia-precio/aplicar`, `GET
/productos/{id_producto}/sugerencia-colocacion`, `POST
/productos/{id_producto}/sugerencia-colocacion/aplicar`.

**Razón**: consistencia con el contrato ya publicado de `001`/`002`; no hay ninguna razón
específica de este dominio para desviarse.
