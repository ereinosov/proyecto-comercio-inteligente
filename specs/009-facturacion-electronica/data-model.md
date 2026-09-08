# Data Model — 009-facturacion-electronica

Una entidad nueva, `factura_simulada`, propiedad de 009 (constitución v2.7.0). 009 **consulta**
`venta`, `renglon_venta`, `producto` (001) y `cliente`, `visita` (002); **no altera el esquema ni
escribe** ninguna de ellas. Migración `0013_factura_simulada`; `downgrade` elimina la tabla sin
pérdida de dato de negocio (la factura es derivada de la venta).

---

## `factura_simulada`

El documento con forma de factura (o nota de crédito) generado a partir de una venta confirmada.
**Todo el contenido es un snapshot**: una factura emitida no cambia aunque cambien la venta, el
cliente o la configuración (research §4, FR-013).

| Campo | Tipo | Notas |
|---|---|---|
| `id_factura_simulada` | `BIGSERIAL PRIMARY KEY` | |
| `id_venta` | `INTEGER NOT NULL` | FK → `venta` (001). **`UNIQUE`** para `tipo='factura'`: una venta, una factura (idempotencia, FR-007/FR-012). |
| `tipo` | `TEXT NOT NULL` | `CHECK (tipo IN ('factura','nota_credito'))` |
| `id_factura_referida` | `BIGINT NULL` | FK → `factura_simulada`. Sólo para `tipo='nota_credito'`: la factura que revierte |
| `establecimiento` | `TEXT NOT NULL` | 3 dígitos, de config (`ESTABLECIMIENTO_SRI`, default `001`) — deriva de la sucursal |
| `punto_emision` | `TEXT NOT NULL` | 3 dígitos, de config (`PUNTO_EMISION_SRI`, default `001`) |
| `numero` | `INTEGER NOT NULL` | correlativo ≥ 1 por `(establecimiento, punto_emision, tipo)` |
| `secuencial` | `TEXT NOT NULL` | `EEE-PPP-NNNNNNNNN` ya formateado (9 dígitos con ceros a la izquierda) |
| `fecha_emision` | `DATE NOT NULL` | fecha local de la sucursal del turno |
| `emisor` | `JSONB NOT NULL` | snapshot: `{razon_social, ruc, direccion?}` del momento de emisión (de config) |
| `comprador` | `JSONB NOT NULL` | snapshot: `{nombre, identificador?}` o `{tipo: "consumidor_final"}` |
| `renglones` | `JSONB NOT NULL` | snapshot: `[{descripcion, cantidad, precio_unitario, importe}]` |
| `subtotal` | `NUMERIC(12,2) NOT NULL` | `round(venta.total / (1 + tarifa_iva); 2)` |
| `tarifa_iva` | `NUMERIC(5,4) NOT NULL` | p. ej. `0.1500` (de config) — snapshot |
| `monto_iva` | `NUMERIC(12,2) NOT NULL` | `total - subtotal` (sin céntimo perdido) |
| `total` | `NUMERIC(12,2) NOT NULL` | `== venta.total` de 001 (IVA incluido en el precio) |
| `medio_pago` | `TEXT NULL` | etiqueta ("efectivo" / "tarjeta"), NUNCA datos de tarjeta (FR-020) |
| `estado` | `TEXT NOT NULL DEFAULT 'emitida'` | `CHECK (estado IN ('emitida','anulada'))` |
| `instante_generacion` | `TIMESTAMPTZ NOT NULL` | |

- `UNIQUE (establecimiento, punto_emision, tipo, numero)` — correlativo sin repeticiones.
- `UNIQUE (id_venta)` para `tipo='factura'` — una factura por venta. (Una `nota_credito` comparte
  `id_venta` con la factura que revierte, de ahí que el UNIQUE se acote por `tipo`; se implementa
  como índice parcial `WHERE tipo='factura'` o como `UNIQUE (id_venta, tipo)`.)
- FK `id_venta` **sin `ON DELETE CASCADE`**: 001 no borra ventas (las anula), así que no aplica.
- 009 nunca hace `UPDATE`/`DELETE`/`INSERT` sobre `venta`, `renglon_venta`, `cliente`, `visita`.

## Reglas de generación (no persistidas)

- **Correlativo**: dentro de la transacción de generación,
  `numero = COALESCE(MAX(numero), 0) + 1` para `(establecimiento, punto_emision, tipo)` con
  bloqueo; el `UNIQUE` protege ante una carrera y se reintenta. Sin huecos (SC-003).
- **Comprador**: se resuelve leyendo la `visita` identificada de la venta (002). Con
  `visita.id_cliente` → `cliente.nombre` (+ `cliente.identificador` si lo hay); sin visita
  identificada → `{tipo: "consumidor_final"}`.
- **Renglones**: de `renglon_venta` (001), con `producto.nombre` como descripción.
- **`fecha_emision`**: día local de la zona horaria de la sucursal del turno de la venta.
- **`total`/`subtotal`/`monto_iva`**: research §6 — `total = venta.total`,
  `subtotal = round(total / (1 + tarifa); 2)`, `monto_iva = total - subtotal`.

## Invariantes

1. `factura.total == venta.total` de 001, siempre (SC-002). 009 no cambia lo que el cliente paga.
2. `subtotal + monto_iva == total`, sin céntimo perdido por redondeo.
3. Una venta con `venta.total = 0` no tiene `factura_simulada` (FR-010).
4. Como mucho una `factura_simulada` de `tipo='factura'` por `id_venta` (SC-004).
5. Una `nota_credito` siempre tiene `id_factura_referida` no nula, apuntando a una factura del
   mismo `id_venta`, y esa factura está en `estado='anulada'`.
6. Todo campo de `emisor`, `comprador`, `renglones`, `tarifa_iva` es un snapshot: no se recalcula
   al leer (FR-013).
7. `medio_pago` nunca contiene PAN, últimos 4 dígitos, ni ningún dato de instrumento de pago;
   sólo la categoría (FR-020).
8. Ninguna sentencia de 009 modifica una tabla de 001/002 (SC-005, verificable por auditoría).
