# Data Model — 008-reportes-inteligencia

Tres entidades nuevas, **todas derivadas y regenerables** (constitución v2.6.0, "Propiedad de
Datos"). Ninguna es fuente de verdad de negocio. Migración `0012_reportes_inteligencia`; el
`downgrade` elimina las tres sin pérdida de dato de negocio.

008 **no altera el esquema de ninguna entidad de 001–007.**

---

## `agregado_reporte`

Caché del resultado ya calculado de una vista (comparativo, tendencia o tablero) para un ámbito
y un período. Se puebla a demanda; el encargado la invalida con "Actualizar" (FR-026, FR-027).

| Campo | Tipo | Notas |
|---|---|---|
| `id_agregado_reporte` | `BIGSERIAL PRIMARY KEY` | |
| `tipo` | `TEXT NOT NULL` | `CHECK (tipo IN ('comparativo','tendencia','tablero'))` |
| `ambito_sucursal` | `INTEGER NULL` | FK → `sucursal`. `NULL` = "todas las sucursales" |
| `periodo_inicio` | `DATE NOT NULL` | fecha local de inicio del período pedido |
| `periodo_fin` | `DATE NOT NULL` | fecha local de fin |
| `granularidad` | `TEXT NOT NULL` | `CHECK (granularidad IN ('total','semana','mes'))`; `total` para comparativo y tablero |
| `contenido` | `JSONB NOT NULL` | el resultado (filas del comparativo, puntos de la serie, tarjetas del tablero). Estructura por `tipo`, documentada en el contrato OpenAPI. |
| `instante_calculo` | `TIMESTAMPTZ NOT NULL` | cuándo se calculó — se muestra en pantalla |

- `UNIQUE (tipo, ambito_sucursal, periodo_inicio, periodo_fin, granularidad)` — una entrada por
  combinación; "Actualizar" hace `DELETE` + recálculo.
- **Regenerable**: `contenido` es exactamente lo que producen los servicios de 008 sobre 001–006.
- No lleva FK a `venta`/`merma`/etc.: es un agregado, no un detalle trazable a una transacción.

## `segmento_cliente`

La definición de un grupo del **último** recálculo de clustering (FR-018, FR-022). Se reemplaza
entera en cada recálculo.

| Campo | Tipo | Notas |
|---|---|---|
| `id_segmento_cliente` | `BIGSERIAL PRIMARY KEY` | |
| `corrida` | `TIMESTAMPTZ NOT NULL` | instante del recálculo que produjo este grupo; igual para todos los grupos de una corrida |
| `etiqueta_grupo` | `TEXT NOT NULL` | identificador estable dentro de la corrida (`grupo_1`…`grupo_4`, o `sin_clasificar`) |
| `centroide_frecuencia` | `NUMERIC(10,4) NOT NULL` | valor del centroide en unidades originales (visitas/día) |
| `centroide_margen` | `NUMERIC(6,4) NOT NULL` | ratio |
| `centroide_recencia_dias` | `NUMERIC(8,2) NOT NULL` | días |
| `n_clientes` | `INTEGER NOT NULL` | cuántos clientes cayeron en el grupo |
| `descripcion` | `TEXT NOT NULL` | frase derivada del centroide (FR-022) — nunca un texto fijo |
| `semilla` | `BIGINT NOT NULL` | la semilla usada (de `config/reportes.py`); documenta el determinismo |

- `UNIQUE (corrida, etiqueta_grupo)`.
- Sólo se conserva la última corrida: al recalcular se borran las filas de `corrida` anterior.
  (Si se decidiera conservar historial de corridas, sería una ampliación posterior; el spec no
  lo pide.)
- **Regenerable**: ejecutar el k-means sobre las features actuales reproduce estos grupos.

## `asignacion_segmento`

Relación cliente ↔ grupo del último recálculo. Una fila por cliente (FR-023).

| Campo | Tipo | Notas |
|---|---|---|
| `id_cliente` | `INTEGER PRIMARY KEY` | FK → `cliente` (002). PK = una asignación por cliente |
| `corrida` | `TIMESTAMPTZ NOT NULL` | instante del recálculo; == `segmento_cliente.corrida` |
| `etiqueta_grupo` | `TEXT NOT NULL` | `grupo_1`…`grupo_4` o `sin_clasificar` |
| `distancia_al_centroide` | `NUMERIC(10,4) NULL` | opcional; útil para elegir "clientes de ejemplo" del grupo. `NULL` para `sin_clasificar` |

- FK `(corrida, etiqueta_grupo)` → `segmento_cliente (corrida, etiqueta_grupo)`.
- `ON DELETE CASCADE` desde `cliente`: si 002 anonimiza/borra un cliente, su asignación se va con
  él (008 no retiene datos de un cliente que 002 ya no tiene).
- **008 no escribe en `cliente`**. El detalle de cliente de 002 que muestra la etiqueta la lee de
  aquí (o vía un endpoint de 008), sin que `cliente` gane una columna.

---

## Features del clustering (no persistidas como tabla)

Las tres features por cliente se calculan al vuelo en cada recálculo desde 002:

- **frecuencia** = `1 / intervalo_compra.intervalo_estimado_dias` si `intervalo_compra.estado =
  'calculado'`, si no `n_visitas / max(1, dias(primera_visita, ultima_visita))`.
- **margen** = `AVG(visita.margen_relativo)` de las visitas del cliente.
- **recencia_dias** = `hoy_local - DATE(MAX(visita.instante))`.

Se estandarizan (z-score) sobre la población de clientes clasificables de la corrida; media y
desviación de la corrida se usan para traducir los centroides de vuelta a unidades originales al
grabar `segmento_cliente`.

## Invariantes

1. `agregado_reporte` nunca contiene una referencia a una fila de detalle de 001–007; es un
   agregado. Truncar la tabla no pierde nada.
2. Toda fila de `asignacion_segmento` apunta a un `segmento_cliente` de la **misma** `corrida`;
   no hay asignaciones "huérfanas" de una corrida anterior.
3. Un cliente con `< N` visitas (N de `config/reportes.py`, por defecto 3) tiene
   `asignacion_segmento.etiqueta_grupo = 'sin_clasificar'`, nunca un `grupo_k`.
4. `SUM(segmento_cliente.n_clientes de la última corrida) == COUNT(asignacion_segmento)`.
5. Ninguna sentencia de 008 hace `INSERT`/`UPDATE`/`DELETE` sobre una tabla de 001–007
   (verificable por auditoría de código — SC-006).
