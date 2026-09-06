---
name: Rasero
description: Punto de venta e inventario para comercio físico multi-sucursal
colors:
  superficie-base: "#F1F4F1"
  superficie-alta: "#FFFFFF"
  tinta: "#1B2621"
  tinta-suave: "#5A6862"
  marca: "#0F5132"
  borde: "#D5DCD6"
  atencion: "#9A5B08"
  critico: "#8E2A2A"
  estimado: "#1F5673"
typography:
  operacion:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontFeature: "tnum"
  analisis:
    fontFamily: "Source Serif 4, Georgia, serif"
rounded:
  operacion: "2px"
  analisis: "6px"
components:
  boton-cobro:
    backgroundColor: "{colors.marca}"
    textColor: "{colors.superficie-alta}"
    rounded: "{rounded.operacion}"
  tabla-operacion:
    backgroundColor: "{colors.superficie-alta}"
    textColor: "{colors.tinta}"
    typography: "{typography.operacion}"
    rounded: "{rounded.operacion}"
  chip-cliente-identificado:
    backgroundColor: "{colors.superficie-alta}"
    textColor: "{colors.tinta}"
    typography: "{typography.operacion}"
    rounded: "{rounded.operacion}"
  bloque-analisis:
    backgroundColor: "{colors.superficie-alta}"
    textColor: "{colors.tinta}"
    typography: "{typography.analisis}"
    rounded: "{rounded.analisis}"
  bloque-analisis-seleccionado:
    backgroundColor: "{colors.superficie-alta}"
    textColor: "{colors.tinta}"
    typography: "{typography.analisis}"
    rounded: "{rounded.analisis}"
---

# Design System: Rasero

## Overview

**Creative North Star: "El Rasero"**

Un rasero es la tabla que se pasa sobre una medida de grano para nivelarla al ras. Es el nombre
del sistema y también su forma: superficie plana, filo recto, todo medido contra la misma
referencia. El sistema no adorna el dato; lo nivela para que se pueda comparar. Donde otros
sistemas de interfaz añaden profundidad, brillo o movimiento para dar importancia, este resta,
porque cualquier capa extra es una oportunidad de falsear la medida.

El sistema tiene **dos registros, nunca uno uniforme**. **Operación** —punto de venta,
inventario, arqueo— es alta densidad: la tabla es el elemento principal, no hay tarjetas, y el
filo es de 2px. **Análisis** —márgenes, pronóstico, clientes, promociones— es lo contrario: una
decisión por bloque, aire visual, líneas de texto bajo 80 caracteres, filo de 6px. Un cajero y
un gerente no miran la misma clase de pantalla, y el sistema lo dice con la forma antes que con
el contenido.

La paleta está anclada en objetos del comercio físico y rechaza explícitamente los fondos
oscuros y los degradados. El color de marca aparece una sola vez por pantalla, en la acción que
compromete dinero.

**Key Characteristics:**

- Dos registros formales (Operación 2px / Análisis 6px) que se eligen por contexto de uso, no por gusto
- Cifras tabulares reales: las columnas de dinero y peso alinean por dígito
- Cero sombras: la profundidad se transmite con tono y borde
- Color semántico reservado a su significado, nunca decorativo
- Toda incertidumbre se comunica con tres portadores simultáneos, nunca solo con color

## Colors

Una paleta de comercio físico: verdes agrisados de anaquel pintado, tinta casi negra con matiz
verde, y tres semánticos que solo aparecen cuando significan algo.

### Primary

- **Verde Rasero** (#0F5132): el único color de marca. Aparece exclusivamente en la acción que
  compromete dinero —el botón de cobro— y como mucho una vez por pantalla. Su rareza es el punto.

### Neutral

- **Superficie Base** (#F1F4F1): el fondo de toda pantalla, un verde agrisado muy claro que evita
  el blanco puro de la hoja en blanco.
- **Superficie Alta** (#FFFFFF): planos que se levantan sobre la base — el cuerpo de una tabla, la
  fila activa. La única forma de "elevar" algo en este sistema.
- **Tinta** (#1B2621): todo el texto de lectura. Casi negro, con el mismo matiz verde de la base,
  para que la página no se lea como tinta de imprenta sobre papel ajeno.
- **Tinta Suave** (#5A6862): encabezados de columna, unidades, texto de apoyo. Nunca para una cifra
  que el operador deba leer con precisión.
- **Borde** (#D5DCD6): la línea de 1px que separa filas, columnas y regiones. Junto con el tono, es
  el único recurso de profundidad del sistema.

### Named Rules

**La Regla del Significado.** Los tres colores semánticos —atención **#9A5B08** (dato envejecido,
stock bajo), crítico **#8E2A2A** (caducado, anomalía) y estimado **#1F5673** (valor calculado, no
observado)— están reservados a su significado. Usar cualquiera de ellos por énfasis, por ritmo
visual o por rellenar una zona apagada está prohibido: si aparece el crítico, algo caducó.

**La Regla de la Sola Voz.** El Verde Rasero aparece una vez por pantalla, en la acción que
compromete dinero. Una segunda aparición lo convierte en decoración y anula la primera.

**La Regla del Ícono.** Todo ícono de la interfaz es un SVG —propio, o de una única librería
coherente con el resto del sistema— y **nunca** un emoji. Un emoji no respeta el sistema tipográfico
(no se compone en IBM Plex Sans ni en Source Serif 4); no respeta el sistema cromático (trae su
propio color y pisa los tres semánticos reservados —atención, crítico, estimado— y el Verde Rasero
exclusivo de la Sola Voz); varía de render entre sistema operativo y navegador —el mismo ícono se ve
distinto en la máquina donde se construye y en la del evaluador, y esa diferencia no es defendible—;
y su volumen, su sombra y su brillo rompen la superficie plana de 2px/6px sin sombras del rasero.
Aplica a los siete módulos, presentes y futuros, sin excepción.

## Typography

**Operación:** IBM Plex Sans (con system-ui, sans-serif)
**Análisis:** Source Serif 4 (con Georgia, serif)

**Character:** Dos voces por registro, no una familia con dos pesos. Plex Sans en Operación
trabaja como tipografía de instrumento: neutra, legible a distancia de brazo, y —lo que importa—
con cifras tabulares reales. Source Serif 4 en Análisis baja el ritmo de lectura porque ahí el
usuario decide, no captura.

### Named Rules

**La Regla de la Columna Alineada.** Toda cifra de dinero o de peso se compone con cifras
tabulares (`font-variant-numeric: tabular-nums`). Un total que baila un píxel entre filas obliga
al cajero a leer dígito por dígito en vez de de un vistazo.

**La Regla de Inter.** Inter está prohibida como tipografía por defecto. No es un juicio sobre la
familia: es el valor por defecto al que deriva cualquier herramienta que no recibió instrucciones,
y su presencia significa que alguien se saltó este documento.

## Layout

Registro de **Operación**: alta densidad de información, la tabla ocupa el ancho disponible y es
el elemento principal de la pantalla. Sin tarjetas — un contenedor con sombra alrededor de cada
grupo de datos gasta espacio vertical que la caja necesita para filas. Las cifras se alinean a la
derecha; las etiquetas, a la izquierda.

Registro de **Análisis**: una decisión por bloque, con aire alrededor. Las líneas de texto se
mantienen por debajo de 80 caracteres.

No hay todavía una escala de espaciado tokenizada; el sistema la adquirirá cuando la primera
pantalla la establezca. Documentar aquí una escala inventada la convertiría en norma sin que
ningún código la haya usado.

## Elevation & Depth

**Este sistema no usa sombras.** Ninguna. La profundidad se transmite con dos recursos: el salto
de tono entre Superficie Base (#F1F4F1) y Superficie Alta (#FFFFFF), y el borde de 1px en
#D5DCD6. Un plano blanco sobre el fondo agrisado ya está "arriba"; no necesita simular que
flota.

### Named Rules

**La Regla del Filo, No la Sombra.** Cuando una región necesite separarse de su entorno, se
separa con borde y tono. Añadir `box-shadow` es importar el vocabulario de otro sistema, y en un
registro de alta densidad las sombras se acumulan hasta emborronar la retícula.

## Shapes

Dos radios, uno por registro: **2px en Operación**, **6px en Análisis**. El de 2px no es "casi
cuadrado por timidez" — es el filo del rasero: suficiente para que no corte, insuficiente para
sugerir suavidad. Los degradados y los fondos oscuros están prohibidos en todo el sistema.

## Components

### Botón de cobro

- **Carácter:** el único bloque de color de la pantalla; se ve antes de buscarlo.
- **Forma:** filo de Operación (2px).
- **Color:** fondo Verde Rasero (#0F5132), texto Superficie Alta (#FFFFFF).
- **Estados:** el foco se marca con un anillo de borde, nunca con sombra ni con brillo.

### Tabla de Operación

- **Carácter:** es la pantalla, no un componente dentro de ella.
- **Fondo:** Superficie Alta (#FFFFFF) sobre la base agrisada.
- **Bordes:** separadores de 1px en #D5DCD6; sin sombra.
- **Tipografía:** IBM Plex Sans con cifras tabulares; encabezados de columna en Tinta Suave.
- **Alineación:** cifras a la derecha, etiquetas a la izquierda.

### Indicador de antigüedad o incertidumbre

- **Carácter:** el componente que hace visible lo que el sistema no sabe con certeza.
- **Comportamiento:** muestra **tres portadores simultáneos** — color semántico, indicador de
  forma (punto lleno / medio / hueco) y el texto explícito de la antigüedad ("hace 3 d").
- **Instancia real:** el estado de fuga de un cliente (Análisis). `sin_senal`/`resuelta` en
  Tinta Suave con punto lleno; `activa` en atención #9A5B08 con punto medio; `confirmada` en
  crítico #8E2A2A con punto hueco — el hueco marca que ese dato está a punto de desaparecer
  (la anonimización programada), no solo que es antiguo.

### Identificar cliente (Operación)

- **Carácter:** un paso opcional que nunca bloquea el cobro; vive en el encabezado de la
  pantalla de venta, nunca dentro de la tabla del ticket ni como modal.
- **Colapsado:** enlace de texto subrayado en Tinta Suave, sin fondo ni borde — no compite con
  la tabla.
- **Expandido:** panel flotante en Superficie Alta, borde de 1px en Borde, filo de Operación
  (2px), tipografía IBM Plex Sans; ofrece buscar o registrar un cliente nuevo en el mismo panel.
- **Seleccionado:** se colapsa a un chip de texto ("Cliente: Nombre") con un botón de quitar
  (✕) en Tinta Suave — reversible en un toque, porque identificar al cliente fue siempre una
  decisión del cajero, no un compromiso.

### Resumen de valor de cliente (Operación)

- **Carácter:** información de contexto durante el cobro, no la confirmación de una acción —
  por eso **nunca se anima al aparecer**, a diferencia del botón de cobro.
- **Con datos suficientes:** la puntuación compuesta en Tinta, cifras tabulares, junto al chip
  de cliente identificado.
- **Con datos insuficientes:** texto en cursiva Tinta Suave ("datos insuficientes") — nunca un
  0 ni una omisión silenciosa (Regla de los Tres Portadores aplicada a un caso sin dato, no
  solo a un dato envejecido).

### Bloque de Análisis: listado y detalle de clientes

- **Carácter:** el primer componente real construido en el registro de Análisis — valida en
  código lo que Colors, Typography y Shapes ya declaraban sobre ese registro sin evidencia
  propia hasta ahora.
- **Bloque de lista:** una decisión por bloque (nunca una fila de tabla densa), Superficie Alta,
  borde de 1px en Borde, filo de Análisis (6px), Source Serif 4; el bloque seleccionado marca
  su borde en Tinta.
- **Panel de detalle:** aparece junto a la lista, nunca en un modal ni reemplazando la lista —
  el gerente compara sin perder su lugar. Desglosa las tres dimensiones del valor (frecuencia,
  monto, margen) que Operación nunca muestra.
- **Momento de revelación:** al elegir un cliente, el panel de detalle entra con una única
  transición de opacidad y desplazamiento vertical corto (320ms) — el momento de animación
  deliberado por pantalla que el registro de Análisis admite, y el único de esta superficie.

### Sugerencia de precio y colocación (Análisis)

- **Carácter:** el primer componente del sistema que pide una acción que sí compromete dinero
  fuera del registro de Operación — aplicar una sugerencia de precio reescribe lo que se cobra.
  Aun así no usa el Verde Rasero: ese color queda reservado a la caja (La Regla de la Sola Voz);
  aquí la confirmación se distingue por texto ("Aplicada"/"Ejecutada") y por el único momento de
  animación de esta tarjeta, no por color de marca.
- **Insumos visibles:** cada sugerencia muestra el margen usado, el rol usado ("sin clasificar" en
  texto explícito si no hay rol) y, para precio, la observación de competencia usada con sus tres
  portadores de antigüedad — o "sin referencia de competencia" en texto si no hubo ninguna.
- **Momento de confirmación:** al aplicar una sugerencia, una única transición de opacidad
  (320ms) marca que la acción ya ocurrió — no es una revelación pasiva como la del detalle de
  cliente, es la confirmación de un acto del encargado, el mismo principio que ya rige la
  animación del botón de cobro en Operación, trasladado a Análisis.
- **Colocación sugerida nunca ejecuta nada:** el botón dice "Confirmar ejecución física", nunca
  "Mover" ni "Reubicar" — el sistema no reubica nada por su cuenta (Principio V, consultiva por
  defecto); el texto del botón es, en sí, parte de la explicabilidad.

### Serie y pronóstico de demanda (Análisis)

- **Carácter:** la superficie donde el sistema muestra un dato observado y, junto a él, su versión
  **estimada** — la demanda corregida por censura de quiebre, precio, promoción y sustitución, y el
  pronóstico que se deriva de ella. Es el caso más exigente de la Regla de los Tres Portadores: en
  la misma tabla conviven una columna de dato (demanda observada, tinta, cifras tabulares) y una de
  estimación (demanda corregida y pronóstico, color **estimado #1F5673**, punto hueco, y una nota
  de texto que dice qué corrección se aplicó).
- **Cuatro vistas por producto**, seleccionables con un segmentado de texto sin fondo de color:
  Pronóstico, Serie de demanda, Validación de la descensura, Sustitutos. Una decisión por vista.
- **El pronóstico nunca aparece solo:** siempre junto a su línea base determinista y a un veredicto
  explícito ("Pronóstico vigente: supera a la línea base" o "no supera su línea base — se recomienda
  la línea base"). Un producto sin histórico suficiente muestra el texto "datos insuficientes",
  nunca un número (misma regla que el resumen de valor de cliente).
- **Validación sintética rotulada:** la vista que compara la descensura contra datos generados
  lleva un rótulo inequívoco **"Datos sintéticos"** en color estimado con borde — no se puede
  confundir con una vista de producción.
- **Momento de revelación:** al terminar de calcularse un pronóstico, entra con una única
  transición de opacidad y desplazamiento vertical corto (320ms) — el momento de animación
  deliberado que el registro de Análisis admite, el mismo patrón que el detalle de cliente.
- **Sin Verde Rasero:** esta pantalla no tiene ninguna acción que comprometa dinero (Regla del
  Registro Sin Dinero); el pronóstico es consultivo y no dispara ninguna compra.

### Promociones inteligentes (Análisis, con una superficie en Operación)

- **Carácter:** tres mecanismos de promoción distintos —no uno genérico— cada uno en su vista de
  un segmentado de texto sin fondo de color: **Cupones por fecha fija**, **Ofertas de recompra**,
  **Experimento de reactivación**. Una decisión por vista, mismo patrón que las cuatro vistas de
  Pronóstico.
- **El experimento es el segundo caso más exigente de la Regla de los Tres Portadores:** el % de
  retorno **observado** de cada grupo va en tinta normal (dato); la incrementalidad, el
  estadístico z, el valor p y el veredicto van en color **estimado #1F5673**, con un indicador de
  forma (▲ significativa / ▬ no significativa / ◇ muestra insuficiente) y el texto explícito de la
  prueba ("incrementalidad +14,3 pp · z = 3,12 · p = 0,001 · significativa"). Nunca sólo color,
  nunca un número sin su prueba. Una muestra insuficiente dice el número exacto ("84 elegibles,
  mínimo 242"), nunca una conclusión.
- **La oferta de recompra nunca aparece sin su justificación:** junto al `precio_garantizado` va
  el texto de qué compras del propio cliente la sustentan (Principio V, explicable). El precio es
  una **reserva de precio, no de inventario** — el texto lo dice, no se garantiza disponibilidad.
- **Momento de revelación:** al cambiar de vista, y al revelar un experimento cerrado, entra con
  una única transición de opacidad y desplazamiento vertical corto (320ms) — el mismo patrón que
  el detalle de cliente y el pronóstico. Sin hover por fila, sin fade-in por tarjeta.
- **Sin Verde Rasero en Análisis:** ninguna acción de la pantalla de Promociones compromete
  dinero (Regla del Registro Sin Dinero); generar cupones, detectar recompras y crear un
  experimento son operaciones consultivas.
- **La única superficie en Operación** es `AplicarPromocionVenta` en el encabezado de Venta.tsx,
  junto a `IdentificarCliente`: radio 2px, IBM Plex Sans con cifras tabulares, sin Verde Rasero,
  reversible en un toque. El cajero marca qué cupón u oferta vigente del cliente se aplica; la
  redención se registra **después** de que la venta se confirmó y **nunca** la bloquea (Principio
  II) — mismo patrón exacto que la visita de cliente de 002.

### Pagos y seguridad (registro mixto: Operación y Análisis)

- **Registro por pantalla, no por módulo.** `TerminalesPago` y `BitacoraPagos` son **Operación**
  (2px, IBM Plex Sans con cifras tabulares, la tabla como elemento principal, sin tarjetas, sin
  animación salvo la confirmación de registrar una terminal o una actualización): un registro de
  datáfonos y un libro de rastro son de la misma familia que el inventario. `CoberturaPago` es
  **Análisis** (6px, Source Serif 4, una decisión por bloque, líneas bajo 80 caracteres): decidir
  si habilitar un medio de pago nuevo en una sucursal es una decisión gerencial.
- **Las señales de firmware usan los tres portadores, y ninguna deshabilita nada.** *Expuesta a
  clonación* = crítico **#8E2A2A** + punto lleno + la referencia de la vulnerabilidad enumerada;
  *desactualizada* = atención **#9A5B08** + punto medio + las dos versiones; *versión de referencia
  desconocida* = atención + punto hueco + texto — nunca "al día". La versión de firmware registrada
  y las fechas van en tinta normal (dato observado). El sistema señala; la persona actúa (FR-012).
- **La cuota de intención de compra no atendida es un valor calculado** → color **estimado
  #1F5673** en la tabla de cobertura; el conteo crudo de eventos y el "¿cubierto?" van en tinta
  normal. Es una **métrica de cobertura** (Lectura Crítica n.º 4), el texto lo dice — no un
  faltante de inventario.
- **Momento de revelación:** el desglose de la cobertura entra con una única transición de opacidad
  y desplazamiento vertical corto (240ms) al recargarse, misma familia que el detalle de cliente y
  el experimento. Sin hover por fila, sin fade-in por bloque. Las dos pantallas de Operación no
  animan nada salvo la confirmación de una acción.
- **La bitácora es sólo lectura.** No hay ningún botón de editar ni de borrar: el rastro es de solo
  anexado (FR-025), forzado por la base de datos. `pan_rechazado` y `terminal_expuesta_detectada`
  se marcan en crítico + punto lleno.
- **La tokenización no tiene pantalla propia.** El token y los últimos cuatro dígitos de una venta
  se hacen visibles a través de la bitácora (`token_emitido`) y del cliente
  `consultarPagoDeVenta`, que el detalle de venta de 001 consumirá. El número de tarjeta completo
  **nunca** llega al frontend.
- **Sin Verde Rasero:** ninguna de las tres pantallas de Pagos tiene una acción que comprometa
  dinero — 007 no mueve dinero (FR-036). Cero apariciones (Regla del Registro Sin Dinero).
- **Sin íconos nuevos:** las señales se comunican con formas dibujadas en CSS (punto lleno / medio
  / hueco), no con íconos — la Regla del Ícono no llega a aplicar.

### Named Rules

**La Regla de los Tres Portadores.** Ningún dato con antigüedad o incertidumbre se comunica solo
con color. Un portador único falla ante daltonismo, impresión en blanco y negro y reflejo de
pantalla — las tres condiciones normales de un local comercial.

**La Regla del Registro Sin Dinero.** Una pantalla que no tiene ninguna acción que comprometa
dinero no usa el Verde Rasero ni una sola vez. "Una vez por pantalla" es un máximo, no una cuota
que cada pantalla deba alcanzar — Clientes.tsx es la primera superficie del sistema en quedar
en cero apariciones, y es el comportamiento correcto, no una omisión.

## Do's and Don'ts

### Do:

- **Do** elegir el registro por contexto de uso: Operación (2px, alta densidad, tabla) para caja e
  inventario; Análisis (6px, aire) para pantallas donde se decide.
- **Do** componer toda cifra de dinero y peso con cifras tabulares reales.
- **Do** transmitir profundidad con el salto de tono #F1F4F1 → #FFFFFF y el borde #D5DCD6.
- **Do** acompañar todo dato incierto o envejecido con sus tres portadores.
- **Do** reservar el Verde Rasero para la acción que compromete dinero, una vez por pantalla —
  y cero veces en una pantalla que no tiene esa acción.
- **Do** revelar el detalle de un bloque de Análisis con una única transición por selección,
  nunca con hover ni fade-in repetido en cada bloque de la lista.
- **Do** mantener cualquier identificación o dato de contexto (como identificar a un cliente en
  caja) reversible en un toque y fuera del camino crítico de la acción que compromete dinero.

### Don't:

- **Don't** usar `box-shadow` en ninguna parte del sistema.
- **Don't** usar degradados ni fondos oscuros.
- **Don't** usar los semánticos (#9A5B08, #8E2A2A, #1F5673) por énfasis o decoración.
- **Don't** envolver grupos de datos en tarjetas dentro del registro de Operación.
- **Don't** usar Inter como tipografía por defecto.
- **Don't** comunicar antigüedad o incertidumbre solo con color.
- **Don't** animar la aparición de un dato de contexto (como un resumen o valor) que no
  confirma una acción del usuario — la animación se reserva para confirmaciones y revelaciones
  deliberadas, nunca para decorar la llegada de un dato.
