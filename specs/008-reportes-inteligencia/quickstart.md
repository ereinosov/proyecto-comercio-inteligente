# Quickstart — 008-reportes-inteligencia

Escenarios de extremo a extremo (TestClient sobre PostgreSQL real, puerto 5442). Todos como
`encargado`. Un solo lugar donde se ve que las cuatro vistas cumplen juntas.

## Preparación común

1. Dos sucursales activas (Quevedo Centro, Buena Fe — nombres de fila, nunca literales de
   código).
2. Un operador `encargado` con turno abierto → token `Authorization: Bearer`.
3. Datos sembrados por sucursal para el mes en curso: ventas, entradas de inventario (para
   costo/margen), mermas, un arqueo descuadrado, un experimento de reactivación cerrado.

## Escenario 1 — Comparativo entre sucursales (User Story 1)

- Sembrar en Quevedo: ventas por 5 000 USD en 300 tickets, margen ponderado ~22 %, merma
  valorada 40 USD. En Buena Fe: 3 200 USD en 210 tickets, margen ~17 %, merma 95 USD.
- `GET /reportes/comparativo?periodo_inicio=<1º del mes>&periodo_fin=<hoy>`.
- **Esperado**: `comparable=true`; dos entradas en `sucursales`; la fila `margen_ponderado` tiene
  la celda de Buena Fe con `diferencia_relativa` "-5 pp vs. Quevedo Centro" y `atencion=true`, la
  de Quevedo sin `diferencia_relativa` y `atencion=false`; la fila `merma_valorada` marca Buena
  Fe con atención (más merma = peor). Cada `valor` coincide con la suma/promedio calculado a mano
  de los datos sembrados.
- Segunda llamada sin `actualizar` → mismo `instante_calculo` (vino de caché).
  `?actualizar=true` → `instante_calculo` nuevo, mismo contenido.

## Escenario 2 — Una sola sucursal (User Story 1, edge)

- Desactivar Buena Fe y sembrar actividad sólo en Quevedo.
- `GET /reportes/comparativo?...`.
- **Esperado**: `comparable=false`; una sola entrada en `sucursales`; ninguna celda con
  `diferencia_relativa`; el frontend muestra la nota "no hay otra sucursal para comparar". Cero
  columnas vacías, cero "N/A".

## Escenario 3 — Tendencia de ventas por semana (User Story 2)

- Sembrar ventas diarias variables durante 10 semanas en Quevedo (zona `America/Guayaquil`),
  incluida una venta a las 23:30 hora local del domingo de la semana 5.
- `GET /reportes/tendencia?indicador=ventas&granularidad=semana&id_sucursal=<quevedo>&periodos=10`.
- **Esperado**: ~10–11 puntos; la venta del domingo 23:30 cae en la semana 5, no en la 6; cada
  `valor` es la suma exacta de los días de esa semana local; el primer punto, si el rango
  empieza a media semana, tiene `completo=false`.
- `id_sucursal` omitido → cada punto es la **suma** de Quevedo + Buena Fe para esa semana (no un
  promedio).

## Escenario 4 — Tendencia de un indicador no disponible (User Story 2, edge)

- `GET /reportes/tendencia?indicador=demanda_producto&id_producto=<producto sin historial>&granularidad=mes`.
- **Esperado**: `disponible=false`, `razon` explícita ("el producto no tiene historial
  suficiente para una serie de demanda"), `puntos=[]`. Cero puntos en cero.

## Escenario 5 — Tablero de KPIs (User Story 3)

- Sembrar: ventas de la semana (1 240 USD, 88 tickets), 3 productos con margen bajo, una merma
  del mes (120 USD), 2 anomalías de caja abiertas, un experimento cerrado "efectivo" el
  2026-08-20, 4 clientes con fuga activa.
- `GET /reportes/tablero`.
- **Esperado**: tarjeta Ventas → "1 240 USD · 88 tickets · 14,09 USD · semana del <fecha>";
  tarjeta Márgenes → "3 productos con margen bajo" con `atencion=true`; tarjeta Fraude →
  "2 anomalías abiertas" `atencion=true`; tarjeta Promociones → "Efectivo · cerrado 2026-08-20";
  tarjeta Clientes → "4 con señal de fuga" `atencion=true`. Cada tarjeta declara su
  `periodo_referencia` (puede diferir entre tarjetas).

## Escenario 6 — Tablero con datos insuficientes (User Story 3, edge)

- Sistema recién sembrado sin ninguna venta esta semana.
- `GET /reportes/tablero`.
- **Esperado**: la tarjeta Ventas tiene `sin_datos=true`, `razon="datos insuficientes para el
  período"`. Nunca "0 USD".

## Escenario 7 — Recálculo de segmentos determinista (User Story 4)

- Sembrar ~40 clientes con tres patrones deliberados:
  - **A** (12 clientes): 8+ visitas, intervalo corto, margen alto, última visita hace < 10 días.
  - **B** (12 clientes): 6+ visitas históricas, última visita hace > 60 días (dejaron de venir).
  - **C** (10 clientes): 3–4 visitas espaciadas, margen bajo.
  - **D** (6 clientes): 1 sola visita.
- `POST /reportes/segmentos/recalculo`.
- **Esperado**: 3 o 4 grupos + `sin_clasificar`; los 6 clientes de D en `sin_clasificar`; ≥ 80 %
  de A juntos, ≥ 80 % de B juntos, ≥ 80 % de C juntos; cada grupo con `descripcion` derivada del
  centroide (el grupo de A ≈ "vienen seguido, dejan buen margen, compraron hace poco"; el de B ≈
  "…compraron hace mucho").
- Segundo `POST /reportes/segmentos/recalculo` sin cambiar datos → `asignacion_segmento` idéntica
  para el 100 % de los clientes; sólo cambia `corrida`.

## Escenario 8 — Base insuficiente para segmentar (User Story 4, edge)

- Sistema con sólo 2 clientes clasificables.
- `POST /reportes/segmentos/recalculo`.
- **Esperado**: `409` con `codigo` de base insuficiente, o (según calibración) una corrida con
  tantos grupos como clientes distintos permitan y una nota. Nunca se fuerzan 3–4 grupos.

## Escenario 9 — Etiqueta de segmento en el detalle de un cliente (User Story 4, frontera 002)

- Tras el escenario 7, `GET /reportes/segmentos/cliente/<un cliente de A>`.
- **Esperado**: `etiqueta_grupo` del grupo de A, `descripcion` derivada, `corrida` = la del
  recálculo. El detalle de cliente de la pantalla de Clientes (002) muestra esa etiqueta como
  dato de lectura; `GET /clientes/{id}` de 002 **no** gana ningún campo nuevo.

## Escenario 10 — Solo lectura sobre 001–007 (SC-006)

- Antes de cualquier llamada a `/reportes/*`, contar filas de `venta`, `cliente`, `merma`,
  `margen_calculado`.
- Ejecutar los escenarios 1, 3, 5, 7.
- **Esperado**: los conteos de `venta`, `cliente`, `merma`, `margen_calculado` (y todo el resto
  de 001–007) **no cambian**. Sólo cambian `agregado_reporte`, `segmento_cliente`,
  `asignacion_segmento`.

## Escenario 11 — Rol (constitución v2.5.0)

- `GET /reportes/tablero` sin token → `401 sesion_invalida`.
- Con token de un `cajero` → `403 rol_insuficiente`.
- Con token de un `encargado` → `200`.
