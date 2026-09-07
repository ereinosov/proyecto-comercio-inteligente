---
name: Rasero
description: Punto de venta e inventario para comercio físico multi-sucursal
colors:
  superficie-base: "#E9EDE9"
  superficie-alta: "#FFFFFF"
  tinta: "#1B2621"
  tinta-suave: "#5A6862"
  marca: "#0F5132"
  acento-secundario: "#7A6A56"
  borde: "#D5DCD6"
  borde-fuerte: "#BCC6BD"
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
  boton-accion-secundaria:
    backgroundColor: "transparent"
    textColor: "{colors.acento-secundario}"
    borderColor: "{colors.acento-secundario}"
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

<!--
INFORME DE IMPACTO — enmienda del sistema de diseño
==================================================
Cambio de versión: 1.6.0 → 1.7.0 (MENOR — una regla reescrita, una sección ajustada, una
variante de componente; ninguna regla se elimina).

Motivo: ronda de ajuste de la pantalla de Venta y del armazón tras revisión en uso.

Regla reescrita: La Regla de la Marca Persistente. El **footer / barra de contexto inferior**
(v1.3.1–v1.6.0) se **retira**. Su información —ícono del comercio, sucursal, caja— sube al
**extremo derecho del nav**, junto al nombre y rol del operador (que ya vivían ahí), como un
**bloque de contexto** con una línea divisoria real entre «lugar» y «operador». Las dos marcas
siguen sin compartir lugar: wordmark de Rasero al extremo izquierdo, contexto del comercio al
extremo derecho — **extremos opuestos** de la misma barra, no "al mismo nivel compitiendo" (que
era lo que los mockups de v1.4.0 rechazaban). Además, una pantalla ya **no repite**
`{sucursal} · {caja}` en su propio encabezado: ese dato vive una sola vez, en el nav (antes se
veía dos veces).

Sección ajustada: "Venta: dos columnas". El **ticket pasa a ser el protagonista** (ancho
disponible) y el **catálogo, apoyo** (columna estrecha y fija). El catálogo gana un **buscador
por nombre** integrado además de los chips de categoría; sus tarjetas se hacen **compactas**
(franja de imagen baja); **9 por página** con un **paginador numerado anclado al pie**. El
producto se agrega **sólo al pulsar "+"**, no al hacer click en la tarjeta. Y agregar el mismo
producto por unidad **suma a la cantidad** del renglón existente en vez de duplicar la fila.

Variante de componente nueva: `Paginador` con `numerado` — botones cuadrados con el número de
cada página (1, 2, 3…) con elipsis cuando hay muchas, además de las flechas. Para grillas cortas
donde ver "en qué página estoy y cuántas hay" de un vistazo importa.

Ajuste de comportamiento: el buscador `SelectorProducto` deja de mostrar el catálogo entero por
defecto — muestra resultados **a medida que se escribe**, en un **panel flotante** que no empuja
la fila (alineación de "Producto" con "Cantidad"). Coherente con la viñeta "Expandido: panel
flotante" del componente "Identificar cliente".

Reglas eliminadas o invertidas: ninguna. Sincronización con la constitución: PENDIENTE, junto
con v1.4.0, v1.5.0 y v1.6.0.

--><!--
INFORME DE IMPACTO — enmienda del sistema de diseño (histórico)
==============================================================
Cambio de versión: 1.5.0 → 1.6.0 (MENOR — dos añadidos, ninguna regla eliminada ni invertida).

Contexto: Fase 3b de la ronda de evolución visual — User Story 12 de 001 añade un catálogo de
productos en grid a la pantalla de Venta, con imágenes de producto.

Añadido 1 — Imágenes de producto (en "Components", bajo "La Regla del Ícono por Categoría").
Un `Producto` puede llevar una `url_imagen` (columna nueva, opcional). Donde antes una lista de
productos mostraba SÓLO el glifo de familia de categoría, ahora un componente compartido —
`ImagenProducto`— muestra la foto si la hay y **cae al glifo de categoría** si no hay URL o si
el `<img>` falla al cargar (`onError`). El glifo deja de ser el único tratamiento y pasa a ser
el **fallback garantizado**: nunca un hueco ni una imagen rota. Las imágenes se alojan **fuera
del repositorio** (URL externa en vivo, configurable por producto desde Administración) — una
decisión consciente, con el riesgo de que una URL no cargue el día de una demo **aceptado
explícitamente** y cubierto por el fallback. La Regla del Ícono por Categoría no se toca: el
glifo sigue siendo SVG de línea, sin color propio, y sigue siendo lo que se ve cuando no hay
foto; sólo se admite que, cuando hay foto real, la foto gana.

Añadido 2 — Layout de dos columnas de Venta (en "Layout"). La pantalla de Venta pasa de una
columna (tabla del ticket arriba, total anclado abajo) a **dos columnas**: catálogo en grid a
la izquierda, ticket a la derecha, con el encabezado a lo ancho y el total + Cobrar anclados
abajo a lo ancho. Por debajo de ~1100px de ancho las dos columnas se apilan en vertical. Sigue
siendo Registro de Operación (2px, IBM Plex Sans, cifras tabulares, sin tarjetas dentro del
ticket, sin sombra). El buscador `SelectorProducto` no desaparece: convive con el grid como
segundo camino para agregar un producto.

Reglas intactas: La Regla de la Sola Voz (el "+" de cada tarjeta del catálogo es contorno en el
Acento Secundario, NUNCA Verde Rasero — el verde sigue sólo en Cobrar), La Regla del Filo (el
grid y las tarjetas se separan con borde y tono, sin sombra), La Regla del Hueco que Enseña (el
grid vacío y el ticket vacío usan `EstadoVacio`).

Sincronización con la constitución: PENDIENTE, junto con la de v1.4.0 y v1.5.0.

--><!--
INFORME DE IMPACTO — enmienda del sistema de diseño (histórico)
==============================================================
Cambio de versión: 1.4.0 → 1.5.0 (MENOR — ronda de evolución visual: todo aditivo o
refinamiento de una regla ya existente; ninguna regla se elimina ni se invierte).

Motivo de la ronda: la austeridad del sistema —correcta como identidad ("el rasero nivela,
no adorna")— se estaba leyendo como "incompleta" en vez de "intencional". La causa no era
incoherencia sino coherencia por sustracción sin compensación: se habían quitado casi todos
los recursos que dan carácter (profundidad, color, movimiento) sin poner en su lugar los que
hacen que lo austero se vea deliberado (una escala de espaciado precisa, jerarquía tipográfica
con contraste real, una jerarquía de borde, un acento usado con seguridad). Esta enmienda no
cambia los principios; mejora la ejecución.

Escalas nuevas (tokenizadas en `frontend/src/estilos/tokens.css`, en sync con
`.impeccable/design.json`), documentadas abajo en "Layout":
  - Espaciado: 7 valores (4 / 8 / 12 / 16 / 24 / 32 / 48px), ni uno más.
  - Tipografía: escala de 12 → display, formaliza los tamaños que dejó la ronda de tipografía
    previa en vez de repetir literales por archivo.
  - Alturas de control: 30 / 36 / 44px — un input, un select y un botón de la misma variante
    miden lo mismo en todas las pantallas.
  - Anillo de foco único (`--foco-anillo`): reemplaza el "2px tinta aquí / cambio de
    border-color allá / outline:none en Arqueo" por un solo tratamiento.

Reglas refinadas (sin reabrirse, sólo se precisa su aplicación):
  - La Regla de la Sola Voz: se FORMALIZA el rol del Verde Rasero. Sigue siendo "una vez por
    pantalla, en la acción que compromete dinero" para el CONTENIDO de la pantalla. Se añade,
    en la capa de CHROME compartido (no en el contenido), un uso de identidad: el acento
    estructural de 2px que marca el ítem de navegación activo. No es decoración ni un segundo
    CTA; es "esto es Rasero" y "aquí estás". La Regla del Registro Sin Dinero queda intacta
    para el área de contenido.
  - La Regla del Filo, No la Sombra: se añade una jerarquía de borde de DOS niveles —hairline
    (`borde` #D5DCD6, 1px entre filas/columnas) y estructural (`borde-fuerte` #BCC6BD, entre
    regiones). Sigue sin haber una sola sombra.
  - Elevation & Depth: Superficie Base pasa de #F1F4F1 a #E9EDE9 — el salto a Superficie Alta
    sube de ~4% a ~7% de luminosidad, suficiente para que una tabla o tarjeta blanca se
    separe del fondo sin sombra. No es una paleta nueva: es el mismo verde agrisado, un punto
    más profundo.
  - Typography: se añade La Regla de la Voz de Análisis — Source Serif 4 vive SÓLO en títulos
    (≥ 20px) y prosa de Análisis; todo control de formulario, tabla, etiqueta y cifra usa IBM
    Plex Sans en ambos registros. Serif a 13-14px en un botón se leía como "sin estilar".
  - Shapes: se evaluó un tercer radio intermedio y se DESCARTÓ. Siguen siendo dos, 2px
    Operación / 6px Análisis; cada componente toma el de su registro.

Componentes nuevos con especificación (abajo, en "Components"): Botón (spec general, no sólo
el de cobro), Campo (input/select), Encabezado de pantalla. La implementación de esta ronda
crea `Boton`, `Campo`, `EncabezadoPantalla` y `SeccionPantalla` y los aplica SÓLO en Venta y
en la navegación; el resto del sistema migra en rondas posteriores, pantalla por pantalla.

Reglas eliminadas o invertidas: ninguna. Sincronización con la constitución: PENDIENTE, junto
con la de v1.4.0 (misma acción de seguimiento).

--><!--
INFORME DE IMPACTO — enmienda del sistema de diseño (histórico)
==============================================================
Cambio de versión: 1.3.1 → 1.4.0 (MENOR — una regla nueva, una regla
reescrita y una extensión de regla; ninguna regla se elimina).

Regla nueva: La Regla del Segundo Tono (Colors → Named Rules). Introduce
un acento secundario tierra (#7A6A56) para la acción secundaria neutra —
disparadores de un flujo secundario que hoy son texto plano subrayado
("+ Identificar cliente", "+ Elegir producto", "+ Aplicar promoción",
"Consulta no atendida", "Cerrar turno"). Tratamiento SOLO de contorno
(borde + texto en el acento, fondo transparente), nunca relleno sólido:
un relleno competiría con el botón de cobro. Convivencia estricta con lo
ya existente: no reemplaza el Verde Rasero (La Regla de la Sola Voz
intacta), no aparece en Análisis con función de dinero (La Regla del
Registro Sin Dinero intacta), no reemplaza ni pisa los tres semánticos
(La Regla del Significado intacta) — es un cuarto color de rol, no de
estado.

Regla reescrita: La Regla de la Marca Persistente. Antes: el ícono del
comercio vivía en el nav global "al mismo nivel visual que el wordmark de
Rasero", y el footer no llevaba ícono ("la marca visual ya vive en el
nav"). Ahora: el nav global lleva SOLO el wordmark de Rasero; el ícono del
comercio baja al footer/barra de contexto, delante del nombre de sucursal
y la caja, en una sola línea. Motivo: los mockups comparativos aprobados
mostraron que dos marcas al mismo nivel en el nav compiten por la lectura
en el arranque de cada pantalla; separar "herramienta" (wordmark, nav) de
"dónde estoy" (ícono + sucursal + caja, footer) baja el ruido sin perder
ninguna de las dos presencias. La jerarquía de los tres usos del activo de
marca no cambia (apertura = logo a color en grande; footer = ícono +
contexto discretos; mono = reportes/dashboards y ahora estados vacíos).

Extensión de regla: La Regla del Hueco que Enseña. Se añade una marca de
agua del logo mono del comercio (`despensa-logo-mono-800w.png`) al 8 % de
opacidad, centrada detrás de las tres partes ya obligatorias (ícono,
título, frase), `pointer-events: none`, sin recortarse contra el
contenedor. No cambia las tres partes obligatorias; es un refuerzo visual
del mismo componente compartido (`EstadoVacio`), no una excepción por
pantalla. Amplía el alcance del logo mono, antes "reservado a reportes y
dashboards", para incluir los estados vacíos.

Componente actualizado: "Identificar cliente (Operación)" → viñeta
"Colapsado". Antes: "enlace de texto subrayado en Tinta Suave, sin fondo
ni borde". Ahora: botón de contorno en el acento secundario (La Regla del
Segundo Tono). Sigue sin competir con la tabla —es contorno, no relleno—
y sigue siendo reversible y fuera del camino crítico del cobro.

Reglas eliminadas: ninguna. Secciones nuevas: ninguna.

Sincronización con la constitución: PENDIENTE. Las tres enmiendas
anteriores de DESIGN.md (1.2.0, 1.3.0, 1.3.1) se registraron cada una en
un historial de `constitution.md` (v2.2.7, v2.2.8, v2.2.9). Esta enmienda
deja esa sincronización sin hacer a propósito: el alcance de este cambio
se acotó a "frontend + DESIGN.md" y tocar `constitution.md` quedó fuera.
Queda como acción de seguimiento registrar v1.4.0 en el historial de la
constitución con la razón "acento secundario de rol; separa las dos marcas
entre nav y footer; marca de agua del mono en estados vacíos".

--><!--
INFORME DE IMPACTO — enmienda del sistema de diseño (histórico)
==============================================================
Cambio de versión: 1.2.1 → 1.3.0 (MENOR — reescribe una regla existente sin
eliminarla; ninguna otra regla cambia).

Regla modificada: La Regla de la Identidad del Comercio. Antes: cabecera con
fondo Tinta y el nombre de sucursal (Source Serif 4) como elemento de mayor
peso. Ahora: cabecera de fondo blanco con el logo a color del comercio como
elemento principal; nombre de sucursal + caja como contexto secundario en Tinta
Suave debajo, con "Última apertura" en formato relativo legible. Motivo: el logo
a color de la marca no está diseñado para fondo oscuro; el bloque Tinta lo
apagaba. El wordmark de Rasero sigue arriba y fuera de la tarjeta; el origen del
logo se fija por VITE_LOGO_COMERCIO (asset de demostración por defecto), nunca un
literal de marca en JSX ni en tabla.

Reglas eliminadas: ninguna. Reglas nuevas: ninguna. Secciones nuevas: ninguna.

Sincronización con la constitución: la enmienda v2.2.8 de constitution.md
registra este mismo cambio en su historial con la razón "reescribe La Regla de la
Identidad del Comercio: cabecera de apertura con logo a color sobre fondo blanco
en vez de bloque Tinta". No toca ningún principio ni la tabla de Propiedad de
Datos: la única sincronización es DESIGN.md ↔ ese historial.

(1.2.1 — PARCHE previo del mismo día: aclaración de "Identificar cliente
(Operación)"; ver historial de versiones al pie.)

--><!--
INFORME DE IMPACTO — enmienda del sistema de diseño (histórico)
==============================================================
Cambio de versión: 1.1.0 → 1.2.0 (MENOR — amplía una guía existente con reglas
nuevas; no elimina ni redefine ninguna regla previa, mismo criterio de versionado
que la constitución).

Reglas añadidas (todas aditivas, con su carácter y su razón, formato de las
existentes):
  - La Regla de la Identidad del Comercio (Components → Named Rules)
  - La Regla del Hueco que Enseña (Components → Named Rules)
  - La Regla del Pulso, No el Brillo (Components → Named Rules)
  - La Regla del Ícono por Categoría (Colors → Named Rules, junto a La Regla del Ícono)
  - La Regla del Modal Administrable (Components → Named Rules)
  - La Regla del Filtro y la Página (Components → Named Rules)
  - La Regla del Grupo de Navegación (Components → Named Rules)

Reglas modificadas o eliminadas: ninguna.
Secciones nuevas: "Historial de versiones del sistema de diseño" (pie).

Sincronización con la constitución: la enmienda v2.2.7 de `constitution.md`
registra este mismo cambio en su historial de versiones con la razón "amplía el
sistema de diseño con reglas de identidad de negocio, estados vacíos, carga y
componentes administrables — no reemplaza ninguna regla previa". El Principio V
("Visible": el sistema de diseño es parte de la explicabilidad) y la sección
"Sistema de Diseño" de la constitución siguen vigentes sin cambio; esta enmienda
sólo añade reglas ejecutables bajo ellas.
-->

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
verde, tres semánticos que solo aparecen cuando significan algo, y un acento tierra apagado
reservado a la acción secundaria neutra.

### Primary

- **Verde Rasero** (#0F5132): el único color de marca. Aparece exclusivamente en la acción que
  compromete dinero —el botón de cobro— y como mucho una vez por pantalla. Su rareza es el punto.

### Secondary

- **Acento Secundario** (#7A6A56): un tierra apagado, sin brillo, para la **acción secundaria
  neutra** —la que no cobra y no comunica un estado. Siempre como contorno (borde + texto),
  nunca como relleno. Ver La Regla del Segundo Tono.

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

*Formalización del rol (v1.5.0).* El verde tiene exactamente estos usos y ningún otro:
(1) la **acción primaria que compromete dinero** —el botón de cobro— una vez, en el área de
contenido de la pantalla; (2) el **wordmark de Rasero** en el nav global; (3) un **acento
estructural de 2px** que marca el ítem de navegación activo. Los usos (2) y (3) viven en el
**chrome compartido** —el armazón que rodea a toda pantalla—, no en el contenido, y son
identidad ("esto es Rasero", "aquí estás"), no una acción ni un énfasis. El chrome es una capa
aparte: que el wordmark y el subrayado de nav activo coexistan con el botón de cobro no cuenta
como "dos voces" —la Sola Voz rige el **contenido** de la pantalla, donde el verde sigue
apareciendo una sola vez—. Nunca en fondos grandes, nunca en dos elementos del contenido a la
vez, nunca decorativo. **La Regla del Registro Sin Dinero sigue intacta**: una pantalla sin
acción de dinero tiene cero verde en su contenido; el acento del nav activo es del armazón.

**La Regla del Ícono.** Todo ícono de la interfaz es un SVG —propio, o de una única librería
coherente con el resto del sistema— y **nunca** un emoji. Un emoji no respeta el sistema tipográfico
(no se compone en IBM Plex Sans ni en Source Serif 4); no respeta el sistema cromático (trae su
propio color y pisa los tres semánticos reservados —atención, crítico, estimado— y el Verde Rasero
exclusivo de la Sola Voz); varía de render entre sistema operativo y navegador —el mismo ícono se ve
distinto en la máquina donde se construye y en la del evaluador, y esa diferencia no es defendible—;
y su volumen, su sombra y su brillo rompen la superficie plana de 2px/6px sin sombras del rasero.
Aplica a los siete módulos, presentes y futuros, sin excepción.

**La Regla del Ícono por Categoría.** En toda superficie donde se liste `Producto` —el catálogo de
Venta, la lista de Precios, la lista de Administración de productos— cada fila o bloque lleva un
ícono SVG de línea simple (stroke, sin relleno) asociado a su `id_categoria`, **nunca** una foto
del producto. Se dibuja un set corto de 4 a 6 íconos genéricos por familia de categoría, derivado
de las categorías reales sembradas en `backend/rasero/semilla_catalogo.py` —hoy Abarrotes (granos
y secos), Bebidas, Frescos (refrigerados/perecederos), Limpieza— más un ícono "otros" de respaldo
para cualquier categoría futura sin familia asignada. El carácter es el mismo que el de La Regla
del Ícono: una sola línea, sin color propio, sin volumen; el ícono orienta la vista por familia,
no decora. **El ícono vive puramente en el frontend**, mapeado por `id_categoria`: NO añade ningún
campo a `producto` ni a `categoria` —esas tablas son de 001 y no se amplían desde una decisión
presentacional— y una categoría sin mapa cae al ícono "otros" en lugar de romper la fila.
**Razón**: una foto de producto en una lista de decisión gerencial pesa, tarda en cargar, varía de
encuadre entre productos y compite con las cifras; un glifo de familia da el mismo golpe de
reconocimiento ("esto es limpieza, esto es fresco") sin ninguno de esos costos, y no obliga a
mantener un activo de imagen por SKU.

**La Regla de la Imagen que se Cae con Gracia (v1.6.0).** En la **pantalla de Venta** —donde el
cajero elige rápido y una foto ayuda a reconocer el producto en el estante, no una lista de
decisión gerencial— un producto puede llevar una foto. Vive en `producto.url_imagen` (opcional)
y se muestra a través de un único componente compartido, `ImagenProducto`, nunca con un `<img>`
suelto. `ImagenProducto` **siempre** cae al glifo de familia de categoría —el de La Regla del
Ícono por Categoría, sin cambiarlo— en dos casos: cuando no hay `url_imagen`, y cuando el `<img>`
dispara `onError` (URL movida, sin conexión, 403…). Nunca un hueco, nunca el marco roto del
navegador. Las imágenes se alojan **fuera del repositorio**: una URL externa por producto,
configurable desde Administración. Es una decisión consciente —el sistema no mantiene un activo
de imagen por SKU, y el día que una URL no cargue el catálogo no se rompe, sólo muestra el
glifo—. La foto sólo se admite donde el reconocimiento rápido pesa más que la sobriedad de la
lista (Venta); en las listas de Precios y Administración sigue rigiendo el glifo a secas.

**La Regla del Segundo Tono.** Hay un cuarto color con nombre —**Acento Secundario #7A6A56**, un
tierra apagado— y su función es una sola: la **acción secundaria neutra**. Son los disparadores
de un flujo opcional que hoy viven como texto plano subrayado sin forma de botón: "+ Identificar
cliente", "+ Elegir producto", "+ Aplicar promoción", "Consulta no atendida", "Cerrar turno".
Antes se perdían contra la tabla; ahora se leen como una acción disponible sin gritar. El
tratamiento es **siempre de contorno**: `border: 1px solid #7A6A56`, texto en #7A6A56, fondo
transparente o Superficie Alta, radio del registro que corresponda (2px en Operación, 6px en
Análisis). **Nunca relleno sólido de este color** — un botón tierra macizo competiría de lejos
con el único bloque de color de la pantalla, que es el de cobro. Este color **no** entra en
ninguna de las prohibiciones que ya rigen: no reemplaza el Verde Rasero (La Regla de la Sola Voz
sigue intacta: el verde es exclusivo de la acción que compromete dinero), no aparece en una
pantalla de Análisis con función de dinero (La Regla del Registro Sin Dinero sigue intacta), y
no reemplaza ni se usa donde ya corresponde uno de los tres semánticos (La Regla del Significado
sigue intacta). Es un color de **rol**, no de estado ni de alerta. **Razón**: hasta ahora el
sistema tenía dos únicos tratamientos para una acción —el bloque Verde de cobro y el texto plano
sin forma— y todo lo que no cobraba caía en el segundo, indistinto del texto de lectura. Un
tercer tratamiento, de contorno y en un tono que no pisa a ninguno de los reservados, da a la
acción secundaria un lugar propio en la jerarquía sin encender otra "voz".

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

**La Regla de la Voz de Análisis.** Source Serif 4 baja el ritmo de lectura, y eso sólo sirve
donde el usuario lee: **títulos de pantalla y de sección (≥ 20px) y prosa** (descripciones,
frases de estado vacío, cuerpo de un modal explicativo). **Nunca** en un control de formulario,
una etiqueta de campo, un encabezado de columna, una celda de tabla ni un botón. Una serif a
13-14px en un botón o un `<label>` no "baja el ritmo": se lee como texto sin estilar, como si
la hoja no hubiera cargado. En esos elementos —en los dos registros— la voz es IBM Plex Sans.
El contraste entre Operación y Análisis lo dan el radio, la densidad y el aire, no ponerle
serif a los widgets.

## Layout

Registro de **Operación**: alta densidad de información, la tabla ocupa el ancho disponible y es
el elemento principal de la pantalla. Sin tarjetas — un contenedor con sombra alrededor de cada
grupo de datos gasta espacio vertical que la caja necesita para filas. Las cifras se alinean a la
derecha; las etiquetas, a la izquierda.

Registro de **Análisis**: una decisión por bloque, con aire alrededor. Las líneas de texto se
mantienen por debajo de 80 caracteres.

**Venta: dos columnas (v1.6.0, ajustada v1.7.0).** La pantalla de Venta —la única de Operación
con dos zonas de trabajo simultáneas— se organiza en **dos columnas de peso desigual**: el
**ticket es el protagonista** y toma el ancho disponible a la derecha; el **catálogo de
productos** es apoyo y ocupa una columna **estrecha y fija** (≈ 380px) a la izquierda. El
encabezado de pantalla va a lo ancho arriba; el **total y el botón Cobrar**, anclados a lo ancho
abajo, nunca se desplazan. Por debajo de ~1100px las dos columnas se apilan en vertical
—catálogo y luego ticket—, sin scroll horizontal a 1366px.

El catálogo: un **buscador por nombre** y los **chips de categoría** fijos arriba; una grilla de
**tarjetas compactas** (thumbnail en franja baja + nombre + precio + un botón "+"), **9 por
página**; y el **paginador numerado anclado al pie** de la columna (cuadros con el número de
página, La Regla del Filtro y la Página). El producto se agrega **sólo al pulsar el "+"** —hacer
click en el resto de la tarjeta no hace nada— y ese "+" es contorno en el Acento Secundario,
**nunca Verde Rasero** (La Regla de la Sola Voz). El catálogo **convive** con el buscador
`SelectorProducto` del "+ Agregar producto" del ticket, no lo reemplaza; agregar por cualquiera
de las dos vías produce **el mismo renglón** (una sola función de "agregar al ticket") y, si el
producto por unidad ya está en el ticket, **suma a su cantidad** en vez de crear una segunda
fila (a granel siempre fila aparte: cada pesada es distinta).

Sigue sin haber tarjetas *dentro* del ticket (La Regla del registro de Operación); las
"tarjetas" son las del catálogo, que es una grilla de elección, no un grupo de datos.

**Escala de espaciado (v1.5.0).** Siete valores, tokenizados en `tokens.css`, y ninguno más:
`--espacio-1: 4px` · `--espacio-2: 8px` · `--espacio-3: 12px` · `--espacio-4: 16px` ·
`--espacio-6: 24px` · `--espacio-8: 32px` · `--espacio-12: 48px`. Todo padding, margin y gap
sale de aquí. Antes de v1.5.0 no había escala y cada pantalla inventaba sus valores (`7/8/10/12/
14/18/20/22px` mezclados); esa deriva era una de las causas de que el sistema se leyera como
"hecho por partes".

**Escala tipográfica (v1.5.0).** `--texto-xs: 12px` (unidades, chips menores) · `--texto-sm:
13px` (encabezados de columna, etiquetas de campo, apoyo) · `--texto-base: 15px` (cuerpo,
celdas, controles) · `--texto-md: 17px` · `--texto-lg: 20px` · `--texto-xl: 24px` (título de
pantalla) · `--texto-2xl: 32px` · `--texto-display` (`clamp(36px, 4vw, 52px)`, la cifra que
domina una pantalla — el total de cobro). Tres pesos: `--peso-normal: 400`, `--peso-medio:
500`, `--peso-fuerte: 600`.

**Alturas de control (v1.5.0).** `--alto-control-sm: 30px` · `--alto-control: 36px` ·
`--alto-control-lg: 44px` (acción primaria de alta frecuencia). Un input, un select y un botón
de la misma variante miden lo mismo en toda pantalla.

## Elevation & Depth

**Este sistema no usa sombras.** Ninguna. La profundidad se transmite con dos recursos: el salto
de tono entre Superficie Base (#E9EDE9) y Superficie Alta (#FFFFFF), y el borde. Un plano blanco
sobre el fondo agrisado ya está "arriba"; no necesita simular que flota.

**Salto de tono (v1.5.0).** Superficie Base pasó de #F1F4F1 a **#E9EDE9**: el mismo verde
agrisado, un punto más profundo. El salto de luminosidad a Superficie Alta sube de ~4% a ~7% —
antes era tan sutil que en muchos monitores la tabla no se distinguía del fondo y la pantalla
se leía como un solo plano.

**Jerarquía de borde (v1.5.0).** Dos niveles, ambos sin sombra: **hairline** (`borde` #D5DCD6,
1px) separa filas, columnas y el contorno de una tabla o tarjeta; **estructural**
(`borde-fuerte` #BCC6BD) separa regiones y secciones —el borde inferior del nav, la franja del
pie, el corte entre un formulario fijo y su tabla— donde el hairline se perdía contra el
contenido.

### Named Rules

**La Regla del Filo, No la Sombra.** Cuando una región necesite separarse de su entorno, se
separa con borde y tono. Añadir `box-shadow` es importar el vocabulario de otro sistema, y en un
registro de alta densidad las sombras se acumulan hasta emborronar la retícula.

## Shapes

Dos radios, uno por registro: **2px en Operación**, **6px en Análisis**. El de 2px no es "casi
cuadrado por timidez" — es el filo del rasero: suficiente para que no corte, insuficiente para
sugerir suavidad. Los degradados y los fondos oscuros están prohibidos en todo el sistema.

En v1.5.0 se evaluó añadir un tercer radio intermedio para componentes que "no encajan limpio"
(botones, chips flotantes) y se **descartó**: cada componente toma el radio del registro donde
vive —un botón de Operación es de 2px, uno de Análisis de 6px— y con eso alcanza. Un tercer
valor sólo habría reabierto la discusión en cada componente nuevo.

## Components

### Botón de cobro

- **Carácter:** el único bloque de color de la pantalla; se ve antes de buscarlo.
- **Forma:** filo de Operación (2px).
- **Color:** fondo Verde Rasero (#0F5132), texto Superficie Alta (#FFFFFF).
- **Estados:** el foco se marca con un anillo de borde, nunca con sombra ni con brillo.

### Botón (spec general, v1.5.0)

Hasta v1.4.0 el sistema sólo tenía spec del botón de cobro; el resto se re-escribía por
pantalla (`botonSecundario`, `botonCancelar`, `botonTexto`, `botonNuevo`, `boton`, `primaria`,
`cancelar`, y los pares `ordenActivo`/`Inactivo`, `segActivo`/`Inactivo`, `vistaActiva`/
`Inactiva`) con tamaños y radios ligeramente distintos. El componente `Boton` unifica las
variantes; la clase equivalente se retira de cada pantalla al migrarla.

- **Forma:** radio del registro; alto de `--alto-control` (o `--alto-control-lg` para la
  acción primaria de alta frecuencia); padding horizontal `--espacio-4`; IBM Plex Sans
  (La Regla de la Voz de Análisis) con `--peso-fuerte` la primaria, `--peso-medio` el resto.
- **Variantes:**
  - `cobro` — sólo Venta. Verde Rasero. La Regla de la Sola Voz.
  - `primaria` — fondo Tinta, texto Superficie Alta. La acción principal de una pantalla que
    **no** compromete dinero (registrar entrada, confirmar conteo, guardar maestro).
  - `secundaria` — contorno en el Acento Secundario #7A6A56, fondo transparente, texto en el
    acento. La acción secundaria **neutra** (La Regla del Segundo Tono). Nunca relleno.
  - `neutra` — borde `--color-borde`, texto Tinta Suave. El "Cancelar" de un par, el "Volver".
  - `fantasma` — sin borde ni fondo, texto Tinta Suave con subrayado en hover. Sólo acciones
    de fila de baja jerarquía dentro de una tabla ("Editar", "Desactivar").
- **Estados:** foco con `--foco-anillo`; `:disabled` baja opacidad a 0.5 y quita el cursor —
  nunca se oculta.

### Campo: input y select (spec general, v1.5.0)

`Campo` envuelve `<label>` + control con un tratamiento único; retira las definiciones locales
de `.entrada` / `.campo` / `.campoFila` / `.campoModal` al migrar cada pantalla.

- **Etiqueta:** IBM Plex Sans `--texto-sm`, Tinta Suave, `--espacio-1` de separación del
  control. Un asterisco de obligatorio usa el componente `Obligatorio` ya existente.
- **Control:** alto `--alto-control`, padding `0 --espacio-3`, borde 1px `--color-borde`, radio
  del registro, fondo Superficie Alta, IBM Plex Sans `--texto-base` con `tabular-nums` si el
  campo es numérico. El `<select>` restyled mantiene su chevron SVG propio (componente
  `Selector`).
- **Foco:** `--foco-anillo`. **Error:** borde `--color-critico` y un mensaje debajo en
  `--color-critico` `--texto-sm` — nunca sólo el borde (mismo principio que los tres
  portadores). **Disabled:** opacidad 0.5.

### Encabezado de pantalla (v1.5.0)

Toda pantalla abre con el mismo bloque, vía `EncabezadoPantalla`: un `<h1>` en `--texto-xl`
`--peso-fuerte` (serif en Análisis, IBM Plex Sans en Operación), padding
`--espacio-6 --espacio-8 --espacio-4` en Análisis y `--espacio-3 --espacio-6` en Operación, y
una zona de acciones alineada a la derecha en la misma línea. La pantalla de Venta —que hasta
v1.4.0 no tenía título, sólo una línea de contexto en Tinta Suave— también lo lleva. El
contexto de sucursal/caja va **debajo** del `<h1>` en `--texto-sm` Tinta Suave, no en su lugar.
`SeccionPantalla` da el mismo padding lateral y el `--espacio-6` entre secciones al resto del
cuerpo.

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
- **Colapsado:** botón de contorno en el Acento Secundario #7A6A56 (La Regla del Segundo Tono):
  borde de 1px y texto en el acento, fondo transparente, filo de Operación (2px). Sigue sin
  competir con la tabla —es contorno, no relleno— pero ahora se lee como una acción disponible,
  no como texto de lectura suelto.
- **Expandido:** panel flotante en Superficie Alta, borde de 1px en Borde, filo de Operación
  (2px), tipografía IBM Plex Sans; **la búsqueda** vive en este panel flotante. **El alta o la
  edición** de un cliente (nombre, fecha de nacimiento, cédula/RUC) abre `ModalAdministrable` —
  registrar un cliente es un formulario de dato maestro y le aplica La Regla del Modal
  Administrable, igual que la edición de Cliente desde `Clientes.tsx`; no un segundo formulario
  suelto dentro del panel (v1.2.1).
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

**La Regla de la Identidad del Comercio.** La pantalla de apertura de turno invierte la jerarquía
habitual de un login. La tarjeta abre con una **cabecera de marca del comercio**: fondo blanco
(Superficie Alta —el logo a color del comercio no está diseñado para fondo oscuro; un bloque
Tinta lo apaga) y el **logo a color del comercio, centrado, como elemento principal**
(ancho ≈ 240–280px). El logo se toma de `VITE_LOGO_COMERCIO`; si no está definida, del asset de
demostración incluido (`despensa-logo-color-800w.png`) —nunca de una tabla ni de una regla de
negocio codificada. El wordmark de Rasero **no** preside la tarjeta: baja a marca de sistema
pequeña y discreta **encima** de la tarjeta, fuera de ella. Debajo del logo, con al menos 12px de
aire, va el contexto real, más pequeño y en Tinta Suave: `{sucursal.nombre} · {caja}` —dato real
de `sucursal.nombre`, nunca un literal en JSX—. Si existe un turno anterior en esa sucursal, una
línea más —"Última apertura: [fecha/hora relativa, p. ej. 'hoy, 07:58' o 'ayer, 18:20']" leída del
`instante_apertura` del turno más reciente de esa sucursal— también en Tinta Suave; si no hay
ninguno, esa línea se omite por completo, nunca un placeholder falso. Esta regla **no** crea
ninguna entidad `Negocio` ni `Empresa`. Cualquier texto de marca del comercio que aparezca en el
frontend (p. ej. "Despensa Los Ríos" como pie de datos de demostración) DEBE venir de una variable
de entorno del frontend, nunca de un literal en JSX ni de una tabla. **Razón**: quien abre turno
no necesita que le recuerden qué software usa —lo abre veinte veces por semana—; el logo del
comercio ancla la pantalla en "esta es tu tienda" y, debajo, el nombre de sucursal y caja le
confirman de un vistazo *en qué sucursal y caja está entrando*, que es el dato que ata todas sus
ventas del turno.

**La Regla de la Marca Persistente (reescrita v1.7.0).** Fuera de la apertura de turno —el
momento ceremonial de La Regla de la Identidad del Comercio—, la marca del comercio no
desaparece, pero **las dos marcas no comparten lugar**: la herramienta y el negocio ocupan
**extremos opuestos de la misma barra de navegación**. (1) Al **extremo izquierdo**, el
**wordmark de Rasero** solo — la herramienta. (2) Al **extremo derecho**, el **bloque de
contexto de sesión**: el **ícono del comercio** (autónomo, ya trae su propio fondo de app-icon
—sin tinte, sin filtro—, ≈ 24px, configurable por `VITE_ICONO_COMERCIO`) seguido de dos grupos
separados por una **línea divisoria real de 1px** (`borde-fuerte`, La Regla del Filo — nunca
sombra): «lugar» = `{sucursal.nombre}` en Tinta a `--texto-sm` con `{turno.caja}` debajo en
Tinta Suave a 11px; «operador» = nombre del operador del turno en Tinta con su rol debajo en
Tinta Suave a 11px en versalitas. Todo dato real del contexto de sesión (`sucursal.nombre`,
`turno.caja`, operador resuelto), nunca un literal; el nombre del comercio como texto, si se
quisiera, vendría de una variable de entorno nueva. **No hay footer**: la barra de contexto
inferior de v1.3.1–v1.6.0 se retira y su información sube, mejor distribuida, al extremo derecho
del nav. **Razón**: los mockups comparativos de v1.4.0 rechazaban el ícono del comercio y el
wordmark **al mismo nivel** compitiendo por la misma lectura; ubicarlos en **extremos opuestos**
—herramienta a la izquierda, "dónde estoy / quién soy" a la derecha, con separación visible entre
sus partes— resuelve esa competencia sin gastar una franja entera al pie ni repetir la sucursal y
la caja en el encabezado de cada pantalla (que además las duplicaba). Una pantalla ya no repite
`{sucursal} · {caja}` en su propio encabezado: ese dato vive una sola vez, en el nav. La
jerarquía de los tres usos del activo de marca no cambia: apertura = logo a color en grande una
vez al día; **nav derecho** = ícono + sucursal + caja + operador discretos y permanentes; mono
(`despensa-logo-mono-800w.png`) = reportes, dashboards y la marca de agua de los estados vacíos
(La Regla del Hueco que Enseña). Ningún uso se solapa.

**La Regla del Hueco que Enseña.** Todo estado vacío —ninguna selección hecha, ninguna fila que
mostrar— se compone de tres partes y nunca de una sola línea de texto plano: (1) un ícono propio
en SVG de línea simple (stroke, sin relleno, color Borde o Tinta Suave), nunca un ícono de librería
genérico de "empty state"; (2) un título corto en el registro tipográfico de la pantalla; y (3)
una frase que explica **qué** aparecerá ahí cuando haya datos —nunca "no hay nada" ni "selecciona
algo". Aplica al panel de detalle de Clientes sin selección, a toda lista nueva de Administración
sin registros y a cualquier lista existente que hoy muestre un placeholder plano de una línea.
Detrás de esas tres partes va una **marca de agua del logo mono del comercio**
(`despensa-logo-mono-800w.png`) al **8 % de opacidad**, centrada en el área vacía,
`pointer-events: none`, a un tamaño que no invada ni se recorte contra los bordes del contenedor
—se adapta al alto disponible, no un valor fijo. Es puro refuerzo: no reemplaza ninguna de las
tres partes obligatorias, no lleva texto propio y vive en el componente compartido `EstadoVacio`,
nunca replicada por pantalla. **Razón**: un hueco es la primera pantalla que ve un evaluador que
no conoce el sistema; decirle qué va a vivir ahí es más barato que un manual y convierte el vacío
en una promesa en lugar de un error, y la marca de agua tenue ancla ese vacío en "esta es tu
tienda" sin restarle protagonismo a la frase que enseña.

**La Regla del Pulso, No el Brillo.** Los estados de carga usan un esqueleto compuesto de bloques
rectangulares en #E4E9E4, con el **mismo radio** (2px o 6px según el registro de la pantalla que
reemplazan) y el **mismo layout aproximado** del contenido real que va a cargar —nunca un layout
genérico de barras iguales. La animación es exclusivamente una oscilación de opacidad entre 100% y
55%, 1.6s, ease-in-out, infinita. Queda **PROHIBIDO** cualquier "shimmer" o gradiente que cruce el
bloque de izquierda a derecha: sería importar un gradiente, y los gradientes están prohibidos en
todo el sistema (La Regla del Filo, No la Sombra). Aplica a cualquier pantalla que hoy no muestre
nada mientras espera al backend. **Razón**: el esqueleto honesto anticipa la forma de lo que viene
—cuántas filas, de qué ancho— y hace que la llegada del dato no reacomode la página; el shimmer
sólo llama la atención sobre la espera.

**La Regla del Modal Administrable.** Todo formulario de creación o edición de un dato maestro
(Sucursal, Producto, Categoría, Zona de exhibición, Medio de pago, y la edición de Cliente) usa un
**único componente reutilizable** —`frontend/src/componentes/ModalAdministrable.tsx`— y nunca un
formulario ad-hoc por pantalla. Estructura: velo de fondo en Tinta al 45% de opacidad sobre el
contenido subyacente (nunca negro puro); tarjeta centrada de máximo 420px de ancho, radio 6px
—siempre registro de Análisis, porque administrar un maestro es una decisión gerencial, no una
operación de caja—; header en Superficie Alta con el título en Source Serif 4 y un botón de cierre
circular a la derecha; cuerpo en Superficie Base con los campos; footer en Superficie Alta con
"Cancelar" (borde, sin relleno) y la acción primaria a la derecha. Sin sombra en ningún borde: la
separación velo / tarjeta / header-footer / cuerpo es puro contraste de tono. **Razón**: cinco
pantallas de administración con cinco formularios distintos divergen en un mes; un modal único hace
que "crear un maestro" se vea y se comporte igual en todo el sistema, y que el atajo "+ Crear
producto" desde Venta sea literalmente el mismo componente que la pantalla de Administración.

**La Regla del Filtro y la Página.** Toda lista que pueda crecer sin límite conocido —Clientes,
cupones emitidos, bitácora de pagos, cualquier lista de Administración— usa **paginación real**,
nunca scroll infinito ni carga completa. El componente `frontend/src/componentes/Paginador.tsx`
recibe página actual, total de páginas y un callback de cambio; se ve como el texto "Página X de Y"
en Tinta Suave con flechas anterior/siguiente en SVG de línea simple (chevron, sin relleno),
**deshabilitadas visualmente** (opacidad reducida, no ocultas) en los extremos. Tamaño de página
por defecto: 20. El patrón baja al backend: todo endpoint GET de listado que hoy devuelva todos los
registros acepta `pagina` y `tamano_pagina` (convención de parámetro opcional, como `id_sucursal`)
y devuelve además el total de registros para que el frontend calcule el total de páginas. **Razón**:
una lista sin techo es rápida con los datos de demostración y se cae en producción; fijar la
paginación como regla —y no como parche por pantalla— evita que cada lista nueva reabra la
discusión.

**La Regla del Grupo de Navegación.** El nav principal deja de ser una fila plana de pestañas.
"Venta" queda siempre visible y a un clic, sin agrupar —es la pantalla de uso más frecuente. El
resto se organiza en cuatro grupos con menú desplegable: **Inventario** (Conteo, Entradas,
Traspasos, Capital), **Precios y demanda** (Precios, Competencia, Pronóstico), **Clientes y promos**
(Clientes, Promociones) y **Caja y seguridad** (Arqueo, Caja y fraude, Terminales, Pagos); más un
quinto elemento, **Administración**, que no es grupo sino una pantalla propia, al final de la barra.
Cada grupo es texto + un chevron SVG de línea simple de 10px que gira 180° al abrir con una
transición de 150ms —animación de mecanismo de interfaz, no decorativa, así que no contradice la
restricción de animación del registro de Análisis. El panel desplegable abre debajo, en Superficie
Alta, borde 1px en Borde, radio 2px (es navegación/estructura, no un bloque de Análisis), con
**separadores de 1px en Borde** entre cada opción —una línea real, no sólo padding— y hover en
Superficie Base por opción. Si la pantalla activa está dentro de un grupo, el **texto del grupo**
—no la opción— lleva el mismo subrayado de 2px en Tinta que marca hoy la pestaña activa, para no
perder contexto con el desplegable cerrado. El operador con turno abierto (`turno.id_operador`
resuelto a nombre) se muestra en la barra, alineado a la derecha, en Tinta Suave. **Razón**:
catorce pestañas planas obligan a leer toda la fila cada vez; cuatro grupos más Venta caben de un
vistazo y agrupan por la pregunta que trae al usuario ("vengo a algo de inventario"), y el nombre
del operador en la barra responde "¿de quién es este turno?" sin abrir otra pantalla.

## Do's and Don'ts

### Do:

- **Do** elegir el registro por contexto de uso: Operación (2px, alta densidad, tabla) para caja e
  inventario; Análisis (6px, aire) para pantallas donde se decide.
- **Do** componer toda cifra de dinero y peso con cifras tabulares reales.
- **Do** sacar todo padding, margin y gap de los 7 valores de `--espacio-*`, y todo tamaño de
  texto de la escala `--texto-*` (v1.5.0). Nunca un literal nuevo.
- **Do** usar IBM Plex Sans en todo control, tabla y etiqueta; Source Serif 4 sólo en títulos
  ≥ 20px y prosa de Análisis (La Regla de la Voz de Análisis).
- **Do** transmitir profundidad con el salto de tono #F1F4F1 → #FFFFFF y el borde #D5DCD6.
- **Do** acompañar todo dato incierto o envejecido con sus tres portadores.
- **Do** reservar el Verde Rasero para la acción que compromete dinero, una vez por pantalla —
  y cero veces en una pantalla que no tiene esa acción.
- **Do** dar a toda acción secundaria neutra —la que no cobra y no es semántica— el contorno en
  Acento Secundario #7A6A56 (La Regla del Segundo Tono), nunca dejarla como texto plano suelto.
- **Do** revelar el detalle de un bloque de Análisis con una única transición por selección,
  nunca con hover ni fade-in repetido en cada bloque de la lista.
- **Do** mantener cualquier identificación o dato de contexto (como identificar a un cliente en
  caja) reversible en un toque y fuera del camino crítico de la acción que compromete dinero.

### Don't:

- **Don't** usar `box-shadow` en ninguna parte del sistema.
- **Don't** usar degradados ni fondos oscuros.
- **Don't** usar los semánticos (#9A5B08, #8E2A2A, #1F5673) por énfasis o decoración.
- **Don't** rellenar de Acento Secundario #7A6A56 ni usarlo con función de dinero o de estado:
  es un contorno para la acción secundaria neutra, y un relleno macizo competiría con el botón
  de cobro (La Regla del Segundo Tono).
- **Don't** envolver grupos de datos en tarjetas dentro del registro de Operación.
- **Don't** usar Inter como tipografía por defecto.
- **Don't** poner Source Serif 4 en un botón, un `<label>`, un encabezado de columna o una
  celda — a 13-14px la serif se lee como "sin estilar" (La Regla de la Voz de Análisis).
- **Don't** repetir el Verde Rasero fuera de sus tres usos formalizados (cobro, wordmark,
  acento de nav activo) — nunca en un fondo, nunca en dos elementos de la misma vista.
- **Don't** comunicar antigüedad o incertidumbre solo con color.
- **Don't** animar la aparición de un dato de contexto (como un resumen o valor) que no
  confirma una acción del usuario — la animación se reserva para confirmaciones y revelaciones
  deliberadas, nunca para decorar la llegada de un dato.
- **Don't** usar "shimmer" ni gradiente que cruce un esqueleto de carga (La Regla del Pulso, No
  el Brillo): el esqueleto sólo oscila su opacidad.
- **Don't** mostrar un estado vacío como una sola línea de texto plano — usa ícono, título y la
  frase de qué aparecerá ahí (La Regla del Hueco que Enseña).
- **Don't** poner una foto de producto en una lista: cada fila lleva el ícono SVG de su familia de
  categoría (La Regla del Ícono por Categoría).
- **Don't** escribir un formulario de alta o edición de un dato maestro por pantalla — se usa el
  único `ModalAdministrable` (La Regla del Modal Administrable).
- **Don't** hardcodear el nombre del comercio de demostración en JSX ni en una tabla; viene de
  `sucursal.nombre` real o de una variable de entorno del frontend (La Regla de la Identidad del
  Comercio).

## Historial de versiones del sistema de diseño

`DESIGN.md` lo deriva el agente documenter de Impeccable a partir de la interfaz ya construida, no
de intenciones previas (constitución, "Sistema de Diseño"). Su historial de versiones sigue el
mismo versionado semántico que la constitución: MENOR para una regla o sección nueva, PARCHE para
una aclaración sin cambio de significado.

- **1.0.0** (2026-09-04) — derivación inicial por el agente documenter, a partir de las primeras
  pantallas de `001-core-ventas-inventario`: dos registros (Operación 2px / Análisis 6px), paleta
  de comercio físico, cifras tabulares, cero sombras, tres portadores de incertidumbre.
- **1.1.0** (2026-09-05) — **La Regla del Ícono** (SVG propio o de una única librería coherente,
  nunca un emoji), añadida tras una auditoría retroactiva de `001`–`005` sin hallazgos.
- **1.2.0** (2026-09-06) — esta enmienda: seis reglas nuevas —**Identidad del Comercio**, **Hueco
  que Enseña**, **Pulso, No el Brillo**, **Modal Administrable**, **Filtro y la Página**, **Grupo
  de Navegación**— más **La Regla del Ícono por Categoría** junto a La Regla del Ícono. Todas
  aditivas: no elimina ni redefine ninguna regla previa. Sincronizada con la enmienda **v2.2.7**
  de la constitución.

- **1.2.1** (2026-09-06) — PARCHE: aclara en "Identificar cliente (Operación)" que el alta y la
  edición de un cliente usan `ModalAdministrable` (ya cubierto por La Regla del Modal
  Administrable, que nombra "la edición de Cliente"); el panel flotante conserva sólo la
  búsqueda. No cambia ninguna regla; reconcilia dos partes del mismo documento al construir la
  User Story 4 de `002` (identificador de cliente por cédula/RUC).
- **1.3.0** (2026-09-06) — MENOR: **La Regla de la Identidad del Comercio** se reescribe. La
  cabecera de la pantalla de apertura pasa de bloque Tinta con el nombre de sucursal como
  elemento de mayor peso, a **cabecera de fondo blanco con el logo a color del comercio como
  elemento principal** (el logo a color no está pensado para fondo oscuro); el nombre de
  sucursal y la caja bajan a contexto secundario en Tinta Suave debajo del logo, con la línea
  "Última apertura: …" en formato relativo legible ("hoy, 07:58"). El wordmark de Rasero sigue
  arriba y fuera de la tarjeta. El origen del logo se fija por `VITE_LOGO_COMERCIO` (asset de
  demostración por defecto); ningún dato de marca en literal de JSX ni en tabla. No elimina
  ninguna regla; ninguna otra regla cambia. Sincronizada con la enmienda **v2.2.8** de la
  constitución.
- **1.3.1** (2026-09-07) — MENOR (aditiva): **La Regla de la Marca Persistente**, nueva. El
  ícono del comercio (`despensa-icon-verde-512.png`, 24px, configurable por
  `VITE_ICONO_COMERCIO`) aparece en el nav global al mismo nivel visual que el wordmark de
  Rasero, y un footer nuevo muestra el nombre de la sucursal activa en Tinta Suave. Cierra la
  brecha de que la marca del comercio sólo se veía en la apertura de turno. No modifica ni
  elimina ninguna regla previa. Sincronizada con la enmienda **v2.2.9** de la constitución.
- **1.4.0** (2026-09-07) — MENOR: ronda de diseño transversal tras mockups comparativos
  aprobados. Regla nueva **La Regla del Segundo Tono** (acento secundario tierra #7A6A56 para
  la acción secundaria neutra, tratamiento sólo de contorno). **La Regla de la Marca Persistente**
  se **reescribe**: el nav global queda con el wordmark de Rasero solo y el ícono del comercio
  baja al footer, delante de `{sucursal} · {caja}` en una línea. **La Regla del Hueco que Enseña**
  se **extiende** con una marca de agua del logo mono al 8 % detrás de las tres partes. Actualiza
  la viñeta "Colapsado" del componente "Identificar cliente (Operación)". No elimina ninguna
  regla. Sincronización con la constitución **pendiente** (ver informe de impacto).
- **1.5.0** (2026-09-07) — MENOR: ronda de evolución visual, de "sobrio pero incompleto" a
  "profesional e intencional". Añade escalas tokenizadas —**espaciado** (7 valores),
  **tipografía**, **alturas de control**, **anillo de foco único**— en `tokens.css` y
  `design.json`. Refina, sin reabrir: **La Regla de la Sola Voz** (formaliza el rol del verde:
  cobro + wordmark + acento de nav activo, nada más), **La Regla del Filo** (jerarquía de
  borde de dos niveles, `borde` y `borde-fuerte` #BCC6BD), **Elevation & Depth** (Superficie
  Base #F1F4F1 → #E9EDE9 para un salto de tono perceptible). Regla nueva **La Regla de la Voz
  de Análisis** (Source Serif 4 sólo en títulos ≥20px y prosa; IBM Plex Sans en todo control,
  tabla y etiqueta). Specs de componente nuevas: **Botón** (general), **Campo**, **Encabezado
  de pantalla**. Se evaluó y descartó un tercer radio. No elimina ni invierte ninguna regla.
  Sincronización con la constitución **pendiente** (junto con la de v1.4.0).
- **1.6.0** (2026-09-07) — MENOR: Fase 3b de la ronda de evolución visual (User Story 12 de
  001). Dos añadidos: **La Regla de la Imagen que se Cae con Gracia** —un producto puede llevar
  una foto por URL externa (`producto.url_imagen`, opcional), mostrada por el componente
  compartido `ImagenProducto`, que **siempre** cae al glifo de familia de categoría si no hay
  URL o si el `<img>` falla; imágenes fuera del repositorio, riesgo de disponibilidad aceptado—;
  y el **layout de dos columnas de Venta** (catálogo en grid · ticket, encabezado a lo ancho,
  total + Cobrar anclados abajo, apilado bajo ~1100px). La Regla de la Sola Voz, del Filo y del
  Hueco que Enseña intactas. Sincronización con la constitución **pendiente** (junto con v1.4.0
  y v1.5.0).
- **1.7.0** (2026-09-07) — MENOR: ronda de ajuste de Venta y armazón. **La Regla de la Marca
  Persistente** se **reescribe**: se retira el footer; su contexto (ícono del comercio +
  sucursal + caja) sube al **extremo derecho del nav** junto al operador y su rol, como un
  bloque con divisor real — wordmark y comercio en **extremos opuestos**, no al mismo nivel. Se
  elimina la repetición de `{sucursal} · {caja}` en el encabezado de cada pantalla.
  **"Venta: dos columnas"** se ajusta: el **ticket es el protagonista**, el **catálogo pasa a
  apoyo** (columna estrecha, tarjetas compactas, buscador integrado, 9 por página, **paginador
  numerado anclado abajo**); el "+" es el único disparador de agregar; agregar el mismo
  producto **suma a la cantidad**. `Paginador` gana la variante `numerado`. `SelectorProducto`
  muestra resultados a medida que se escribe, en panel flotante. Ninguna regla se elimina.
  Sincronización con la constitución **pendiente** (junto con v1.4.0–v1.6.0).

**Versión**: 1.7.0 | **Derivada**: 2026-09-04 | **Última enmienda**: 2026-09-07
