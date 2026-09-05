# Data Model: Precios y Márgenes

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo
singular, sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Importes y
costos en `NUMERIC(12,4)` (misma escala que `producto.precio_vigente` y `lote.costo_unitario` de
`001`), márgenes (ratios) en `NUMERIC(6,4)` (misma escala que `visita.margen_relativo` de `002`),
instantes en `TIMESTAMPTZ`. **Ningún tipo de coma flotante aparece en este modelo.**

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las cuatro entidades que la constitución asigna a
`003-precios-margenes` **tras la enmienda v2.2.3**: `rol_producto`, `margen_calculado`,
`sugerencia_precio`, `sugerencia_colocacion`. Ninguna otra. La entrada original de la constitución
(`costo_producto`, `margen_calculado`, `rol_producto`, `sugerencia_colocacion`) se corrigió antes de
escribir este documento — ver research.md #2 y el informe de impacto de sincronización al inicio de
`constitution.md`. No hay discrepancia pendiente entre este documento y la tabla vigente
(constitución v2.2.5; la entrada de 003 no cambió desde v2.2.3).

**Frontera de propiedad explícita — lectura y escritura, no posesión**: este módulo consulta
`producto` (`es_granel`, `precio_vigente`), `producto_precio_sucursal` (override, FR-050),
`zona_exhibicion` (catálogo con `grado_privilegio`), `lote` y `existencia` (costo vigente, FEFO),
`observacion_precio` y `canal_competencia` (competencia). Todas son propiedad de
`001-core-ventas-inventario`. `003` las **lee sin poseerlas** (mismo patrón que `002` ya validó
para `lote`/`movimiento_inventario`, research.md #2 de `002`), y además **escribe** en
`producto_precio_sucursal` al aplicar una sugerencia de precio — no con acceso directo al ORM de
`001`, sino llamando a `fijar_precio_sucursal`, una función nueva que `001` expone en su propio
`servicios/catalogo.py` (research.md #7). Ninguna columna de `001` se duplica en este documento.

---

## `rol_producto`

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` PK, FK → `producto` (`001`) | Uno a lo sumo por producto. Ausencia de fila = "sin clasificar" (FR-007) |
| `rol` | `ENUM('gancho_trafico', 'generador_margen')` NOT NULL | |
| `instante_asignacion` | `TIMESTAMPTZ NOT NULL` | Se sobrescribe con cada cambio (FR-006); no lleva historial de asignaciones previas (research.md #3) |

*Por qué tabla propia y no columna de `producto`*: ver research.md #3 — alterar el esquema de
`producto` (propiedad de `001`) desde `003` está prohibido por la constitución, con independencia
de que el enunciado hable del "rol del producto" en lenguaje natural.

## `margen_calculado`

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` PK, FK → `producto` (`001`) | PK compuesta |
| `id_sucursal` | `INTEGER` PK, FK → `sucursal` (`001`) | PK compuesta. El margen se resuelve por sucursal (FR-001), nunca de forma global cuando existe override |
| `costo_vigente` | `NUMERIC(12,4) NULL` | Costo del lote que la política FEFO de `001` consumiría primero (research.md #4). `NULL` cuando no hay existencia con lote (FR-003) |
| `precio_vigente` | `NUMERIC(12,4) NOT NULL` | Precio resuelto para esa sucursal: override de `producto_precio_sucursal` si existe, si no `producto.precio_vigente` |
| `margen` | `NUMERIC(6,4) NULL` | `(precio_vigente − costo_vigente) / precio_vigente`. `NULL` cuando `costo_vigente` es `NULL` (FR-003) |
| `confiable` | `BOOLEAN NOT NULL DEFAULT TRUE` | `FALSE` cuando `costo_vigente <= 0` (FR-004); en ese caso `margen` se calcula igual pero se muestra marcado como no confiable |
| `instante_calculo` | `TIMESTAMPTZ NOT NULL` | Instante del último recálculo. Se sobrescribe (upsert) en cada lectura (research.md #4) — no representa un histórico |

*Patrón de actualización*: `upsert` (`ON CONFLICT (id_producto, id_sucursal) DO UPDATE`) ejecutado
por el propio servicio de lectura, nunca por disparador de base de datos ni tarea de fondo
(research.md #4). Esto es lo que garantiza SC-001: el valor mostrado siempre refleja el costo y
precio vigentes en el instante de la consulta.

## `sugerencia_precio`

Append-only: cada sugerencia generada es una fila nueva; ninguna se sobrescribe ni se borra
(Principio IV). El histórico de sugerencias de un producto queda consultable.

| Campo | Tipo | Notas |
|---|---|---|
| `id_sugerencia_precio` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` (`001`) | |
| `id_sucursal` | `INTEGER` FK → `sucursal` (`001`) | |
| `precio_sugerido` | `NUMERIC(12,4) NOT NULL` | Resultado del algoritmo de research.md #5 |
| `margen_usado` | `NUMERIC(6,4) NULL` | Snapshot de `margen_calculado.margen` en el instante de generación. `NULL` si no era calculable |
| `rol_usado` | `ENUM('gancho_trafico', 'generador_margen') NULL` | Snapshot de `rol_producto.rol`. `NULL` = "sin clasificar" en el instante de generación (FR-007) |
| `id_observacion_precio_usada` | `BIGINT FK → observacion_precio (001) NULL` | La observación de competencia vigente y comparable usada, si la hubo (FR-009). `NULL` = "sin referencia de competencia" (FR-010) |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |
| `aplicada` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` cuando el encargado la aplicó (FR-012, FR-013) |
| `instante_aplicacion` | `TIMESTAMPTZ NULL` | |

*Por qué snapshot de valores y no claves foráneas mutables* (salvo `id_observacion_precio_usada`,
que sí es estable — una observación ya capturada no cambia): `margen_calculado` se sobrescribe en
cada lectura (research.md #4); si `sugerencia_precio` referenciara la fila de `margen_calculado` en
vez de copiar su valor, una consulta posterior mostraría el margen *actual*, no el que realmente
motivó esa sugerencia — rompiendo la explicabilidad que exige FR-014 y Principio V.

*Aplicar una sugerencia* (FR-013, research.md #7): en la misma transacción, el servicio llama a
`fijar_precio_sucursal` (función de `001`, `servicios/catalogo.py`) con `precio_sugerido`, que crea
o actualiza la fila de `producto_precio_sucursal`, y marca esta fila de `sugerencia_precio` como
`aplicada = TRUE` con su `instante_aplicacion`. Revertir la aplicación es una operación normal de
`001` (editar o eliminar el override, que ya admite ausencia de fila = vuelve al precio base) — no
exige ninguna operación especial de deshacer en `003` (Principio V, "reversible").

## `sugerencia_colocacion`

Append-only, mismo principio que `sugerencia_precio`.

| Campo | Tipo | Notas |
|---|---|---|
| `id_sugerencia_colocacion` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` (`001`) | |
| `id_sucursal` | `INTEGER` FK → `sucursal` (`001`) | |
| `id_zona_exhibicion` | `INTEGER` FK → `zona_exhibicion` (`001`) | Zona sugerida. Debe pertenecer a `id_sucursal` (regla de aplicación, no `CHECK` entre tablas de distinto propietario) |
| `margen_usado` | `NUMERIC(6,4) NULL` | Snapshot, igual criterio que `sugerencia_precio` |
| `rol_usado` | `ENUM('gancho_trafico', 'generador_margen') NULL` | Snapshot. `NULL` = "sin clasificar" |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |
| `aplicada` | `BOOLEAN NOT NULL DEFAULT FALSE` | `TRUE` cuando el encargado confirma haber ejecutado físicamente la reubicación (FR-017) — el sistema nunca la ejecuta ni la registra por su cuenta |
| `instante_aplicacion` | `TIMESTAMPTZ NULL` | |

*Sin restricción de unicidad sobre `id_zona_exhibicion`*: dos sugerencias distintas pueden apuntar
a la misma zona para productos distintos (FR-019); el sistema no arbitra el conflicto, el encargado
decide.

*Sin zonas catalogadas* (FR-018): si `zona_exhibicion` no tiene ninguna fila para `id_sucursal`, no
se genera ninguna `sugerencia_colocacion`; el servicio lo indica explícitamente en la respuesta, sin
crear una fila con `id_zona_exhibicion` inventado.

---

## Entidades de `001` consultadas (no poseídas por este módulo)

| Entidad | Qué se consulta |
|---|---|
| `producto` | `es_granel` (determina la base de medida de costo y precio, sin conversión — ver research.md), `precio_vigente` (precio base) |
| `producto_precio_sucursal` | Override de precio por sucursal (lectura para resolver el vigente; escritura al aplicar una sugerencia, research.md #7) |
| `zona_exhibicion` | Catálogo con `grado_privilegio`, para sugerencia de colocación |
| `lote` / `existencia` | Costo vigente, vía el mismo criterio FEFO que `001` usa para vender |
| `observacion_precio` / `canal_competencia` | Insumo de competencia para sugerencia de precio; se respeta `comparable = FALSE` (FR-011) |

## Consultas derivadas (no son tablas)

- **Listado de márgenes por sucursal** (para la pantalla de Análisis): `SELECT` sobre
  `margen_calculado` filtrando por `id_sucursal`, recalculando primero cada fila visible
  (research.md #4).
- **Explicación de una sugerencia**: no requiere `JOIN` con `margen_calculado` ni `rol_producto`
  vigentes — los campos `margen_usado`/`rol_usado` ya están congelados en la propia
  `sugerencia_precio`/`sugerencia_colocacion` (ver nota de snapshot arriba).
