# Quickstart: Pagos y Seguridad

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus reglas difíciles: **el PAN nunca
se persiste ni se expone** en ningún punto; la tokenización es idempotente por cobro y **no bloquea
la venta de `001`**; una señal de firmware **nunca deshabilita** una terminal; la cobertura de medios
refleja el estado histórico y **no** es faltante de inventario; y la bitácora es de **solo anexado**.
No contiene código de implementación: eso pertenece a `tasks.md` y a la fase de implementación.

## Requisitos previos

- **`001-core-ventas-inventario` Setup + Foundational + User Story 1 completa**: `venta` (con
  `id_turno` y `referencia_terminal_pago TEXT NULL` opaca), `turno` (`id_operador`, sucursal),
  `sucursal` (`zona_horaria`), `operador` (`es_encargado`) — este módulo los **consulta** (nunca
  escribe en ellos).
- **`007` no está bloqueado por ningún dato de `001` faltante** (a diferencia de `006`). La entidad
  `token_pago` la añadió la enmienda constitucional **v2.2.6** (aprobada y aplicada el 2026-09-05).
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usan `001`–`006`. La migración `0007`
  requiere la extensión `btree_gist` (`CREATE EXTENSION IF NOT EXISTS btree_gist`, incluida en el
  `upgrade`).
- Python 3.12 y Node.js 20, mismo entorno que el resto de módulos.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0007_pagos_seguridad
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

Parámetros en `backend/rasero/config/pagos.py` (research.md #10), sobrescribibles por variable de
entorno: `MEDIOS_PAGO_BASE` (5 medios sembrados en la migración), `DIGITOS_CONSERVADOS=4`,
`RETENCION_BITACORA_ANIOS=2`, `ULTIMA_VERSION_FIRMWARE={}` (lo puebla el negocio, por modelo),
`LISTA_FIRMWARE_VULNERABLE=[]` (lo puebla el negocio), `BIN_MARCA` (prefijo → marca).

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_firmware_dominio.py tests/unidad/test_token_dominio.py
pytest tests/integracion/test_cobertura.py tests/integracion/test_terminales.py tests/integracion/test_tokenizacion.py tests/integracion/test_bitacora.py
pytest tests/contrato/test_contrato_pagos.py
```

Las ocho suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de fusionar.
**No hay ninguna prueba `xfail`**: nada de este módulo está bloqueado por `001`.

---

## Escenarios de validación

Cada escenario se comprueba contra PostgreSQL real (puerto 5442).

### 1. El PAN nunca se persiste ni se expone (FR-017, SC-006, SC-007)

1. Tokenizar 20 cobros con `POST /pagos/tokens`, números de tarjeta válidos (Luhn), distintos.
2. Barrer **todas** las columnas de las cinco tablas del módulo, el log de la aplicación y **todas**
   las respuestas de `GET /pagos/...` buscando cualquier secuencia de 13–19 dígitos que pase Luhn.
3. **Esperado**: cero coincidencias. Cada `token_pago` tiene exactamente {`token`, `id_venta`,
   `clave_idempotencia`, `ultimos_digitos`, `marca`, `tipo`, `id_terminal_pago`, `id_sucursal`,
   `instante`, `dia_local`, `marca_tiempo_origen`} y nada más.
4. `GET /pagos/ventas/{id_venta}/pago` devuelve `token` y `ultimos_digitos` (4 dígitos), nunca el
   número completo.
5. Dos cobros con la **misma** tarjeta en dos ventas → dos `token` distintos (sin estabilidad entre
   ventas, research.md #4).

### 2. Rechazo de PAN completo, registrado sin el número (FR-018, SC-008)

1. `POST /pagos/tokens` con `numero_tarjeta` colocado (por error de integración) en un campo que no
   corresponde, o `ultimos_digitos` con 16 dígitos.
2. **Esperado**: `400 pagos_pan_detectado`; `GET /pagos/bitacora?tipo_evento=pan_rechazado` incluye
   una entrada nueva cuyo `resultado` y `referencia_recurso_id` **no** contienen ningún dígito del
   número más allá de los 4 permitidos.

### 3. Idempotencia de la tokenización — reintento de red del datáfono (FR-021, SC-009, research.md #15)

1. `POST /pagos/tokens { id_venta: 42, clave_idempotencia: "k1", ... }` → `201`, `token: T`.
2. Repetir 9 veces la **misma** petición (misma `id_venta`, misma `clave_idempotencia`).
3. **Esperado**: las 9 responden `200` con el **mismo** `token: T`. Una sola fila en `token_pago`
   para `id_venta = 42`.
4. `POST /pagos/tokens { id_venta: 42, clave_idempotencia: "k2", ... }` (bug del cliente, clave
   nueva) → `200` con `token: T` + entrada `token_idempotencia_divergente` en la bitácora.
5. `POST /pagos/tokens { id_venta: 99, clave_idempotencia: "k1", ... }` (clave reusada) →
   `409 pagos_clave_idempotencia_reusada`.

### 4. La tokenización no es camino crítico (FR-020, SC-010, SC-013)

1. Se cuentan las filas de `venta`, `turno` y `operador` de `001`.
2. Se simula una falla de `POST /pagos/tokens` (terminal cancela la captura). La venta de `001` se
   completa con su comportamiento base y su `referencia_terminal_pago` queda `NULL`.
3. **Esperado**: `GET /pagos/ventas/{id_venta}/pago` → `404 pagos_venta_sin_tokenizacion`. El conteo
   de filas de las tres tablas de `001` es idéntico antes y después: `007` no escribió en `001`.
4. Más tarde, `007` procesa el cobro pendiente → se crea `token_pago` y la consulta pasa a `200`.

### 5. Cobro offline se reconcilia por marca de tiempo de origen (FR-022)

1. Un cobro con tarjeta sin conectividad: `001` completa la venta y la encola.
2. Al recuperar conectividad, `POST /pagos/tokens` se reenvía con la misma `id_venta`, la misma
   `clave_idempotencia` y `marca_tiempo_origen` = el instante del cobro físico.
3. **Esperado**: se crea un único `token_pago`; su `marca_tiempo_origen` es el del cobro físico, no
   el de recepción. La regla de conflicto de `001` (gana la marca más antigua sobre `id_venta`)
   aplica sin cambios.

### 6. Firmware: "desactualizada" / "expuesta" / "referencia desconocida", con motivo (FR-010, FR-011, SC-004, SC-005)

1. Config: `ULTIMA_VERSION_FIRMWARE = {"P400": "3.2.0"}`,
   `LISTA_FIRMWARE_VULNERABLE = [{"modelo": "P400", "version": "3.0.1", "referencia": "CVE-2025-XXXX"}]`.
2. Terminales: A `P400 3.2.0`, B `P400 3.0.1`, C `P400 2.9.0`, D `Move5000 1.4.0`.
3. `GET /pagos/terminales?id_sucursal=`.
4. **Esperado**: A sin señal; B `expuesta_a_clonacion: true` con `referencias_vulnerabilidad:
   ["CVE-2025-XXXX"]` **y** `desactualizada: true`; C `desactualizada: true` (2.9.0 < 3.2.0), no
   expuesta; D `version_referencia_desconocida: true` (no hay `Move5000` en la config), **nunca**
   "al día".
5. **Ninguna** de las cuatro queda deshabilitada, bloqueada ni impedida de uso (FR-012, SC-005).
6. `LISTA_FIRMWARE_VULNERABLE = []` → B deja de estar `expuesta_a_clonacion` (sigue `desactualizada`).

### 7. Actualizar firmware reevalúa la terminal y deja rastro (FR-013)

1. `POST /pagos/terminales/{B}/firmware { version: "3.2.0", fecha, id_operador }`.
2. **Esperado**: B pasa a `desactualizada: false`, `expuesta_a_clonacion: false`; `historial_firmware`
   con la entrada nueva; `GET /pagos/bitacora?tipo_evento=firmware_actualizado` la incluye.
3. `POST .../firmware { version: "3.1.0" }` (retrocede) → `400 pagos_version_no_avanza`.

### 8. Señal de firmware atribuida a la sucursal del momento evaluado (FR-014)

1. Terminal registrada en sucursal 1 el `2026-01-01`; movida a sucursal 2 el `2026-06-01`
   (`PATCH /pagos/terminales/{id}`).
2. `GET /pagos/terminales?id_sucursal=1` incluye la terminal en el tramo hasta `2026-05-31`;
   `?id_sucursal=2` la incluye desde `2026-06-01`. Nunca en las dos a la vez para el mismo período.

### 9. Cobertura histórica: refleja el estado de entonces (FR-002, SC-001)

1. `PUT /pagos/cobertura { id_sucursal: 2, id_medio_pago: <tarjeta_credito>, acepta: true,
   fecha_desde: "2026-03-01", id_operador }`.
2. `GET /pagos/cobertura?id_sucursal=2&desde=2026-01-01&hasta=2026-02-28` → tarjeta de crédito
   `cubierto: false`.
3. `GET /pagos/cobertura?id_sucursal=2&desde=2026-04-01&hasta=2026-04-30` → `cubierto: true`.

### 10. Intención no atendida: métrica de cobertura, nunca venta ni consulta_no_atendida (FR-003, FR-005, SC-002)

1. Se cuentan las filas de `venta` y `consulta_no_atendida` de `001`.
2. `POST /pagos/intencion-no-atendida { id_sucursal: 2, id_medio_pago_deseado: <transferencia>,
   id_operador, clave_idempotencia }` tres veces (claves distintas).
3. **Esperado**: cero filas nuevas en `venta` y `consulta_no_atendida`. Tres entradas
   `intencion_no_atendida` en la bitácora.
4. `GET /pagos/cobertura?id_sucursal=2&...` → el medio `transferencia` con `intencion_no_atendida: 3`
   y `cuota_no_atendida` como razón sobre el total de eventos del período.

### 11. Bitácora de solo anexado (FR-025, SC-012)

1. Se toma una entrada existente de `bitacora_auditoria`.
2. Se intenta `UPDATE bitacora_auditoria SET resultado = '...' WHERE ...` y `DELETE FROM
   bitacora_auditoria WHERE ...` con el rol de aplicación (`rasero_app`).
3. **Esperado**: ambas fallan con error de permiso de PostgreSQL (`REVOKE UPDATE, DELETE`). No existe
   ningún endpoint de edición ni de borrado en `contracts/openapi.yaml`.

### 12. Ninguna entrada de bitácora contiene datos de pago completos (FR-026, SC-011)

1. Ejecutar un ciclo completo: emitir token, rechazar un PAN, actualizar firmware, cambiar cobertura,
   registrar intención no atendida.
2. **Esperado**: cada hecho genera una entrada con `tipo_evento`, `instante`, `dia_local`,
   `id_sucursal`, `iniciador_tipo` y `resultado`. Barrer todas las entradas: ninguna contiene una
   secuencia que pase Luhn ni un CVV.

### 13. Purga de tokens huérfanos no toca `001` (research.md #4)

1. Se archiva/borra una `venta` de `001` (simulado).
2. Se corre la tarea `purgar_tokens_huerfanos`.
3. **Esperado**: la fila de `token_pago` cuyo `id_venta` ya no resuelve se elimina; se anexa
   `token_purgado` a la bitácora (con `id_venta`, `ultimos_digitos`, `marca` — nada sensible). `007`
   **no** disparó el archivado de `001`.

### 14. Nada se agrega entre sucursales sin discriminar (FR-006, FR-034, SC-003)

1. Cobertura, terminales y bitácora en dos sucursales.
2. `GET /pagos/cobertura`, `GET /pagos/terminales` y `GET /pagos/bitacora` **sin** `id_sucursal` →
   `400 pagos_sucursal_requerida`. Con `id_sucursal` → solo las de esa sucursal.

### 15. Sin procesamiento financiero real (FR-036, SC-014)

1. Revisar `contracts/openapi.yaml` y el código: no hay ningún cliente HTTP hacia un adquirente,
   pasarela o procesador; ningún endpoint de autorización, captura financiera o settlement; ningún
   campo ni tabla de importe de pago.

### 16. Contrato público (SC — Principio III)

1. `pytest tests/contrato/test_contrato_pagos.py`.
2. **Esperado**: cada endpoint de `contracts/openapi.yaml` responde en su forma feliz y en sus modos
   de fallo declarados, con el error `{codigo, mensaje}` unificado con `001`–`006`.

---

## Checklist de cierre

- [ ] Migración `0007_pagos_seguridad` aplica y revierte limpio (incluida `CREATE EXTENSION
      btree_gist` y `REVOKE UPDATE, DELETE ON bitacora_auditoria`).
- [ ] Las 5 tablas (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`,
      `token_pago`) son las únicas nuevas; ninguna tabla de indicadores de firmware, ninguna tabla de
      eventos de intención no atendida.
- [ ] Las 8 suites obligatorias del plan en verde. Sin `xfail`.
- [ ] Barrido de PAN: 0 secuencias que pasen Luhn en columnas, logs, bitácora y respuestas.
- [ ] `TerminalesPago.tsx` y `BitacoraPagos.tsx` en registro Operación (2px, IBM Plex Sans tabular,
      sin animación salvo confirmación); `CoberturaPago.tsx` en Análisis (6px, Source Serif 4).
- [ ] Cero apariciones del Verde Rasero en las tres pantallas (Regla del Registro Sin Dinero).
- [ ] `tsc -b`, `eslint`, `vite build` en verde.
- [ ] `DESIGN.md` actualizado por el agente `documenter` a partir de las pantallas construidas.
