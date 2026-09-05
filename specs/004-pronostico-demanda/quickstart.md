# Quickstart: Pronóstico de Demanda

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus reglas difíciles: la serie
observada nunca se toca, la corregida por quiebre siempre queda `>=` la observada, la descensura
se valida contra una serie sintética con demanda verdadera conocida, y ningún pronóstico que no
supere su línea base se presenta como vigente. No contiene código de implementación: eso pertenece
a `tasks.md` y a la fase de implementación.

## Requisitos previos

- `001-core-ventas-inventario` construido y con su esquema aplicado: `venta`, `renglon_venta`,
  `movimiento_inventario`, `existencia`, `lote`, `producto`, `producto_precio_sucursal`,
  `sucursal` deben existir, porque este módulo los **consulta** (nunca escribe en ellos).
- **Bloqueo conocido**: `consulta_no_atendida` (001 User Story 3, tareas T050–T053) **no está
  implementada**. Los escenarios 3 y 6 de abajo se ejecutan igual, pero `respaldo_quiebre` sólo
  tomará el valor `metodo_base` hasta que `001` desbloquee FR-007. La prueba de contrato para el
  camino `consulta_no_atendida` queda escrita y marcada `xfail` hasta entonces.
- `005-promociones-inteligentes` no existe todavía: todos los períodos se tratan como sin
  promoción (FR-030). El gancho de integración se prueba con una marca inyectada manualmente.
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usan `001`/`002`/`003`.
- Python 3.12 y Node.js 20, mismo entorno que el resto de módulos.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0004_pronostico_demanda
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_censura.py tests/unidad/test_pronostico.py
pytest tests/integracion/test_descensura_sintetica.py tests/integracion/test_pronostico_linea_base.py tests/integracion/test_serie_precio_promo.py
pytest tests/contrato/test_contrato_pronostico.py
```

Las seis suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de
fusionar. Sin pruebas de interfaz ni maquetación, por decisión expresa del Principio III.

## Escenarios de validación

Los identificadores entre paréntesis remiten a los requisitos del [spec](./spec.md).

### 1. La serie observada es un registro de hechos (FR-001 a FR-004, User Story 1)

Registra ventas de un producto en una sucursal durante varios días vía `001`. Consulta
`GET /demanda?id_sucursal=...&id_producto=...`.

**Esperado**: `demanda_observada` por período coincide con la cantidad vendida neta de anulaciones
(research.md #3). Cambia un dato de origen que no debería alterar la historia (por ejemplo,
recalcula la ventana) y vuelve a consultar: `demanda_observada` de los períodos ya materializados
no cambia (FR-004).

### 2. Descensura por quiebre: corregida ≥ observada, nunca menor (FR-005 a FR-011, User Story 1)

Un producto con demanda diaria estable ~10 u que se agota durante 3 días (existencia reconstruida
≤ 0 esos días, ventas 0).

**Esperado**: `GET /demanda` muestra, para esos 3 días, `demanda_observada: "0"` y
`demanda_corregida` igual al **máximo** de la demanda observada del producto entre los N (≈30)
días recientes sin quiebre (research.md #5); `correccion_quiebre > 0`;
`respaldo_quiebre: "metodo_base"`. Un día sin quiebre no recibe corrección por este eje
(`correccion_quiebre: "0"`, FR-011).

### 3. Descensura con evidencia de consultas no atendidas (FR-007) — bloqueado por 001

Mismo producto y ventana de quiebre, con registros de `consulta_no_atendida` en `001` para esos
días.

**Esperado cuando 001 implemente su User Story 3**: `respaldo_quiebre: "consulta_no_atendida"` y
la magnitud de la corrección usa ese conteo como evidencia directa, no sólo el método base.
**Hoy**: la prueba de contrato de este camino está marcada `xfail` (no hay forma de crear una
`consulta_no_atendida` porque su endpoint no existe). Ver plan.md, "Estado de implementación por
historia".

### 4. Censura total (FR-012, edge case)

Un producto que estuvo agotado durante todo el histórico disponible y sin ninguna
`consulta_no_atendida`.

**Esperado**: `GET /demanda` devuelve `demanda_corregida: null` con
`estado: "no_estimable_censura_total"` — nunca un `0` ni un valor inventado.

### 5. Validación con serie sintética (FR-013 a FR-017, User Story 2, SC-002)

`POST /demanda-sintetica` con una serie que incluye: nivel base + patrón semanal, dos intervalos
de quiebre con `demanda_latente_verdadera` fijada, un escenario con
`consultas_no_atendidas_sinteticas` y otro sin ellas. Luego
`GET /demanda-sintetica/validacion?id_sucursal=...&id_producto=...`.

**Esperado**: `descensura_mejora_sobre_no_corregir: true` — el `error_medio_descensura` es menor
que el `error_medio_sin_corregir` en ambos caminos (`con_consulta_no_atendida` y
`solo_metodo_base`). Consulta `GET /demanda` de producción para otro producto real: ninguna fila
sintética aparece (FR-017).

### 6. Ajuste cruzado por sustituto (FR-009 b, research.md #6)

Declara `POST /sustituciones` con `id_producto` = azúcar morena, `id_producto_sustituto` = azúcar
blanca. Provoca un quiebre de azúcar morena durante 4 días en el que la azúcar blanca vende por
encima de su propio máximo de N.

**Esperado**: la `demanda_corregida` de la azúcar morena en esos días =
estimado base + exceso observado de azúcar blanca (`ajuste_cruzado_sustituto > 0`), sin reemplazar
el estimado base; la serie de la azúcar blanca muestra `senal_sustitucion` en esos períodos
(FR-033) pero **no** se le descuenta ningún volumen (FR-034). Si la azúcar blanca también estuvo
en quiebre esos días, no hay ajuste ni señal (FR-036).

### 7. Eje de precio sin histórico de precio de 001 (FR-025 a FR-028, User Story 4)

Un producto cuyo `renglon_venta.precio_aplicado` fue $2,00 en la primera mitad del histórico y
$2,40 en la segunda; precio de referencia actual $2,40.

**Esperado**: los períodos a $2,00 se normalizan hacia $2,40 con
`correccion_precio` explicando `precio_vigente_periodo`, precio de referencia y
`elasticidad_usada` (research.md #8b). Un período **sin ventas** aparece con
`precio_vigente_periodo: null` y `correccion_precio: "0"` — "sin corrección de precio" (FR-027), no
un precio inventado.

### 8. Neutralizar un período de promoción (FR-029 a FR-031, User Story 5)

Inyecta manualmente la marca `con_promocion` en un período (simulando la futura entrada de `005`).

**Esperado**: ese período aparece en `demanda_corregida` con `excluido_por_promocion: true`; su
`demanda_observada` no cambia (FR-031); la serie no tiene un hueco silencioso, el período sigue
visible marcado.

### 9. El pronóstico se deriva de la serie corregida y declara su línea base (FR-018 a FR-022, User Story 3)

`GET /productos/{id}/pronostico?id_sucursal=...&horizonte=corto` para un producto con serie
corregida y suficiente histórico.

**Esperado**: `serie_pronosticada` día a día; `factores.nivel_suavizado` y `factores.alfa_usado`
presentes; `periodo_datos_desde`/`hasta` y `valor_linea_base` (promedio móvil de la demanda
**observada sin corregir**, FR-022) presentes. Con `horizonte=medio`, además
`factores.multiplicadores_tramo` (research.md #8d).

### 10. Un pronóstico que no supera la línea base no se presenta vigente (FR-022, SC-004)

Un producto con demanda muy errática donde el suavizado exponencial no mejora al promedio móvil.

**Esperado**: la respuesta trae el pronóstico calculado pero `vigente: false` y
`motivo_no_vigente: "no supera la linea base"`. La interfaz muestra la línea base, no la serie
pronosticada.

### 11. Producto nuevo sin histórico suficiente (FR-023)

`GET /productos/{id}/pronostico` para un producto con menos de N períodos de demanda observada.

**Esperado**: `vigente: false`, `motivo_no_vigente: "datos insuficientes"`, `serie_pronosticada`
vacía — nunca un número por defecto.

### 12. Todo se filtra por sucursal (FR-037)

`GET /demanda?id_sucursal=<Quevedo Centro>` y la misma llamada con `<Buena Fe>` para el mismo
producto.

**Esperado**: series distintas, cada una con su propio `id_sucursal`; no existe ninguna respuesta
del contrato que sume las dos sucursales sin discriminar el origen.

## Comprobaciones de diseño

No llevan prueba automatizada —la interfaz está exenta por el Principio III— pero se verifican a
ojo antes de dar el módulo por terminado:

- `Pronostico.tsx` usa los tokens ya definidos en `frontend/src/estilos/tokens.css`; ningún color,
  radio o tipografía nuevo se incrusta en el componente.
- Toda la pantalla respeta el registro de Análisis (radio 6px, Source Serif 4, aire visual, líneas
  bajo 80 caracteres) — este módulo no toca el registro de Operación en ningún punto.
- La demanda **observada** y la **corregida/pronóstico** se distinguen con los **tres** portadores
  simultáneos: color `estimado` `#1F5673`, forma (línea punteada / punto hueco) y texto explícito
  ("estimado", "corregido por quiebre", "pronóstico"). Nunca sólo color.
- "Datos insuficientes", "no estimable por censura total" y "sin corrección de precio" se comunican
  siempre con texto explícito, nunca sólo con la ausencia de un número.
- El único momento de animación deliberado es al revelar el detalle de por qué un período fue
  corregido; no hay hover por punto ni fade-in por bloque.
- `ValidacionDescensura.tsx` está rotulada de forma inequívoca como **datos sintéticos** y no
  puede confundirse con una vista de producción.
