# Feature Specification: Precios y Márgenes

**Feature Branch**: `003-precios-margenes` — se desarrolla sobre `master`; no se creó rama dedicada.

**Created**: 2026-09-05

**Status**: Draft

**Input**: Decidir y sugerir, para cada producto, el precio de venta (y su posible override por
sucursal, ya provisto como capacidad por `001-core-ventas-inventario`, FR-050) y la colocación en
zona de exhibición (ya catalogada por `001`, FR de `zona_exhibicion`), a partir del margen real del
producto y de su rol comercial (`rol_producto`: gancho de tráfico vs. generador de margen). El
precio de competencia se usa como insumo, siempre como observación fechada con canal y frescura
(ya registrada por `001`, FR-022 a FR-027) y nunca como atributo fijo del producto ni obtenida por
scraping. Esta funcionalidad decide la política de precio y colocación; no reimplementa la
capacidad de override por sucursal ni el catálogo de zonas ni el registro de observaciones de
competencia, que ya pertenecen a `001`.

> Nota de idioma: los encabezados de sección se conservan en inglés porque son la estructura
> literal de la plantilla de Spec Kit que leen los comandos posteriores. Todo el contenido va en
> español, conforme a la constitución del proyecto.

## Clarifications

### Session 2026-09-05

- Q: ¿Debe `resolver_margen_visita` de `002-clientes-fidelizacion` migrar a consumir el margen real
  que define este spec (FR-001), o debe su aproximación provisional quedar fija de forma permanente
  por ser suficiente para su propósito (ranking relativo de clientes, no precisión contable)? → A:
  Migra. `003` es la fuente canónica de la definición de margen (propiedad de datos ya establecida
  en su Key Entities); mantener dos fórmulas de margen en paralelo para el mismo concepto de negocio
  crea dos fuentes de verdad, indefendible frente a la pregunta de por qué el sistema calcula el
  margen de dos formas distintas. Se acepta como riesgo documentado, no como bloqueo, que si `003`
  evoluciona su definición de margen (por ejemplo, de margen bruto a margen neto con costeo de
  indirectos) el ranking de valor de cliente de `002` puede cambiar como efecto colateral de ese
  cambio — el acoplamiento es intencional y queda registrado en FR-022 y en Assumptions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calcular el margen real de un producto (Priority: P1)

El encargado abre la ficha de precios de un producto y ve su margen real — no una aproximación —
calculado a partir de su costo vigente y su precio actual, por sucursal cuando el precio difiere
por sucursal (FR-050 de `001`). Este margen real es la base de la que dependen tanto la sugerencia
de precio como la de colocación: sin él, ninguna de las dos decisiones tiene fundamento.

**Why this priority**: es el cimiento de todo lo demás. La sugerencia de precio, la de colocación y
la clasificación de rol de producto necesitan un margen confiable; construir cualquiera de ellas
antes tendría que inventar su propio número, exactamente el problema que esta funcionalidad existe
para resolver (incluyendo el reemplazo de la aproximación provisional de `002`).

**Independent Test**: para un producto con costo y precio conocidos, y para uno vendido a granel,
se puede verificar que el margen real mostrado coincide con el cálculo esperado, sin depender de
que exista todavía ninguna sugerencia de precio o colocación.

**Acceptance Scenarios**:

1. **Given** un producto con costo vigente de $6 y precio de $10 en una sucursal sin override,
   **When** el encargado consulta su margen real, **Then** el sistema muestra 40% de margen sobre
   el precio de venta.
2. **Given** el mismo producto con un override de precio de $9 declarado solo en Buena Fe,
   **When** el encargado consulta el margen real para Quevedo Centro y, por separado, para Buena
   Fe, **Then** cada sucursal muestra su propio margen, resuelto contra el precio que realmente
   aplica en ella.
3. **Given** un producto a granel cuyo costo y precio están expresados por kilogramo, **When** se
   calcula su margen real, **Then** el cálculo los usa directamente, sin convertir ninguno de los
   dos: ambos ya comparten la misma base de medida en `001` (ver Assumptions).
4. **Given** un producto sin ningún lote con existencia vigente (sin costo actual disponible),
   **When** el encargado consulta su margen real, **Then** el sistema indica explícitamente que no
   hay margen calculable por falta de costo, en vez de mostrar un cero o un valor inventado.

---

### User Story 2 - Clasificar el rol comercial de un producto (Priority: P2)

El encargado marca cada producto con su rol comercial: gancho de tráfico (atrae visitas aunque deje
poco margen) o generador de margen (deja el margen que sostiene el negocio). Este rol, junto con el
margen real, es el criterio que usan las sugerencias de precio y de colocación.

**Why this priority**: sin `rol_producto`, las sugerencias de precio y colocación no tienen forma de
distinguir "este producto vale la pena dejarlo barato para que la gente entre" de "este producto es
el que paga las cuentas" — es el segundo insumo indispensable, después del margen real.

**Independent Test**: se puede clasificar un producto y confirmar que la clasificación persiste y es
consultable, sin depender de que exista todavía ninguna sugerencia de precio o colocación para ese
producto.

**Acceptance Scenarios**:

1. **Given** un producto sin rol asignado, **When** el encargado lo marca como gancho de tráfico,
   **Then** el sistema guarda la clasificación y la refleja en cualquier consulta posterior del
   producto.
2. **Given** un producto ya clasificado como generador de margen, **When** el encargado cambia su
   clasificación a gancho de tráfico, **Then** el cambio se guarda con su instante, y las
   sugerencias de precio y colocación generadas después usan la nueva clasificación (las ya
   generadas no se recalculan retroactivamente).

---

### User Story 3 - Sugerir precio de venta usando margen, rol y competencia (Priority: P3)

El encargado abre la vista de precio sugerido de un producto, que combina su margen real, su rol
comercial y — cuando existe — la observación de precio de competencia más reciente y su frescura
(ya capturada por `001`). El sistema sugiere un precio (y, si aplica, un override por sucursal); el
encargado decide si lo aplica.

**Why this priority**: es el propósito comercial central del módulo, pero depende de que las dos
historias anteriores (margen real y rol de producto) ya existan — sin ellas la sugerencia no tendría
sobre qué apoyarse.

**Independent Test**: para un producto con margen real y rol ya definidos, se puede generar una
sugerencia de precio y verificar que es explicable a partir de esos insumos, con y sin observación
de competencia disponible.

**Acceptance Scenarios**:

1. **Given** un producto generador de margen sin ninguna observación de competencia registrada,
   **When** el encargado pide una sugerencia de precio, **Then** el sistema sugiere un precio
   apoyado solo en margen real y rol, y lo marca explícitamente como "sin referencia de
   competencia".
2. **Given** un producto gancho de tráfico con una observación de competencia capturada hace 2 días
   en un canal dado, **When** el encargado pide una sugerencia de precio, **Then** la sugerencia
   muestra esa observación como parte de su base, junto con su antigüedad (mismo patrón de color,
   forma y texto que usa `001` para la frescura, FR-024).
3. **Given** una sugerencia de precio generada, **When** el encargado la revisa, **Then** el sistema
   NO modifica el precio ni el override por sucursal por su cuenta — la aplicación exige una acción
   explícita del encargado.
4. **Given** un producto con override de precio ya declarado en una sucursal (FR-050 de `001`),
   **When** se genera una sugerencia para esa sucursal, **Then** la sugerencia se calcula contra el
   precio que realmente aplica ahí (el override), no contra el precio base global.
5. **Given** una sugerencia de precio que el encargado decide aplicar, **When** confirma la
   aplicación, **Then** el sistema crea o actualiza el override de precio por sucursal
   correspondiente y deja registro de qué sugerencia lo originó.

---

### User Story 4 - Sugerir colocación en zona de exhibición (Priority: P4)

El encargado consulta, para un producto, en qué zona de exhibición conviene colocarlo, a partir de
su rol comercial y su margen real, usando el catálogo de zonas (con su grado de privilegio) que ya
provee `001`.

**Why this priority**: es valioso pero depende de que el rol de producto y el margen real ya existan
como insumos confiables; es la extensión natural de la sugerencia de precio hacia una segunda
palanca comercial (dónde se exhibe, no solo a cuánto se vende).

**Independent Test**: para un producto con rol y margen ya definidos, se puede pedir una sugerencia
de colocación y verificar que referencia una zona existente del catálogo de `001`, con la
justificación de por qué esa zona.

**Acceptance Scenarios**:

1. **Given** un producto clasificado como gancho de tráfico, **When** el encargado pide una
   sugerencia de colocación, **Then** el sistema sugiere una zona de exhibición existente y explica
   la sugerencia en términos de su rol y margen.
2. **Given** una sugerencia de colocación, **When** el encargado la revisa, **Then** el sistema NO
   reubica el producto por su cuenta — la sugerencia queda disponible para que el encargado la
   ejecute físicamente cuando decida hacerlo.
3. **Given** un producto sin ninguna zona de exhibición catalogada todavía en la sucursal,
   **When** se pide una sugerencia de colocación, **Then** el sistema indica que no hay zonas
   disponibles para sugerir, en vez de sugerir una zona inexistente.

---

### Edge Cases

- ¿Qué pasa si se pide una sugerencia de precio o colocación para un producto sin `rol_producto`
  todavía asignado? El sistema lo señala explícitamente como "sin clasificar" en la sugerencia; no
  asume un rol por defecto en silencio (ver Assumptions para el valor de retorno exacto).
- ¿Qué pasa si el costo vigente de un producto es cero o negativo (dato de origen inconsistente)?
  El sistema NO oculta el problema calculando un margen de 100% o negativo sin más: la sugerencia se
  marca como no confiable y señala el dato de costo como causa.
- ¿Qué pasa con una observación de competencia de presentación no comparable (ya marcada como tal
  por `001`)? La sugerencia de precio la excluye de su base, igual que la comparación de `001` la
  excluye de la comparación normalizada.
- ¿Qué pasa si dos sugerencias de colocación distintas apuntan a la misma zona de exhibición para
  dos productos distintos? El sistema no arbitra el conflicto por su cuenta: ambas sugerencias se
  muestran, y la decisión de cuál producto ocupa la zona queda en el encargado.
- ¿Qué pasa si se aplica una sugerencia de precio y después cambia el costo del producto (nueva
  compra a otro costo)? La sugerencia ya aplicada no se recalcula retroactivamente; una nueva
  consulta de margen real y una nueva sugerencia sí reflejan el costo actualizado.

## Requirements *(mandatory)*

### Functional Requirements

**Margen real**

- **FR-001**: El sistema DEBE calcular el margen real de un producto como `(precio − costo) /
  precio`, resuelto contra el precio que aplica en la sucursal indicada (precio base o su override,
  FR-050 de `001`), nunca contra un precio global cuando existe un override.
- **FR-002**: El costo usado en el cálculo DEBE ser el costo vigente de la existencia disponible del
  producto en esa sucursal. Para un producto a granel (`producto.es_granel`), ese costo y el precio
  contra el que se compara ya están expresados en la misma base de medida en `001` (por kilogramo);
  el cálculo los usa tal cual, sin convertir ninguno de los dos (ver Assumptions).
- **FR-003**: Cuando un producto no tenga costo vigente disponible (sin existencia con lote), el
  sistema DEBE indicarlo explícitamente como margen no calculable, sin sustituirlo por cero ni por
  un valor supuesto.
- **FR-004**: Cuando el costo vigente sea cero o negativo, el sistema DEBE marcar el margen
  resultante como no confiable y señalar el dato de costo como causa, en lugar de mostrar un
  porcentaje sin advertencia.

**Rol de producto**

- **FR-005**: El sistema DEBE permitir clasificar cada producto con un `rol_producto` de dos
  valores: gancho de tráfico o generador de margen.
- **FR-006**: El sistema DEBE registrar el instante en que se asigna o cambia un `rol_producto`.
- **FR-007**: Un producto sin `rol_producto` asignado DEBE tratarse como "sin clasificar" en toda
  sugerencia que lo involucre, nunca asumir uno de los dos valores por defecto de forma silenciosa.

**Precio sugerido**

- **FR-008**: El sistema DEBE generar una sugerencia de precio por producto y sucursal, a partir del
  margen real (FR-001) y el `rol_producto` (FR-005), cuando ambos estén disponibles.
- **FR-009**: Cuando exista al menos una observación de precio de competencia vigente para el
  producto (registrada por `001`, FR-022 a FR-027), la sugerencia DEBE incorporarla como insumo
  adicional y mostrar su antigüedad con los mismos tres portadores que usa `001` (color, forma y
  texto, FR-024).
- **FR-010**: Cuando no exista ninguna observación de competencia para el producto, la sugerencia
  DEBE generarse igual, apoyada solo en margen real y rol, y marcarse explícitamente como "sin
  referencia de competencia".
- **FR-011**: Una observación de competencia marcada como no comparable (presentación no
  convertible, ya excluida por `001` de su comparación normalizada) NO DEBE usarse como base de una
  sugerencia de precio.
- **FR-012**: El sistema NO DEBE modificar el precio base ni ningún override de precio por sucursal
  de forma automática. Toda sugerencia de precio requiere una acción explícita del encargado para
  aplicarse.
- **FR-013**: Cuando el encargado aplique una sugerencia de precio, el sistema DEBE crear o
  actualizar el override de precio por sucursal correspondiente (capacidad ya provista por `001`,
  FR-050) y dejar registro de qué sugerencia lo originó.
- **FR-014**: El sistema DEBE dejar registro de los insumos usados para generar cada sugerencia de
  precio (margen real, rol de producto, y la observación de competencia usada si la hubo), de modo
  que la sugerencia sea explicable después de generada.

**Colocación sugerida**

- **FR-015**: El sistema DEBE generar una sugerencia de colocación en zona de exhibición por
  producto y sucursal, a partir del `rol_producto` y el margen real, usando exclusivamente zonas ya
  catalogadas por `001` para esa sucursal.
- **FR-016**: El sistema NO DEBE crear, modificar ni eliminar zonas de exhibición; esa capacidad
  pertenece a `001`.
- **FR-017**: El sistema NO DEBE reubicar físicamente ni registrar por su cuenta un producto en una
  zona; la sugerencia de colocación es una recomendación que el encargado ejecuta o descarta.
- **FR-018**: Cuando no exista ninguna zona de exhibición catalogada para la sucursal, el sistema
  DEBE indicarlo explícitamente en vez de sugerir una zona inexistente.
- **FR-019**: El sistema DEBE permitir que dos sugerencias de colocación distintas señalen la misma
  zona para productos distintos sin bloquear ninguna de las dos; la resolución del conflicto queda
  en el encargado.

**Frontera con precio de competencia (propiedad de `001`)**

- **FR-020**: El sistema NO DEBE registrar observaciones de precio de competencia ni el catálogo de
  canales; ambos son propiedad de `001` (FR-022 a FR-026) y este módulo solo los consulta.
- **FR-021**: El sistema NO DEBE obtener precios de competencia por scraping ni ningún mecanismo
  automatizado de captura externa; toda observación de competencia sigue siendo la que `001` recibe
  por carga manual o por archivo (FR-026).

**Integración con `002-clientes-fidelizacion`**

- **FR-022**: `resolver_margen_visita` de `002-clientes-fidelizacion` (`margen_resolver.py`,
  fórmula provisional documentada en research.md #2 de `002` a la espera de que `003` existiera)
  DEBE migrar a consumir la definición de margen real de este módulo (FR-001) en vez de mantener su
  fórmula propia. `003` es la fuente canónica de la definición de margen; mantener dos fórmulas en
  paralelo para el mismo concepto de negocio crearía dos fuentes de verdad. Esta migración es
  trabajo de implementación de `003` (afecta un archivo propiedad de `002`) y queda pendiente como
  tarea explícita al planificar esta funcionalidad — ver Assumptions para el riesgo de acoplamiento
  aceptado.

### Key Entities *(include if feature involves data)*

- **rol_producto**: clasificación comercial de un producto (gancho de tráfico o generador de
  margen), con el instante de su última asignación. Atributo nuevo de `producto`, propiedad de este
  módulo.
- **margen_calculado**: margen real de un producto resuelto para una sucursal, derivado del costo
  vigente y el precio que aplica ahí (base o su override). No es una tabla de hechos históricos como
  `visita.margen_relativo` de `002`: representa el margen actual, recalculable en cualquier momento.
- **sugerencia_precio**: recomendación de precio para un producto y sucursal, con los insumos que la
  originaron (margen real, rol de producto, observación de competencia usada si la hubo), su
  instante de generación, y si fue aplicada o no.
- **sugerencia_colocacion**: recomendación de zona de exhibición para un producto y sucursal, con los
  insumos que la originaron, su instante de generación, y si fue aplicada o no. Referencia una
  `zona_exhibicion` ya catalogada por `001`; no crea zonas nuevas.

Entidades de `001` que este módulo consulta pero no posee (frontera de propiedad de datos): `producto`
(atributo `es_granel`), `producto_precio_sucursal` (override, FR-050), `zona_exhibicion` (catálogo con
grado de privilegio), `lote` (costo vigente), `existencia`, `observacion_precio` y `canal_competencia`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para cualquier producto con costo y precio vigentes, el margen real mostrado coincide
  con `(precio − costo) / precio` resuelto para la sucursal consultada, en el 100% de los casos
  verificados.
- **SC-002**: El 100% de las sugerencias de precio y de colocación generadas son explicables después
  de generadas: cualquier persona puede reconstruir, a partir del registro, qué margen, qué rol de
  producto y (si aplica) qué observación de competencia las originó.
- **SC-003**: Ninguna sugerencia de precio o de colocación modifica el override de precio por
  sucursal, el precio base o la asignación física de un producto sin una acción explícita del
  encargado que la confirme (0% de aplicaciones automáticas).
- **SC-004**: Cuando existe una observación de competencia vigente para un producto, su antigüedad
  se refleja en la sugerencia de precio con los mismos tres portadores (color, forma, texto) en el
  100% de los casos, igual que exige `001` para su propia comparación de precios.
- **SC-005**: Un producto sin `rol_producto` asignado nunca aparece con una sugerencia que asuma un
  rol por defecto: en el 100% de esos casos la sugerencia se marca como "sin clasificar".

## Assumptions

- **Alcance de "margen real"**: se define como margen bruto sobre precio de venta —
  `(precio − costo) / precio`, la misma forma que ya usa la aproximación provisional de `002` — y no
  incorpora asignación de costos indirectos (renta, personal, mermas no vendidas). Ampliar el margen
  real para incluir costeo de indirectos es una evolución futura de este mismo módulo, no un
  requisito de esta primera versión: el enunciado no exige costeo de indirectos y no hay
  necesidad demostrada de esa complejidad todavía.
- **Costo vigente**: cuando un producto tiene varios lotes con existencia simultánea a distinto
  costo, el margen real usa el costo del lote que la política de salida de `001` consumiría primero
  (caducidad más próxima, entrada como desempate) como aproximación de "costo vigente"; no promedia
  costos entre lotes. Esta es una decisión de implementación razonable, no una que cambie el alcance
  del módulo, y puede refinarse en `plan.md` sin volver a este spec.
- **Sin conversión de unidades entre costo y precio (corrección detectada durante
  implementación, no en clarify)**: el borrador inicial de este spec asumía, por error, que el
  margen de un producto a granel necesitaba "la misma conversión gramos/kg que aplica `001`" al
  calcular costo y precio. Es falso: `lote.costo_unitario` y `producto.precio_vigente` (ambos de
  `001`) ya están expresados en la misma base de medida —por unidad, o por kilogramo si
  `producto.es_granel`— así que su cociente no requiere convertir nada. La confusión venía de
  `margen_relativo` de `002` (`margen_resolver.py`), que sí convierte, pero por una razón distinta
  y no comparable: ese cálculo multiplica `costo_unitario` (por kg) por
  `movimiento_inventario.cantidad` (en gramos, de una venta real) para obtener el costo total de
  esa venta — un margen de **transacción**, con una cantidad variable de por medio. El margen real
  de este módulo es un margen de **catálogo** (precio de lista contra costo vigente, sin cantidad
  vendida alguna): comparten el nombre "margen" y la forma del cociente, pero no el mismo cálculo,
  y el segundo nunca necesitó la conversión del primero. FR-001, FR-002 y el Acceptance Scenario 3
  de User Story 1 ya reflejan esta corrección.
- **Sugerir, no decidir por su cuenta**: en línea con lo que ya declara `001` para `zona_exhibicion`
  ("el módulo de precios y márgenes la usa para sugerir colocación") y con el patrón ya establecido
  para comparación de precios (FR-028 de `001`, "el sistema NO DEBE ajustar ningún precio de forma
  automática"), este módulo nunca aplica sus propias sugerencias: siempre requiere una acción
  explícita del encargado. "Decide" en la descripción de esta funcionalidad significa que el sistema
  calcula y propone un precio y una colocación concretos (no solo datos crudos), no que los aplique
  sin intervención humana.
- **Asignación de `rol_producto`**: la clasificación de un producto como gancho de tráfico o
  generador de margen es una decisión manual del encargado, no inferida automáticamente por el
  sistema a partir de historial de ventas. El sistema no impone un valor por defecto cuando falta
  (FR-007); una futura versión podría sugerir una clasificación inicial a partir de datos, pero esa
  capacidad no es parte de esta especificación.
- **Alcance por sucursal**: `rol_producto` es una clasificación por producto, no por sucursal —
  un producto es gancho de tráfico o generador de margen de forma consistente en toda la cadena,
  aunque su margen real y su precio sí puedan diferir por sucursal (igual que ya permite `001`,
  FR-050).
- **Dependencia de `001`**: este módulo requiere que `zona_exhibicion`, `producto_precio_sucursal`,
  `observacion_precio` y `canal_competencia` ya existan tal como los define `001`; no los
  reimplementa ni duplica sus columnas.
- **Acoplamiento aceptado con `002` (FR-022)**: al migrar `resolver_margen_visita` para consumir la
  definición de margen real de este módulo, `002-clientes-fidelizacion` queda acoplado a cómo `003`
  define ese margen. Si `003` evoluciona esa definición en una versión futura (por ejemplo, de
  margen bruto a margen neto con costeo de indirectos — ver la primera asunción de esta lista), el
  ranking de valor de cliente de `002` puede cambiar como efecto colateral, sin que `002` haya
  cambiado ningún requisito propio. Este acoplamiento es intencional: la alternativa —mantener dos
  fórmulas de margen independientes para el mismo concepto de negocio— es la que se descartó en
  Clarifications por crear dos fuentes de verdad. El riesgo queda registrado aquí para que `plan.md`
  y `data-model.md` de esta funcionalidad lo hagan explícito (por ejemplo, en una sección de
  "Dependencias entre módulos"), no para que quede oculto.
