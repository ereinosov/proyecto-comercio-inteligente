# Feature Specification: Reportes e Inteligencia

**Feature Branch**: `008-reportes-inteligencia` — se desarrolla sobre `master`; no se crea rama dedicada (igual que 007).

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Capa estratégica de solo lectura sobre los datos ya calculados por 001–006: comparativo entre sucursales, tendencias multi-semana/mes, KPIs consolidados y segmentación de clientes por clustering. Rol mínimo: encargado."

## Resumen

Los módulos 001–007 resuelven, cada uno, **una decisión operativa o táctica del día**: cobrar,
reponer, ajustar un precio, entender una fuga, cuadrar una caja. Ninguno responde la pregunta
que se hace el dueño de "Despensa Los Ríos" **el domingo por la noche**: *¿cómo va el negocio, y
en qué se distinguen mis dos tiendas?* Esta funcionalidad es esa capa: **una pantalla de lectura
pura** que no captura ningún dato nuevo del operador y no ejecuta ninguna acción — cruza,
agrega y presenta lo que 001–006 ya calcularon, a la escala de la semana y el mes en vez del
turno y el día.

Cuatro vistas, cada una entregable y demostrable por separado:

1. **Comparativo entre sucursales** — Quevedo Centro vs. Buena Fe, mismo período, lado a lado, en
   ventas, margen y merma.
2. **Tendencias** — las series que 001/004/006 ya producen, agregadas por semana o por mes.
3. **Tablero de KPIs** — un puñado de números que resumen el estado de cada módulo.
4. **Segmentos de clientes** — agrupación por similitud (clustering) de los clientes según su
   frecuencia, su margen y su recencia, datos que 002 ya calcula.

Es la única superficie del sistema donde aparece una técnica de agrupamiento no supervisado; el
resto es estadística descriptiva. Toda la vista es de rol **`encargado`** (constitución v2.5.0,
"Autorización de pantalla": capa táctica/estratégica, no operación de caja).

## Clarifications

### Session 2026-09-07

- Q: ¿Esta funcionalidad captura o modifica algún dato de negocio? → A: No. Es de **solo
  lectura**. Lo único que puede escribir es material derivado y regenerable: una tabla de caché
  de agregados y la asignación de cada cliente a un segmento. Nada de eso es fuente de verdad;
  todo se puede reconstruir desde 001–006 borrando la caché.
- Q: ¿El comparativo entre sucursales se codifica para exactamente dos tiendas? → A: No. Compara
  **todas** las sucursales activas que el sistema conozca (`sucursal`), presentadas en columnas.
  Hoy son dos; codificar "dos" está PROHIBIDO por FR-046 de 001, igual que en el resto del
  sistema. Con una sola sucursal, la vista comparativa muestra esa sucursal sin columna de
  contraste y lo dice explícitamente.
- Q: ¿Qué técnica se usa para segmentar clientes, y por qué no una regla fija de umbrales? → A:
  **k-means (algoritmo de Lloyd), k entre 3 y 4**, sobre tres ejes normalizados —frecuencia,
  margen, recencia—. Una regla de umbrales fijos ("cliente de alto valor = gasta más de X")
  obliga a elegir X, y ese X envejece y hay que re-justificarlo. El clustering **deja que los
  datos digan dónde están los grupos**; el sistema sólo nombra cada grupo por su centroide
  ("compran seguido y dejan buen margen", "hace mucho que no vienen"). Es defendible en una
  demostración —"agrupamos por parecido, no por una raya que pusimos nosotros"— y de bajo riesgo:
  no usa ningún dato externo, no se entrena contra etiquetas, y su resultado es determinista con
  semilla fija (misma exigencia que el experimento de reactivación de 005).
- Q: ¿La segmentación corre en vivo al abrir la pantalla, o se recalcula por lote? → A: **Por
  lote**, disparado explícitamente por el encargado desde la propia pantalla (botón "Recalcular
  segmentos"), y su resultado se guarda con la marca de tiempo del cálculo. Correrlo en cada
  carga de página gastaría CPU en repetir el mismo resultado y haría la pantalla lenta sin
  aportar frescura real (los segmentos no cambian entre las 15:00 y las 15:05).
- Q: ¿Los KPIs y las tendencias se calculan en vivo o se cachean? → A: Se calculan en vivo la
  primera vez que se piden para un período y se **cachean** por (tipo de reporte, sucursal o
  "todas", período). La caché se marca con su instante de cálculo y se puede invalidar
  explícitamente ("Actualizar"). No hay trabajo en segundo plano programado en esta
  funcionalidad: el recálculo siempre lo pide una persona.

## Dependencias entre módulos

Esta funcionalidad **sólo lee** de los demás. No modifica ninguna tabla de 001–007.

| Origen | Qué consume | Cómo |
|---|---|---|
| 001 | `venta`, `renglon_venta`, `movimiento_inventario`, `existencia`, `sucursal` | ventas y unidades por período y sucursal; valor de inventario |
| 002 | `cliente`, `visita`, `intervalo_compra`, `senal_fuga` | frecuencia, margen de visita, recencia y estado de fuga por cliente (insumo del clustering) |
| 003 | `margen_calculado` / servicio de margen | margen real por producto y sucursal; margen promedio ponderado |
| 004 | `demanda_corregida`, `pronostico` | serie de demanda para la vista de tendencias |
| 005 | `experimento_reactivacion`, `redencion_promocion` | resultado (veredicto z) del último experimento cerrado; redenciones del período |
| 006 | `merma`, `arqueo`, `anomalia_caja` | merma valorada del período; diferencias de arqueo; anomalías abiertas |
| 007 | `cobertura_pago`, intención no atendida | cuota de intención de compra no atendida por medio de pago |

**Frontera de propiedad de datos.** 008 **no es dueña** de ningún dato de negocio. Introduce
dos entidades **derivadas y regenerables** —una caché de agregados y la asignación de segmento de
cada cliente— que la constitución debe declarar como propiedad de 008 en su sección "Propiedad de
Datos y Nomenclatura" **antes** de `/speckit-plan` (enmienda v2.6.0, MENOR; ver "Dependencias
Constitucionales"). Ningún cálculo de 008 alimenta de vuelta a 001–007.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comparar las dos sucursales en un vistazo (Priority: P1)

El encargado abre "Reportes", elige un período (por defecto: el mes en curso) y ve una tabla con
**una columna por sucursal activa** y una fila por indicador: ventas totales, número de tickets,
ticket promedio, margen promedio ponderado, merma valorada, diferencia de arqueo acumulada. Cada
celda muestra el valor y, cuando hay más de una sucursal, la diferencia relativa contra la mejor
del grupo (por ejemplo "−12 % vs. Quevedo Centro"), con el color semántico de atención sólo
cuando esa diferencia significa un problema real (menos margen, más merma), nunca decorativo.

**Why this priority**: es el uso que motiva toda la funcionalidad —"¿cómo va cada tienda?"— y el
más simple de construir: son sumas y promedios de datos que 001/003/006 ya exponen. Entregable
solo, ya justifica la pantalla.

**Independent Test**: sembrar ventas, mermas y márgenes distintos en dos sucursales para un mes;
abrir la vista comparativa; verificar que (a) hay una columna por sucursal, (b) cada indicador
coincide con la suma/promedio calculado a mano de los datos de 001/003/006, (c) la diferencia
relativa se calcula contra la mejor sucursal del indicador, (d) con una sola sucursal activa la
vista lo dice y no inventa una columna de contraste.

**Acceptance Scenarios**:

1. **Given** dos sucursales con ventas registradas en el período, **When** el encargado abre el
   comparativo, **Then** ve una columna por sucursal con ventas, tickets, ticket promedio,
   margen, merma y diferencia de arqueo, cada valor igual al agregado de los datos de origen.
2. **Given** una sucursal con margen promedio 18 % y otra con 25 % en el mismo período, **When**
   se renderiza la fila de margen, **Then** la celda de la sucursal de 18 % muestra "−7 pp vs.
   [nombre de la otra]" con el color de atención; la de 25 % no lleva color.
3. **Given** un sistema con una sola sucursal activa, **When** el encargado abre el comparativo,
   **Then** ve los indicadores de esa sucursal y una nota explícita de que no hay otra sucursal
   con la que comparar; ninguna columna vacía ni "N/A".
4. **Given** un período sin ninguna venta en una sucursal, **When** se renderiza su columna,
   **Then** los indicadores derivados de ventas se muestran como "sin datos" (no como cero), y el
   resto (merma, arqueo) con su valor real si lo hay.
5. **Given** una sucursal desactivada a mitad del período, **When** se arma el comparativo,
   **Then** esa sucursal sigue apareciendo si tuvo actividad en el período (el dato histórico no
   se oculta), marcada como desactivada.

---

### User Story 2 - Ver la tendencia de un indicador por semana o por mes (Priority: P2)

El encargado elige un indicador (ventas, unidades vendidas, margen promedio, merma valorada,
demanda de un producto) y una granularidad (semana o mes) y ve una **serie temporal agregada**:
en vez del detalle diario que ya muestran Pronóstico y Precios, un punto por semana o por mes,
sobre el rango que elija (por defecto: las últimas 12 semanas o los últimos 6 meses). Puede
acotar por sucursal o ver "todas". La serie marca visualmente los períodos con datos
incompletos (una semana a medias al inicio o al final del rango) para no leer una caída falsa.

**Why this priority**: convierte datos que ya existen a nivel diario en una lectura estratégica.
Depende de que 001/004/006 expongan sus series; es agregación temporal, sin cálculo nuevo de
negocio.

**Independent Test**: sembrar ventas diarias variables durante 10 semanas en una sucursal;
pedir la tendencia de ventas por semana; verificar que cada punto es la suma exacta de los días
de esa semana (semana local de la zona horaria de la sucursal), que una semana parcial al borde
del rango se marca como incompleta, y que "todas las sucursales" suma las series por período.

**Acceptance Scenarios**:

1. **Given** ventas diarias en un rango de 10 semanas, **When** el encargado pide "ventas por
   semana", **Then** ve 10 (u 11) puntos, cada uno igual a la suma de las ventas de esa semana
   local.
2. **Given** una granularidad "mes" y un rango de 6 meses, **When** se arma la serie, **Then**
   cada punto es el agregado del mes calendario local de la sucursal (no ventanas de 30 días).
3. **Given** un rango cuyo primer período está a medias (empieza un miércoles), **When** se
   renderiza, **Then** ese punto se marca como "período incompleto" y no se compara como si
   fuera un período entero.
4. **Given** el filtro "todas las sucursales", **When** se arma la tendencia, **Then** cada punto
   es la suma de las series por sucursal para ese período, no un promedio.
5. **Given** un indicador que un módulo de origen no calcula para el rango pedido (p. ej.
   pronóstico de un producto sin historial), **When** se pide su tendencia, **Then** la serie se
   entrega vacía con la razón explícita, nunca ceros que parezcan datos.

---

### User Story 3 - Leer el tablero de KPIs consolidados (Priority: P2)

El encargado abre la pestaña "Tablero" y ve **una tarjeta por módulo**, cada una con dos o tres
números que resumen su estado, con su período de referencia explícito:

- **Ventas** (001): ventas de la semana, tickets, ticket promedio.
- **Márgenes** (003): margen promedio ponderado de la semana; número de productos con margen
  bajo o con pérdida.
- **Inventario** (001): valor de inventario a hoy; número de lotes con capital inmovilizado.
- **Mermas** (006): merma valorada del mes; su peso sobre las ventas del mes.
- **Fraude/caja** (006): número de anomalías de caja abiertas; diferencia de arqueo acumulada
  del mes.
- **Pagos** (007): cuota de intención de compra no atendida del mes por falta de un medio de
  pago.
- **Promociones/reactivación** (005): veredicto del último experimento cerrado
  ("efectivo" / "no efectivo" / "sin evidencia") y su fecha.
- **Clientes** (002): número de clientes con señal de fuga activa o confirmada.

Cada número es un enlace mental a su pantalla de detalle (no navega, pero el encargado sabe
dónde ir). Un módulo sin datos suficientes para su KPI muestra la razón, no un cero.

**Why this priority**: es el "estado del negocio en una pantalla" que pide el dueño. Cada KPI ya
existe en su módulo; esta vista sólo los reúne. Segundo en prioridad porque aporta más si el
comparativo (P1) ya está.

**Independent Test**: sembrar un estado conocido en cada módulo (unas ventas, un margen bajo, una
merma, una anomalía abierta, un experimento cerrado con veredicto conocido); abrir el tablero;
verificar que cada tarjeta muestra exactamente el número que su módulo de origen reporta para el
período indicado, y que una tarjeta sin datos lo declara.

**Acceptance Scenarios**:

1. **Given** ventas de la semana por 1 240 USD en 88 tickets, **When** se renderiza la tarjeta de
   Ventas, **Then** muestra "1 240 USD · 88 tickets · 14,09 USD ticket promedio · semana del
   [fecha]".
2. **Given** el último experimento de reactivación cerrado con veredicto "efectivo" el 2026-08-20,
   **When** se renderiza la tarjeta de Promociones, **Then** muestra "Efectivo · cerrado
   2026-08-20"; si nunca se cerró uno, muestra "Sin experimento cerrado".
3. **Given** un módulo cuyo KPI necesita más historial del que hay (p. ej. margen de la semana sin
   ninguna venta), **When** se renderiza su tarjeta, **Then** dice "datos insuficientes para el
   período", nunca "0".
4. **Given** 3 anomalías de caja abiertas, **When** se renderiza la tarjeta de Fraude, **Then**
   muestra "3 anomalías abiertas" con el color de atención; con 0 abiertas, sin color.
5. **Given** un período de referencia distinto por KPI (semana para ventas, mes para merma),
   **When** se renderiza el tablero, **Then** cada tarjeta declara su propio período; no se
   fuerza un período único para todas.

---

### User Story 4 - Segmentar los clientes por similitud (Priority: P3)

El encargado abre "Segmentos", pulsa "Recalcular segmentos" y el sistema agrupa a todos los
clientes con historial suficiente en **3 o 4 grupos** según tres ejes: **frecuencia** (visitas
por unidad de tiempo), **margen** (margen relativo promedio de sus visitas) y **recencia** (días
desde la última visita). El resultado se muestra como una lista de grupos, cada uno con: cuántos
clientes tiene, el perfil de su centroide traducido a lenguaje ("vienen seguido, dejan buen
margen, compraron hace poco") y algunos clientes de ejemplo. Cada cliente queda asignado a un
grupo, y ese dato aparece también en el detalle del cliente en la pantalla de Clientes (002),
como una etiqueta de lectura.

El cálculo es **determinista con semilla fija** (misma exigencia que el experimento de 005): dos
recálculos sobre los mismos datos dan los mismos grupos. Los clientes sin historial mínimo
(menos de N visitas) quedan fuera del cálculo, en un grupo "sin clasificar" explícito, no
forzados a un cluster.

**Why this priority**: es la parte más ambiciosa y la única con una técnica no trivial; se
prioriza tercera porque el comparativo y el tablero ya entregan la mayor parte del valor
estratégico y ésta añade profundidad, no fundamento. Independiente: se puede construir y
demostrar sola sobre los datos de 002.

**Independent Test**: sembrar ~40 clientes con patrones de compra deliberadamente distintos (un
grupo que viene seguido y deja buen margen, uno que vino mucho y dejó de venir, uno esporádico de
bajo margen); recalcular segmentos; verificar que (a) los clientes de cada patrón sembrado caen
mayoritariamente juntos, (b) dos recálculos dan la misma asignación, (c) los clientes con 1 sola
visita quedan "sin clasificar", (d) cada grupo trae su descripción derivada del centroide.

**Acceptance Scenarios**:

1. **Given** clientes con historial suficiente, **When** el encargado pulsa "Recalcular
   segmentos", **Then** cada cliente queda asignado a uno de 3–4 grupos y el resultado se guarda
   con su instante de cálculo.
2. **Given** un recálculo previo, **When** se recalcula de nuevo sin que cambien los datos,
   **Then** la asignación de cada cliente es idéntica (semilla fija).
3. **Given** un cliente con una sola visita, **When** se recalcula, **Then** ese cliente aparece
   en "sin clasificar", nunca dentro de un grupo.
4. **Given** un grupo cuyo centroide tiene frecuencia alta, margen alto y recencia baja, **When**
   se muestra ese grupo, **Then** su descripción dice, en lenguaje llano, "vienen seguido, dejan
   buen margen y compraron hace poco" — derivada de los valores del centroide, no un texto fijo.
5. **Given** el detalle de un cliente ya segmentado en la pantalla de Clientes (002), **When** se
   abre, **Then** muestra la etiqueta de su grupo como dato de lectura, con la fecha del último
   recálculo.
6. **Given** que no se ha recalculado nunca, **When** el encargado abre "Segmentos", **Then** ve
   un estado vacío que explica qué aparecerá al recalcular (La Regla del Hueco que Enseña), no
   una lista vacía.

---

### Edge Cases

- **Período sin ningún dato en ningún módulo** (sistema recién instalado): cada vista muestra su
  estado vacío que enseña qué aparecerá, nunca una tabla de ceros.
- **Sucursal creada después del inicio del período elegido**: aparece en el comparativo sólo por
  el sub-período en que existió, con nota.
- **Cambio de zona horaria de una sucursal a mitad de una serie**: los períodos se calculan con
  la zona horaria vigente de la sucursal en cada instante (mismo criterio que 006 usa para el día
  local); un cambio se documenta como caso conocido, no se re-proyecta el histórico.
- **Clustering con menos clientes clasificables que k**: si hay menos de k clientes con historial
  mínimo, no se fuerza el número de grupos; se reportan tantos grupos como clientes distintos
  permitan, o se declara que no hay base suficiente para segmentar.
- **Caché desactualizada respecto a datos que cambiaron** (una venta se anuló después de cachear
  un agregado): la caché muestra su instante de cálculo; el encargado puede forzar "Actualizar".
  El sistema no intenta detectar cambios aguas arriba en tiempo real.
- **Dos sucursales empatadas en el "mejor" valor de un indicador**: la diferencia relativa de las
  demás se calcula contra ese valor; las empatadas no llevan marca de diferencia.
- **Recálculo de segmentos disparado dos veces seguidas** (doble clic): idempotente por el
  instante — el segundo recálculo produce el mismo resultado y sólo actualiza la marca de tiempo.

## Requirements *(mandatory)*

### Functional Requirements

**Alcance y naturaleza**

- **FR-001**: La funcionalidad DEBE ser de **solo lectura** respecto a los datos de negocio de
  001–007: NO crea, modifica ni borra ninguna `venta`, `cliente`, `merma`, `margen_calculado`,
  `experimento_reactivacion` ni ninguna otra entidad de esos módulos.
- **FR-002**: Los únicos datos que la funcionalidad PUEDE escribir son **derivados y
  regenerables**: (a) una caché de agregados de reporte, y (b) la asignación de cada cliente a un
  segmento. Borrar ambos y recalcular DEBE reproducir exactamente el mismo estado a partir de
  001–006.
- **FR-003**: Toda la pantalla y todos sus endpoints DEBEN exigir rol **`encargado`** o superior
  (constitución v2.5.0, "Autorización de pantalla"), verificado por el mecanismo central
  `exige_rol`, nunca duplicado.
- **FR-004**: Ningún literal de las dos sucursales reales ("Quevedo Centro", "Buena Fe",
  "Despensa Los Ríos") DEBE aparecer en código, identificador técnico ni configuración: las
  sucursales se leen de `sucursal` (FR-046 de 001).

**Comparativo entre sucursales (User Story 1)**

- **FR-005**: El sistema DEBE presentar, para un período elegido, una comparación con **una
  columna por sucursal activa (o con actividad en el período)** y filas para: ventas totales,
  número de tickets, ticket promedio, margen promedio ponderado, merma valorada, diferencia de
  arqueo acumulada.
- **FR-006**: Cada valor de una celda DEBE coincidir exactamente con el agregado calculable de
  los datos de origen de 001/003/006 para esa sucursal y período.
- **FR-007**: Cuando hay más de una sucursal, cada celda DEBE mostrar además su diferencia
  relativa contra la **mejor** sucursal de esa fila, y aplicar el color semántico de atención
  SÓLO cuando esa diferencia indica un peor resultado (menos margen, más merma, más faltante de
  arqueo) — nunca decorativo (La Regla del Significado).
- **FR-008**: Con una sola sucursal, la vista DEBE mostrar sus indicadores y declarar
  explícitamente que no hay otra sucursal para comparar; PROHIBIDO mostrar una columna vacía o
  "N/A".
- **FR-009**: Un indicador sin base de cálculo para una sucursal-período (p. ej. margen sin
  ninguna venta) DEBE mostrarse como "sin datos", nunca como cero.

**Tendencias (User Story 2)**

- **FR-010**: El sistema DEBE entregar, para un indicador y una granularidad (`semana` | `mes`),
  una serie de puntos donde cada punto es el agregado de ese indicador en ese período **local**
  de la sucursal (semana o mes calendario en su zona horaria), sobre un rango configurable (por
  defecto: 12 semanas o 6 meses hacia atrás).
- **FR-011**: Un período parcial en un extremo del rango DEBE marcarse como "incompleto" para que
  no se lea como una variación real.
- **FR-012**: Con el ámbito "todas las sucursales", cada punto DEBE ser la **suma** de las series
  por sucursal para ese período, no un promedio.
- **FR-013**: Los indicadores disponibles para tendencia DEBEN ser al menos: ventas totales,
  unidades vendidas, margen promedio ponderado, merma valorada, y demanda corregida de un
  producto (de 004).

**Tablero de KPIs (User Story 3)**

- **FR-014**: El tablero DEBE mostrar **una tarjeta por módulo** (Ventas, Márgenes, Inventario,
  Mermas, Fraude/caja, Pagos, Promociones, Clientes), cada una con 2–3 cifras resumen y su
  **período de referencia explícito** (que puede diferir entre tarjetas: semana para ventas, mes
  para merma, "a hoy" para inventario).
- **FR-015**: Cada cifra del tablero DEBE coincidir con lo que su módulo de origen reporta para
  ese período; el tablero no recalcula la regla de negocio, sólo la muestra.
- **FR-016**: Una tarjeta sin datos suficientes para su KPI DEBE declarar la razón ("datos
  insuficientes para el período"), nunca mostrar "0".
- **FR-017**: Las cifras que representan un problema (margen bajo, anomalías abiertas, faltante de
  arqueo, cuota de intención no atendida por encima de un umbral) DEBEN llevar el color de
  atención; las neutras, no.

**Segmentación de clientes (User Story 4)**

- **FR-018**: El sistema DEBE agrupar a los clientes con historial mínimo en **3 o 4 grupos**
  mediante un algoritmo de agrupamiento por similitud (k-means / Lloyd) sobre tres ejes
  normalizados: **frecuencia**, **margen relativo promedio** y **recencia**. Los tres ejes se
  derivan de datos que 002 ya calcula (`visita`, `intervalo_compra`).
- **FR-019**: El cálculo DEBE ser **determinista con semilla fija**: dos recálculos sobre los
  mismos datos producen la misma asignación de cada cliente y las mismas descripciones de grupo.
- **FR-020**: El recálculo DEBE dispararlo **una persona** explícitamente desde la pantalla; NO
  hay recálculo automático en cada carga ni trabajo programado en segundo plano en esta
  funcionalidad. El resultado se guarda con su instante de cálculo.
- **FR-021**: Los clientes con menos de N visitas (umbral de calibración, por defecto 3 —
  coherente con el mínimo de `intervalo_compra` de 002) DEBEN quedar en un grupo **"sin
  clasificar"** explícito, nunca forzados a un cluster.
- **FR-022**: Cada grupo DEBE mostrarse con: número de clientes, una **descripción en lenguaje
  llano derivada de su centroide** (alta/media/baja en cada eje traducido a frase), y algunos
  clientes de ejemplo. PROHIBIDO un texto de grupo fijo que no dependa del centroide.
- **FR-023**: La asignación de segmento de un cliente DEBE aparecer como **etiqueta de lectura**
  en el detalle del cliente de la pantalla de Clientes (002), con la fecha del último recálculo.
  002 no gana ninguna capacidad de escritura por esto.
- **FR-024**: Si hay menos clientes clasificables que `k`, el sistema NO DEBE forzar `k` grupos;
  reporta los que la base permita o declara que no hay base para segmentar.
- **FR-025**: El algoritmo NO DEBE usar ninguna librería pesada de aprendizaje automático ni
  ningún dato externo al sistema; su implementación DEBE ser explicable en pocos párrafos
  (inicialización, asignación al centroide más cercano, recálculo de centroides, parada por
  convergencia o iteración máxima).

**Caché y frescura**

- **FR-026**: Los agregados de comparativo, tendencia y tablero DEBEN calcularse a demanda y
  **cachearse** por (tipo de reporte, ámbito de sucursal, período). Cada entrada de caché DEBE
  llevar su instante de cálculo.
- **FR-027**: El encargado DEBE poder forzar el recálculo de una vista ("Actualizar"), que
  reemplaza la entrada de caché correspondiente.
- **FR-028**: El sistema NO DEBE intentar detectar en tiempo real que un dato aguas arriba
  cambió; la responsabilidad de refrescar es del encargado, informado por el instante de cálculo
  visible.

**Presentación**

- **FR-029**: La sección DEBE usar el activo de marca **`despensa-logo-mono-800w.png`** como su
  elemento visual, coherente con la reserva ya escrita en DESIGN.md ("mono = reportes,
  dashboards y la marca de agua de los estados vacíos"). Ningún otro uso del activo de marca se
  solapa.
- **FR-030**: Todo estado vacío de la sección (período sin datos, segmentos nunca calculados)
  DEBE seguir La Regla del Hueco que Enseña (ícono + título + frase de qué aparecerá), vía el
  componente compartido `EstadoVacio`.
- **FR-031**: La sección es registro de **Análisis** (Source Serif 4 en títulos y prosa, radio
  6px), coherente con las demás pantallas gerenciales; ningún elemento usa el Verde Rasero (La
  Regla de la Sola Voz / del Registro Sin Dinero).

### Key Entities *(include if feature involves data)*

- **Agregado de reporte cacheado**: una fila de resultado ya calculado para una vista. Atributos:
  tipo de reporte (comparativo | tendencia | tablero), ámbito (una sucursal o "todas"), período
  (inicio, fin, granularidad), el conjunto de cifras resultante, instante de cálculo. Regenerable
  desde 001–006; borrarla no pierde nada.
- **Segmento de cliente**: la definición de un grupo producido por el último recálculo. Atributos:
  identificador del grupo, valores del centroide en cada eje (frecuencia, margen, recencia),
  número de clientes, descripción derivada, instante del recálculo, semilla usada.
- **Asignación de segmento**: relación cliente ↔ segmento del último recálculo. Atributos: cliente,
  segmento (o "sin clasificar"), instante del recálculo. Una fila por cliente; se reemplaza
  entera en cada recálculo.

Ninguna de estas tres es fuente de verdad de negocio; las tres se reconstruyen ejecutando los
cálculos de 008 sobre 001–006.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un encargado que abre "Reportes" identifica en menos de **30 segundos** cuál de sus
  sucursales tiene peor margen y peor merma en el mes en curso, sin abrir ninguna otra pantalla.
- **SC-002**: El **100 %** de las cifras del comparativo y del tablero coincide, al centavo o a la
  unidad, con el agregado calculado a mano de los datos de 001–006 para el mismo período y
  ámbito.
- **SC-003**: Dos recálculos de segmentos sobre los mismos datos producen asignaciones
  **idénticas** para el 100 % de los clientes.
- **SC-004**: En un conjunto de prueba con tres patrones de compra deliberadamente separados, al
  menos el **80 %** de los clientes de cada patrón cae en el mismo grupo.
- **SC-005**: Ninguna vista muestra "0" donde el dato correcto es "sin datos": el **100 %** de las
  celdas y tarjetas sin base de cálculo lo declaran explícitamente.
- **SC-006**: La sección no introduce ninguna escritura sobre las tablas de 001–007: una
  auditoría del código de 008 encuentra **cero** sentencias de modificación sobre esas tablas.
- **SC-007**: La primera carga de una vista para un período nuevo responde en un tiempo aceptable
  para una pantalla gerencial (percepción de "casi inmediato" para el comparativo y el tablero;
  el recálculo de segmentos puede tardar más y muestra su progreso).
- **SC-008**: Un evaluador que ve la pantalla de segmentos entiende, sin explicación previa, que
  los grupos salieron de "agrupar clientes parecidos" y no de reglas fijas — verificable pidiendo
  a un tercero que describa con sus palabras qué está viendo.

## Assumptions

- **Volumen de datos.** El catálogo, la clientela y el historial son los de un minimarket de dos
  tiendas (decenas de miles de ventas, cientos de clientes, decenas de productos). El clustering
  y las agregaciones se calculan sobre ese orden de magnitud sin paginación ni muestreo; si el
  volumen creciera un orden de magnitud, se revisa la estrategia de caché.
- **Períodos por defecto.** Comparativo: mes en curso. Tendencias: 12 semanas / 6 meses hacia
  atrás. Tablero: cada KPI con el período natural de su módulo (semana para ventas y márgenes,
  mes para merma y arqueo, "a hoy" para inventario). Todos configurables.
- **`k` del clustering.** Se fija en 3 o 4 tras una calibración simple (regla del codo sobre la
  inercia, o simplemente probar 3 y 4 y quedarse con el más interpretable); no es un parámetro
  que el encargado ajuste desde la interfaz en esta versión.
- **Umbral de historial mínimo para segmentar.** 3 visitas, reutilizando el mínimo que 002 ya
  exige para calcular `intervalo_compra`. Ajustable por calibración, no por interfaz.
- **Zona horaria de los períodos.** Se usa la zona horaria de la `sucursal` (mismo criterio que
  006 para el día local); "todas las sucursales" agrega por período local de cada una y suma.
- **Sin exportación.** No se exige exportar a PDF/hoja de cálculo en esta versión; la pantalla es
  suficiente. Si más adelante se añade, reutilizará el patrón de generación de documentos del
  proyecto (ver 009).
- **Sin trabajo programado.** Toda regeneración de caché y de segmentos la dispara una persona.
  No se añade ningún job ni cron en esta funcionalidad.
- **Reutiliza servicios de lectura existentes.** Donde 001–006 ya exponen un servicio o endpoint
  de lectura que entrega el agregado necesario (márgenes por sucursal, resumen de mermas por
  semana, resumen de fuga), 008 lo consume en vez de re-consultar las tablas base.

## Dependencias Constitucionales

- **Enmienda requerida ANTES de `/speckit-plan`** (mismo patrón que v2.2.3–v2.2.6 para 003–006):
  la sección "Propiedad de Datos y Nomenclatura" de la constitución DEBE ganar una entrada para
  `008-reportes-inteligencia` que declare sus tres entidades derivadas (agregado cacheado,
  segmento de cliente, asignación de segmento) como **propiedad de 008 y regenerables**, y
  registre la frontera "008 sólo lee de 001–007; nada de 008 alimenta de vuelta". Sería la
  enmienda **v2.6.0** (MENOR: añade una entrada de propiedad de datos y, si se decide, una
  mención en Principio V sobre el clustering como "inteligencia explicable y reversible" — encaja
  en el principio ya existente sin redefinirlo). El conteo de entidades por módulo se actualiza
  para incluir las de 008.
- **Principio V (Inteligencia Explicable y Reversible)** ya cubre el clustering sin cambios: es
  explicable (algoritmo de pocos pasos, descrito), reversible (borrar y recalcular), determinista
  (semilla fija) y no usa datos externos. La enmienda sólo lo hace explícito para esta técnica.
- **Constitución v2.5.0, "Autorización de pantalla"**: ya asigna "Reportes e inteligencia (spec
  008)" al rol `encargado`. Esta spec lo implementa; no requiere cambio ahí.
- **Sincronización de citas**: la enmienda v2.6.0 actualiza las citas de "versión vigente" de
  001–008 sólo si toca el texto de un principio; si se limita a la tabla de Propiedad de Datos,
  se sincroniza esa sección y 008, sin barrer 001–007 (mismo criterio que v2.5.0).
