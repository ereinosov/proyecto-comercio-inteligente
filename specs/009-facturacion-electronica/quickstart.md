# Quickstart — 009-facturacion-electronica

Escenarios de extremo a extremo (TestClient sobre PostgreSQL real, puerto 5442). Todos con una
sesión de turno de `cajero` válida. Configuración de prueba: `RUC_COMERCIO`,
`RAZON_SOCIAL_COMERCIO`, `TARIFA_IVA=0.15`, `ESTABLECIMIENTO_SRI=001`, `PUNTO_EMISION_SRI=001`
(valores de demostración, nunca literales).

## Escenario 1 — Factura al cerrar la venta (User Story 1)

1. Abrir turno; entrada de inventario; cobrar una venta de 2 renglones cuyo `venta.total` sea
   8,63.
2. `POST /facturas {id_venta}`.
3. **Esperado**: `201`; `tipo=factura`; `secuencial` = `001-001-000000001`;
   `total` = "8.63" (== `venta.total`); `subtotal` = "7.50"; `monto_iva` = "1.13";
   `subtotal + monto_iva == total`; `renglones` con las descripciones de los productos;
   `comprador.tipo` = "consumidor_final"; `aviso_simulacion` presente y no vacío.
4. Verificar que `venta` y `renglon_venta` de 001 **no cambiaron** (mismo conteo, mismos valores).

## Escenario 2 — Comprador identificado (User Story 1)

- Cobrar una venta identificando un cliente con cédula.
- `POST /facturas {id_venta}`.
- **Esperado**: `comprador.tipo` = "identificado", `nombre` y `identificador` del cliente. Si el
  cliente tiene nombre pero no identificador → `nombre` presente, `identificador` null (sin
  "N/A").

## Escenario 3 — Idempotencia por venta (User Stories 1 y 2)

- `POST /facturas {id_venta}` dos veces para la misma venta.
- **Esperado**: la primera `201`, la segunda `200` con **la misma** `id_factura_simulada` y el
  mismo `secuencial`. `SELECT count(*) FROM factura_simulada WHERE id_venta = ? AND tipo='factura'`
  = 1 (SC-004).

## Escenario 4 — Correlativo sin huecos por sucursal (User Story 1)

- Cobrar 3 ventas seguidas en la sucursal A y 2 en la sucursal B; generar sus 5 facturas.
- **Esperado**: A tiene `…000000001`, `…000000002`, `…000000003`; B tiene `…000000001`,
  `…000000002`. Cada sucursal es su propio establecimiento/punto; sin huecos ni repeticiones
  (SC-003).

## Escenario 5 — El cobro no se bloquea si la factura falla (User Story 1, SC-007)

- Simular el fallo de `POST /facturas` (servicio caído / venta inexistente).
- **Esperado**: la venta ya está registrada por 001; `GET /facturas/venta/{id}` devuelve
  `factura: null`. El frontend muestra "Generar factura". Ninguna reversión del cobro.

## Escenario 6 — Regenerar la factura de una venta antigua (User Story 2)

- Tomar una venta cobrada que nunca tuvo factura; `POST /facturas {id_venta}`.
- **Esperado**: se crea la factura con los datos de esa venta y el secuencial que le toca por
  orden de generación. Segunda llamada → `200`, misma factura (FR-011, FR-012).

## Escenario 7 — Venta de total 0 no genera factura (Edge)

- Editar el carrito de una venta hasta total 0 y cobrar (caso de 001); `POST /facturas {id_venta}`.
- **Esperado**: `422` con `codigo` explícito; ninguna fila en `factura_simulada` para esa venta
  (FR-010).

## Escenario 8 — Anulación → nota de crédito (User Story 3)

1. Cobrar una venta, generar su factura.
2. Anular la venta (flujo de 001).
3. `POST /facturas/nota-credito/{id_venta}`.
4. **Esperado**: `201`; la factura original queda `estado=anulada`; la nota de crédito tiene
   `tipo=nota_credito`, `id_factura_referida` = la factura anulada, totales que revierten los de
   la factura, y su propio `secuencial` del correlativo de `nota_credito`. Mismo `aviso_simulacion`.
5. `venta` y `anulacion_venta` de 001 **no cambiaron** por la acción de 009.

## Escenario 9 — Anular una venta sin factura (User Story 3, Edge)

- Cobrar una venta, NO generar factura, anularla; `POST /facturas/nota-credito/{id_venta}`.
- **Esperado**: `204` (no hay factura que revertir). La anulación de 001 procede igual.

## Escenario 10 — Snapshot inmutable (FR-013)

- Generar una factura; cambiar `RAZON_SOCIAL_COMERCIO` en configuración; `GET /facturas/venta/{id}`.
- **Esperado**: `emisor.razon_social` sigue siendo el del momento de emisión, no el nuevo. Una
  factura **nueva** (de otra venta) sí usa el valor nuevo.

## Escenario 11 — Sin datos de pago en la factura (FR-020, Principio IV)

- Cobrar con `referencia_terminal_pago` (tarjeta); generar la factura.
- **Esperado**: `medio_pago` = "tarjeta" (etiqueta); ningún dígito de tarjeta, ningún PAN, ningún
  "últimos 4" en ninguna parte del cuerpo de la factura.

## Escenario 12 — Solo lectura sobre 001/002 (SC-005)

- Contar filas de `venta`, `renglon_venta`, `cliente`, `visita` antes.
- Ejecutar los escenarios 1, 2, 3, 8.
- **Esperado**: esos conteos **no cambian**. Sólo cambia `factura_simulada`.

## Escenario 13 — Rol (constitución v2.5.0)

- `POST /facturas` sin token → `401 sesion_invalida`.
- Con token de `cajero` → funciona (la factura es flujo de caja, no pantalla de encargado).
