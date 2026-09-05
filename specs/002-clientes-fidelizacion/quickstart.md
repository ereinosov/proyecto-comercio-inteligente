# Quickstart: Clientes y Fidelización

**Fase 1** · 2026-09-04 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus tres reglas difíciles: el
intervalo de compra es siempre por cliente, la fuga confirmada dispara retención (no borrado
inmediato), y el valor de cliente no es un ranking por monto. No contiene código de
implementación: eso pertenece a `tasks.md` y a la fase de implementación.

## Requisitos previos

- El módulo `001-core-ventas-inventario` ya construido y con su esquema aplicado: `venta`,
  `renglon_venta`, `lote` y `movimiento_inventario` deben existir, porque `visita` los referencia
  y `margen_resolver.py` los consulta (research.md #2).
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usa `001`.
- Python 3.12 y Node.js 20, mismo entorno que `001`.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0002_clientes_fidelizacion
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

La tarea de anonimización no corre junto al servidor; se invoca aparte (o se programa con el
planificador del sistema operativo fuera de este plan):

```bash
python -m rasero.tareas.anonimizar_clientes
```

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_intervalo_compra.py tests/unidad/test_fuga_cliente.py tests/unidad/test_valor_cliente.py
pytest tests/integracion/test_visita_desde_venta.py tests/integracion/test_anonimizacion.py
pytest tests/contrato/test_contrato_clientes.py
```

Las seis suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de fusionar.
Sin pruebas de interfaz ni maquetación, por decisión expresa del Principio III.

## Escenarios de validación

Los identificadores entre paréntesis remiten a los requisitos del [spec](./spec.md).

### 1. Registrar cliente y su primera visita (FR-001 a FR-005, User Story 1)

Registra un cliente con nombre y fecha de nacimiento. Completa una venta en `001` identificando a
ese cliente, y llama `POST /clientes/{id_cliente}/visitas` con el `id_venta` resultante.

**Esperado**: la visita queda con `monto_total` igual al total de la venta y `margen_relativo`
(un ratio, ej. 0.25 = 25%, no un monto) calculado por `margen_resolver.py`. `intervalo_compra` de
ese cliente sigue en
`datos_insuficientes` (una sola visita no basta).

### 2. Venta sin cliente identificado (FR-004)

Completa una venta en `001` sin identificar ningún cliente.

**Esperado**: no se crea ninguna visita, ningún cliente cambia de valor ni de estado de fuga. La
venta en sí es indistinguible de cualquier otra venta de `001`.

### 3. Intervalo esperado y umbral de "datos insuficientes" (FR-006, FR-007, SC-001, SC-004)

Registra un cliente con exactamente 2 visitas separadas por 10 días. Consulta su detalle.

**Esperado**: `intervalo_compra.estado = 'datos_insuficientes'`, `intervalo_esperado_dias = null`.
El cliente no aparece como "en riesgo" ni como "sin riesgo" en ningún listado: aparece marcado
explícitamente como datos insuficientes. Añade una tercera visita 12 días después de la segunda.

**Esperado ahora**: `estado = 'calculado'`, `intervalo_esperado_dias` es la mediana de los
intervalos observados (10 y 12 → 11).

### 4. Señal de fuga activa y resuelta (FR-008, FR-009, User Story 3)

Con el cliente del escenario anterior (intervalo esperado de 11 días), deja pasar más de 11 días
sin una nueva visita.

**Esperado**: aparece una `senal_fuga` en estado `activa`, con `instante_deteccion` poco después de
cumplirse el umbral. Registra una nueva visita de ese cliente.

**Esperado**: la señal pasa a `resuelta`, con `instante_resolucion` igual al instante de esa
visita. La señal no se borra: sigue consultable con su histórico completo.

### 5. Fuga confirmada, retención y anonimización (FR-014, FR-015, FR-016)

Con un cliente cuyo intervalo esperado es de 20 días, deja pasar 100 días sin visita (5× su
intervalo, y menor que el piso de 12 meses, así que aplica el piso).

**Esperado**: a los 20 días la señal pasa a `activa`; al llegar a 365 días sin visita (el piso de
FR-014, mayor que 5×20=100), pasa a `confirmada`, con `instante_purga_programada` = fecha de
confirmación + 90 días. Ejecuta `anonimizar_clientes_vencidos()` antes de esa fecha: el cliente
**no** cambia. Avanza el reloj más allá de `instante_purga_programada` y vuelve a ejecutar la
tarea.

**Esperado**: `cliente.anonimizado = true`, `nombre`/`fecha_nacimiento`/`contacto` en `null`,
`id_cliente` y su `senal_fuga`/`intervalo_compra` siguen consultables con sus valores agregados
intactos.

### 6. Cancelación de la anonimización por regreso del cliente (FR-015, edge case)

Repite el escenario 5, pero antes de que venza `instante_purga_programada`, registra una nueva
visita de ese cliente.

**Esperado**: la señal pasa a `resuelta`, `instante_purga_programada` se limpia, y una ejecución
posterior de `anonimizar_clientes_vencidos()` no toca a ese cliente.

### 7. El valor de cliente no es un ranking por monto (FR-010, FR-011, SC-002)

Crea el cliente **A**: 3 visitas muy espaciadas (intervalo esperado grande, o sea baja
frecuencia) y de monto alto cada una, margen bajo. Crea el cliente **B**: 4 visitas seguidas y
cercanas entre sí (intervalo esperado corto, alta frecuencia), de monto moderado cada una, margen
alto. Ambos necesitan el mínimo de 3 visitas de la regla #3 de `research.md` — con menos, quedan
en `datos_insuficientes` y quedan fuera de cualquier ranking (FR-007), no simplemente "más abajo".
El monto total acumulado de A es mayor que el de B.

**Esperado**: en `GET /clientes?orden=monto_total`, A aparece antes que B. En
`GET /clientes?orden=valor` (o en el listado por defecto), B puede aparecer antes que A, porque su
percentil de frecuencia y de margen compensan su menor monto total — el orden compuesto no es el
mismo que el de monto total simple.

### 8. Resumen en Operación vs. desglose en Análisis (FR-011, Sistema de Diseño)

Identifica al cliente B del escenario anterior durante una venta en `Venta.tsx`.

**Esperado**: se muestra únicamente su puntuación compuesta, sin desglose, sin animación de
revelación (no es una confirmación de acción del cajero). Abre luego su detalle en la pantalla
`Clientes.tsx` (registro de Análisis).

**Esperado**: se revela el desglose de las tres dimensiones con el momento de animación
deliberado que cita la constitución para este registro, radio de 6px y tipografía Source Serif 4.

### 9. Cumpleañeros expuestos sin acción propia (FR-012, FR-013)

Registra un cliente cuya fecha de nacimiento cae dentro de los próximos 7 días. Llama
`GET /clientes/cumpleanos?desde=<hoy>&hasta=<hoy+7>`.

**Esperado**: el cliente aparece en la respuesta. Ningún cupón, descuento ni notificación se genera
desde este módulo: la respuesta es solo datos para que `005-promociones-inteligentes` decida.

## Comprobaciones de diseño

No llevan prueba automatizada —la interfaz está exenta por el Principio III— pero se verifican a
ojo antes de dar el módulo por terminado:

- `Clientes.tsx` usa los tokens ya definidos en `frontend/src/estilos/tokens.css`; ningún color,
  radio o tipografía nuevo se incrusta en el componente.
- El resumen compuesto en `Venta.tsx` respeta el registro de Operación (radio 2px, IBM Plex Sans,
  sin tarjeta); el desglose en `Clientes.tsx` respeta el de Análisis (radio 6px, Source Serif 4,
  aire visual, líneas bajo 80 caracteres).
- El estado de fuga se comunica siempre con tres portadores (color, forma, texto de antigüedad),
  nunca solo color.
- El único momento de animación deliberado de este módulo es al revelar el detalle de un cliente
  en `Clientes.tsx`; no hay hover por fila ni fade-in por tarjeta en ningún registro.
