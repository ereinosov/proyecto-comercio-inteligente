# Quickstart: Promociones Inteligentes

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus reglas difíciles: los tres
mecanismos operan por separado; la reserva del empuje de recompra es de precio y no toca el
inventario de `001`; la aleatorización del experimento es reproducible con semilla y no depende de
la paridad del id; la incrementalidad se juzga con una prueba z de dos proporciones; y la marca de
"promoción activa" que `004` consume aparece en cuanto hay una redención. No contiene código de
implementación: eso pertenece a `tasks.md` y a la fase de implementación.

## Requisitos previos

- **`002-clientes-fidelizacion` completo** (checkpoint `2fd6381`): `cliente`, `visita`,
  `intervalo_compra`, `senal_fuga`, `GET /clientes/cumpleanos`, `POST /clientes/{id}/visitas` y
  `evaluar_fugas_pendientes` deben existir — este módulo los **consulta** (nunca escribe en ellos).
- **`001-core-ventas-inventario` User Story 1 completa** (checkpoint `873228d`): `venta`,
  `renglon_venta`, `existencia`, `producto`, `sucursal`, `turno`, `producto_precio_sucursal` y la
  resolución de precio por sucursal.
- **`004-pronostico-demanda` completo** (checkpoint `41ad08c`): ya tiene el gancho listo para
  consumir `GET /promociones/marca-activa` (hoy trata todo período como sin promoción, FR-030 de
  `004`).
- **Sin bloqueos**: a diferencia de `004` (bloqueado por `consulta_no_atendida` de `001`), ninguna
  historia de `005` espera nada. Ver plan.md, "Estado de implementación por historia".
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usan `001`–`004`.
- Python 3.12 y Node.js 20, mismo entorno que el resto de módulos.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0005_promociones_inteligentes
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Generación de cupones de un rango (tarea, fuera del camino crítico HTTP — patrón de 002)
python -m rasero.tareas.generacion_cupones 2026-09-01 2026-09-30

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_experimento_asignacion.py tests/unidad/test_prueba_z.py tests/unidad/test_promociones_dominio.py
pytest tests/integracion/test_generacion_cupones.py tests/integracion/test_oferta_recompra.py tests/integracion/test_experimento_reactivacion.py tests/integracion/test_marca_promocion_activa.py
pytest tests/contrato/test_contrato_promociones.py
```

Las siete suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de
fusionar. Sin pruebas de interfaz ni maquetación, por decisión expresa del Principio III.

## Escenarios de validación

Los identificadores entre paréntesis remiten a los requisitos del [spec](./spec.md).

### 1. Cupón por fecha fija: fecha llega → cupón, sin medición (FR-001 a FR-006, User Story 1)

Registra en `002` un cliente con fecha de nacimiento el 15 de septiembre. Corre
`POST /promociones/cupones/generacion {desde: "2026-09-01", hasta: "2026-09-30"}`.

**Esperado**: `GET /promociones/cupones?id_cliente=...` devuelve un cupón con
`fecha_objetivo: "2026-09-15"`, `valido_desde: "2026-09-08"`, `valido_hasta: "2026-09-29"`,
`estado: "generado"`. El cupón NO tiene ningún campo de grupo, semilla ni incrementalidad
(contraste con el mecanismo 3).

### 2. Cupón: idempotencia y frontera con `002` (FR-002, FR-003, FR-007)

Corre la generación del escenario 1 **otra vez**, con un rango solapado
(`{desde: "2026-09-10", hasta: "2026-10-10"}`).

**Esperado**: `cupones_generados: 0`, `cupones_ya_existentes: 1` — no se crea un segundo cupón por
la misma `fecha_objetivo` del mismo cliente (`UNIQUE (id_cliente, fecha_objetivo)`). Anonimiza ese
cliente en `002` (o usa uno ya anonimizado) y repite: no aparece en la generación, porque
`GET /clientes/cumpleanos` de `002` ya lo excluye. En ningún momento `005` consultó
`cliente.fecha_nacimiento`.

### 3. Empuje de recompra: reserva de PRECIO, sin tocar inventario (FR-008 a FR-011, User Story 2)

Un cliente de `002` con `intervalo_compra.estado = "calculado"` (>= 3 visitas), intervalo esperado
~20 días, que compró el mismo producto en 4 de sus últimas 6 visitas, y que lleva 17 días sin
comprar (85 % de su intervalo). Corre `POST /promociones/ofertas-recompra/deteccion {id_sucursal: ...}`.

**Esperado**: `GET /promociones/ofertas-recompra?id_cliente=...` devuelve una oferta de ese
producto con `precio_garantizado` = precio resuelto para la sucursal − 8 %,
`estado_reserva: "vigente"`, `desenlace: "pendiente"`, `justificacion.compras_del_producto: 4`.
**Verifica en `001`**: no se creó ningún `movimiento_inventario` ni cambió `existencia` — la
reserva es sólo de precio (FR-010, FR-011).

### 4. Empuje de recompra: una oferta activa por par, y vencimiento (FR-014, Edge Cases)

Corre la detección del escenario 3 **otra vez**.

**Esperado**: `ofertas_propuestas: 0`, `ofertas_ya_activas: 1` — el índice único parcial
`(id_cliente, id_producto) WHERE desenlace = 'pendiente'` impide la segunda. Adelanta el reloj más
allá de `reserva_hasta` sin que el cliente compre y consulta: `estado_reserva: "vencida"`,
`desenlace: "reserva_vencida"`. No hubo stock que liberar (nunca se apartó).

### 5. Reactivación: aleatorización reproducible y no sesgada (FR-016, FR-017, SC-005, SC-006)

**Preparación (datos de demostración del examen, research.md #10c)**: carga el juego sintético de
reactivación con `python -m rasero.semilla_reactivacion` — **325 clientes** de "Despensa Los Ríos"
con `senal_fuga` activa. Los 325 son **margen operativo** sobre el mínimo real que el diseño exige,
`n* = 242`; no son un parámetro del modelo. La utilidad crea los clientes con los servicios
públicos de `002`/`001`, nunca escribiendo directo en `senal_fuga`.

Corre `POST /promociones/experimentos {semilla: 20260905}` dos veces (borrando el primer
experimento entre medias, o comparando las asignaciones).

**Esperado**: `n_elegibles: 325`, `tamano_minimo_muestra: 121`, `veredicto: "en_curso"` (325 ≥
242). Con la misma semilla y los mismos elegibles, `GET .../asignaciones` devuelve **exactamente**
los mismos clientes en los mismos grupos (SC-005). La proporción de `id_cliente` pares en el grupo
tratamiento **no** difiere significativamente de la del control (SC-006): la asignación no es
predecible por la paridad del id. Cambia la semilla → grupos distintos.

### 6. Reactivación: sólo el tratamiento recibe descuento; 005 no toca `senal_fuga` (FR-018, FR-028)

Sobre el experimento del escenario 5, revisa `GET .../asignaciones?grupo=control`.

**Esperado**: ningún cliente de control tiene una `redencion_promocion` de tipo `reactivacion`
posible — `POST /promociones/redenciones` con la `id_asignacion_experimento` de un control devuelve
`400`. Verifica en `002` que las `senal_fuga` de todos los asignados **no cambiaron de estado** por
crear el experimento (FR-028): siguen `activa`, con su `instante_deteccion` intacto.

### 7. Reactivación: cierre, incrementalidad y prueba z (FR-019 a FR-024, User Story 3)

Con el experimento del escenario 5 (grupos de 162 y 163), simula las visitas de retorno de la
ventana de 42 días a las tasas del juego sintético (`simular_retornos`, research.md #10c):
**47 de 162** en tratamiento (~29 %) y **24 de 163** en control (~15 %). Corre
`POST /promociones/experimentos/{id}/cierre`.

**Esperado**: `retorno_tratamiento: "0.2901"`, `retorno_control: "0.1472"`,
`incrementalidad: "0.1429"`; `estadistico_z` y `valor_p` coinciden con el cálculo a mano
(proporción agrupada 0,2185; error estándar 0,04584; `z ≈ 3,12`; `p ≈ 0,0018`);
`veredicto: "efectivo"` porque `incrementalidad > 0` y `valor_p < 0,05`. Repite el cierre: idéntico
resultado (idempotente). Con la semilla fija `20260905` y estas tasas, el veredicto `efectivo` es
**reproducible** entre corridas de la demo (research.md #10c).

### 8. Reactivación: incrementalidad no significativa y negativa (FR-021, Edge Cases)

Repite el escenario 7 con **30 de 162** retornos de tratamiento y **26 de 163** de control
(`incrementalidad ≈ 0,026`, proporción agrupada 0,172, `z ≈ 0,61`, `p ≈ 0,54`).

**Esperado**: `veredicto: "no_efectivo"` — la diferencia no es significativa. Con **22 de 162** de
tratamiento y **30 de 163** de control (`incrementalidad ≈ −0,048`): `veredicto: "no_efectivo"`, la
incrementalidad negativa se registra tal cual y la interfaz la muestra como contraproducente, nunca
recortada a cero.

### 9. Reactivación: muestra insuficiente (FR-025)

Sobre una base **distinta** con sólo **90 clientes** con `senal_fuga` activa (no el juego de 325 de
la demo), corre `POST /promociones/experimentos`.

**Esperado**: `201` con `veredicto: "muestra_insuficiente"`,
`motivo_muestra_insuficiente: "90 elegibles, mínimo 242 (MDE 15 pp, poder 0,80)"`, sin
`n_tratamiento` / `n_control`, sin asignaciones creadas. `POST .../cierre` sobre él devuelve `409`.

### 10. Redención del cupón (User Story 1) y marca de "promoción activa" para 004 (User Story 4) (FR-005, FR-030 a FR-034, SC-009)

Un cliente redime su cupón del escenario 1 en una venta de `001` de la sucursal Quevedo Centro el
15 de septiembre (el cajero cobra menos; la venta se completa en `001` de forma normal). Luego
`POST /promociones/redenciones {id_venta: ..., tipo_origen: "cupon", id_cupon: ...}`.

**Esperado — parte de US1** (`POST /promociones/redenciones`, ya disponible en el MVP): el cupón
pasa a `estado: "redimido"`; por conteo directo, no se creó ningún `movimiento_inventario` ni
cambió `existencia`/`venta`/`renglon_venta`.

**Esperado — parte de US4** (`GET /promociones/marca-activa`, disponible al cerrar US4):
`GET /promociones/marca-activa?id_sucursal=<Quevedo Centro>&desde=2026-09-15&hasta=2026-09-15`
devuelve una fila por **cada producto** de esa venta (el cupón sin `id_producto` se expande vía
`renglon_venta`), con `tipos: ["fecha_fija"]`. Un producto no vendido ese día no aparece. La misma
consulta para Buena Fe devuelve vacío — nunca se agregan dos sucursales (FR-035).

### 11. La redención se registra después de la venta, nunca la bloquea (User Story 1, Principio II)

Detén el servicio de `005`. Completa una venta en `001` con un descuento aplicado por el cajero.

**Esperado**: la venta se cierra con normalidad en `001`. Reinicia `005` y registra la redención
con `POST /promociones/redenciones` — se acepta igual (la venta ya existe). `005` nunca fue camino
crítico del cobro.

### 12. Idempotencia de la redención (User Story 1, FR-005)

Repite el `POST /promociones/redenciones` del escenario 10 con el mismo `id_cupon`.

**Esperado**: `200` (no `201`) con la misma `id_redencion_promocion` — el índice único parcial
sobre `id_cupon` impide la segunda fila.

## Comprobaciones de diseño

No llevan prueba automatizada —la interfaz está exenta por el Principio III— pero se verifican a
ojo antes de dar el módulo por terminado:

- `Promociones.tsx` y sus componentes usan los tokens ya definidos en
  `frontend/src/estilos/tokens.css`; ningún color, radio o tipografía nuevo se incrusta.
- `Promociones.tsx` respeta el registro de **Análisis** (radio 6px, Source Serif 4, aire visual,
  líneas bajo 80 caracteres): es una decisión gerencial, no operación de caja.
- `AplicarPromocionVenta.tsx`, montado dentro de `Venta.tsx`, respeta el registro de **Operación**
  (radio 2px, IBM Plex Sans con cifras tabulares, sin animación salvo confirmación) y **no bloquea**
  el cobro — mismo patrón que `IdentificarCliente.tsx` de `002`.
- El resultado del experimento distingue **dato** (% de retorno observado de cada grupo, tinta
  normal) de **inferencia** (incrementalidad, z, p, veredicto) con los **tres** portadores: color
  `estimado` `#1F5673`, forma, y texto explícito ("z = 2,63 · p = 0,004 · significativa").
- "Muestra insuficiente", "reserva vencida", "sin cupón vigente" y "no significativa" se comunican
  siempre con texto explícito, nunca sólo con la ausencia de un número o con color.
- El único momento de animación deliberado es al revelar el detalle de un experimento cerrado; no
  hay hover por fila ni fade-in por tarjeta.
