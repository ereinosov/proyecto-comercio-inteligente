---
version: 1
slug: "frontend-src-pantallas-venta-tsx"
primary_target: "frontend/src/pantallas/Venta.tsx"
related_targets: []
---

Alcance: pantalla de Venta del punto de venta (001-core-ventas-inventario). Modo: Operate.

Audiencia y tarea: el cajero cobra con clientes esperando, mezclando productos por unidad y
productos a peso leídos en báscula. Acción: cerrar la venta. Contenido real: catálogo vía
GET /productos, venta vía POST /ventas (backend construido y verificado). Restricciones:
ninguna validación de existencias bloquea el cobro; saldo negativo se acepta y se advierte;
la venta es idempotente por clave generada antes del primer intento.

Momento memorable: la fila que se abre en el sitio para pesar y se cierra confirmada, sin que
el cajero cambie nunca de contexto.

Decisiones sin resolver: ninguna de composición; el mundo visual está fijado por la
constitución (v2.2.2, sección Sistema de Diseño) y no admite alternativas de paleta ni
tipografía.

## Direction contract

THESIS: la venta es una sola tabla que se edita a sí misma. Rechaza el arreglo por defecto de
la categoría —catálogo a un lado, ticket al otro, formulario modal para el peso— porque cada
uno de esos saca al cajero del renglón que está cobrando.

OWN-WORLD: registro de Operación de Rasero. Superficie base #F1F4F1 con planos altos #FFFFFF,
tinta #1B2621 y tinta suave #5A6862, borde #D5DCD6, marca #0F5132 solo en la acción de cobro.
Semánticos reservados: atención #9A5B08 (stock bajo), crítico #8E2A2A (caducado/anomalía),
estimado #1F5673 (valor calculado). IBM Plex Sans con cifras tabulares reales. Radio 2px.
Sin tarjetas, sin degradados, sin fondos oscuros. Reconocible con todo el contenido quitado
por la densidad tabular y el filo de 2px.

STORY: el cajero entiende que todo el cobro vive en una sola tabla; cree que no perderá el hilo
al pesar un producto; y cierra la venta sin haber salido de esa tabla ni una vez.

FIRST VIEWPORT: barra superior fina con operador, sucursal y caja del turno abierto. Debajo,
a todo el ancho, la tabla de renglones: producto, cantidad, precio aplicado, importe, todas
las cifras alineadas por dígito a la derecha. La fila activa se expande en el sitio revelando
su captura de peso o cantidad. Al pie, anclado, el total en la escala tipográfica mayor de la
pantalla y a su derecha la acción de cobro en #0F5132, el único bloque de marca del viewport.

FORM: tabla de fila expansible; índice 5 de mi lista ordenada, carta que lideró el reparto.
Seed key 19f69875 (scope surface, mode operate, dealt 5/1/4).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
verdict, DESIGN.md, and every shipping raster carrying its provenance.
