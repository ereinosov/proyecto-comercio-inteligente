# Data Model: Core de Ventas e Inventario

**Fase 1** · 2026-09-04 · Plan: [plan.md](./plan.md) · Decisiones: [research.md](./research.md)

Convención constitucional aplicada en todo el documento: español, `snake_case`, sustantivo singular,
sin la letra "ñ", claves foráneas `id_` + nombre de la tabla referida. Importes en `NUMERIC(12,2)`,
precios por unidad de medida en `NUMERIC(12,4)`, pesos en `INTEGER` de gramos, instantes en
`TIMESTAMPTZ`. **Ningún tipo de coma flotante aparece en este modelo.**

## Conformidad con la tabla de propiedad de la constitución

Este modelo introduce dos entidades que no estaban en la ratificación original de la tabla de
propiedad, y ambas ya fueron incorporadas por enmienda:

- `conteo_renglon`, las líneas contadas de un `conteo_fisico` — hijo estructural de una entidad ya
  asignada a 001. Incorporada por la enmienda **v2.1.1**.
- `producto_precio_sucursal`, el override opcional de `producto.precio_vigente` por sucursal.
  Incorporada por la enmienda **v2.1.2**, a raíz de que las observaciones de competencia se
  capturan por canal y los competidores de Quevedo Centro no son los de Buena Fe: un precio global
  haría imposible responder a la presión competitiva local.

**No hay discrepancia pendiente**: las 20 entidades de este documento coinciden con la tabla
vigente (constitución v2.2.5; la entrada de 001 no cambió desde v2.1.2).

`traspaso` deliberadamente **no** tiene tabla de renglones: sus líneas son los propios movimientos
de inventario que lo referencian, lo que evita una segunda entidad nueva.

---

## Catálogo y estructura

### `sucursal`

| Campo | Tipo | Notas |
|---|---|---|
| `id_sucursal` | `INTEGER` PK | |
| `nombre` | `TEXT NOT NULL UNIQUE` | "Quevedo Centro", "Buena Fe" en el juego de datos |
| `zona_horaria` | `TEXT NOT NULL` | Identificador IANA. Toda agregación por día usa este valor |

Cardinalidad no acotada. Codificar en cualquier parte que las sucursales son dos está PROHIBIDO.

### `categoria`

| Campo | Tipo | Notas |
|---|---|---|
| `id_categoria` | `INTEGER` PK | |
| `nombre` | `TEXT NOT NULL UNIQUE` | |
| `dias_umbral_inmovilizado` | `INTEGER NULL` | Nulo ⇒ hereda el umbral global de respaldo (FR-034) |

### `producto`

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` PK | |
| `id_categoria` | `INTEGER` FK → `categoria` | |
| `nombre` | `TEXT NOT NULL` | |
| `es_granel` | `BOOLEAN NOT NULL DEFAULT FALSE` | Determina si la cantidad es unidad o gramos |
| `precio_vigente` | `NUMERIC(12,4) NOT NULL` | Precio **base** del catálogo. Por unidad, o por kilogramo si `es_granel` |
| `lleva_caducidad` | `BOOLEAN NOT NULL DEFAULT FALSE` | |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. Ver nota de `venta.moneda` |

*Regla*: la política de cómo se fija `precio_vigente` pertenece a `003-precios-margenes`; este
módulo solo lo almacena. El precio efectivo por sucursal se resuelve junto con
`producto_precio_sucursal` (ver abajo), y el resultado es lo que se copia al renglón de venta.

### `producto_precio_sucursal`

**Override opcional**, no reemplazo. Existe porque las observaciones de competencia se capturan
por canal y los competidores de una sucursal no son los de la otra: un precio único para las dos
sucursales haría imposible responder a la presión competitiva local que describe el caso de
negocio ("si tienes un precio ligeramente mayor, pierdes la venta").

| Campo | Tipo | Notas |
|---|---|---|
| `id_producto` | `INTEGER` FK → `producto` | PK compuesta |
| `id_sucursal` | `INTEGER` FK → `sucursal` | PK compuesta |
| `precio_vigente` | `NUMERIC(12,4) NOT NULL` | Precio de esa sucursal para ese producto |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. Ver nota de `venta.moneda` |

*Resolución del precio efectivo* (aplicada por el servicio de venta, no en el esquema):

```sql
COALESCE(
  (SELECT precio_vigente FROM producto_precio_sucursal
   WHERE id_producto = :id_producto AND id_sucursal = :id_sucursal),
  (SELECT precio_vigente FROM producto WHERE id_producto = :id_producto)
)
```

Si no existe fila para esa combinación de producto y sucursal, se aplica el precio base de
`producto`. La política de **cómo** fijar cualquiera de los dos precios sigue perteneciendo a
`003-precios-margenes`; este módulo solo provee la capacidad de que el precio pueda diferir por
sucursal y resuelve cuál aplica al vender.

### `zona_exhibicion`

| Campo | Tipo | Notas |
|---|---|---|
| `id_zona_exhibicion` | `INTEGER` PK | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | |
| `nombre` | `TEXT NOT NULL` | |
| `grado_privilegio` | `SMALLINT NOT NULL` | Mayor = más privilegiada |

Catalogada aquí; usada por `003-precios-margenes` para sugerir colocación.

---

## Personas y turnos

### `operador`

| Campo | Tipo | Notas |
|---|---|---|
| `id_operador` | `INTEGER` PK | |
| `nombre` | `TEXT NOT NULL` | |
| `pin_hash` | `TEXT NOT NULL` | Hash del PIN de 4 dígitos. **El PIN nunca se almacena en claro** |
| `es_encargado` | `BOOLEAN NOT NULL DEFAULT FALSE` | Única distinción de capacidad; no es un sistema de roles |
| `activo` | `BOOLEAN NOT NULL DEFAULT TRUE` | |

*Alcance*: sin recuperación de PIN por correo, sin expiración de sesión, sin control de acceso a
pantallas por rol (FR-006). `es_encargado` existe solo para dos operaciones: reasignar un PIN y
anular una venta de un turno cerrado (FR-049).

### `turno`

| Campo | Tipo | Notas |
|---|---|---|
| `id_turno` | `INTEGER` PK | |
| `id_operador` | `INTEGER` FK → `operador` | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | |
| `caja` | `TEXT NOT NULL` | Identificador de la caja física |
| `instante_apertura` | `TIMESTAMPTZ NOT NULL` | |
| `instante_cierre` | `TIMESTAMPTZ NULL` | Nulo ⇒ turno en curso |

*Estado*: `abierto` (cierre nulo) → `cerrado`. Un turno cerrado no vuelve a abrirse.

---

## Inventario

### `lote`

| Campo | Tipo | Notas |
|---|---|---|
| `id_lote` | `INTEGER` PK | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | Un lote pertenece a exactamente una sucursal (FR-015) |
| `costo_unitario` | `NUMERIC(12,4) NOT NULL` | Por unidad o por kilogramo. **Costo, nunca margen** (FR-014) |
| `fecha_caducidad` | `DATE NULL` | Nulo ⇒ el producto no caduca |
| `instante_entrada` | `TIMESTAMPTZ NOT NULL` | Desempate cuando la caducidad empata o no existe |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. Ver nota de `venta.moneda` |

**Índice de selección FEFO**:
`(id_sucursal, id_producto, fecha_caducidad NULLS LAST, instante_entrada, id_lote)`.

### `movimiento_inventario`

Única fuente de verdad del inventario.

| Campo | Tipo | Notas |
|---|---|---|
| `id_movimiento_inventario` | `BIGINT` PK | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `id_lote` | `INTEGER` FK → `lote` NULL | Nulo solo cuando el producto no tiene lote alguno en esa sucursal |
| `tipo` | `ENUM` | `entrada_compra`, `salida_venta`, `entrada_anulacion`, `salida_traspaso`, `entrada_traspaso`, `ajuste_conteo` |
| `cantidad` | `NUMERIC(14,0)` | Unidades o **gramos**, según `producto.es_granel`. Positiva en entradas, negativa en salidas |
| `instante` | `TIMESTAMPTZ NOT NULL` | |
| `id_venta` / `id_traspaso` / `id_conteo_fisico` / `id_anulacion_venta` | FK NULL | **Exactamente una** no nula: el hecho que originó el movimiento |

*Restricción* *(corregida durante /speckit-implement)*: `CHECK` atado al `tipo`, no una cuenta
genérica de "exactamente una no nula" — `entrada_compra` no tiene ninguna de las cuatro
referencias (no existe una entidad de compra en este módulo; el lote es su propio registro de
origen); `salida_venta` exige `id_venta`; `entrada_anulacion` exige `id_anulacion_venta`;
`salida_traspaso`/`entrada_traspaso` exigen `id_traspaso`; `ajuste_conteo` exige
`id_conteo_fisico` — y en cada caso, únicamente esa referencia. La versión genérica original
("exactamente una de las cuatro") se descubrió inconsistente al sembrar datos de entrada de
compra: ninguna fila de `entrada_compra` puede satisfacerla, y además permitía en teoría una
`salida_venta` enlazada a `id_traspaso` en vez de a `id_venta`. Ningún movimiento existe sin
hecho que lo origine, cuando corresponde (Principio IV).

### `existencia`

**Agregación derivada, no autoritativa.** Ante discrepancia gana la recomputación desde
`movimiento_inventario`.

| Campo | Tipo | Notas |
|---|---|---|
| `id_sucursal` | `INTEGER` | PK compuesta |
| `id_producto` | `INTEGER` | PK compuesta |
| `id_lote` | `INTEGER NULL` | PK compuesta |
| `cantidad` | `NUMERIC(14,0) NOT NULL` | **Sin restricción de no negatividad** (FR-047) |

*Actualización*: siempre por suma de delta en la misma transacción del movimiento
(`ON CONFLICT DO UPDATE SET cantidad = existencia.cantidad + EXCLUDED.cantidad`). **Nunca por
asignación de un valor absoluto**, para que no exista forma de sobrescribir un saldo sin movimiento.

### `traspaso`

| Campo | Tipo | Notas |
|---|---|---|
| `id_traspaso` | `INTEGER` PK | |
| `id_sucursal_origen` | `INTEGER` FK → `sucursal` | |
| `id_sucursal_destino` | `INTEGER` FK → `sucursal` | `CHECK` origen ≠ destino |
| `estado` | `ENUM` | `en_transito`, `recibido` |
| `instante_despacho` | `TIMESTAMPTZ NOT NULL` | |
| `instante_recepcion` | `TIMESTAMPTZ NULL` | |

*Sin tabla de renglones*: las líneas del traspaso son sus propios movimientos. Los de tipo
`salida_traspaso` se crean al despachar; los de `entrada_traspaso`, al confirmar la recepción.

**Invariante del sistema** (prueba obligatoria n.º 5):

```text
inventario_total = Σ existencia.cantidad
                 + Σ |cantidad| de movimientos salida_traspaso de traspasos en_transito
```

Esa suma no cambia al despachar. La discrepancia de recepción es la diferencia, por producto, entre
lo despachado y lo confirmado del mismo `id_traspaso` (FR-019).

---

## Venta

### `venta`

| Campo | Tipo | Notas |
|---|---|---|
| `id_venta` | `BIGINT` PK | |
| `clave_idempotencia` | `TEXT NOT NULL UNIQUE` | Generada por el cliente antes del primer intento |
| `id_turno` | `INTEGER` FK → `turno` | De aquí se derivan operador, sucursal y caja |
| `referencia_terminal_pago` | `TEXT NULL` | **Referencia opaca**. La entidad `terminal_pago` es propiedad de `007-pagos-seguridad` y NO se define aquí |
| `instante` | `TIMESTAMPTZ NOT NULL` | |
| `total` | `NUMERIC(12,2) NOT NULL` | Suma de los importes ya redondeados de cada renglón |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. El sistema opera en una sola moneda (FR-045); la columna existe porque la constitución exige que todo importe persistido lleve su moneda asociada |

### `renglon_venta`

| Campo | Tipo | Notas |
|---|---|---|
| `id_renglon_venta` | `BIGINT` PK | |
| `id_venta` | `BIGINT` FK → `venta` | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `cantidad_unidades` | `INTEGER NULL` | Para productos no granel |
| `cantidad_gramos` | `INTEGER NULL` | Para productos granel |
| `precio_aplicado` | `NUMERIC(12,4) NOT NULL` | **Copiado** del producto al vender, para que la venta siga siendo reconstruible si el precio cambia |
| `importe` | `NUMERIC(12,2) NOT NULL` | Redondeado a 2 decimales en el renglón |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. Ver nota de `venta.moneda` |

*Restricción*: `CHECK` que obliga a que exactamente una de las dos cantidades sea no nula, y a que
sea estrictamente positiva. Es lo que hace imposible un renglón de peso cero o negativo.

### `anulacion_venta`

| Campo | Tipo | Notas |
|---|---|---|
| `id_anulacion_venta` | `BIGINT` PK | |
| `id_venta` | `BIGINT` FK → `venta` UNIQUE | Una venta se anula a lo sumo una vez |
| `id_operador` | `INTEGER` FK → `operador` | Quien anula, que puede no ser quien vendió (FR-049) |
| `instante` | `TIMESTAMPTZ NOT NULL` | |
| `motivo` | `TEXT NULL` | |

*Regla de autorización* (FR-049): si la venta pertenece al turno en curso del propio operador, puede
anularla él. Si el turno está cerrado, requiere `operador.es_encargado = TRUE`.
La venta anulada **permanece visible**, nunca se borra. Cada renglón genera un movimiento
`entrada_anulacion` que repone la existencia en el mismo lote del que salió.

---

## Señales del punto de venta

### `consulta_no_atendida`

| Campo | Tipo | Notas |
|---|---|---|
| `id_consulta_no_atendida` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | |
| `id_turno` | `INTEGER` FK → `turno` | |
| `instante` | `TIMESTAMPTZ NOT NULL` | |
| `saldo_en_el_instante` | `NUMERIC(14,0) NOT NULL` | Congelado al registrar (FR-021) |

*Sin ningún dato de cliente*. Registrable en dos toques desde la pantalla de venta.
`saldo_en_el_instante` es lo que permite a `004-pronostico-demanda` distinguir un agotamiento real
de un producto que estaba pero no se localizó.

---

## Competencia

### `canal_competencia`

| Campo | Tipo | Notas |
|---|---|---|
| `id_canal_competencia` | `INTEGER` PK | |
| `nombre` | `TEXT NOT NULL` | |
| `nombre_normalizado` | `TEXT NOT NULL UNIQUE` | Minúsculas, sin acentos ni espacios extremos; evita duplicados (FR-025) |

Catálogo **abierto**: el operador lo alimenta al capturar.

### `observacion_precio`

| Campo | Tipo | Notas |
|---|---|---|
| `id_observacion_precio` | `BIGINT` PK | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `id_canal_competencia` | `INTEGER` FK → `canal_competencia` | |
| `presentacion_cantidad` | `NUMERIC(12,3) NOT NULL` | Cantidad de la presentación observada |
| `presentacion_unidad` | `ENUM` | `unidad`, `gramo`, `mililitro` |
| `precio_observado` | `NUMERIC(12,2) NOT NULL` | Precio de esa presentación |
| `moneda` | `CHAR(3) NOT NULL DEFAULT 'USD'` | ISO 4217. Ver nota de `venta.moneda` |
| `fuente` | `TEXT NOT NULL` | |
| `origen_captura` | `ENUM` | `manual`, `archivo`. **Nunca obtención automática de sitios de terceros** (FR-026) |
| `instante_captura` | `TIMESTAMPTZ NOT NULL` | |
| `id_turno` | `INTEGER` FK → `turno` NULL | Operador que capturó |
| `comparable` | `BOOLEAN NOT NULL DEFAULT TRUE` | Falso cuando la presentación no admite normalización |

*Normalización*: el precio por unidad de medida se **calcula al leer**, no se almacena.
**La antigüedad tampoco se almacena** (FR-024): se calcula en el momento de la consulta.

---

## Verificación de inventario

### `conteo_fisico`

| Campo | Tipo | Notas |
|---|---|---|
| `id_conteo_fisico` | `INTEGER` PK | |
| `id_sucursal` | `INTEGER` FK → `sucursal` | |
| `estado` | `ENUM` | `abierto`, `resuelto` |
| `alcance` | `JSONB NULL` | Subconjunto de productos o categorías; nulo ⇒ toda la sucursal |
| `instante_inicio` | `TIMESTAMPTZ NOT NULL` | |
| `instante_resolucion` | `TIMESTAMPTZ NULL` | |

### `conteo_renglon`

| Campo | Tipo | Notas |
|---|---|---|
| `id_conteo_renglon` | `BIGINT` PK | |
| `id_conteo_fisico` | `INTEGER` FK → `conteo_fisico` | |
| `id_producto` | `INTEGER` FK → `producto` | |
| `id_lote` | `INTEGER` FK → `lote` NULL | |
| `cantidad_contada` | `NUMERIC(14,0) NOT NULL` | |
| `cantidad_esperada` | `NUMERIC(14,0) NOT NULL` | Saldo calculado, congelado al capturar |
| `diferencia` | `NUMERIC(14,0)` | Columna generada: contada − esperada |

*Sin clasificación de causa* (FR-031): la diferencia se expone en bruto. Clasificarla como merma,
robo o error de registro es propiedad de `006-caja-mermas-fraude`.
Al resolver, cada renglón con diferencia distinta de cero genera un movimiento `ajuste_conteo`
trazable al conteo (FR-032).

---

## Reconciliación offline

### `operacion_pendiente`

| Campo | Tipo | Notas |
|---|---|---|
| `id_operacion_pendiente` | `UUID` PK | Generado en el dispositivo |
| `tipo_operacion` | `ENUM` | `venta`, `consulta_no_atendida`, `anulacion_venta`, `recepcion_traspaso`, `resolucion_conteo` |
| `carga` | `JSONB NOT NULL` | Cuerpo original de la petición |
| `recurso_afectado` | `TEXT NOT NULL` | Clave del recurso sobre el que actúa; base de la detección de conflicto |
| `marca_tiempo_origen` | `TIMESTAMPTZ NOT NULL` | Reportada por el dispositivo |
| `instante_recepcion` | `TIMESTAMPTZ NULL` | Puesta por el servidor. Comparar ambas revela un reloj desviado |
| `estado` | `ENUM` | `pendiente_de_sincronizar`, `sincronizada`, `conflicto_resuelto` |
| `id_operacion_prevaleciente` | `UUID` FK → `operacion_pendiente` NULL | Referencia a la que ganó el desempate |

*Regla de conflicto*: sobre un mismo `recurso_afectado` prevalece la `marca_tiempo_origen` más
antigua, **en las dos direcciones**. La desplazada pasa a `conflicto_resuelto` con
`id_operacion_prevaleciente` relleno y **permanece visible**: eliminarla u ocultarla está PROHIBIDO.

---

## Consultas derivadas (no son tablas)

- **Capital inmovilizado** (FR-033 a FR-036): lotes cuya última salida excede
  `COALESCE(categoria.dias_umbral_inmovilizado, umbral_global)`. Valor =
  `cantidad_restante × costo_unitario`; un lote sin costo se muestra **no calculable**, nunca cero.
- **Comparación de precios** (FR-027): precio propio contra observaciones vigentes, cada una
  normalizada a precio por unidad de medida y con su antigüedad calculada al leer.
- **Cierre por día local**: `(instante AT TIME ZONE sucursal.zona_horaria)::date`, nunca `::date`
  sobre el instante crudo.
