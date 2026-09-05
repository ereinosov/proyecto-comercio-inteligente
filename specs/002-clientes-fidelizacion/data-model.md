# Data Model: Clientes y Fidelización

**Fase 1** · 2026-09-04 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo
singular, sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Importes en
`NUMERIC(12,2)`, instantes en `TIMESTAMPTZ`. **Ningún tipo de coma flotante aparece en este
modelo.**

## Conformidad con la tabla de propiedad de la constitución

Este modelo define exactamente las cuatro entidades que la constitución asigna a
`002-clientes-fidelizacion`: `cliente`, `visita`, `intervalo_compra`, `senal_fuga`. Ninguna otra.
`visita` referencia `venta` (propiedad de `001`) por clave foránea, sin redefinirla ni duplicar sus
columnas salvo el snapshot explícito de `monto_total`/`margen_relativo` que FR-005 exige. El margen
no tiene tabla propia todavía porque `003-precios-margenes` no existe (ver research.md #2); cuando
exista, `margen_resolver.py` cambia de implementación sin que este documento cambie.

**Frontera de propiedad explícita — lectura, no posesión**: mientras `003` no exista,
`margen_resolver.py` (invocado al crear una `visita`) lee `lote.costo_unitario` y
`movimiento_inventario` para calcular `visita.margen_relativo` (research.md #2). Ambas tablas son
propiedad de `001-core-ventas-inventario`. `002` las **consulta, no las posee**: no las redefine,
no duplica sus columnas y no altera su esquema. Es el mismo patrón de frontera que la constitución
ya declara para `anomalia_caja` (006) consultando `movimiento_inventario`/`venta` (001), y para la
frontera "costo pertenece a 001, margen pertenece a 003" de la propia tabla de propiedad de datos.

---

## `cliente`

| Campo | Tipo | Notas |
|---|---|---|
| `id_cliente` | `INTEGER` PK | |
| `nombre` | `TEXT NULL` | Obligatorio al registrar (regla de aplicación, FR-001); se vacía a `NULL` al anonimizar (FR-016) |
| `fecha_nacimiento` | `DATE NULL` | Obligatoria al registrar (FR-001, única base del cupón de `005`); se vacía al anonimizar |
| `contacto` | `TEXT NULL` | Siempre opcional; se vacía al anonimizar si existía |
| `fecha_alta` | `TIMESTAMPTZ NOT NULL` | |
| `anonimizado` | `BOOLEAN NOT NULL DEFAULT FALSE` | |
| `instante_anonimizacion` | `TIMESTAMPTZ NULL` | Puesto por la tarea de fondo (FR-015) |

*Nota de esquema*: `nombre` y `fecha_nacimiento` son `NULL`-ables a nivel de columna únicamente
para admitir el estado post-anonimización; la API rechaza un registro que no los incluya (FR-001).
Es el mismo patrón que `001` ya usa para reglas que no son restricciones de esquema (por ejemplo,
el PIN de operador nunca se valida en la base de datos, se valida en el servicio).

*Tras la anonimización* (FR-016): `nombre`, `fecha_nacimiento` y `contacto` quedan en `NULL`;
`id_cliente` y las filas de `intervalo_compra`/`senal_fuga` asociadas se conservan intactas, porque
son las métricas agregadas que FR-016 exige preservar y no contienen ningún dato que reidentifique
a la persona.

## `visita`

| Campo | Tipo | Notas |
|---|---|---|
| `id_visita` | `BIGINT` PK | |
| `id_cliente` | `INTEGER` FK → `cliente` | |
| `id_venta` | `BIGINT` FK → `venta` (`001`) UNIQUE | Una venta genera a lo sumo una visita |
| `instante` | `TIMESTAMPTZ NOT NULL` | Copiado de `venta.instante` al crear la visita |
| `monto_total` | `NUMERIC(12,2) NOT NULL` | Copiado de `venta.total`. Snapshot: no se recalcula si `venta` cambiara |
| `margen_relativo` | `NUMERIC(6,4) NOT NULL` | **Ratio**, no monto: `(monto_total − costo) / monto_total`, ej. `0.2500` = 25% de margen sobre el precio de venta. Resuelto por `margen_resolver.resolver_margen_visita` (research.md #2) en el instante de la visita, leyendo — sin poseer — `lote.costo_unitario` de `001` (ver nota de propiedad de datos arriba). **Snapshot deliberado** (FR-005, edge case de spec): no se recalcula si el margen del producto cambia después en `003` |

*Restricción*: `id_venta UNIQUE` es lo que impide que una misma venta produzca dos visitas si la
llamada `POST /clientes/{id_cliente}/visitas` se reintenta (ver contrato: reintento devuelve la
visita ya existente, mismo patrón de idempotencia que `001` usa para `venta`).

## `intervalo_compra`

| Campo | Tipo | Notas |
|---|---|---|
| `id_cliente` | `INTEGER` PK, FK → `cliente` | Una fila por cliente, se actualiza en el sitio |
| `intervalo_esperado_dias` | `NUMERIC(8,2) NULL` | Mediana de los intervalos entre visitas consecutivas (research.md #3). `NULL` mientras `estado = 'datos_insuficientes'` |
| `visitas_consideradas` | `INTEGER NOT NULL DEFAULT 0` | Cuántas visitas sustentan el cálculo actual |
| `estado` | `ENUM('datos_insuficientes', 'calculado')` | `calculado` requiere `visitas_consideradas >= 3` (research.md #3) |
| `instante_calculo` | `TIMESTAMPTZ NOT NULL` | Se recalcula, en la misma transacción, cada vez que ese cliente registra una nueva visita |

*Regla* (FR-006, FR-007): mientras `estado = 'datos_insuficientes'`, este cliente queda excluido
tanto de la detección de fuga (FR-008/FR-014) como del cálculo de percentiles del valor de cliente
(research.md #4) — no participa con un valor por defecto, simplemente no entra en la población
comparada.

## `senal_fuga`

| Campo | Tipo | Notas |
|---|---|---|
| `id_senal_fuga` | `BIGINT` PK | |
| `id_cliente` | `INTEGER` FK → `cliente` | |
| `estado` | `ENUM('activa', 'confirmada', 'resuelta')` | Ver máquina de estados abajo |
| `instante_deteccion` | `TIMESTAMPTZ NOT NULL` | Cuándo superó 1× su intervalo esperado (FR-008) |
| `instante_confirmacion` | `TIMESTAMPTZ NULL` | Cuándo superó el umbral de FR-014 (5× o piso de 12 meses) |
| `instante_resolucion` | `TIMESTAMPTZ NULL` | Cuándo el cliente volvió a comprar (FR-009) |
| `instante_purga_programada` | `TIMESTAMPTZ NULL` | `instante_confirmacion + 90 días` (FR-015). Se limpia si se resuelve antes de vencer |

**Restricción**: índice único parcial `UNIQUE (id_cliente) WHERE estado IN ('activa', 'confirmada')`
— a lo sumo una señal abierta por cliente a la vez. Una señal `resuelta` no se borra: queda como
histórico (Principio IV) y una futura reincidencia crea una fila nueva.

**Máquina de estados**:

```text
(sin señal) --supera 1× intervalo esperado--> activa
activa --supera 5× intervalo esperado, o 12 meses (el mayor)--> confirmada
activa --nueva visita--> resuelta
confirmada --nueva visita, antes de instante_purga_programada--> resuelta
                                                                  (cancela la purga programada)
confirmada --vence instante_purga_programada sin nueva visita--> (anonimizacion.py anonimiza
                                                                   al cliente; la señal permanece
                                                                   'confirmada', el cliente queda
                                                                   'anonimizado')
```

Una señal `confirmada` cuyo cliente ya fue anonimizado permanece en ese estado: es el registro,
sin datos personales, de que ese cliente llegó a fuga confirmada. Es la métrica agregada que
FR-016 exige conservar.

---

## Consultas derivadas (no son tablas)

- **Valor de cliente** (FR-010, FR-011, research.md #4): para cada cliente con
  `intervalo_compra.estado = 'calculado'`, se calcula el percentil de frecuencia (inverso de
  `intervalo_esperado_dias`), de monto acumulado (`SUM(visita.monto_total)`) y de margen — este
  último como `SUM(visita.monto_total × visita.margen_relativo) / SUM(visita.monto_total)`, el
  ratio de margen del cliente ponderado por el tamaño de cada visita, no un promedio simple de
  ratios ni una suma de `margen_relativo` (que al ser una fracción, sumarla sin ponderar no tendría
  significado) — contra esa misma población. La puntuación compuesta es el promedio simple de los
  tres percentiles.
  - **Resumen** (registro de Operación, FR-011a): solo la puntuación compuesta.
  - **Desglose** (registro de Análisis, FR-011b): los tres percentiles por separado.
  - Un cliente en `datos_insuficientes` no tiene puntuación ni percentil: se muestra como tal, no
    como cero (FR-007, SC-004).
- **Cumpleañeros** (FR-012): `SELECT` sobre `cliente` filtrando por día y mes de
  `fecha_nacimiento` dentro del rango pedido, excluyendo clientes anonimizados (ya no tienen
  `fecha_nacimiento`). Expuesto para que `005-promociones-inteligentes` lo consuma; este módulo no
  decide ninguna acción sobre el resultado (FR-013).
