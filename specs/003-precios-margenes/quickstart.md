# Quickstart: Precios y Márgenes

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus reglas difíciles: el margen se
recalcula siempre al leer, ninguna sugerencia se aplica sola, la colocación sigue al margen (no al
rol), y `002-clientes-fidelizacion` deja de usar su fórmula interina. No contiene código de
implementación: eso pertenece a `tasks.md` y a la fase de implementación.

## Requisitos previos

- `001-core-ventas-inventario` ya construido y con su esquema aplicado: `producto`,
  `producto_precio_sucursal`, `zona_exhibicion`, `lote`, `existencia`, `observacion_precio` y
  `canal_competencia` deben existir, porque este módulo los consulta (y escribe en
  `producto_precio_sucursal` al aplicar una sugerencia de precio).
- `002-clientes-fidelizacion` ya construido, para validar la migración de FR-022.
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usan `001`/`002`.
- Python 3.12 y Node.js 20, mismo entorno que `001`/`002`.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0003_precios_margenes
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_margen_calculado.py tests/unidad/test_sugerencias.py
pytest tests/integracion/test_aplicar_sugerencia.py tests/integracion/test_migracion_margen_visita.py
pytest tests/contrato/test_contrato_precios.py
```

Las cinco suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de
fusionar. Sin pruebas de interfaz ni maquetación, por decisión expresa del Principio III.

## Escenarios de validación

Los identificadores entre paréntesis remiten a los requisitos del [spec](./spec.md).

### 1. Margen real de un producto (FR-001 a FR-004, User Story 1)

Un producto con costo vigente $6 y precio $10 en una sucursal sin override.

**Esperado**: `GET /productos/{id}/margen?id_sucursal=...` responde `margen: 0.40`,
`confiable: true`. Cambia el costo vigente (nueva compra a otro costo) y vuelve a consultar.

**Esperado ahora**: el margen refleja el nuevo costo de inmediato — no hace falta esperar ninguna
tarea de fondo (research.md #4).

### 2. Margen no calculable y no confiable (FR-003, FR-004, edge cases)

Un producto sin ninguna existencia con lote en la sucursal.

**Esperado**: `margen: null`, sin sustituirlo por cero. Un producto con costo vigente de $0 o
negativo (dato de origen inconsistente).

**Esperado**: `margen` se calcula igual pero `confiable: false`, con el costo como causa señalada.

### 3. Precio por sucursal resuelto contra el override (FR-001, FR-050 de 001)

Un producto con precio base $10 y un override de $9 declarado solo en Buena Fe.

**Esperado**: `GET /productos/{id}/margen?id_sucursal=<Quevedo Centro>` resuelve el margen contra
$10; la misma llamada con `id_sucursal=<Buena Fe>` lo resuelve contra $9.

### 4. Clasificar el rol de un producto (FR-005 a FR-007, User Story 2)

`PUT /productos/{id}/rol` con `rol: gancho_trafico`.

**Esperado**: `GET` posteriores del mismo producto reflejan el rol. Un producto nunca clasificado
aparece en cualquier sugerencia marcado explícitamente "sin clasificar" (FR-007), nunca con un rol
supuesto.

### 5. Sugerencia de precio con y sin competencia (FR-008 a FR-011, User Story 3)

Un producto **gancho de tráfico** con una observación de competencia normalizada por debajo del
precio vigente, capturada hace 2 días.

**Esperado**: `GET .../sugerencia-precio` sugiere igualar o bajar hacia el precio de competencia,
sin cruzar el costo vigente como piso, y `observacion_competencia_usada` muestra esa observación
con `dias_de_antiguedad: 2`. El mismo producto sin ninguna observación de competencia.

**Esperado**: la sugerencia mantiene el precio vigente y `observacion_competencia_usada: null`
("sin referencia de competencia", FR-010).

### 6. La sugerencia nunca se aplica sola (FR-012, FR-013)

Genera una sugerencia de precio y espera sin llamar a `/aplicar`.

**Esperado**: `GET /productos/{id}/margen` sigue mostrando el precio vigente original — la
sugerencia no cambió nada. Llama a `/sugerencia-precio/aplicar` con esa `id_sugerencia_precio`.

**Esperado**: `producto_precio_sucursal` (de `001`) queda creado o actualizado con el precio
sugerido, y la sugerencia queda con `aplicada: true` y su `instante_aplicacion`.

### 7. Colocación sigue al margen, no al rol (FR-015 a FR-019, User Story 4, Lectura Crítica n.º 3)

Dos productos de la misma sucursal: uno con margen alto clasificado como gancho de tráfico, otro
con margen bajo clasificado como generador de margen (caso deliberadamente cruzado).

**Esperado**: `GET .../sugerencia-colocacion` sugiere la zona de mayor `grado_privilegio` para el
producto de **margen alto** (el gancho de tráfico de este ejemplo), no para el que tiene el rol
"generador de margen" — el ranking depende del margen real, el rol solo aparece en la explicación
(research.md #6).

### 8. Sin zonas catalogadas (FR-018)

Una sucursal sin ninguna `zona_exhibicion` registrada en `001`.

**Esperado**: `GET .../sugerencia-colocacion` responde `404` indicando que no hay zonas
disponibles, sin inventar ninguna.

### 9. Migración del margen de `002` (FR-022, contrato de research.md #8)

Antes de la migración: registra una venta con un producto vía `001`, identifica cliente y crea su
`visita` en `002` (flujo ya existente). Después de la migración de `margen_resolver.py`: repite el
mismo flujo con un producto cuyo margen real ya está calculado en `003`.

**Esperado**: `visita.margen_relativo` de la nueva venta coincide con el margen que
`servicios/margenes.resolver_margen_producto` de `003` devuelve para ese producto y sucursal en ese
instante (ponderado por monto si la venta tiene más de un renglón, misma fórmula ya documentada en
research.md #4 de `002`). Una `visita` creada **antes** de la migración conserva su
`margen_relativo` original, sin recalcularse retroactivamente.

## Comprobaciones de diseño

No llevan prueba automatizada —la interfaz está exenta por el Principio III— pero se verifican a
ojo antes de dar el módulo por terminado:

- `Precios.tsx` usa los tokens ya definidos en `frontend/src/estilos/tokens.css`; ningún color,
  radio o tipografía nuevo se incrusta en el componente.
- Toda la pantalla respeta el registro de Análisis (radio 6px, Source Serif 4, aire visual, líneas
  bajo 80 caracteres) — este módulo no toca el registro de Operación en ningún punto.
- "Sin clasificar", "no calculable", "no confiable" y "sin referencia de competencia" se comunican
  siempre con texto explícito, nunca solo con la ausencia de un número.
- La antigüedad de una observación de competencia usada en una sugerencia se muestra con los tres
  portadores exigidos (color, forma, texto), igual que ya exige `001` para su propia comparación.
- El único momento de animación deliberado de este módulo es al confirmar la aplicación de una
  sugerencia (precio o colocación); no hay hover por fila ni fade-in por tarjeta.
