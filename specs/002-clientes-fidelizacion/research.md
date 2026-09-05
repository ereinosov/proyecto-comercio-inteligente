# Research: Clientes y Fidelización

**Fase 0** · 2026-09-04 · Plan: [plan.md](./plan.md)

No quedó ningún `NEEDS CLARIFICATION` en `spec.md` al llegar a esta fase (los tres del borrador
inicial se resolvieron en la sesión de clarificación de 2026-09-04, ver `## Clarifications` en
spec.md). Las decisiones siguientes son las que el plan debía resolver por su cuenta.

---

## 1. Reutilización íntegra del stack de `001`

**Decisión**: mismo backend (Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2) y mismo
frontend (React 18 + Vite, sin librería de componentes de terceros) que `001-core-ventas-inventario`,
sobre la misma base PostgreSQL 16.

**Razón**: el Principio I prohíbe introducir una segunda tecnología que cumpla la misma función que
una ya presente, salvo justificación registrada. No hay ninguna característica de este módulo
—cálculo de intervalos, umbral de fuga, agregación de valor— que exija un lenguaje, framework o
motor distinto de los que ya sirven a `001`.

**Alternativas descartadas**: un servicio analítico separado (por ejemplo, un job en otro lenguaje
más cómodo para estadística) — rechazado porque las operaciones involucradas (medianas, percentiles,
sumas) no superan lo que el mismo stack ya resuelve, y separar servicios introduciría sincronización
de datos entre dos fuentes de verdad sin necesidad demostrada.

---

## 2. Margen de una visita mientras `003-precios-margenes` no existe

**Decisión**: `margen_resolver.py` expone una única función,
`resolver_margen_visita(id_venta) -> Decimal`, que hoy calcula el margen como un **ratio
relativo al precio de venta** (margen bruto, no *markup* sobre costo), no como un monto absoluto:

```text
costo_total_venta   = Σ costo_unitario_del_lote × cantidad_en_la_unidad_de_costo_del_lote,
                       para cada movimiento_inventario de tipo salida_venta con ese id_venta
                       (lote.costo_unitario, vía movimiento_inventario — ver nota de propiedad
                       de datos más abajo)

margen_relativo_visita = (venta.total − costo_total_venta) / venta.total
```

El resultado, una fracción (por ejemplo `0.2500` = 25% de margen sobre el precio de venta), se
congela en `visita.margen_relativo`, redondeada a 4 decimales (`NUMERIC(6,4)`, mismo redondeo
`ROUND_HALF_UP` que usa `dominio/totales.py` para dinero) en el momento de crear la visita, como
exige FR-005 — la misma congelación (snapshot), solo que expresada como proporción y no como
importe.

**Corrección descubierta durante `/speckit-implement`**: `costo_unitario` es "por unidad o por
kilogramo" (data-model.md de `001`), igual que `precio_aplicado`. Para un producto a granel,
`movimiento_inventario.cantidad` está en **gramos** enteros; sumar `costo_unitario × cantidad`
sin convertir sobrevaloraría el costo en un factor de 1000. `resolver_margen_visita` consulta
`producto.es_granel` y convierte a kilogramos antes de multiplicar — la misma conversión que
`dominio/totales.calcular_importe_renglon` ya aplica al precio. La fórmula de esta decisión queda
corregida aquí para reflejarlo; el detalle no estaba explícito en la redacción original.

**Razón**: `003-precios-margenes` no está construido y no hay una tabla `margen_calculado` que
consultar todavía. Bloquear `002` hasta que `003` exista contradice el propio spec, que ordena las
historias de usuario asumiendo que el valor de cliente se puede entregar ya (User Story 2). Aislar
el cálculo detrás de una función con firma estable permite sustituir la implementación por una
consulta real a `003` sin tocar `data-model.md` de `visita` ni ningún consumidor.

**Por qué relativo y no absoluto** (corrección sobre la versión anterior de esta decisión): un
margen absoluto en moneda mezcla dos señales distintas — cuánto vendió (tamaño del ticket) y qué
tan rentable fue proporcionalmente esa venta — y esa mezcla ya la captura la dimensión "monto" del
valor de cliente (research.md #4). Si "margen" también escala con el tamaño del ticket, deja de
aportar información nueva y penaliza sistemáticamente a un cliente que compra barato aunque sea muy
rentable por unidad vendida. Expresarlo como fracción del precio de venta desacopla las dos
dimensiones: dos clientes con el mismo ratio de margen quedan igual de bien clasificados en esa
dimensión sin importar si uno gasta 5 y el otro 500.

Además, un ratio es la unidad en la que casi cualquier implementación razonable de "margen" en
`003` también se expresará — es la definición estándar de margen bruto en retail. Congelar hoy la
métrica en esa misma unidad es lo que evita que, al sustituir esta fórmula por la consulta real a
`003`, el orden de clientes ya calculado cambie **solo por un cambio de escala** (de moneda a
fracción) en vez de por una diferencia real de criterio de negocio. Si `003` decide un criterio de
margen distinto al bruto simple (por ejemplo, con asignación de costos indirectos), el orden podrá
cambiar — pero por ese motivo declarado, no por una inconsistencia de unidades que esta decisión ya
evita.

**Alternativas descartadas**: margen absoluto en moneda (versión original de esta decisión) —
descartada por lo anterior: acopla "margen" a "monto" y hace que el reemplazo futuro por `003`
pueda reordenar clientes por un artefacto de escala; *markup* sobre costo
(`(precio − costo) / costo`) en vez de margen sobre precio de venta — descartado porque no está
acotado por arriba de forma natural (un costo cercano a cero dispara el ratio sin límite), lo que
distorsiona el percentil de esa dimensión; dejar `margen_relativo` nulo hasta que `003` exista —
rechazado porque FR-010 exige combinar las tres dimensiones desde ya, y un margen permanentemente
nulo invalidaría esa dimensión para todos los clientes, no sería una limitación puntual; duplicar
la lógica de negocio de margen que `003` eventualmente definirá (roles de producto, asignación de
costos indirectos) — rechazado porque violaría la propiedad de datos de `003`, mientras que un
margen bruto simple es un cálculo aritmético de dominio público que no anticipa ninguna regla de
negocio exclusiva de `003`.

**Nota de propiedad de datos**: `lote.costo_unitario` y `movimiento_inventario` son propiedad de
`001-core-ventas-inventario`. `margen_resolver.py` los **lee, no los posee**: no los redefine, no
los duplica y no altera su esquema — el mismo patrón de consulta entre funcionalidades que la
constitución ya declara para `anomalia_caja` (006) sobre `movimiento_inventario`/`venta` (001), y
para la frontera entre "costo" (001) y "margen" (003). Ver la nota equivalente en `data-model.md`.

**Nota de migración futura**: cuando `003` exista, el cambio se limita a la implementación interna
de `resolver_margen_visita`; `visita.margen_relativo` ya calculado con la fórmula interina **no se
recalcula retroactivamente** (mismo principio de snapshot que ya declara FR-005 respecto a cambios
de margen después de la visita).

---

## 3. Umbral mínimo de historial e intervalo esperado

**Decisión**: un cliente necesita **al menos 3 visitas** (2 intervalos entre visitas consecutivas)
para salir de `datos_insuficientes`. `intervalo_esperado_dias` es la **mediana** de esos intervalos,
recalculada con cada visita nueva.

**Razón**: con 1 visita no hay ningún intervalo que medir. Con 2 visitas hay exactamente un
intervalo, indistinguible de una ocurrencia aislada — no hay forma de saber si ese cliente compra
así de seguido siempre o si fue una coincidencia. 3 visitas son el primer punto en el que existen
dos intervalos que comparar entre sí. Se usa la mediana, y no el promedio, porque es la que se
comporta mejor a medida que se acumulan más visitas: con exactamente dos intervalos la mediana
coincide con el promedio (es un caso degenerado esperado, no un error), pero desde el tercer
intervalo en adelante la mediana deja de moverse por un solo valor atípico (por ejemplo, unas
vacaciones que duplican un intervalo normal), mientras que el promedio sí lo arrastra.

**Alternativas descartadas**: exigir 2 visitas (1 intervalo) — rechazado por indistinguible de una
coincidencia, tal como se explicó; exigir 5 o más visitas para mayor robustez estadística —
rechazado porque retrasa demasiado la cobertura de clientes nuevos frente al beneficio marginal, y
la constitución exige degradar con gracia (mostrar "datos insuficientes"), no maximizar precisión a
costa de cobertura; promedio simple desde el inicio — rechazado por sensibilidad a un solo intervalo
atípico, justo el caso que un cliente estacional produce con facilidad.

---

## 4. Fórmula del valor de cliente

**Decisión**: para cada cliente con historial suficiente, se calcula el percentil de cada una de
las tres dimensiones contra la población de clientes con historial suficiente:

- **Frecuencia**: inverso de `intervalo_esperado_dias`.
- **Monto**: `SUM(visita.monto_total)` acumulado del cliente.
- **Margen**: el ratio de margen del cliente, **ponderado por el monto de cada visita** —
  `SUM(visita.monto_total × visita.margen_relativo) / SUM(visita.monto_total)` —, no un promedio
  simple de los ratios por visita. La ponderación es necesaria porque un promedio simple trataría
  igual una visita de 2 con 90% de margen que una de 200 con 20%, cuando la segunda aportó mucho
  más margen real; el resultado de la fórmula ponderada equivale, de hecho, al margen bruto total
  del cliente dividido entre su monto total.

La puntuación compuesta es el **promedio simple de los tres percentiles**. El desglose que exige
FR-011b son los tres percentiles por separado, no valores en dólares, días o ratios crudos.

**Razón**: las tres dimensiones tienen escalas incompatibles entre sí (días, moneda, moneda de
margen) y sumarlas u ponderarlas directamente exigiría un tipo de cambio arbitrario entre "un día
menos de espera" y "un dólar más de margen" que nadie pidió y que no es explicable ante un gerente.
Convertir cada una a un percentil dentro de la propia base de clientes hace las tres comparables sin
inventar una tasa de conversión, y el promedio simple —no ponderado— es el reflejo directo y
auditable de "las tres pesan igual", tal como se decidió para esta funcionalidad. La línea base
exigida por el Principio V es precisamente el orden por `monto_total` solo, que es el criterio que
el negocio usa hoy por impresión; SC-002 se verifica comparando el orden compuesto contra esa línea
base.

**Alternativas descartadas**: ponderación fija arbitraria (por ejemplo, 40% monto, 30% frecuencia,
30% margen) — rechazada por no tener ninguna base declarada, y el propio contexto de la
funcionalidad establece que las tres "importan tanto", no una jerarquía; normalización min-max en
vez de percentil — rechazada porque un solo cliente extremo (una compra corporativa gigante,
irreal en este dominio pero no imposible) comprimiría a todos los demás cerca de cero, mientras que
el percentil es indiferente a la magnitud del extremo.

---

## 5. Integración con la creación de una venta, sin tocar el esquema de `venta`

**Decisión**: `venta` y `renglon_venta` (propiedad de `001`) no ganan ninguna columna nueva. Cuando
el cajero identifica a un cliente en `Venta.tsx`, el frontend completa la venta contra `001` como
siempre y, solo si esa venta se confirmó (`201` o el `200` idempotente), hace una segunda llamada
`POST /clientes/{id_cliente}/visitas` con el `id_venta` recién obtenido. El backend valida que esa
venta exista y que no tenga ya una visita asociada (`visita.id_venta UNIQUE`).

**Razón**: la tabla de propiedad de datos de la constitución asigna `venta` a `001` en exclusiva;
añadirle un `id_cliente` opcional sería redefinir una entidad ajena, prohibido explícitamente. Un
segundo paso posterior a la confirmación mantiene la venta como hecho autónomo de `001` —se
completa igual si el segundo paso falla— y es coherente con FR-003: identificar al cliente nunca
puede ser parte de la transacción crítica del cobro.

**Alternativas descartadas**: añadir `id_cliente` nullable a `venta` — rechazado por violar la
propiedad de datos; una única llamada combinada "venta + cliente" en un nuevo endpoint que orqueste
ambos módulos — rechazado porque acoplaría el contrato de `001` (ya publicado y estable) a la
existencia de `002`, exactamente lo que la propiedad de datos por funcionalidad busca evitar.

**Consecuencia aceptada**: si la segunda llamada falla (red, servidor caído un instante), la venta
queda registrada en `001` sin visita asociada en `002`. Es preferible a bloquear o revertir el
cobro; el cliente simplemente no acumula esa visita, igual que si el cajero hubiera decidido no
identificarlo. No se implementa reintento automático en este plan: es una pérdida de señal
analítica, no de dinero ni de existencia, y el Principio II no exige más que esto.

---

## 6. Anonimización como tarea de fondo

**Decisión**: `anonimizacion.py` expone una función `anonimizar_clientes_vencidos()` que se invoca
como tarea programada diaria (`python -m rasero.tareas.anonimizar_clientes`, mismo patrón que
`python -m rasero.semilla` ya usado por `001`), no en el camino de ninguna petición HTTP. Recorre
las señales de fuga en estado `confirmada` cuyo `instante_purga_programada` ya venció y anonimiza
al cliente correspondiente en la misma transacción en que marca la purga como ejecutada.

**Razón**: FR-015 exige que la anonimización sea automática al vencer el plazo, pero nada en el
spec exige que sea instantánea al segundo exacto; una tarea diaria cumple el requisito sin arriesgar
que un cálculo de purga compita con tráfico de lectura o escritura real. Mantiene además la regla
general de este módulo (y del Principio II) de que ninguna función de fidelización es camino
crítico de nada.

**Alternativas descartadas**: calcular "¿debería estar anonimizado?" al vuelo en cada lectura, sin
purgar realmente la fila — rechazado porque no cumple FR-016 (los datos personales deben dejar de
existir, no solo de mostrarse); disparador de base de datos que anonimice al escribir — rechazado
por la misma razón que `001` rechazó triggers para `existencia`: esconde el flujo de control fuera
del código de aplicación.

---

## 7. Convención de endpoints

**Decisión**: se reutiliza la convención ya fijada por `001` — sustantivos en plural,
`kebab-case`, acciones no CRUD como subrecurso: `POST /clientes`, `GET /clientes`,
`GET /clientes/{id_cliente}`, `POST /clientes/{id_cliente}/visitas`, `GET /clientes/cumpleanos`,
`GET /clientes/busqueda`.

**Razón**: consistencia con el contrato ya publicado de `001`; no hay ninguna razón específica de
este dominio para desviarse.

---

## 8. Aritmética de intervalos: sin zona horaria de sucursal

**Decisión**: los intervalos entre visitas se calculan como diferencia directa entre
`TIMESTAMPTZ` en UTC (`visita.instante` de una y de la siguiente), sin convertir a día local de
ninguna sucursal.

**Razón**: la regla de día local de sucursal que exige la constitución aplica a **agregaciones de
negocio por día** (cierre de caja, ventas del día), pensadas para un límite de calendario. El
intervalo de compra de un cliente mide **tiempo transcurrido real** entre dos instantes, y un
cliente puede comprar en cualquiera de las dos sucursales indistintamente; elegir la zona horaria de
cuál de las dos sucursales sería arbitrario y no cambia el resultado en más de unas horas, muy por
debajo de la escala de días en que se mide un intervalo de compra.

**Alternativas descartadas**: usar la zona horaria de la sucursal de la visita más reciente —
rechazada por arbitraria (¿y si las dos visitas fueron en sucursales distintas?) y por no aportar
ninguna diferencia práctica a la escala de días del cálculo.
