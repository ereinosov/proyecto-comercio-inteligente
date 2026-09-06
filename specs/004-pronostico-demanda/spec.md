# Feature Specification: Pronóstico de Demanda

**Feature Branch**: `004-pronostico-demanda` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-05

**Status**: Draft

**Input**: Pronosticar, por producto y sucursal, la demanda futura que sirve para decidir cuánto
pedir y cuánto exhibir, partiendo de que la demanda histórica registrada NO es una señal limpia:
está contaminada por al menos cuatro fuentes que se modelan con profundidad desigual. (1) Quiebres
de stock —la fuente central y de tratamiento más profundo—: durante los días sin existencia las
ventas registradas subestiman la demanda real, que queda censurada; hay demanda latente no
observada que debe recuperarse. (2) Precio: los cambios de precio (incluido el override por
sucursal de `001-core-ventas-inventario`, FR-050) alteran la demanda observada, y un pronóstico que
ignora el precio vigente de cada período histórico confunde cambio de precio con cambio de demanda
base. (3) Promociones: las ventas bajo promoción activa (dependencia futura de
`005-promociones-inteligentes`) no reflejan demanda a precio normal y deben poder excluirse o
marcarse al construir la serie. (4) Sustitutos —el de menor profundidad—: la demanda de un producto
puede subir porque su sustituto se agotó, no porque haya más demanda real de ese producto; se
modela solo permitiendo declarar manualmente una relación de sustitución entre dos productos y
señalar el efecto, sin inferencia automática ni cuantificación estadística de la canibalización.
Este módulo consulta, sin reimplementar, la existencia y los movimientos de inventario, las
consultas no atendidas y las observaciones de precio de competencia de `001`, y la marca de
promoción activa de `005`; posee las series de demanda observada y corregida, el pronóstico y la
tabla de sustitución. La generación del pronóstico es consultiva: el sistema propone; la persona
decide cuánto pedir o exhibir (Principio V de la constitución).

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-05

- Q: ¿Qué método usa el sistema para cuantificar la demanda latente durante un quiebre de stock
  (FR-009)? → A: Dos niveles, no un solo estimador. **(a) Método base**: sustituir la demanda del
  período censurado por el máximo de demanda observada del mismo producto y sucursal entre los N
  períodos más recientes sin quiebre (N es un parámetro razonable, ≈30 días, documentado en
  Assumptions) — aritmética simple, derivable a mano, sin estimadores de máxima verosimilitud ni
  supuestos de distribución. **(b) Ajuste cruzado cuando aplica**: si el producto tiene un sustituto
  declarado (`sustitucion_producto`, User Story 6) y ese sustituto registró un alza de demanda
  durante la ventana de quiebre del producto original, esa alza se usa como señal adicional para
  ajustar el estimado del método base **al alza**, complementándolo, nunca reemplazándolo. Mantiene
  el cálculo derivable a mano y conecta la descensura con User Story 6 en vez de tratar la censura
  de forma aislada de las demás fuentes de contaminación.
- Q: ¿Con qué horizonte y granularidad se emite el pronóstico (FR-019)? → A: Granularidad diaria y
  dos horizontes con propósitos distintos: **corto (7 a 14 días)** para decisiones de reposición y
  **medio (30 días)** para detectar patrones simples de estacionalidad intramensual relevantes en un
  minimarket de barrio (por ejemplo, picos asociados a fechas de pago de sueldo o quincena),
  mediante comparación de promedios por tramo del mes. Alcance deliberadamente acotado: NO se modela
  estacionalidad anual ni festiva ni descomposición estacional formal.
- Q: ¿Qué familia de método de pronóstico se usa (FR-020)? → A: Suavizado exponencial simple sobre
  la serie ya corregida por censura — no promedio móvil plano, no ARIMA, Prophet ni métodos de
  aprendizaje automático. Pondera los períodos recientes sobre los antiguos con un único parámetro α
  explicable y ajustable; la fórmula completa es derivable en una línea sin depender de una
  librería estadística. Más completo que un promedio móvil simple, pero defendible sin apoyo de
  código que el autor no pueda explicar. La línea base determinista de respaldo (FR-022) sigue
  siendo el promedio móvil de la demanda observada sin corregir.

## User Scenarios & Testing *(mandatory)*

<!-- Historias ordenadas por dependencia real, no por número de fuente de contaminación. La
descensura por quiebre de stock va primero por ser la corrección base sobre la que operan las
demás; la validación con datos sintéticos va segunda porque es el único camino para verificar esa
corrección mientras la dependencia de `001` (`consulta_no_atendida`) siga sin implementarse. -->

### User Story 1 - Descensurar la demanda por quiebre de stock (Priority: P1)

El analista del negocio consulta, para un producto y una sucursal, una serie histórica de demanda
en la que los períodos en que el producto estuvo agotado ya no subestiman la demanda: el sistema
identifica esos intervalos de existencia cero y estima la demanda latente que no llegó a
registrarse como venta, produciendo una serie de demanda corregida mayor o igual a la observada en
esos períodos, nunca menor. Es la corrección más central del módulo y la base de todas las demás.

**Why this priority**: sin esta corrección, todo pronóstico que se apoye en la demanda histórica
hereda el sesgo del agotamiento y pedirá sistemáticamente de menos, que es exactamente el problema
que este módulo existe para resolver. Las correcciones por precio, promoción y sustitutos se
aplican encima de la serie ya descensurada por quiebre; construirlas antes obligaría a rehacerlas
sobre la base corregida.

**Independent Test**: para un producto con un intervalo histórico conocido de existencia cero,
se puede verificar que la serie de demanda corregida sube en ese intervalo respecto de la observada,
que la corrección es explicable (dice de qué valor observado partió, qué intervalo consideró y si se
apoyó en consultas no atendidas o en interpolación) y que los períodos sin quiebre no se alteran.

**Acceptance Scenarios**:

1. **Given** un producto con ventas registradas y un intervalo de tres días con existencia cero en
   una sucursal, **When** se construye su demanda corregida, **Then** el valor corregido de esos
   días es mayor o igual al observado y nunca menor, y conserva el valor observado de partida.
2. **Given** ese mismo intervalo de quiebre con registros de `consulta_no_atendida` de `001` para el
   producto y la sucursal, **When** se descensura, **Then** el sistema usa ese conteo de demanda no
   atendida como evidencia directa de la magnitud de la demanda latente, y marca la corrección como
   respaldada por consultas no atendidas.
3. **Given** un intervalo de quiebre sin ningún registro de `consulta_no_atendida`, **When** se
   descensura, **Then** el sistema estima la demanda latente por interpolación desde períodos
   comparables sin quiebre y marca la corrección como estimación de menor confianza, distinta de una
   respaldada por consultas no atendidas.
4. **Given** un período sin ningún día de existencia cero, **When** se construye la demanda
   corregida, **Then** el sistema no aplica corrección por quiebre a ese período: la demanda
   observada se conserva sin cambios por este eje.
5. **Given** un producto que estuvo agotado durante todo el histórico disponible y sin consultas no
   atendidas, **When** se intenta descensurar, **Then** el sistema marca la demanda como "no
   estimable por censura total" en vez de devolver un cero o un valor inventado.

---

### User Story 2 - Validar la descensura contra datos sintéticos con demanda latente conocida (Priority: P2)

El equipo carga una serie histórica sintética —generada, no observada— en la que la demanda latente
real de cada período de quiebre es un dato conocido de antemano, y compara la demanda corregida que
produce el sistema contra ese valor verdadero para medir el error de la descensura. Es el único
camino para validar la lógica de User Story 1 mientras la parte de `001` que la alimenta con datos
reales (`consulta_no_atendida`) siga sin implementarse (ver Dependencias entre módulos).

**Why this priority**: la descensura de User Story 1 no es verificable contra datos reales todavía
—`consulta_no_atendida` está especificada en `001` pero no implementada— y una corrección que no se
puede validar no se puede desplegar (Principio V: con línea base, acotada). Los datos sintéticos con
demanda latente conocida desbloquean esa validación sin esperar a `001`. Va inmediatamente después
de User Story 1 porque sin ella esa historia queda sin prueba de fondo.

**Independent Test**: se genera una serie sintética con períodos de quiebre cuya demanda latente
verdadera está fijada, se corre la descensura del sistema y se verifica que el reporte de error
compara el valor corregido estimado contra el verdadero y que el error de descensurar es menor que
el error de no corregir nada (usar la demanda observada tal cual).

**Acceptance Scenarios**:

1. **Given** una serie sintética con demanda latente verdadera conocida en sus períodos de quiebre,
   **When** el sistema produce la demanda corregida, **Then** se puede consultar el error de
   descensura como la diferencia entre la demanda corregida estimada y la demanda verdadera de cada
   período.
2. **Given** esa serie sintética, **When** se compara el error de la demanda corregida contra el
   error de usar la demanda observada sin corregir, **Then** el error de la demanda corregida es
   menor: la descensura acerca la serie al valor verdadero, no la aleja.
3. **Given** una serie sintética con al menos un escenario de quiebre con `consulta_no_atendida`
   sintética y al menos uno sin ella, **When** se valida, **Then** ambos caminos de descensura
   (respaldado por consultas y por interpolación) quedan ejercidos y medidos por separado.
4. **Given** datos sintéticos cargados, **When** se consulta cualquier pronóstico de producción,
   **Then** los datos sintéticos están marcados como tales y no se mezclan con datos de demanda
   reales.

---

### User Story 3 - Generar el pronóstico de demanda a partir de la serie corregida (Priority: P3)

El encargado consulta, para un producto y una sucursal, un pronóstico de demanda para un horizonte
futuro, calculado sobre la serie de demanda corregida —no sobre la demanda observada cruda—, con los
factores que lo determinan, el período de datos histórico usado y el valor de la línea base
determinista contra la que se compara. El pronóstico es el insumo para decidir cuánto pedir y cuánto
exhibir; la decisión es de la persona, no del sistema.

**Why this priority**: es el propósito comercial del módulo, pero depende de que la serie ya esté
descensurada por quiebre (User Story 1) y de que esa corrección esté validada (User Story 2). Un
pronóstico sobre una serie sin corregir reproduce el sesgo de agotamiento; construirlo antes de las
dos primeras historias no tendría una base confiable sobre la que apoyarse.

**Independent Test**: para un producto con serie corregida y suficiente histórico, se puede generar
un pronóstico y verificar que es explicable a partir de sus insumos, que declara su línea base
determinista y su período de datos, y que un producto sin histórico suficiente se marca como "datos
insuficientes" en vez de recibir un número.

**Acceptance Scenarios**:

1. **Given** un producto con serie de demanda corregida y suficiente histórico en una sucursal,
   **When** el encargado pide un pronóstico, **Then** el sistema devuelve una proyección de demanda
   para el horizonte definido, acompañada de los factores que la determinan y del período de datos
   histórico usado.
2. **Given** un pronóstico generado, **When** el encargado lo revisa, **Then** ve el valor de la
   línea base determinista de respaldo (por ejemplo, el promedio móvil de la demanda observada sin
   corregir) junto al pronóstico, para poder juzgar si el modelo aporta sobre esa línea base.
3. **Given** un pronóstico que no supera a su línea base determinista, **When** se evalúa su
   despliegue, **Then** el sistema no lo presenta como pronóstico vigente: prevalece la línea base
   (Principio V).
4. **Given** un producto nuevo sin histórico suficiente, **When** el encargado pide un pronóstico,
   **Then** el sistema responde "sin pronóstico por datos insuficientes" en vez de un valor por
   defecto.
5. **Given** un pronóstico generado, **When** se consulta, **Then** el sistema no ha emitido ninguna
   orden de compra ni cambio de exhibición: el pronóstico es consultivo y la decisión de cuánto
   pedir o exhibir queda en la persona.

---

### User Story 4 - Corregir la serie por el precio vigente en cada período histórico (Priority: P4)

El analista consulta una serie de demanda corregida que, además de la descensura por quiebre,
separa el cambio de demanda atribuible a un cambio de precio del cambio de demanda base: cada
período histórico se normaliza hacia un precio de referencia usando el precio que realmente estuvo
vigente en esa sucursal en ese período (precio base o su override de `001`).

**Why this priority**: es la segunda contaminación en importancia después del quiebre, pero se
aplica encima de la serie ya descensurada; sin la corrección de precio, un pronóstico confunde "la
demanda bajó" con "subimos el precio". Depende de la serie base de User Story 1 y del pronóstico de
User Story 3 para ser demostrable como mejora medible.

**Independent Test**: para un producto con al menos un cambio de precio documentado en su histórico,
se puede verificar que la serie corregida atribuye parte de la variación de demanda al precio y no a
la demanda base, y que la corrección es explicable (qué precios, qué períodos, qué factor).

**Acceptance Scenarios**:

1. **Given** un producto cuyo precio vigente en una sucursal subió a la mitad del histórico,
   **When** se construye la demanda corregida, **Then** los períodos previos y posteriores al cambio
   se normalizan al mismo precio de referencia y la corrección registra qué precio aplicó a cada
   tramo.
2. **Given** un producto con un override de precio por sucursal (`001`, FR-050), **When** se corrige
   su serie para esa sucursal, **Then** el eje de precio usa el precio que realmente aplicó ahí (el
   override), no el precio base global.
3. **Given** un período histórico para el que `001` no conserva el precio vigente de ese tramo,
   **When** se corrige la serie, **Then** ese período se marca como "sin corrección de precio" en
   vez de asumir un precio retroactivo.
4. **Given** una corrección de precio aplicada, **When** se revisa, **Then** es explicable: indica
   qué precios, qué períodos y qué factor o elasticidad se usó.

---

### User Story 5 - Neutralizar los períodos con promoción activa (Priority: P5)

El analista construye una serie de demanda a precio normal excluyendo o marcando los períodos en
que el producto estuvo bajo una promoción activa, de modo que las ventas promocionales no inflen la
demanda base que alimenta el pronóstico. La fuente de qué períodos tuvieron promoción activa es
`005-promociones-inteligentes` cuando exista.

**Why this priority**: una promoción distorsiona la demanda de forma parecida a un cambio de precio,
pero su calendario es propiedad de `005`, que todavía no existe. La corrección se especifica ahora y
su gancho de integración queda documentado; hasta que `005` exista, todos los períodos se tratan
como sin promoción. Depende de la serie base y va después de la corrección de precio por ser el
mismo tipo de distorsión con una dependencia externa aún no disponible.

**Independent Test**: con una marca de "promoción activa" provista manualmente para un período
(simulando la futura entrada de `005`), se puede verificar que ese período queda excluido o marcado
en la demanda corregida, que sigue visible sin cambios en la demanda observada, y que la exclusión
queda registrada.

**Acceptance Scenarios**:

1. **Given** un producto con un período marcado como de promoción activa, **When** se construye la
   demanda corregida, **Then** ese período se excluye o se marca de forma que no infle la demanda a
   precio normal, y la demanda observada de ese período se conserva intacta.
2. **Given** un período promocional excluido, **When** se revisa la serie corregida, **Then** la
   exclusión queda registrada con su motivo, y no como un hueco silencioso en la serie.
3. **Given** que `005-promociones-inteligentes` todavía no está implementado, **When** se construye
   cualquier serie corregida, **Then** el sistema trata todos los períodos como sin promoción y el
   gancho de integración con `005` queda documentado, no oculto.

---

### User Story 6 - Declarar sustitutos y señalar demanda inflada por quiebre de un sustituto (Priority: P6)

El encargado declara manualmente que un producto puede sustituir a otro, y el sistema señala —como
marca cualitativa para revisión, no como ajuste numérico— los períodos en que un producto muestra
demanda por encima de su nivel típico mientras un sustituto declarado suyo estuvo agotado en la
misma sucursal y período. Es la contaminación de menor profundidad del módulo: se declara la
relación y se señala el efecto, sin inferirlo ni cuantificarlo estadísticamente.

**Why this priority**: es un efecto real —la demanda de un producto sube porque su sustituto se
agotó, no porque haya más demanda real de él— pero su tratamiento profundo (inferir relaciones,
cuantificar canibalización) es un proyecto en sí mismo que el enunciado no exige. El alcance mínimo
defendible es una tabla simple de sustitución y una señal. Va última porque depende de la detección
de quiebres de User Story 1 y aporta el refinamiento marginal más pequeño.

**Independent Test**: se declara una relación de sustitución entre dos productos, se produce un
período en que uno tuvo quiebre y el otro vendió por encima de su nivel típico, y se verifica que el
sistema emite una señal explicable (qué producto se agotó, qué relación declarada la conecta, qué
período) sin descontar ningún volumen automáticamente.

**Acceptance Scenarios**:

1. **Given** dos productos sin relación declarada, **When** el encargado declara que uno sustituye
   al otro, **Then** la relación queda guardada con su instante y es consultable después.
2. **Given** una relación de sustitución declarada y un período en que el producto sustituido tuvo
   quiebre de stock mientras el sustituto vendió por encima de su nivel típico en la misma sucursal,
   **When** se revisa la serie del sustituto, **Then** ese período aparece señalado como demanda
   potencialmente inflada por sustitución.
3. **Given** esa señal, **When** se revisa, **Then** el sistema no ha descontado ningún volumen de
   la demanda del sustituto ni ha cuantificado la canibalización: la señal es una marca para
   revisión humana.
4. **Given** un período en que el producto sustituido y su sustituto estuvieron ambos agotados,
   **When** se evalúa la señal, **Then** no se emite: sin trasvase observable no hay efecto que
   señalar.

---

### User Story 7 - Visualizar la demanda pronosticada vs. la histórica censurada (Priority: P7)

El encargado, al abrir la vista de Pronóstico de un producto, ve una línea de tiempo con dos
series superpuestas: la **demanda observada** día a día (el dato crudo, con sus quiebres) y la
**demanda corregida y pronosticada** (la serie descensurada por los cuatro ejes más el horizonte
de pronóstico que la continúa). Así puede juzgar de un vistazo cuánto corrigió el método y hacia
dónde proyecta, en vez de leer dos tablas de números.

**Why this priority**: es una lectura pura sobre datos que User Stories 1–5 ya producen
(`demanda_observada`, `demanda_corregida`) y sobre el `serie_pronosticada` de User Story 3. No
escribe ningún dato ni cambia ningún contrato; es aditiva y no reabre el checkpoint de las
historias previas.

**Independent Test**: para un producto con historial de demanda y al menos un intervalo de
quiebre corregido, se abre la vista de Pronóstico y se verifica que el gráfico muestra la serie
observada y, encima, la serie corregida (más alta en los períodos de quiebre) y que la línea
corregida se prolonga con el horizonte de pronóstico cuando este es vigente.

**Acceptance Scenarios**:

1. **Given** un producto con serie de demanda observada y corregida, **When** el encargado abre
   la vista de Pronóstico, **Then** ve un gráfico de líneas con "Demanda observada" en Tinta y
   "Corregida / pronosticada" en el color Estimado, y la tabla de la proyección sigue debajo.
2. **Given** un pronóstico vigente, **When** se renderiza el gráfico, **Then** la línea estimada
   se prolonga sobre el horizonte de días futuros, sin línea observada en ese tramo (no hay dato
   futuro que dibujar).
3. **Given** un producto sin ninguna venta registrada todavía, **When** se abre su vista de
   Pronóstico, **Then** el gráfico muestra un estado vacío que explica qué aparecerá ahí, nunca
   un lienzo en blanco.

---

### Edge Cases

- **Censura total del histórico**: un producto agotado durante todo el histórico disponible y sin
  consultas no atendidas no tiene ningún período sin quiebre del que tomar el máximo de referencia
  del método base (FR-009); su demanda latente no es estimable y se marca "no estimable por censura
  total", nunca un cero (ver Acceptance Scenario 5 de User Story 1).
- **Quiebre y promoción en el mismo período**: se aplican en el orden que fija Assumptions —quiebre
  primero sobre la serie base, luego precio, luego promoción, luego señal de sustitución—, porque la
  descensura por quiebre es la base sobre la que operan las demás correcciones.
- **`consulta_no_atendida` sobre un producto con saldo positivo**: `001` permite registrarla (ver
  Edge Cases de `001`); este módulo no la cuenta como evidencia de censura por agotamiento —se trata
  como un producto que estaba pero no se localizó, no como demanda latente por quiebre.
- **Cambio de precio a mitad de un período**: el período tiene dos precios vigentes; la demanda se
  atribuye al precio vigente durante más días del período, con el más reciente como desempate (ver
  Assumptions); refinable en `plan.md`.
- **Sustituto que también tuvo quiebre en el mismo período**: la señal de sustitución no se emite
  (ambos agotados, sin trasvase observable).
- **Relación de sustitución mutua o circular** (A sustituye a B y B sustituye a A): permitida; la
  señal se evalúa por dirección según cuál de los dos tuvo el quiebre en el período.
- **Histórico muy corto** (comercio recién digitalizado): el pronóstico se marca "datos
  insuficientes"; la descensura puede correr pero se marca como de baja confianza.
- **Producto nuevo sin histórico ni sustituto declarado**: queda fuera de los límites del modelo, y
  ese límite se documenta antes de implementar (Principio V: acotada).
- **Sucursales con historiales dispares para el mismo producto**: cada serie, corrección y
  pronóstico se calcula y se consulta por sucursal; agregar varias sucursales sin discriminar el
  origen está PROHIBIDO (ver FR-037).

## Requirements *(mandatory)*

### Functional Requirements

**Serie de demanda observada**

- **FR-001**: El sistema DEBE construir `demanda_observada` por producto, sucursal y período,
  agregando las ventas registradas en `venta` y `renglon_venta` de `001`. El período base es diario
  (ver Assumptions); la agregación a períodos mayores para el pronóstico se decide en `plan.md`.
- **FR-002**: Cada período de `demanda_observada` DEBE registrar si el producto tuvo quiebre de
  stock durante el período y con qué extensión (días o fracción de existencia cero), consultando
  `existencia` y `movimiento_inventario` de `001` sin sobrescribirlos ni recalcularlos.
- **FR-003**: Cada período DEBE registrar el precio vigente del producto en esa sucursal durante el
  período (precio base o su override, `producto_precio_sucursal` de `001`) y si hubo promoción
  activa (marca provista por `005` cuando exista; ver Dependencias entre módulos).
- **FR-004**: `demanda_observada` es un registro de hechos y NO DEBE modificarse retroactivamente
  cuando cambian los datos de origen; toda corrección vive en `demanda_corregida`, no aquí.

**Descensura por quiebre de stock**

- **FR-005**: El sistema DEBE identificar, por producto y sucursal, los intervalos históricos en que
  la existencia fue cero, a partir de `movimiento_inventario` y `existencia` de `001`.
- **FR-006**: Para cada intervalo de quiebre, el sistema DEBE estimar la demanda latente no
  observada y producir un valor de `demanda_corregida` mayor o igual al observado en ese período,
  nunca menor.
- **FR-007**: Cuando exista registro de `consulta_no_atendida` de `001` (FR-020/FR-021 de `001`)
  para el producto, la sucursal y el intervalo, el sistema DEBE usar ese conteo de demanda no
  atendida como evidencia directa de la magnitud de la demanda latente, en lugar de estimarla sólo
  con el método base de FR-009.
- **FR-008**: Cuando NO exista `consulta_no_atendida` para el intervalo, el sistema DEBE estimar la
  demanda latente aplicando el método base de FR-009 y DEBE marcar ese valor como estimación,
  explícitamente distinta de una respaldada por consultas no atendidas.
- **FR-009**: El sistema DEBE cuantificar la demanda latente de un período censurado por quiebre en
  dos niveles, que son la forma concreta de la estimación genérica de FR-008:
  - **(a) Método base**: sustituir la demanda del período censurado por el máximo de demanda
    observada del mismo producto y sucursal entre los N períodos más recientes sin quiebre (N es un
    parámetro documentado en Assumptions). El cálculo DEBE ser aritmética simple, derivable a mano,
    sin estimadores de máxima verosimilitud ni supuestos de distribución.
  - **(b) Ajuste cruzado cuando aplica**: si el producto tiene un sustituto declarado
    (`sustitucion_producto`, User Story 6) y ese sustituto registró un alza de demanda durante la
    ventana de quiebre del producto original, el sistema DEBE usar esa alza como señal adicional
    para ajustar el estimado del método base **al alza**, complementándolo, nunca reemplazándolo.
  El nivel (b) sólo se aplica cuando existe la relación de sustitución de User Story 6; su ausencia
  no bloquea el nivel (a). Ver Clarifications (Session 2026-09-05) y Assumptions.
- **FR-010**: Cada valor de `demanda_corregida` por quiebre DEBE conservar: el valor observado de
  partida, el intervalo de quiebre considerado, si la corrección se apoyó en consultas no atendidas
  o sólo en el método base de FR-009, si se aplicó el ajuste cruzado por sustituto (FR-009 b), y el
  factor de corrección aplicado (Principio V: explicable).
- **FR-011**: El sistema NO DEBE aplicar corrección por quiebre a un período sin existencia cero
  registrada; por ese eje, demanda observada es igual a demanda real en esos períodos.
- **FR-012**: Cuando un producto no tenga ningún período sin quiebre del cual tomar el máximo de
  referencia del método base (FR-009) y tampoco tenga consultas no atendidas, el sistema DEBE marcar
  su demanda como "no estimable por censura total", sin sustituirla por cero ni por un valor
  supuesto.

**Validación con datos sintéticos**

- **FR-013**: El sistema DEBE poder cargar una serie histórica sintética de demanda en la que la
  demanda latente verdadera de cada período de quiebre es un dato conocido (generado, no observado).
- **FR-014**: El sistema DEBE permitir comparar la `demanda_corregida` que produce contra la demanda
  latente verdadera de la serie sintética y reportar el error de descensura por período.
- **FR-015**: El sistema DEBE permitir verificar que, sobre la serie sintética, el error de la
  demanda corregida es menor que el error de usar la demanda observada sin corregir.
- **FR-016**: La serie sintética DEBE incluir períodos con quiebre y sin quiebre, y al menos un
  escenario de quiebre con `consulta_no_atendida` sintética y uno sin ella, para ejercer y medir por
  separado los caminos de FR-007 y FR-008.
- **FR-017**: Los datos sintéticos DEBEN estar marcados como tales y NO DEBEN mezclarse con datos de
  demanda reales en ninguna consulta de pronóstico de producción. No pertenecen al juego de datos
  "Despensa Los Ríos" ni se cargan en el entorno de producción.

**Pronóstico**

- **FR-018**: El sistema DEBE generar un `pronostico` de demanda por producto, sucursal y horizonte,
  derivado de `demanda_corregida` y NO de `demanda_observada` cruda.
- **FR-019**: El pronóstico DEBE producirse con **granularidad diaria** y en **dos horizontes** con
  propósitos distintos:
  - **Horizonte corto (7 a 14 días)**: para decisiones de reposición.
  - **Horizonte medio (30 días)**: para detectar patrones simples de estacionalidad intramensual
    (por ejemplo, picos asociados a fechas de pago de sueldo o quincena), mediante comparación de
    promedios por tramo del mes. NO se modela estacionalidad anual ni festiva ni descomposición
    estacional formal (ver Assumptions).
- **FR-020**: El método de pronóstico DEBE ser **suavizado exponencial simple** sobre la serie ya
  corregida por censura (FR-018) — no promedio móvil plano, no ARIMA, Prophet ni métodos de
  aprendizaje automático. Pondera los períodos recientes sobre los antiguos con un único parámetro α
  explicable y ajustable; la fórmula completa DEBE ser derivable en una línea sin depender de una
  librería estadística. El valor de α y su calibración inicial se deciden en `plan.md`.
- **FR-021**: Cada `pronostico` DEBE acompañarse de los factores que lo determinan, el período de
  datos histórico usado y el valor de la línea base determinista contra la que se compara (Principio
  V: explicable, con línea base).
- **FR-022**: El sistema DEBE declarar una línea base determinista de respaldo (por ejemplo, el
  promedio móvil de la demanda observada sin corregir) y NO DEBE presentar como vigente un
  pronóstico que no supere esa línea base (Principio V).
- **FR-023**: Para un producto sin histórico suficiente, el sistema DEBE responder "sin pronóstico
  por datos insuficientes", nunca un valor por defecto (Principio V: acotada).
- **FR-024**: El sistema NO DEBE emitir órdenes de compra ni cambios de exhibición de forma
  automática a partir del pronóstico; el pronóstico es consultivo y la decisión de cuánto pedir o
  exhibir es de la persona (Principio V: consultiva por defecto).

**Eje de precio**

- **FR-025**: El sistema DEBE normalizar la serie hacia una `demanda_corregida` a un precio de
  referencia, separando el cambio de demanda atribuible a un cambio de precio del cambio de demanda
  base, usando el precio vigente por período de FR-003.
- **FR-026**: La corrección de precio DEBE resolverse contra el precio que realmente aplicó en la
  sucursal (precio base o su override, FR-050 de `001`), nunca contra un precio global cuando existe
  un override.
- **FR-027**: Cuando la serie histórica no permita reconstruir el precio vigente de un período
  (`001` no conserva histórico de precio para ese tramo), el sistema DEBE marcar ese período como
  "sin corrección de precio" en vez de asumir un precio retroactivo.
- **FR-028**: El efecto de precio estimado DEBE ser explicable: qué precios, qué períodos y qué
  factor o elasticidad se aplicó (Principio V).

**Eje de promoción**

- **FR-029**: El sistema DEBE poder excluir o marcar los períodos con promoción activa al construir
  `demanda_corregida`, de modo que la demanda a precio normal no quede inflada por ventas
  promocionales.
- **FR-030**: La identificación de qué períodos tuvieron promoción activa DEBE provenir de
  `005-promociones-inteligentes` cuando exista; hasta entonces, el sistema DEBE tratar todos los
  períodos como sin promoción y dejar el gancho de integración documentado (ver Dependencias entre
  módulos).
- **FR-031**: Un período marcado como promocional y excluido DEBE seguir visible sin cambios en
  `demanda_observada` (no se borra el hecho), y su exclusión DEBE quedar registrada en
  `demanda_corregida` con su motivo, no como un hueco silencioso.

**Eje de sustitutos (menor profundidad)**

- **FR-032**: El sistema DEBE permitir declarar manualmente una relación de sustitución entre dos
  productos (`sustitucion_producto`), sin inferirla automáticamente a partir de correlación de
  ventas ni de ningún otro dato.
- **FR-033**: Cuando un producto tuvo quiebre de stock en un período y otro producto declarado como
  su sustituto muestra demanda observada por encima de su nivel típico en la misma sucursal y
  período, el sistema DEBE señalar esa demanda como potencialmente inflada por sustitución.
- **FR-034**: El sistema NO DEBE cuantificar con precisión estadística el efecto de canibalización
  ni descontar automáticamente ningún volumen de la demanda del sustituto; la señal de FR-033 es una
  marca cualitativa para revisión humana, no un ajuste numérico (alcance mínimo defendible).
- **FR-035**: La señal de sustitución DEBE ser explicable: qué producto tuvo quiebre, qué relación
  de sustitución declarada la conecta y en qué período (Principio V).
- **FR-036**: La señal de FR-033 NO DEBE emitirse cuando el producto sustituido y su sustituto
  estuvieron ambos agotados en el mismo período: sin trasvase observable no hay efecto que señalar.

**Fronteras de propiedad de datos**

- **FR-037**: Toda serie, corrección y pronóstico DEBE identificarse por sucursal; agregar demanda
  de varias sucursales sin discriminar la de origen está PROHIBIDO (Principio IV y restricción
  multi-sucursal de la constitución).
- **FR-038**: El sistema NO DEBE registrar, modificar ni recalcular `existencia`,
  `movimiento_inventario`, `lote`, `venta`, `renglon_venta`, `consulta_no_atendida`,
  `observacion_precio`, `canal_competencia` ni `producto_precio_sucursal`; todas son propiedad de
  `001` y este módulo solo las consulta.
- **FR-039**: El sistema NO DEBE crear ni gestionar campañas ni envíos promocionales; son propiedad
  de `005`. Este módulo solo consume la marca de "período con promoción activa".
- **FR-040**: `demanda_observada`, `demanda_corregida`, `pronostico` y `sustitucion_producto` son
  propiedad de este módulo. `sustitucion_producto` fue añadida a la tabla de Propiedad de Datos de
  la constitución por la enmienda **v2.2.4** (antes de este `/speckit-plan`), a raíz de FR-032,
  User Story 6 y FR-009 (b) — ver Dependencias entre módulos y plan.md.

**Visualización (User Story 7)**

- **FR-041**: El sistema DEBE ofrecer, en la vista de Pronóstico de un producto, un gráfico de
  líneas con dos series a lo largo del tiempo: "Demanda observada" (el valor de
  `demanda_observada` por período) y "Demanda corregida / pronosticada" (el valor de
  `demanda_corregida` por período, prolongado por `pronostico.serie_pronosticada` cuando el
  pronóstico es vigente). No reemplaza la tabla de la proyección.
- **FR-042**: La serie observada usa el color Tinta (dato); la serie corregida/pronosticada usa
  el color Estimado (#1F5673, valor calculado), consistente con La Regla de los Tres Portadores
  del módulo. NO DEBE usar el color de marca ni una paleta decorativa.
- **FR-043**: El gráfico es puramente de lectura: NO calcula ni escribe ningún dato nuevo. Un
  producto sin serie de demanda muestra un estado vacío explicativo, nunca un lienzo en blanco.

### Key Entities *(include if feature involves data)*

- **demanda_observada**: serie histórica de demanda tal como se registró —ventas agregadas por
  producto, sucursal y período— sin ninguna corrección. Por período marca si hubo quiebre de stock
  y su extensión, el precio vigente y si hubo promoción activa. Es un registro de hechos, no se
  recalcula retroactivamente. Propiedad de este módulo.
- **demanda_corregida**: serie derivada de `demanda_observada` tras aplicar, en orden, las
  correcciones por quiebre de stock (User Story 1), precio (User Story 4), promoción (User Story 5)
  y la señal de sustitución (User Story 6). Cada valor corregido conserva el valor observado de
  partida y qué correcciones se aplicaron, con qué factor y con qué respaldo (consultas no atendidas
  o método base de FR-009, con o sin ajuste cruzado por sustituto), para ser explicable (Principio
  V). Propiedad de este módulo.
- **pronostico**: proyección de demanda futura por producto, sucursal y horizonte, derivada de
  `demanda_corregida`, con los factores que la determinan, el período de datos histórico usado y el
  valor de la línea base determinista contra la que se compara. Un producto sin histórico suficiente
  no recibe valor: se marca "datos insuficientes". Propiedad de este módulo.
- **sustitucion_producto**: relación declarada manualmente entre un producto y otro que puede
  sustituirlo; tabla simple con dos referencias a `producto` (el sustituido y el sustituto) y el
  instante de la declaración. No se infiere automáticamente ni cuantifica el efecto de
  canibalización. Propiedad de este módulo — añadida a la tabla de Propiedad de Datos de la
  constitución por la enmienda **v2.2.4** (ver Dependencias entre módulos).

Entidades de `001` que este módulo consulta pero no posee (frontera de propiedad de datos):
`producto`, `sucursal`, `producto_precio_sucursal` (precio y override), `existencia`,
`movimiento_inventario`, `lote`, `venta`, `renglon_venta`, `consulta_no_atendida`,
`observacion_precio`, `canal_competencia`. Entidad de `005` que este módulo consumirá cuando exista:
la marca de "promoción activa" por producto, sucursal y período (derivada de `campania`).

## Dependencias entre módulos

Esta sección es de lectura obligatoria antes de `/speckit-plan`: fija qué se puede construir ahora y
qué queda bloqueado, y no debe quedar oculta en `plan.md`.

**Lo que este módulo consulta y no reimplementa** (mismo patrón que `003-precios-margenes` frente a
`001`):

- De `001-core-ventas-inventario`: `existencia` y `movimiento_inventario` (para detectar intervalos
  de existencia cero), `consulta_no_atendida` (para la magnitud de la demanda latente por quiebre),
  `venta` y `renglon_venta` (para la serie observada), `producto_precio_sucursal` y el precio
  vigente (para el eje de precio), `observacion_precio` y `canal_competencia` (contexto de precio de
  competencia), `producto`, `lote` y `sucursal`.
- De `005-promociones-inteligentes` (futuro): la marca de "período con promoción activa" por
  producto y sucursal.

**Lo que este módulo posee**: `demanda_observada`, `demanda_corregida`, `pronostico` y
`sustitucion_producto`. Las cuatro figuran en la tabla de Propiedad de Datos de la constitución
para `004`: las tres primeras desde la ratificación; `sustitucion_producto` desde la enmienda
**v2.2.4** (2026-09-05), del mismo tipo que la v2.2.3 que añadió `sugerencia_precio` a `003` —
escrita al arrancar el `/speckit-plan` de este módulo, tras verificar que la entrada de 004 no
tenía ninguna otra inconsistencia. Escribir y aprobar este spec no requería la enmienda;
implementar `sustitucion_producto`, sí, y ya está resuelta.

**BLOQUEO explícito de implementación (no oculto)**:

- `consulta_no_atendida` está **especificada** en `001-core-ventas-inventario` (User Story 3,
  FR-020 y FR-021) pero **no implementada**: sus tareas T050–T053 en `001/tasks.md` siguen
  pendientes, y el último checkpoint del proyecto solo cubre `001` Setup + Foundational + User Story
  1.
- En consecuencia, la parte de la User Story 1 que se apoya en datos **reales** de demanda no
  atendida (FR-007) queda **bloqueada** hasta que `001` implemente esa User Story 3. Por
  transitividad, la validación de la descensura contra datos reales y el pronóstico de producción
  sobre series reales también esperan.
- La descensura puede implementarse **parcialmente** sin ese bloqueo: detectar intervalos de
  existencia cero (FR-005) y estimar demanda latente por interpolación (FR-008) sólo requiere
  `existencia` y `movimiento_inventario`, ya disponibles. Lo que `consulta_no_atendida` aporta y la
  interpolación no es la **magnitud observada** de la demanda no atendida; sin ella la descensura es
  de menor fidelidad, y así debe marcarse (FR-008, FR-010).
- Este spec se puede **escribir y aprobar ahora**. La User Story 2 (datos sintéticos con demanda
  latente conocida) existe precisamente para no bloquear la validación de la lógica de descensura
  mientras dure el bloqueo de `001`: es la ruta de verificación que no depende de datos reales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para el 100% de los períodos históricos con quiebre de stock registrado, la demanda
  corregida es mayor o igual a la observada, y la diferencia es explicable a partir del registro
  (consultas no atendidas, o método base de FR-009 con o sin ajuste cruzado por sustituto).
- **SC-002**: Sobre la serie sintética con demanda latente conocida, el error medio de la demanda
  corregida frente al valor verdadero es menor que el error de usar la demanda observada sin
  corregir, en los escenarios con y sin `consulta_no_atendida` sintética.
- **SC-003**: El 100% de los pronósticos generados declara sus factores, su período de datos
  histórico y el valor de su línea base determinista; ninguno se presenta sin esa información.
- **SC-004**: Ningún pronóstico que no supere su línea base determinista queda presentado como
  vigente (0%).
- **SC-005**: Ningún producto sin histórico suficiente recibe un valor de pronóstico numérico: en el
  100% de esos casos se marca "datos insuficientes".
- **SC-006**: El 100% de las correcciones por quiebre, precio, promoción y sustitución sobre un
  período quedan registradas de forma que se puede reconstruir la serie observada original y cada
  ajuste aplicado.
- **SC-007**: Ninguna operación de este módulo modifica existencia, movimientos, precio, ventas,
  consultas no atendidas o campañas (0% de escrituras sobre datos de `001` o `005`).
- **SC-008**: El sistema no emite ninguna orden de compra ni cambio de exhibición automático a
  partir del pronóstico (0% de acciones automáticas).
- **SC-009**: Toda serie y todo pronóstico se puede filtrar por sucursal, y ninguna vista agrega
  varias sucursales sin discriminar la de origen.

## Assumptions

- **Período base de la serie**: diario, en línea con la granularidad diaria del pronóstico (FR-019).
  Es el mínimo que permite ubicar un quiebre de stock con precisión de día, que es la resolución de
  `movimiento_inventario` de `001`.
- **Definición de "quiebre de stock" de un período**: con el período base diario (bullet anterior),
  un día cuenta como censurado **sólo si el producto estuvo sin existencia el día COMPLETO** —el
  saldo reconstruido desde `movimiento_inventario` de `001` se mantuvo en cero o negativo durante
  todo el día—, no si se agotó a media jornada. Un saldo positivo pero bajo tampoco cuenta.
  **Razón**: la granularidad ya fijada es diaria (FR-019); representar un quiebre parcial ("estuvo
  agotado 6 de las 10 horas de venta") exigiría una unidad de tiempo más fina que el día, que está
  fuera del alcance de esta versión. Es una decisión conservadora a propósito: sólo se descensura lo
  que el spec llama "no tuvo existencia durante X días", nunca un día que aún pudo vender parte de
  la jornada. En el código esta regla es la constante nombrada `SALDO_MAXIMO_EN_QUIEBRE`
  (`dominio/serie_demanda.py`), con la misma razón anotada allí; se documenta también aquí para no
  depender de esa nota durante la revisión.
- **Demanda observada neta de anulaciones**: la demanda observada de un período es la salida de
  mercancía **neta** — `salida_venta` menos `entrada_anulacion` del mismo producto, sucursal y día
  local. **Razón**: una venta anulada no es demanda satisfecha; la mercancía volvió al lote, así
  que no debe contar como una unidad demandada. Esta decisión no estaba en el borrador del spec y se
  tomó durante la implementación de User Story 1; tratar la anulación como demanda real "que existió
  aunque se revirtió" sería una enmienda de este spec, no una decisión libre de implementación.
- **Precio de referencia del eje de precio**: el precio vigente actual del producto en la sucursal;
  el pronóstico responde a "cuánta demanda esperar al precio de hoy". Ajustable en `plan.md` sin
  volver a este spec.
- **Período con varios precios vigentes**: la demanda se atribuye al precio vigente durante más días
  del período, con el más reciente como desempate. Refinable en `plan.md`.
- **Orden de aplicación de correcciones** sobre la serie: (1) quiebre de stock, (2) precio, (3)
  promoción, (4) señal de sustitución — el mismo orden que la prioridad de las user stories, porque
  la descensura por quiebre es la base sobre la que operan las demás.
- **Descensura sin `consulta_no_atendida`**: se hace con el método base de FR-009 (máximo de la
  demanda observada del producto entre los N períodos recientes sin quiebre) y se marca
  explícitamente como estimación de menor confianza que una respaldada por consultas no atendidas
  (FR-008).
- **Ventana N del método base de FR-009**: el punto de partida es N ≈ 30 días (los 30 períodos
  diarios más recientes sin quiebre del mismo producto y sucursal). El valor exacto de N es un
  parámetro que se fija y calibra en `plan.md`; queda dentro del método ya decidido, no lo cambia.
- **Alcance acotado del pronóstico**: el horizonte medio (30 días, FR-019) sólo compara promedios
  por tramo del mes para captar picos intramensuales simples (quincena, pago de sueldo). NO se
  modela estacionalidad anual, festiva ni de temporada, ni se aplica descomposición estacional
  formal; ampliarlo es una evolución futura de este módulo, no un requisito de esta versión.
- **Parámetro α del suavizado exponencial (FR-020)**: el factor de suavizado y su calibración
  inicial se deciden en `plan.md`. La familia de método (suavizado exponencial simple sobre la serie
  corregida) ya está fijada y no se reabre en `plan.md`.
- **Datos sintéticos de la User Story 2**: son un artefacto de validación, no un juego de datos de
  demostración. No pertenecen a "Despensa Los Ríos" ni se cargan en el entorno de producción
  (constitución: separación herramienta/datos).
- **Relación de sustitución**: es una declaración manual del encargado, no inferida por el sistema a
  partir de correlación de ventas; una versión futura podría sugerirla, fuera del alcance de este
  spec (mismo criterio que la asignación manual de `rol_producto` en `003`).
- **Eje de promoción parcialmente inerte hasta `005`**: el gancho de integración se especifica ahora
  (FR-029 a FR-031); la fuente de la marca "promoción activa" llega cuando `005` exista. Hasta
  entonces todos los períodos se tratan como sin promoción.
- **Histórico de precio incompleto**: si `001` no conserva el precio vigente de un tramo, ese tramo
  va sin corrección de precio; no se inventa un precio retroactivo (FR-027).
- **Umbrales y ventanas concretos** (qué es "nivel típico" de un sustituto, cuánto histórico es
  "suficiente" para pronosticar, el valor exacto de N y de α) son decisiones de `plan.md` dentro de
  los métodos ya fijados en Clarifications; no reabren esas decisiones.
- **Constitución vigente citada**: v2.3.0. La enmienda que esta funcionalidad motivó es la v2.2.4
  (añade `sustitucion_producto` a la tabla de Propiedad de Datos de 004; ver plan.md y research.md
  #2); v2.2.5 (`005`), v2.2.6 (`007`) y v2.3.0 (Principio VI, "Autorización y Roles", sobre el
  esquema de `operador` de `001`) son posteriores y sin efecto sobre este módulo.
- **Decisiones de alcance mayor resueltas en Clarifications (Session 2026-09-05)**: FR-009 (método
  de cuantificación de la censura: base por máximo de N períodos recientes + ajuste cruzado por
  sustituto), FR-019 (granularidad diaria, horizontes corto de 7–14 días y medio de 30 días) y
  FR-020 (suavizado exponencial simple sobre la serie corregida). Ninguna quedó con default
  silencioso; ajustarlas en el futuro es una enmienda de este spec, no una decisión libre de
  `plan.md`.
