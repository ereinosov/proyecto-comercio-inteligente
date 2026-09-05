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

### Named Rules

**La Regla de los Tres Portadores.** Ningún dato con antigüedad o incertidumbre se comunica solo
con color. Un portador único falla ante daltonismo, impresión en blanco y negro y reflejo de
pantalla — las tres condiciones normales de un local comercial.

## Do's and Don'ts

### Do:

- **Do** elegir el registro por contexto de uso: Operación (2px, alta densidad, tabla) para caja e
  inventario; Análisis (6px, aire) para pantallas donde se decide.
- **Do** componer toda cifra de dinero y peso con cifras tabulares reales.
- **Do** transmitir profundidad con el salto de tono #F1F4F1 → #FFFFFF y el borde #D5DCD6.
- **Do** acompañar todo dato incierto o envejecido con sus tres portadores.
- **Do** reservar el Verde Rasero para la acción que compromete dinero, una vez por pantalla.

### Don't:

- **Don't** usar `box-shadow` en ninguna parte del sistema.
- **Don't** usar degradados ni fondos oscuros.
- **Don't** usar los semánticos (#9A5B08, #8E2A2A, #1F5673) por énfasis o decoración.
- **Don't** envolver grupos de datos en tarjetas dentro del registro de Operación.
- **Don't** usar Inter como tipografía por defecto.
- **Don't** comunicar antigüedad o incertidumbre solo con color.
