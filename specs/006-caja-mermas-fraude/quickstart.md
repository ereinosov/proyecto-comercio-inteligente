# Quickstart: Caja, Mermas y Fraude

**Fase 1** · 2026-09-05 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo sus reglas difíciles: el arqueo de
caja cuadra por turno y **no** es señal del fraude de sub-registro; la merma se clasifica sobre la
diferencia bruta de `001` y se valora al costo del lote (nunca cero); los indicadores por operador se
calculan sin librería y se presentan como desviación de la línea base de pares, nunca como conclusión
de fraude; y una diferencia sin explicación queda como `anomalia_caja` que el sistema **nunca** cierra
por su cuenta. No contiene código de implementación: eso pertenece a `tasks.md` y a la fase de
implementación.

## Requisitos previos

- **`001-core-ventas-inventario` User Story 1 completa** (checkpoint `873228d`): `venta`,
  `renglon_venta`, `turno`, `operador`, **`anulacion_venta`** (T032), `producto`, `sucursal`,
  `producto_precio_sucursal`, `lote` — este módulo los **consulta** (nunca escribe en ellos).
- **BLOQUEO parcial por `001` User Story 5** (`conteo_fisico` / `conteo_renglon`, T065–T071): el
  **esquema** existe en la migración `0001`, el **servicio no**. Las partes bloqueadas
  (clasificar una diferencia de conteo, el cruce contra el faltante de inventario, las anomalías de
  origen inventario) tienen sus pruebas marcadas `@pytest.mark.xfail(reason="001 User Story 5 —
  T065–T071", strict=True)`. Ver plan.md, "Estado de implementación por historia".
- **`007-pagos-seguridad` no existe**: el arqueo compara total contado contra total registrado, sin
  desglose por medio de pago (research.md #4).
- Misma base **PostgreSQL 16 nativa**, puerto **5442**, que ya usan `001`–`005`.
- Python 3.12 y Node.js 20, mismo entorno que el resto de módulos.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
. .venv/bin/activate                                 # Windows: .venv\Scripts\activate
alembic upgrade head                                  # aplica también 0006_caja_mermas_fraude
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm run dev
```

Parámetros de calibración en `backend/rasero/config/caja.py` (research.md #16), sobrescribibles por
variable de entorno: `VENTANA_ALERTA_CADUCIDAD_DIAS=14`, `TOLERANCIA_CUADRE_ARQUEO=0.00`,
`UMBRAL_MINIMO_VENTAS_INDICADOR=20`, `RAZON_DESVIACION_ANULACIONES=2.0`,
`RAZON_DESVIACION_PRECIO_BAJO_LISTA=2.0`.

## Pruebas

```bash
# Desde la raíz
pytest tests/unidad/test_arqueo_dominio.py tests/unidad/test_merma_valoracion.py tests/unidad/test_indicadores_operador.py
pytest tests/integracion/test_arqueo.py tests/integracion/test_merma.py tests/integracion/test_deteccion_fraude.py tests/integracion/test_anomalias.py
pytest tests/contrato/test_contrato_caja.py
```

Las siete suites de la tabla "Pruebas obligatorias" del plan deben estar en verde antes de fusionar;
las pruebas marcadas `xfail` (rama de `conteo_renglon`, cruce de inventario, anomalías de origen
inventario) permanecen `xfail` hasta que `001` implemente su User Story 5.

---

## Escenarios de validación

Cada escenario se comprueba contra PostgreSQL real (puerto 5442). Los marcados **⛔ xfail** dependen
de `001` User Story 5 y se documentan como fallo esperado, no como error.

### 1. El arqueo cuadra por turno y congela lo esperado (FR-002, FR-003, SC-001)

1. Un operador abre turno, registra tres ventas por `10.00`, `5.50` y `4.00`, cierra turno.
2. `POST /caja/arqueos { id_turno, monto_contado: "19.50", marca_tiempo_origen }`.
3. **Esperado**: `201` con `monto_esperado: "19.50"`, `diferencia: "0.00"`, `genero_anomalia: false`,
   `id_operador` y `id_sucursal` los del turno, `dia_local` el día local de la sucursal.
4. Se anula una de las ventas **después** del arqueo. Se vuelve a `GET /caja/arqueos/{id}`.
5. **Esperado**: `monto_esperado` sigue siendo `"19.50"` (congelado, research.md #4) — la anulación
   posterior no reescribe la diferencia registrada.

### 2. Faltante sin motivo → anomalía; con motivo → sin anomalía (FR-004, FR-027, FR-031, SC-010)

1. Turno con ventas por `100.00`. `POST /caja/arqueos { monto_contado: "92.00" }` (sin
   `motivo_conocido`).
2. **Esperado**: `diferencia: "-8.00"`, `genero_anomalia: true`, `id_anomalia_caja` presente;
   `GET /caja/anomalias?estado=sin_explicacion` la incluye con `origen: "efectivo"`.
3. Otro turno con ventas por `100.00`. `POST /caja/arqueos { monto_contado: "98.00",
   motivo_conocido: "mal dado el cambio" }`.
4. **Esperado**: `diferencia: "-2.00"`, `genero_anomalia: false`; **0 anomalías** nuevas.

### 3. Idempotencia del arqueo por turno (FR-005, SC-003)

1. `POST /caja/arqueos` 10 veces con el mismo `id_turno` y `monto_contado`.
2. **Esperado**: la primera responde `201`, las nueve siguientes `200` con el **mismo** `id_arqueo`.
   Exactamente una fila en `arqueo` para ese turno.

### 4. Turno sin ventas → esperado cero, no error (FR-007)

1. Un operador abre y cierra turno sin registrar ninguna venta.
2. `POST /caja/arqueos { monto_contado: "0.00" }`.
3. **Esperado**: `201`, `monto_esperado: "0.00"`, `diferencia: "0.00"`.

### 5. Frontera: el arqueo no escribe en `001` (SC-002, SC-011)

1. Se cuentan las filas de `venta`, `renglon_venta` y `movimiento_inventario`.
2. Se ejecuta un ciclo completo de arqueo (registro + ajuste vía `PATCH`).
3. **Esperado**: el conteo de filas de las tres tablas de `001` es idéntico antes y después.

### 6. Valoración de merma al costo del lote; "no calculable" nunca es cero (FR-010, FR-015, SC-005)

1. Producto con un lote de `costo_unitario = "2.00"`. `POST /caja/mermas { id_producto, id_sucursal,
   cantidad_faltante: 3, causa: "dano", id_operador_registro }` (sin `id_conteo_renglon`).
2. **Esperado**: `201`, `valoracion: "6.00"`, `conciliar_con_conteo: true`, **sin** `id_operador` de
   imputación.
3. Producto sin ningún lote con costo. Misma llamada.
4. **Esperado**: `valoracion: null` (la interfaz muestra "no calculable"), **nunca** `"0.00"`.
5. Producto a granel: `cantidad_faltante` en gramos, valoración sobre gramos al costo por kilogramo.

### 7. Alerta de caducidad: informativa, marca los ya caducados (FR-014)

1. Lotes con `fecha_caducidad` a `+3`, `+10` y `-2` días del día local; existencia positiva.
2. `GET /caja/alertas-caducidad?id_sucursal=&dentro_de_dias=14`.
3. **Esperado**: los tres lotes listados; el de `-2` con `ya_caducado: true` (color crítico), los
   otros con `ya_caducado: false` (color atención); cada uno con `valor_en_riesgo`. Ninguna
   escritura en `lote` ni en `existencia`.

### 8. Merma declarada fuera de conteo no ajusta existencia (FR-012, FR-034, SC-011)

1. Se cuenta `existencia` del producto. `POST /caja/mermas` (sin `id_conteo_renglon`).
2. **Esperado**: `existencia` sin cambios; la merma con `conciliar_con_conteo: true`.

### 9. ⛔ xfail — Clasificar una diferencia de `conteo_renglon` de `001` (FR-009, FR-015)

1. `POST /caja/mermas { id_conteo_renglon, causa: "vencimiento", ... }`.
2. **Esperado hoy**: `409 caja_bloqueado_por_001`. **Al implementar `001` User Story 5**: `201` con
   la merma valorada sobre la `diferencia` que `001` expone, sin recalcular esa diferencia.

### 10. Indicadores por operador: derivados, como desviación de pares (FR-018, FR-019, FR-023, SC-007, SC-008)

1. Tres operadores con ~40 ventas cada uno en el período. El operador B anula el 20 % de sus ventas;
   A y C, el 3 %.
2. `GET /caja/indicadores-operador?id_sucursal=&desde=&hasta=`.
3. **Esperado**: `mediana_pares_tasa_anulaciones` ≈ `0.03`; el operador B con `se_desvia: true` y
   `detalle_desviacion` que enumera "tasa 0,20 vs mediana de pares 0,03 (×6,7)"; A y C con
   `se_desvia: false`. **En ningún campo** aparece la palabra "fraude".
4. Un cuarto operador con solo 8 ventas y 2 anulaciones (25 %): `comparable: false`, `se_desvia:
   false` — no entra en la mediana ni recibe señal (`UMBRAL_MINIMO_VENTAS_INDICADOR`).

### 11. Arqueo cuadrado NO descarta el fraude (FR-008, FR-026, SC-004)

1. Un turno del operador B con arqueo de `diferencia: "0.00"` pero tasa de anulaciones atípica.
2. `GET /caja/indicadores-operador` sigue señalando a B; `GET /caja/anomalias` (cuando el cruce esté
   disponible) muestra la anomalía de inventario aunque el arqueo cuadró.
3. **Esperado**: la respuesta del cruce y la interfaz indican explícitamente que un arqueo con
   diferencia cero **no** es evidencia de ausencia de sub-registro.

### 12. ⛔ xfail — Cruce inventario-ventas y anomalía de origen inventario (FR-020, FR-025, SC-012)

1. Conteo físico de `001` con faltante de `10` unidades de un producto; `4` explicadas por una merma
   ya clasificada; `1` por una anulación registrada.
2. `POST /caja/cruce-operador { id_sucursal, desde, hasta, id_conteo_fisico }`.
3. **Esperado hoy**: `409 caja_bloqueado_por_001`. **Al implementar `001` User Story 5**: se crea una
   `anomalia_caja` de `origen: "inventario"` con `magnitud: 5` (10 − 4 − 1), `indicador_snapshot` con
   el desglose y el reparto por turno, e `id_operador` = el del turno con mayor participación. Si la
   merma y las anulaciones hubieran explicado las 10, **no se crea nada** (FR-025, FR-031).

### 13. El sistema nunca cierra una anomalía por el paso del tiempo (FR-029, SC-009)

1. Una `anomalia_caja` en `sin_explicacion`. Se avanza el reloj de prueba 90 días. Se corren las
   tareas de mantenimiento del sistema.
2. **Esperado**: la anomalía **sigue** `sin_explicacion` y sigue apareciendo en
   `GET /caja/anomalias?estado=sin_explicacion`. Ninguna transición automática.

### 14. Resolución de una anomalía por una persona (FR-030)

1. `POST /caja/anomalias/{id}/resolucion { resolucion: "error operativo confirmado", id_operador,
   nota }`.
2. **Esperado**: `estado: "resuelta"`, `id_operador_resolucion` e `instante_resolucion` poblados,
   `historial` con una entrada nueva que conserva el `estado` anterior (`sin_explicacion`) y el
   instante.
3. Un segundo `POST` de resolución sobre la misma anomalía → `400 caja_anomalia_ya_resuelta`.

### 15. Nada se agrega entre sucursales sin discriminar (FR-038, SC-006)

1. Arqueos, mermas y anomalías en dos sucursales.
2. `GET /caja/arqueos`, `GET /caja/mermas` y `GET /caja/anomalias` **sin** `id_sucursal` →
   `400 caja_sucursal_requerida`. Con `id_sucursal` → solo las de esa sucursal.

### 16. Contrato público (SC — Principio III)

1. `pytest tests/contrato/test_contrato_caja.py`.
2. **Esperado**: cada endpoint de `contracts/openapi.yaml` responde en su forma feliz y en sus modos
   de fallo declarados, con el error `{codigo, mensaje}` unificado con `001`–`005`.

---

## Checklist de cierre

- [ ] Migración `0006_caja_mermas_fraude` aplica y revierte limpio.
- [ ] Las 3 tablas (`arqueo`, `merma`, `anomalia_caja`) son las únicas nuevas; ninguna tabla de
      indicadores.
- [ ] Las 7 suites obligatorias del plan en verde; los `xfail` de `001` User Story 5 documentados,
      no como error.
- [ ] `Arqueo.tsx` en registro Operación (2px, IBM Plex Sans tabular, sin animación salvo
      confirmación); `Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx` en Análisis (6px,
      Source Serif 4).
- [ ] Cero apariciones del Verde Rasero en las cuatro pantallas (Regla del Registro Sin Dinero).
- [ ] `tsc -b`, `eslint`, `vite build` en verde.
- [ ] `DESIGN.md` actualizado por el agente `documenter` a partir de las pantallas construidas.
