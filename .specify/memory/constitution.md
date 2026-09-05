<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.2 → 2.2.3
Tipo de cambio: PARCHE — corrige la propiedad de datos de
`003-precios-margenes`, detectada al escribir su `data-model.md` en
`/speckit-plan`. Mismo tipo de corrección que v2.1.1/v2.1.2 sobre 001: la
tabla original era un supuesto anterior a la especificación real del módulo,
y esta enmienda la reemplaza por lo que su spec y su diseño de datos
realmente exigen. No cambia ningún principio.

Principios modificados: ninguno.
Secciones añadidas: ninguna.
Secciones eliminadas: ninguna.

Secciones modificadas:
  - Propiedad de Datos y Nomenclatura, entrada de `003-precios-margenes`:
      * Se retira `costo_producto` de la lista de entidades propias de 003.
        Contradecía la frontera ya declarada dos líneas más abajo en la
        misma sección ("el costo del producto es dato de compra y pertenece
        a 001; el margen es cálculo derivado... y pertenece a 003") y el
        patrón ya implementado en 002 (`margen_resolver.py` lee
        `lote.costo_unitario` de 001 sin poseerlo, documentado en su
        research.md #2). `003` consulta el costo vigente vía `lote` y
        `existencia` de 001; no necesita ni debe mantener una tabla de costo
        propia.
      * Se añade `sugerencia_precio` a la lista de entidades propias de 003.
        `003-precios-margenes/spec.md` (FR-008, FR-013, FR-014) exige
        generar una sugerencia de precio con registro de los insumos que la
        originaron y, al aplicarla, dejar registro de qué sugerencia creó o
        modificó el override de precio por sucursal — lo mismo que la
        entidad hermana `sugerencia_colocacion`, ya presente en la lista
        original, hace para colocación. No estaba en la ratificación
        original porque esa lista se escribió antes de que existiera el
        spec de 003.
    Lista resultante de 003: `margen_calculado`, `rol_producto`,
    `sugerencia_precio`, `sugerencia_colocacion` (4 entidades, mismo conteo
    que antes; cambia la composición, no el tamaño).

Decisiones de alcance vigentes (sin cambio en 2.2.3):
  - `sucursal` es entidad de primera clase con cardinalidad no acotada; el
    alcance del examen cubre exactamente dos sucursales (Quevedo Centro y
    Buena Fe, del juego de datos Despensa Los Ríos).
  - La constitución fija un conjunto cerrado de decisiones técnicas (motor de
    datos, nomenclatura, tipografía y paleta); el resto se decide por
    funcionalidad en plan.md.
  - Las seis lecturas críticas del enunciado son sección propia, no un sexto
    principio.
  - Rigor de pruebas: pragmático y proporcional al riesgo (sin TDD estricto).
  - Reconciliación: no se exige estrategia de fusión más allá del desempate
    por marca de tiempo.
  - Propiedad de datos de 001-core-ventas-inventario: 20 entidades vigentes
    desde v2.1.2.
  - Puerta de sincronización de enmiendas (v2.2.0).

Historial de versiones:
  - 1.0.0 (2026-09-04) — ratificación inicial, 5 principios.
  - 1.0.1 (2026-09-04) — traducción completa al español y alcance multi-sucursal.
  - 2.0.0 (2026-09-04) — identidad Rasero; redefinición de los Principios I y IV;
    propiedad de datos, nomenclatura, sistema de diseño e infraestructura.
  - 2.0.1 (2026-09-04) — nombre del comercio de demostración y su prohibición
    como identificador técnico.
  - 2.0.2 (2026-09-04) — implementación mínima de reconciliación offline.
  - 2.1.0 (2026-09-04) — propiedad de datos corregida a partir de la
    especificación de 001.
  - 2.1.1 (2026-09-04) — `conteo_renglon` añadida a 001.
  - 2.1.2 (2026-09-04) — `producto_precio_sucursal` añadida a 001.
  - 2.2.0 (2026-09-04) — puerta de sincronización de enmiendas.
  - 2.2.1 (2026-09-04) — nombre del comando de Impeccable corregido de `teach`
    a `init`, tras verificar la herramienta instalada.
  - 2.2.2 (2026-09-04) — los tres pasos reales de Impeccable (init / new-work /
    documenter) documentados por separado; tercera corrección consecutiva
    sobre el mecanismo de la misma herramienta.
  - 2.2.3 (2026-09-05) — esta enmienda: propiedad de datos de
    `003-precios-margenes` corregida a partir de su especificación real
    (`costo_producto` retirado, `sugerencia_precio` añadida), detectada al
    escribir `data-model.md` de 003 en `/speckit-plan`.

Artefactos de funcionalidad afectados: las citas de versión vigente en
spec.md, plan.md y data-model.md de 001 y de 002 se sincronizan a v2.2.3 en
este mismo cambio (puerta de sincronización de enmiendas, v2.2.0);
`003-precios-margenes` nace directamente citando v2.2.3, no requiere
sincronización retroactiva.

TODOs pendientes: ninguno.
-->

# Constitución de Rasero

Rasero es una plataforma de retail inteligente: punto de venta, gestión de inventario,
márgenes, previsión de demanda y fidelización para comercio físico multi-sucursal. Esta
constitución define las reglas no negociables que gobiernan cómo se especifica, diseña,
construye y revisa el producto.

## Identidad del Proyecto

Un rasero es la tabla que se pasa sobre una medida de grano para nivelarla al ras. De ahí
viene "medir con el mismo rasero", y de ahí viene la tesis del sistema: aplicar un mismo
criterio objetivo a productos y clientes que hoy el dueño juzga por impresión. Ese criterio
es explícito y siempre el mismo —margen real, demanda corregida por censura, valor de
cliente por frecuencia y margen— y toda funcionalidad DEBE poder explicar sus salidas en
esos términos.

El nombre del sistema es independiente del nombre del comercio ficticio usado en los datos
de demostración. Rasero es una herramienta genérica; NO está construida para un comercio
específico, y ninguna regla de negocio particular de un comercio de ejemplo puede quedar
codificada en el modelo, el esquema o la interfaz.

El comercio ficticio de los datos de demostración es **Despensa Los Ríos**, con dos
sucursales: **Quevedo Centro** y **Buena Fe**. Ese nombre pertenece exclusivamente a los
datos de prueba y a los scripts de carga inicial, y vive únicamente como valor de fila.
Usarlo en nombres de tabla, esquemas, endpoints, componentes de interfaz, espacios de
nombres, ramas, variables o cualquier otro identificador técnico está PROHIBIDO. Rasero es
el sistema; Despensa Los Ríos es un juego de datos. Mezclarlos en el código ata la
herramienta a su propio ejemplo y contradice el párrafo anterior.

## Principios Fundamentales

### I. Dominio Primero, Contratos Explícitos

El modelo de dominio del retail —producto, existencia, precio, venta, devolución, caja,
sucursal— DEBE definirse antes que cualquier decisión de framework, biblioteca o
infraestructura. Cada funcionalidad DEBE declarar en su especificación las entidades que
toca y el contrato observable que expone (endpoint, comando, evento o vista) antes de
escribir código de implementación.

La constitución fija un conjunto cerrado y enumerado de decisiones técnicas, y solo ese: el
motor de datos y su configuración de desarrollo (ver "Infraestructura de datos"), la
convención de nomenclatura de datos, y la tipografía y paleta del sistema de diseño. Todo
lo demás —lenguaje, framework de aplicación, capa de acceso a datos, empaquetado— se decide
por funcionalidad en `plan.md` y DEBE justificarse frente a los requisitos del dominio, no
frente a la familiaridad del equipo. Introducir una segunda tecnología que cumple la misma
función que una ya presente en el proyecto está PROHIBIDO salvo justificación registrada en
la sección de complejidad del plan.

**Razón**: en retail el dominio sobrevive a los frameworks. Un modelo de existencias mal
definido corrompe inventario, arqueos y previsiones durante años; un framework se sustituye.
Las pocas decisiones que sí se fijan aquí lo están porque su cambio invalidaría datos ya
capturados (precisión numérica) o rompería la coherencia visual del conjunto.

### II. Fiabilidad Operativa en el Punto de Venta

Una caja no puede detenerse. Todo flujo que participe en una venta DEBE cumplir:

- **Degradación, nunca bloqueo**: si un servicio de inteligencia, red o reporte no responde,
  la venta se completa igualmente con el comportamiento base determinista. Ninguna función
  de IA, analítica o telemetría puede ser camino crítico de un cobro.
- **Idempotencia obligatoria**: toda operación que altera inventario, dinero o documentos
  fiscales DEBE aceptar una clave de idempotencia y producir el mismo resultado ante
  reintentos. Los reintentos duplicados NO pueden generar ventas, cargos ni movimientos
  de existencias duplicados.
- **Reconciliación explícita**: las operaciones ejecutadas sin conectividad DEBEN encolarse
  con marca de tiempo de origen y resolverse mediante una regla de conflicto documentada en
  la especificación de la funcionalidad. Descartar silenciosamente una operación encolada
  está PROHIBIDO.

  La implementación mínima exigida de esta regla es la siguiente, y es propiedad de
  `001-core-ventas-inventario`:

  - Toda operación ejecutada sin conectividad se persiste localmente con estado
    `pendiente_de_sincronizar` y su marca de tiempo de origen.
  - Al recuperar conectividad, las operaciones pendientes se envían al servidor en orden de
    marca de tiempo de origen.
  - La regla de conflicto por defecto es **gana la marca de tiempo más antigua sobre el mismo
    recurso**: prevalece la operación que ocurrió primero en el mundo físico, no la que llegó
    primero al servidor.
  - La operación desplazada por un conflicto se marca como `conflicto_resuelto` con
    referencia a la operación que prevaleció, y permanece visible para revisión humana.
    Eliminarla u ocultarla está PROHIBIDO.

  No se exige resolución automática más allá de esta regla de desempate. Una estrategia de
  fusión más sofisticada es mejora futura, no requisito de entrega; implementarla sin
  necesidad demostrada es complejidad que DEBE justificarse en el plan.

**Razón**: el coste de un fallo en caja es una fila de clientes y dinero descuadrado, no un
error en un registro técnico. La fiabilidad es requisito funcional, no atributo de calidad.

### III. Pruebas Proporcionales al Riesgo

Las pruebas son OBLIGATORIAS donde el error cuesta dinero o corrompe datos; en el resto son
una decisión de ingeniería. No se exige TDD estricto ni un umbral global de cobertura.

DEBEN existir pruebas automatizadas, y estar en verde antes de fusionar, para:

- Cálculo monetario, impuestos, descuentos, redondeo y totales.
- Toda transición de estado de inventario y de documentos de venta o devolución.
- Todo contrato público (API, evento, esquema persistido) en su forma feliz y en sus modos
  de fallo declarados.
- Toda corrección de defecto: la prueba de regresión DEBE fallar antes del arreglo y pasar
  después. Un arreglo sin esa prueba no se fusiona.

Para interfaz de usuario, maquetación y código exploratorio, las pruebas son opcionales y su
ausencia NO bloquea la revisión. Añadir pruebas que solo replican la implementación está
desaconsejado.

**Razón**: exigir cobertura uniforme produce suites caras que nadie mantiene; concentrar el
esfuerzo en dinero, existencias y contratos protege lo que realmente no puede fallar.

### IV. Trazabilidad de Cada Transacción

Toda operación que mueva dinero o existencias DEBE dejar un rastro reconstruible: qué pasó,
cuándo, en qué sucursal y caja, iniciada por qué operador o proceso, y con qué resultado.

- Los registros DEBEN ser estructurados y consultables por identificador de venta, de
  producto y de sucursal. El filtro por sucursal es obligatorio con independencia de cuántas
  sucursales haya desplegadas; agregar sin discriminar la sucursal de origen está PROHIBIDO.
- El estado de inventario DEBE poder reconstruirse a partir de sus movimientos; sobrescribir
  una cantidad sin registrar el movimiento que la origina está PROHIBIDO.
- **Traspaso entre sucursales**: todo traspaso de inventario entre sucursales DEBE
  registrarse como dos asientos enlazados —salida en la sucursal de origen y entrada en la
  de destino— referidos ambos a una misma operación de traspaso identificable. Registrarlo
  como dos ajustes de inventario independientes, sin referencia común entre ellos, está
  PROHIBIDO. La existencia total del sistema DEBE ser reconstruible en cualquier instante,
  incluido el intervalo en que un traspaso está en curso: la mercancía en tránsito pertenece
  a la operación de traspaso y no desaparece del inventario total mientras viaja.
- Los mensajes de error expuestos al operador DEBEN indicar la acción correctiva; volcar
  trazas técnicas en la interfaz de caja está PROHIBIDO.
- Los rastros NO DEBEN contener datos de pago completos ni datos personales más allá del
  identificador mínimo necesario.

**Razón**: un arqueo que no cuadra se resuelve con historia, no con conjeturas. Sin rastro
reconstruible, cada discrepancia se convierte en una investigación manual. Dos ajustes
sueltos hacen que la mercancía en tránsito se evapore del recuento total, y ese hueco es
indistinguible de una merma o de un robo.

### V. Inteligencia Explicable y Reversible

Las funciones "inteligentes" —previsión de demanda, sugerencia de reposición, precios
dinámicos, detección de anomalías— están sujetas a restricciones adicionales:

- **Explicable**: cada salida DEBE ir acompañada de los factores que la determinan y del
  periodo de datos usado. Una recomendación que el encargado de tienda no puede justificar
  ante su gerente no se despliega.
- **Consultiva por defecto**: la inteligencia propone; la persona decide. Cualquier acción
  automática sobre inventario o precio requiere aprobación explícita registrada en la
  especificación de la funcionalidad, y DEBE ser reversible con una operación de deshacer.
- **Con línea base**: toda funcionalidad predictiva DEBE declarar su alternativa determinista
  de respaldo y medirse contra ella. Si no supera la línea base, no se despliega.
- **Acotada**: los límites del modelo (datos mínimos, estacionalidad no cubierta, productos
  nuevos sin histórico) DEBEN documentarse en la especificación antes de la implementación.
- **Visible**: la explicabilidad se ejerce en la interfaz, no solo en la documentación. El
  sistema de diseño es parte de este principio y sus reglas —distinción entre dato observado
  y valor estimado, portadores redundantes de incertidumbre— son de cumplimiento obligatorio.
  Ver la sección "Sistema de Diseño".

**Razón**: una previsión errónea que compra de más inmoviliza capital real. La inteligencia
solo aporta valor si es auditable y se puede revertir, y una explicación que el operador no
puede leer en pantalla no es una explicación.

## Lecturas Críticas del Enunciado

El caso de negocio provisto por el docente se implementa con criterio, no al pie de la letra.
Las siguientes seis lecturas son decisiones de análisis ya tomadas: DEBEN mantenerse
documentadas y cualquier especificación que las contradiga DEBE justificar por qué. Se
registran como sección propia y no como principio porque son análisis del caso, no reglas
de ingeniería de aplicación general.

1. **El arqueo horario no detecta el fraude que parece detectar.** "Cobrar 5, registrar 3"
   NO produce descuadre de caja: si el cajero se queda la diferencia, el efectivo físico
   coincide con lo registrado y no hay nada que un arqueo pueda encontrar. Ese fraude se
   detecta por otras señales —discrepancia entre salida de inventario y venta registrada,
   tasa de anulaciones por cajero, concentración de ventas bajo precio de lista en un turno—
   y esas señales DEBEN implementarse. El arqueo horario sí detecta un fraude distinto
   (retiro de efectivo sin registrar venta) y se implementa para ese caso, no para aquel.

2. **El precio depende del rol del producto, no de una regla única.** Bajar el precio de los
   productos más vendidos (gancho de tráfico) y subirlo en los de nicho (generador de margen)
   no contradice "decidir por margen y no por volumen": son dos roles distintos. El rol del
   producto DEBE modelarse de forma explícita; sin él, las recomendaciones del propio sistema
   se contradicen entre sí.

3. **La colocación física es parte de la decisión de precio.** El producto de mayor margen va
   a zona de exhibición privilegiada y el de menor margen a zona relegada. La salida del
   módulo de precios y márgenes DEBE incluir sugerencia de zona, no solo de precio.

4. **Hay venta perdida antes de que exista transacción.** Un cliente que no entra porque el
   comercio no acepta su medio de pago preferido no aparece en ningún registro de ventas,
   porque no hay transacción que registrar. Se trata como métrica de cobertura de medios de
   pago por sucursal, no como venta perdida en el sentido de faltante de inventario.

5. **El umbral de inactividad no puede ser global.** Treinta días sin comprar pueden ser
   abandono para un cliente y comportamiento normal para otro. El modelo DEBE derivar un
   intervalo de compra esperado por cliente individual; aplicar un umbral uniforme de fuga a
   toda la base de clientes está PROHIBIDO.

6. **Las promociones son tres mecanismos, no uno.** Implementarlas como un mecanismo único
   está PROHIBIDO. Son:
   - **Cupón por fecha fija** (cumpleaños): regla simple, sin inferencia.
   - **Empuje por patrón de recompra detectado**, con reserva del producto: regla de patrón.
   - **Descuento de reactivación a cliente inactivo**: el único que exige medir el efecto
     incremental real contra un grupo de control —si el cliente habría vuelto igualmente, el
     descuento destruye el margen que pretendía proteger. El grupo de control es obligatorio
     para este tipo, y su ausencia invalida cualquier afirmación sobre la eficacia de la
     campaña.

## Propiedad de Datos y Nomenclatura

Cada entidad del modelo pertenece a exactamente una funcionalidad. Las demás la consultan;
NO la redefinen, NO la duplican y NO alteran su esquema. Un cambio de esquema sobre una
entidad ajena DEBE hacerse en la funcionalidad propietaria. Esta tabla es de referencia
obligatoria y se mantiene actualizada conforme evolucionan los `data-model.md` de cada
funcionalidad; si un `data-model.md` y esta tabla discrepan, prevalece esta tabla hasta que
una enmienda la corrija.

- **001-core-ventas-inventario**: `sucursal`, `producto`, `producto_precio_sucursal`, `categoria`,
  `zona_exhibicion`, `lote`, `existencia`, `movimiento_inventario`, `traspaso`, `venta`,
  `renglon_venta`, `anulacion_venta`, `consulta_no_atendida`, `observacion_precio`,
  `canal_competencia`, `conteo_fisico`, `conteo_renglon`, `operador`, `turno`,
  `operacion_pendiente`.
- **002-clientes-fidelizacion**: `cliente`, `visita`, `intervalo_compra`, `senal_fuga`.
- **003-precios-margenes**: `margen_calculado`, `rol_producto`, `sugerencia_precio`,
  `sugerencia_colocacion`. (`costo_producto` retirado y `sugerencia_precio` añadida por la
  enmienda **v2.2.3**, a raíz de la especificación real de 003 — ver frontera de "costo" más
  abajo.)
- **004-pronostico-demanda**: `demanda_observada`, `demanda_corregida`, `pronostico`.
- **005-promociones-inteligentes**: `campania`, `envio_promocional`, `grupo_control`.
- **006-caja-mermas-fraude**: `arqueo`, `merma`, `anomalia_caja`.
- **007-pagos-seguridad**: `terminal_pago`, `medio_pago`, `cobertura_pago`,
  `bitacora_auditoria`.

Fronteras entre funcionalidades adyacentes, donde la propiedad es fácil de confundir:

- El **costo** del producto es dato de compra y pertenece a 001; el **margen** es cálculo
  derivado con reglas de negocio y pertenece a 003.
- La **fecha de caducidad** del lote vive en inventario (001); la **política de alerta** y la
  **contabilización de la pérdida** viven en mermas (006).
- El **conteo físico** y la **diferencia bruta** contra el saldo calculado pertenecen a inventario
  (001), que ejecuta el conteo y expone el descuadre sin interpretarlo; la **clasificación de la
  causa** de esa diferencia —merma, robo, error de registro— pertenece a 006, que no ejecuta
  conteos.
- La **detección** de riesgo de fuga pertenece a clientes (002); la **decisión** de ofrecer
  descuento de reactivación pertenece a promociones (005).
- `anomalia_caja` es propiedad de 006, pero se **calcula consultando** `movimiento_inventario`,
  `venta` y `anulacion_venta`, propiedad de 001. Eso es consulta entre funcionalidades, no
  redefinición, y no infringe la regla de propiedad. Es además la forma en que la Lectura Crítica
  n.º 1 exige detectar el fraude de "cobrar 5, registrar 3": cruzando salida de inventario contra
  venta registrada y tasa de anulaciones por operador, no buscando un descuadre de efectivo que ese
  fraude nunca produce.

**Convención de nomenclatura**: identificadores de datos en español, `snake_case`, sustantivo
en singular, sin prefijo de número de módulo. La letra "ñ" está PROHIBIDA en identificadores
—se translitera como "ni": `campania`, nunca `campaña`— por compatibilidad de codificación
entre clientes de base de datos. Las claves foráneas se nombran `id_` seguido del nombre de
la tabla referida (`id_sucursal`, `id_producto`).

## Sistema de Diseño

El diseño visual es el vehículo de la explicabilidad exigida por el Principio V, no un tema
estético aparte. Sus reglas son normativas.

**Dos registros visuales según contexto de uso**, nunca uno uniforme:

- **Operación** (punto de venta, inventario, arqueo): alta densidad de información, la tabla
  como elemento principal, sin tarjetas. Radio de borde 2px. La animación se permite
  únicamente como confirmación de una acción del usuario —registrar venta, confirmar cobro,
  marcar consulta no atendida—. La animación decorativa, o disparada por scroll o por hover
  pasivo, está PROHIBIDA en este registro.
- **Análisis** (márgenes, pronóstico, clientes, promociones): una decisión por bloque, aire
  visual, líneas de texto por debajo de 80 caracteres. Radio de borde 6px. Se admite un
  momento de animación deliberado por pantalla —por ejemplo, al revelar el detalle de un
  cliente en riesgo de fuga— para señalar que eso es una decisión y no un dato más.

Un momento orquestado y deliberado por pantalla es PREFERIBLE a efectos repetidos en cada
elemento. El hover en cada fila y el fade-in en cada tarjeta son la señal más reconocible de
interfaz genérica y están desaconsejados en todo el sistema.

**Paleta**, anclada en objetos del comercio físico. Los fondos oscuros y los degradados están
PROHIBIDOS:

| Rol | Valor |
|---|---|
| Superficie base | `#F1F4F1` |
| Superficie alta | `#FFFFFF` |
| Tinta | `#1B2621` |
| Tinta suave | `#5A6862` |
| Marca | `#0F5132` |
| Borde | `#D5DCD6` |

Los colores semánticos se reservan exclusivamente para su significado y su uso decorativo
está PROHIBIDO: atención `#9A5B08` (dato envejecido, stock bajo), crítico `#8E2A2A`
(caducado, anomalía), estimado `#1F5673` (valor calculado, no observado).

**Tipografía por registro**: IBM Plex Sans en operación, con cifras tabulares reales para que
las columnas de dinero y de peso alineen por dígito; Source Serif 4 en análisis. Inter como
tipografía por defecto está PROHIBIDA.

**Redundancia de portadores**: todo dato con antigüedad o incertidumbre DEBE mostrar tres
portadores simultáneos y nunca solo color: el color semántico, un indicador de forma (punto
lleno, medio o hueco) y la antigüedad en texto explícito ("hace 3 d"). Un portador único
falla ante daltonismo, impresión en blanco y negro o reflejo de pantalla.

**Herramienta de ejecución**: la implementación de estos tokens en código durante la fase de
frontend se hace con la skill/toolkit Impeccable (`github.com/pbakaus/impeccable`). La
herramienta EJECUTA las decisiones de esta sección; NO las toma por su cuenta. Opera en pasos
distintos, y confundirlos es lo que esta constitución ya erró tres veces:

- **`init`** captura verdad de producto en `PRODUCT.md` —usuarios, propósito, restricciones—.
  Tiene PROHIBIDO escribir `DESIGN.md` y PROHIBIDO recibir contenido visual: paleta,
  tipografía y radios no se le entregan aquí.
- **`new-work`** construye una superficie. Cuando el mundo visual ya está fijado —como lo está
  en esta sección— NO abre torneo de identidad: mantiene el sistema fijo y decide únicamente
  la composición de esa pantalla. Es el paso que recibe esta sección como mundo fijado.
- **El agente documenter** escribe `DESIGN.md` AL FINAL, derivándolo de la interfaz ya
  construida, no de las intenciones previas. `DESIGN.md` no existe antes de la primera
  pantalla.

Es OBLIGATORIO que el contenido de esta sección llegue a `new-work` como mundo fijado antes de
generar cualquier interfaz: omitirlo hace que la herramienta derive hacia sus valores por
defecto genéricos, que es exactamente el resultado que esta sección existe para evitar. Ningún
paso de Impeccable puede proponer paleta o tipografía alternativas: están decididas aquí.

## Restricciones Técnicas y de Datos

- **Modelo multi-sucursal**: `sucursal` es una entidad de primera clase del dominio, con
  cardinalidad no acotada. El esquema, las consultas y los contratos DEBEN admitir N
  sucursales sin cambios estructurales: toda existencia, venta, caja, arqueo y previsión
  se identifica por su sucursal. Codificar un número fijo de sucursales en esquemas,
  consultas, claves, índices o interfaces está PROHIBIDO. El alcance de implementación y
  demostración de este examen cubre exactamente dos sucursales; esa cifra es una
  restricción de entrega, nunca un supuesto del modelo.
- **Infraestructura de datos**: el motor es PostgreSQL. En desarrollo se ejecuta de forma
  nativa, no en contenedor, para no consumir recursos de máquina durante el trabajo activo, y
  escucha en el puerto **5442** en lugar del 5432 por defecto, para no colisionar con otros
  proyectos del curso instalados en la misma máquina. El empaquetado en Docker Compose con
  volumen nombrado se hace en la fase final del proyecto, no durante el desarrollo. El uso de
  SQLite está PROHIBIDO en toda fase: carece de tipo `NUMERIC` real y opera en coma flotante,
  lo que introduce error de redondeo en cálculos de dinero y de peso en gramos, y no
  reproduce el comportamiento de PostgreSQL contra el que se valida el sistema.
- **Tiempo**: los instantes DEBEN almacenarse en UTC y presentarse en la zona horaria de la
  sucursal a la que pertenece la operación. Las agregaciones de negocio (cierre de caja,
  ventas del día) DEBEN calcularse sobre el día local de esa sucursal, no sobre el día UTC.
  Un informe que abarque varias sucursales DEBE declarar qué criterio de día aplica.
- **Precisión monetaria**: los importes DEBEN representarse con tipos decimales de precisión
  fija o enteros en la unidad mínima de la moneda. El uso de coma flotante binaria para
  dinero está PROHIBIDO. Cada importe persistido DEBE llevar su moneda asociada. La misma
  regla aplica al peso en gramos de los productos a granel.
- **Datos de pago**: los datos completos de tarjeta NO se almacenan, registran ni transmiten
  por sistemas propios. La integración con pasarelas de pago DEBE delegar la captura del
  medio de pago y conservar únicamente identificadores y últimos dígitos.
- **Datos personales**: los datos de clientes se recogen solo cuando una funcionalidad
  declarada los requiere, con finalidad y periodo de retención documentados en su
  especificación.
- **Migraciones**: todo cambio de esquema persistido DEBE ser versionado, aplicarse mediante
  script reproducible y llevar un procedimiento de reversión documentado.
- **Configuración y secretos**: los secretos DEBEN inyectarse por entorno. Un secreto en el
  repositorio es un defecto bloqueante, y su rotación es obligatoria si llegó a fusionarse.

## Flujo de Desarrollo y Puertas de Calidad

- **Ciclo Spec Kit**: toda funcionalidad no trivial recorre `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. La especificación describe el
  comportamiento observable; las decisiones de implementación pertenecen al plan.
- **Puerta constitucional**: el `plan.md` DEBE completar su sección `Constitution Check`.
  Cualquier desviación se registra en la tabla de complejidad con su justificación y la
  alternativa más simple descartada. Una desviación no registrada bloquea la fusión.
- **Puerta de propiedad de datos**: toda especificación que introduzca o modifique una
  entidad DEBE contrastarla contra la tabla de "Propiedad de Datos y Nomenclatura". Definir
  una entidad ya propiedad de otra funcionalidad, o nombrarla fuera de la convención,
  bloquea la fusión.
- **Puerta de sincronización de enmiendas**: toda enmienda a esta constitución DEBE, en el
  mismo cambio, actualizar todas las referencias a ella que existan en los artefactos de las
  funcionalidades afectadas (`spec.md`, `plan.md`, `data-model.md`, `contracts/`,
  `checklists/`, `tasks.md`) — número de versión citado como vigente, listas y conteos de
  entidades, y cualquier nota que describa como pendiente o bloqueado algo que la enmienda
  resuelve. Dejar un artefacto citando como vigente una versión superada está PROHIBIDO. Una
  enmienda que no sincroniza sus artefactos no está completa, aunque `constitution.md` sea
  correcto en sí mismo. Excepción: una cita histórica —que describe qué enmienda introdujo
  qué regla, no que reclama ser el estado actual— NO se barre; permanece correcta de forma
  permanente. La puerta aplica únicamente a las referencias que afirman describir el estado
  vigente.
- **Revisión**: todo cambio se revisa antes de fusionar. La revisión DEBE verificar
  explícitamente el cumplimiento de los Principios II, III y IV cuando el cambio toca
  dinero, existencias o contratos públicos.
- **Puertas automáticas**: compilación, análisis estático y las pruebas exigidas por el
  Principio III DEBEN estar en verde. Fusionar con puertas en rojo está PROHIBIDO;
  deshabilitar una prueba requiere registrar el motivo y la fecha límite de reactivación.
- **Ámbito acotado**: un cambio que altera un contrato público y además refactoriza su
  implementación DEBE separarse en cambios distintos.
- **Despliegue**: cada versión desplegable DEBE ser identificable y poder revertirse sin
  intervención manual sobre los datos.

## Gobernanza

Esta constitución prevalece sobre cualquier otra práctica, convención o preferencia del
equipo. Ante conflicto entre este documento y una guía, plantilla o costumbre, prevalece
este documento.

**Enmiendas**: cualquier persona del equipo puede proponer una enmienda mediante un cambio
sobre este archivo que incluya la motivación, el impacto sobre funcionalidades en curso y,
si procede, el plan de migración. La enmienda requiere aprobación en revisión antes de
fusionarse. Los cambios en artefactos ya especificados o planificados se reconcilian en su
propia funcionalidad; ninguna enmienda reescribe retroactivamente trabajo ya entregado.

**Versionado**: esta constitución sigue versionado semántico.

- **MAYOR**: eliminación o redefinición incompatible de un principio o de la gobernanza.
- **MENOR**: nuevo principio o sección, o ampliación material de una guía existente.
- **PARCHE**: aclaraciones, redacción y correcciones sin cambio de significado.

**Cumplimiento**: la verificación ocurre en dos puntos. En `/speckit-plan`, mediante la
puerta `Constitution Check` antes de generar artefactos de diseño. En revisión de código,
antes de fusionar. Una violación detectada tras la fusión se registra como defecto y se
corrige o se convierte en enmienda; permanecer indefinidamente en incumplimiento tácito
está PROHIBIDO.

**Versión**: 2.2.2 | **Ratificada**: 2026-09-04 | **Última enmienda**: 2026-09-04
