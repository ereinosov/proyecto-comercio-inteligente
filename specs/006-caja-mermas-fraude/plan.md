# Implementation Plan: Caja, Mermas y Fraude

**Branch**: `006-caja-mermas-fraude` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-caja-mermas-fraude/spec.md`

## Summary

Detecta y atribuye las pérdidas de valor que un cuadre diario deja escapar, distinguiendo **tres
fenómenos con lógica de detección distinta** (FR-037), cada uno con su registro propio:

1. **Merma física** (`merma`) — pérdida de producto sin venta asociada. Toma la `diferencia` bruta
   que `001` ya expone en un `conteo_renglon` (o una declaración fuera de conteo), le asigna una
   **causa** (`ENUM`: vencimiento, daño, robo externo, error de conteo, merma de granel, pendiente),
   la **valora** al costo del lote FEFO de `001` (NULL = "no calculable", nunca cero) y la atribuye a
   una sucursal y a un período entre conteos — **nunca a un operador** (FR-011). Añade una alerta de
   caducidad derivada de `lote.fecha_caducidad`.
2. **Diferencia caja-cobrado** (`arqueo`) — al cierre de cada turno, el efectivo y los comprobantes
   contados contra `SUM(venta.total)` del turno (consulta a `001`). `UNIQUE (id_turno)` da la
   idempotencia (FR-005); `id_operador` / `id_sucursal` / `dia_local` se denormalizan de `turno`.
   Sin desglose por medio de pago hasta que exista `007` (research.md #4).
3. **Fraude por sub-registro** ("cobrar 5, registrar 3") — **cálculo derivado** sobre `001`
   (`anulacion_venta`, `renglon_venta`, `movimiento_inventario`, `conteo_renglon`), **nunca entidad
   propia** (research.md #2/#7): tasa de anulaciones por operador, concentración de ventas bajo
   precio de lista, y el cruce del faltante de inventario no explicado por merma contra las ventas
   registradas, repartido por turno. El resultado —cuando no hay explicación conocida— se registra en
   `anomalia_caja` de `origen = 'inventario'`. **El arqueo de efectivo NO es señal de este fraude**
   (FR-008, Lectura Crítica n.º 1): en este fraude el efectivo cuadra con lo registrado.

Un `anomalia_caja` transversal (`origen` ∈ {efectivo, inventario}, `estado` `sin_explicacion →
resuelta`, `historial` JSONB, `indicador_snapshot` JSONB) recoge toda diferencia que ninguna causa
conocida explica. El sistema **nunca fuerza una clasificación ni cierra la anomalía por el paso del
tiempo** (FR-029): permanece visible hasta que una persona la resuelve.

Se construye como extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic sobre
PostgreSQL 16 (puerto 5442) y del mismo frontend React 18 + TS + Vite que `001`–`005`. **Tres**
entidades nuevas (`arqueo`, `merma`, `anomalia_caja`) en el mismo esquema mediante la migración
`0006_caja_mermas_fraude`.

**Dos ejes que condicionan el plan**:

1. **Sin enmienda constitucional** (a diferencia de `003`/`004`/`005`): las tres entidades de `006`
   en la tabla de "Propiedad de Datos y Nomenclatura" (`arqueo`, `merma`, `anomalia_caja`) son
   **exactamente** las que el spec exige. La constitución además ya anticipa que `anomalia_caja` "se
   calcula consultando `movimiento_inventario`, `venta` y `anulacion_venta`" — los indicadores por
   operador son cálculo derivado, no tablas (research.md #2).
2. **BLOQUEO parcial por `001`**: `conteo_fisico` / `conteo_renglon` (User Story 5 de `001`, tareas
   T065–T071) están **especificadas y con esquema en la migración `0001`, pero sin servicio ni
   endpoint**. US1 (arqueo) no está bloqueada; US2, US3 y US4 tienen partes bloqueadas, marcadas
   `⛔ BLOQUEADA por 001 (T065–T071)` con `xfail` en las pruebas — mismo tratamiento que `004` dio a
   `consulta_no_atendida` (research.md #10, "Estado de implementación por historia" abajo).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001`–`005`. Introducir un segundo lenguaje, framework o **librería estadística**
(`scipy`, `statsmodels`, `numpy` para esto) para la misma función está PROHIBIDO por el Principio I
y se descarta explícitamente en research.md #16: la línea base de los indicadores por operador es
una **razón sobre la mediana** de un conjunto de pares, aritmética de una línea.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend);
Vite + React sin librería de componentes de terceros (frontend). Todas ya presentes. Este plan
**no añade ninguna dependencia nueva**.

**Storage**: la misma base PostgreSQL 16 de `001`–`005`, nativa en desarrollo, puerto **5442**. Las
tres entidades se agregan al mismo esquema mediante la migración `0006_caja_mermas_fraude`; no se
crea una base ni un esquema aparte. SQLite sigue PROHIBIDO.

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`–`005`.

**Target Platform**: mismo servidor de un solo nodo y mismo navegador de escritorio.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se
crea un servicio nuevo.

**Performance Goals**: registrar un arqueo, clasificar una merma o resolver una anomalía responde en
menos de 1 s. El cálculo de `GET /caja/indicadores-operador` y de `POST /caja/cruce-operador` para
una sucursal y una ventana de ≤ 60 días responde en menos de 2 s p95 — son consultas de agregación
sobre `venta` / `anulacion_venta` / `movimiento_inventario` de `001` indexadas por sucursal y por
día, nunca un bucle por operador ni por venta.

**Constraints**: ninguna función de este módulo participa en `POST /ventas` ni es camino crítico de
un cobro (Principio II); el arqueo se registra **después** del cierre del turno y es offline-capable
con la regla de reconciliación de `001` (FR-006); `006` **nunca** ajusta `existencia`,
`movimiento_inventario`, `venta` ni ningún precio (FR-032), **nunca** ejecuta un conteo físico
(FR-033), **nunca** bloquea, suspende ni sanciona a un operador de forma automática (FR-024, FR-040);
toda detección, arqueo, merma y anomalía se identifica por sucursal (FR-038, Principio IV); toda
cantidad monetaria en tipos decimales exactos — coma flotante binaria PROHIBIDA en el esquema y en
el código.

**Scale/Scope**: mismo orden de magnitud que `001`–`005` — decenas de turnos por semana y por
sucursal, cientos de productos, dos sucursales en el alcance de examen (cifra de entrega, no del
modelo). `arqueo`, `merma` y `anomalia_caja` son **append + máquina de estados** (nunca se recomputan
al leer, a diferencia de `margen_calculado` de `003` o `demanda_corregida` de `004`). Los indicadores
por operador, el cruce inventario-ventas y la alerta de caducidad son las **únicas consultas
derivadas** del módulo — ninguna es tabla.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.5** (vigente). Este módulo **no motiva ninguna
enmienda** (ver "Nota sobre la propiedad de datos" abajo).

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`arqueo`, `merma`, `anomalia_caja`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack de `001`–`005`; **no** introduce librería estadística — la línea base de los indicadores es una razón sobre la mediana de un conjunto (research.md #16). |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna función participa en `POST /ventas` ni en ningún flujo de cobro. El arqueo se registra **después** del cierre del turno, por una llamada aparte e idempotente por `id_turno` (FR-005), offline-capable con la regla de `001` (FR-006). La clasificación de merma y la resolución de anomalía son administrativas. Si `006` no responde, la caja cobra y cierra el turno igual. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias": el cálculo de `monto_esperado` del arqueo y su diferencia con signo, la idempotencia por `id_turno`, la valoración de merma al costo del lote (con el caso "no calculable"), la frontera de solo lectura con `001` (0 escrituras), la creación de `anomalia_caja` solo cuando no hay explicación (FR-031) y que el sistema nunca la cierra por tiempo (FR-029) tienen suite obligatoria. Interfaz y maquetación de las cuatro pantallas quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `arqueo`, `merma` y `anomalia_caja` son append + estado, nunca se borran. Cada arqueo guarda `monto_esperado` congelado, `monto_contado`, `diferencia` y `ajustes`; cada merma, el `id_conteo_renglon` de origen (o su ausencia), la causa y la valoración con su costo; cada anomalía, su `historial` JSONB completo de cambios de estado con quién y cuándo, y su `indicador_snapshot`. Todo lleva `id_sucursal`; `GET /caja/anomalias`, `/caja/mermas` y `/caja/arqueos` filtran por sucursal y nunca agregan dos sin discriminar (FR-038). |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: cada señal del cruce por operador enumera las anulaciones, los renglones bajo precio de lista y el faltante de qué conteo la sustentan, y el período (FR-022, SC-007); cada anomalía y cada merma se reconstruye del registro (FR-039). **Consultiva por defecto**: `006` detecta, atribuye y explica; **nunca** ajusta inventario, bloquea operadores ni sanciona (FR-024, FR-040). La acción correctiva la decide una persona. **Con línea base**: los indicadores por operador se presentan **siempre** como desviación respecto del comportamiento de los pares comparables de la misma sucursal (FR-023), nunca como conclusión de fraude. **Acotada**: límites documentados — sin desglose por medio de pago hasta `007` (research.md #4), cruce de inventario bloqueado hasta `001` User Story 5 (research.md #10), reparto proporcional del faltante como indicador y no imputación individual (Edge Case del spec). **Visible**: registro mixto Operación/Análisis con los tres portadores para "sin explicación", "no calculable" y "lote caducado" (research.md #15). |

**Nota sobre la propiedad de datos**: al preparar este plan se contrastó la entrada **completa** de
`006-caja-mermas-fraude` en la tabla de "Propiedad de Datos y Nomenclatura" (`arqueo`, `merma`,
`anomalia_caja`) contra el spec y las fronteras de la propia sección (research.md #2). **No se
encontró ninguna discrepancia** — a diferencia de `003` (v2.2.3, `costo_producto` retirado), `004`
(v2.2.4, `sustitucion_producto` añadida) y `005` (v2.2.5, de 3 a 6 entidades). Las tres entidades
listadas son exactamente las que el spec exige. La constitución además ya declara legítimo el diseño:
"`anomalia_caja` es propiedad de 006, pero se **calcula consultando** `movimiento_inventario`,
`venta` y `anulacion_venta`, propiedad de 001. Eso es consulta entre funcionalidades, no
redefinición". Los indicadores por operador (tasa de anulaciones, concentración de ventas bajo precio
de lista, cruce inventario-ventas) son **cálculo derivado**, nunca tabla — decisión cerrada en
research.md #2/#7. **La Puerta de propiedad de datos no bloquea la fusión.**

**Lecturas Críticas del Enunciado aplicadas** (decisiones de análisis ya tomadas, no reabiertas):

- **Lectura n.º 1** ("el arqueo horario no detecta el fraude que parece detectar"): es **el**
  principio rector de este módulo. FR-008 lo hace explícito: el arqueo de efectivo, por sí solo,
  NO DEBE usarse como señal de fraude por sub-registro, y una diferencia de arqueo igual a cero NO
  DEBE presentarse como evidencia de ausencia de fraude. El fraude de "cobrar 5, registrar 3" se
  detecta **solo** cruzando salida de inventario contra venta registrada, tasa de anulaciones por
  operador y concentración de ventas bajo precio de lista (FR-018 a FR-020). El arqueo se implementa
  para el fraude **distinto** que sí produce descuadre: retiro de efectivo sin registrar venta
  (`anomalia_caja` de origen efectivo).
- **Frontera `001` / `006`** (ya escrita en la constitución): "el conteo físico y la diferencia
  bruta pertenecen a `001`, que ejecuta el conteo y expone el descuadre sin interpretarlo; la
  clasificación de la causa de esa diferencia —merma, robo, error de registro— pertenece a `006`,
  que no ejecuta conteos". El esquema lo refleja: `merma.id_conteo_renglon` es una FK de solo
  lectura hacia `001`; no hay ninguna tabla de conteo en `006`.
- **Frontera con la caducidad**: "la fecha de caducidad del lote vive en inventario (`001`); la
  política de alerta y la contabilización de la pérdida viven en mermas (`006`)". La alerta de
  caducidad es una consulta derivada de `lote.fecha_caducidad`; `006` no escribe en `lote`.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`–`005`. Nueva migración Alembic `0006` sobre el mismo esquema. |
| Precisión exacta en dinero y en peso en gramos | Montos de arqueo y valoración de merma en `NUMERIC(12,2)`; cantidades faltantes en `NUMERIC(14,0)` (unidades o gramos, como `001`); razones y tasas de los indicadores calculadas con `Decimal` y presentadas como cadena. Ningún `float` en el esquema ni en el cálculo de diferencias. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `arqueo`, `merma`, `anomalia_caja`. Claves foráneas `id_turno`, `id_conteo_renglon`, `id_sucursal`, `id_producto`, `id_operador`, `id_lote`, `id_arqueo`. |
| Tiempo en UTC, agregaciones por día local de la sucursal | `arqueo.dia_local`, `merma.periodo_desde`/`periodo_hasta` y `anomalia_caja.periodo_*` son **días locales** de la sucursal: `(instante AT TIME ZONE sucursal.zona_horaria)::date` (research.md #12). Los filtros `desde`/`hasta` de los endpoints se interpretan como día local. |
| Propiedad de datos: exactamente las 3 entidades de 006 | `data-model.md` define únicamente `arqueo`, `merma`, `anomalia_caja`. `turno`, `venta`, `renglon_venta`, `anulacion_venta`, `movimiento_inventario`, `existencia`, `conteo_fisico`, `conteo_renglon`, `lote`, `operador`, `producto`, `sucursal`, `producto_precio_sucursal` (de `001`) se **consultan, nunca se redefinen ni se escriben**. Los tests de frontera cuentan filas antes y después para verificar 0 escrituras. |
| Sistema de diseño: registros Operación y Análisis | Ver "Sistema de diseño en el frontend". `Arqueo.tsx` es Operación (2px, IBM Plex Sans, cifras tabulares, sin animación salvo confirmación); `Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx` son Análisis (6px, Source Serif 4). Regla del Registro Sin Dinero: cero apariciones del Verde Rasero en las cuatro pantallas (research.md #15). |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0006_caja_mermas_fraude`) con `downgrade` que elimina las tres tablas y sus `ENUM`. |
| Inteligencia explicable y reversible (Principio V) | Ver tabla de Principios. Nada que "deshacer" porque el módulo nunca actúa sobre inventario, precio ni personas — una merma mal clasificada se reclasifica, una anomalía se reabre; ambas conservan su historial. |

**Resultado de la puerta**: PASA. Sin desviaciones que requieran Complexity Tracking.

**Re-verificación tras la Fase 1 (data-model.md, contracts/, quickstart.md)**: sin cambios en el
veredicto. El diseño confirma que (a) las tres tablas son exactamente las de la tabla de propiedad;
(b) no hay `float` en el esquema; (c) el contrato no expone ningún endpoint que ajuste inventario,
precio o el estado de un operador, ni que ejecute un conteo; (d) `merma.id_conteo_renglon` y todas
las referencias a `001` son FK de solo lectura, y ninguna columna de `001` se duplica salvo las
denormalizaciones justificadas de `arqueo` (`id_operador`, `id_sucursal`, `dia_local`, todas
derivadas de `turno` e inmutables — research.md #4); (e) toda ruta lleva `id_sucursal` o lo deriva,
y `GET /caja/anomalias` / `/caja/mermas` / `/caja/arqueos` lo exigen (Principio IV, FR-038);
(f) `anomalia_caja` nunca transita a `resuelta` sin `id_operador_resolucion` e `instante_resolucion`
(FR-030), y no hay ninguna transición automática por tiempo (FR-029).

## Estado de implementación por historia (dependencias verificadas contra el repositorio)

El spec (sección "Dependencias entre módulos") exige que este plan diga qué se puede construir ya.
**Verificación**: `git log` y `specs/001-core-ventas-inventario/tasks.md` en el árbol de trabajo.

| Dependencia | Estado real | Fuente |
|---|---|---|
| `001` — `venta`, `renglon_venta`, `turno`, `operador`, **`anulacion_venta`** (T032), `producto`, `sucursal`, `producto_precio_sucursal`, `lote`, resolución de precio por sucursal | **Entregado** (checkpoint `873228d`; T001–T043 de `001/tasks.md` en `[X]`, `anulacion_venta` en T032) | `specs/001-core-ventas-inventario/tasks.md`, migración `0001` |
| `001` — **`conteo_fisico`, `conteo_renglon`** (User Story 5, T065–T071): servicio de inicio y resolución de conteo, endpoints `POST /conteos-fisicos` y `/resolucion`, pantallas `ConteoFisico.tsx` / `ResolucionConteo.tsx` | **NO entregado** (T065–T071 en `[ ]`). El **esquema** de `conteo_fisico` y `conteo_renglon` **sí** existe en la migración `0001` (`001/data-model.md`) | `specs/001-core-ventas-inventario/tasks.md` líneas 166–180 |
| `007-pagos-seguridad` — `medio_pago`, `terminal_pago` | **NO existe** (ni spec) — por eso el arqueo compara total contra total (research.md #4) | tabla de Propiedad de Datos de la constitución |
| `004` — consume la `demanda_observada.con_promocion` de `005`; **no** interactúa con `006` | Sin relación directa (research.md #4 del checklist del spec) | — |

| Historia de `006` | ¿Construible ahora? | Nota |
|---|---|---|
| **US1 — Arqueo de caja por turno** | **Sí, completa** | Solo `turno` y `venta` de `001` (entregadas). Construye la tabla `arqueo` y el ciclo `POST /caja/arqueos` + `GET /caja/arqueos`. Crea la `anomalia_caja` de origen efectivo cuando la diferencia no tiene motivo. |
| **US2 — Clasificar mermas físicas** | **Parcial** | **No bloqueado**: alerta de caducidad (FR-014, `GET /caja/alertas-caducidad`) y declaración de merma fuera de conteo (FR-012, `POST /caja/mermas` sin `id_conteo_renglon`) — solo necesitan `lote`. **⛔ BLOQUEADO por `001` (T065–T071)**: clasificar una `diferencia` de `conteo_renglon` (FR-009, FR-015) — la rama de `POST /caja/mermas` que recibe `id_conteo_renglon`. |
| **US3 — Cruce por operador para detectar sub-registro** | **Parcial** | **No bloqueado**: tasa de anulaciones (FR-018) y concentración de ventas bajo precio de lista (FR-019) — `GET /caja/indicadores-operador`, solo necesitan `venta`, `anulacion_venta`, `renglon_venta`. **⛔ BLOQUEADO por `001` (T065–T071)**: el cruce contra el faltante de inventario (FR-020) — la parte de `POST /caja/cruce-operador` que lee `conteo_renglon`. |
| **US4 — Gestionar anomalías sin explicación** | **Parcial** | **No bloqueado**: anomalías de `origen = 'efectivo'` (desde US1) y su resolución (`GET /caja/anomalias`, `POST /caja/anomalias/{id}/resolucion`). **⛔ BLOQUEADO por `001` (T065–T071)**: anomalías de `origen = 'inventario'`, que dependen del cruce de FR-020. |

**Conclusión para `/speckit-tasks`**: el plan de tareas ordena US1 → US2 → US3 → US4. Las tareas
bloqueadas se marcan `⛔ BLOQUEADA por 001 (T065–T071)` y sus pruebas llevan
`@pytest.mark.xfail(reason="001 User Story 5 / conteo_fisico sin implementar — T065–T071",
strict=True)`. Al implementarse `001` User Story 5, se quitan los `xfail` y se completan las tareas
bloqueadas — mismo procedimiento que `004` documentó para `consulta_no_atendida` (T014, T009).

## Project Structure

### Documentation (this feature)

```text
specs/006-caja-mermas-fraude/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Fase 2 (/speckit-tasks — no lo crea este comando)
```

### Source Code (repository root)

Misma estructura de primer nivel que `001`–`005`, fijada y no negociable. Este módulo **extiende**
`backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel. (Rutas
verificadas: `backend/migraciones/versions/` contiene `0001`–`0005`; `backend/rasero/config/` ya
existe con `pronostico.py` y `promociones.py`.)

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── config/
│   │   │   └── caja.py                        # NUEVO — los 5 parámetros de research.md #16, sobrescribibles por entorno (patrón de config/pronostico.py y config/promociones.py)
│   │   ├── dominio/
│   │   │   ├── arqueo.py                      # NUEVO — funciones puras: diferencia con signo, resolución del día local del turno, decisión "genera anomalía" (research.md #4)
│   │   │   ├── merma.py                       # NUEVO — funciones puras: valoración al costo del lote FEFO (con caso "no calculable"), período entre conteos (research.md #5, #11)
│   │   │   └── indicadores_operador.py        # NUEVO — funciones puras: tasa de anulaciones, concentración bajo precio de lista, reparto proporcional del faltante, línea base por razón sobre la mediana de pares (research.md #7)
│   │   ├── persistencia/
│   │   │   └── modelos.py                     # AMPLIADO — Arqueo, Merma, AnomaliaCaja
│   │   ├── servicios/
│   │   │   ├── arqueos.py                     # NUEVO (US1) — registrar_arqueo (calcula monto_esperado desde 001, congela, crea anomalia_caja de origen efectivo si procede), listar_arqueos, ajustar_arqueo
│   │   │   ├── mermas.py                      # NUEVO (US2) — clasificar_merma (rama con id_conteo_renglon ⛔ / rama declaración libre ✓), listar_mermas, alertas_caducidad (consulta derivada sobre 001)
│   │   │   └── deteccion_fraude.py            # NUEVO (US3+US4) — indicadores_operador (consulta derivada ✓), cruce_inventario_ventas (⛔ parte de conteo_renglon), listar_anomalias, resolver_anomalia
│   │   └── api/
│   │       └── caja.py                        # NUEVO — routers de arqueos, mermas, alertas-caducidad, cruce-operador, indicadores-operador, anomalias
│   └── migraciones/versions/
│       └── 0006_caja_mermas_fraude.py         # NUEVO — 3 tablas + 3 ENUM, con downgrade
├── frontend/src/
│   ├── pantallas/
│   │   ├── Arqueo.tsx                         # NUEVO — registro de OPERACIÓN: tabla de arqueos por turno, captura del efectivo contado, diferencia con signo (research.md #15)
│   │   ├── Mermas.tsx                         # NUEVO — registro de ANÁLISIS: clasificar diferencias de conteo, declarar merma libre, alertas de caducidad
│   │   ├── AnomaliasCaja.tsx                  # NUEVO — registro de ANÁLISIS: cola de anomalías sin explicación, detalle con historial e indicador_snapshot, resolución
│   │   └── IndicadoresOperador.tsx            # NUEVO — registro de ANÁLISIS: tasa de anulaciones y concentración bajo precio de lista por operador, con la línea base de pares y quién se desvía
│   ├── servicios/
│   │   └── caja.ts                            # NUEVO — cliente HTTP de los endpoints /caja
│   └── App.tsx                                # AMPLIADO — nuevas pestañas "Arqueo" (Operación) y "Caja y fraude" (Análisis, agrupa Mermas / Anomalías / Indicadores)
└── tests/
    ├── unidad/
    │   ├── test_arqueo_dominio.py             # NUEVO — diferencia con signo, día local, decisión "genera anomalía" con y sin motivo
    │   ├── test_merma_valoracion.py           # NUEVO — valoración al costo del lote FEFO; producto sin costo → "no calculable", nunca cero (SC-005)
    │   └── test_indicadores_operador.py       # NUEVO — tasa de anulaciones, concentración bajo precio de lista, reparto proporcional, línea base por mediana de pares, umbral mínimo de ventas
    ├── integracion/
    │   ├── test_arqueo.py                     # NUEVO (US1) — monto_esperado = SUM(venta.total) del turno; idempotencia por id_turno (FR-005, SC-003); turno sin ventas → esperado 0 (FR-007); frontera: 0 escrituras en venta (SC-002); diferencia sin motivo → anomalia_caja de origen efectivo (FR-004, FR-027)
    │   ├── test_merma.py                      # NUEVO (US2) — declaración fuera de conteo ✓ (FR-012); alerta de caducidad ✓ (FR-014); clasificación de conteo_renglon ⛔ xfail (FR-009, FR-015); desglose por causa/producto/sucursal (FR-016); 0 escrituras en existencia (FR-034, SC-011)
    │   ├── test_deteccion_fraude.py           # NUEVO (US3) — tasa de anulaciones y concentración bajo precio de lista por operador ✓ (FR-018, FR-019); línea base como desviación de pares, nunca conclusión de fraude (FR-023, SC-008); cruce contra faltante de inventario ⛔ xfail (FR-020); arqueo cuadrado NO descarta fraude (FR-026, SC-004)
    │   └── test_anomalias.py                  # NUEVO (US4) — anomalía de origen efectivo desde US1 ✓; el sistema nunca la cierra por tiempo (FR-029, SC-009); resolución registra estado_anterior en historial (FR-030); diferencia totalmente explicada → 0 anomalías (FR-031, SC-010, SC-012); anomalía de origen inventario ⛔ xfail
    └── contrato/
        └── test_contrato_caja.py              # NUEVO — respuestas de contracts/openapi.yaml en forma feliz y modos de fallo, con el formato de error {codigo, mensaje} unificado
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001`–`005` cambia de propiedad ni de esquema. Este módulo **solo lee** de `001` — no escribe en
ninguna tabla ajena, ni siquiera a través de una función-puente (a diferencia de `003`, que escribía
en `producto_precio_sucursal`). No necesita ninguna función nueva en los servicios de `001`.

`frontend/src/App.tsx` se **amplía** (no se reescribe) con dos pestañas nuevas. `Arqueo.tsx` vive en
el registro de Operación, junto al cierre de turno; las otras tres en Análisis.

## Pruebas obligatorias

Derivadas del Principio III. El riesgo central del módulo es doble: (a) un arqueo que trate una
diferencia de cero como "sin novedad" enmascara el fraude de sub-registro que la Lectura Crítica
n.º 1 describe —el que **nunca** produce descuadre de caja—; (b) una señal por operador presentada
como conclusión de fraude, o un faltante de inventario imputado a un operador sin descontar la merma
declarada, acusa a una persona con un cálculo mal hecho.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Cálculo y congelación del arqueo | `tests/integracion/test_arqueo.py` | `monto_esperado` = `SUM(venta.total)` de las ventas del turno, **congelado** en la fila: anular una venta **después** del arqueo no cambia `monto_esperado` ni `diferencia` (research.md #4). `diferencia` con signo correcto (faltante negativo, sobrante positivo). Turno sin ventas → `monto_esperado = 0`, no error (FR-007). Idempotencia: 10 `POST /caja/arqueos` con el mismo `id_turno` → exactamente un `arqueo` (SC-003). Por conteo directo de filas, `POST /caja/arqueos` no toca `venta`, `renglon_venta` ni `movimiento_inventario` (SC-002, SC-011). |
| 2 | El arqueo NO es señal de fraude por sub-registro | `tests/integracion/test_deteccion_fraude.py` | Un turno con `diferencia = 0` en el arqueo pero con tasa de anulaciones atípica y (cuando `001` lo permita) faltante de inventario no explicado → `GET /caja/indicadores-operador` **señala** a ese operador y `POST /caja/cruce-operador` genera la anomalía; la respuesta indica explícitamente que el arqueo cuadrado **no** descarta el fraude (FR-008, FR-026, SC-004). |
| 3 | Valoración de merma al costo del lote | `tests/unidad/test_merma_valoracion.py` + `tests/integracion/test_merma.py` | Merma de N unidades de un producto con costo de lote conocido → `valoracion = N × lote.costo_unitario` del lote FEFO; producto a granel → sobre gramos al costo por kilogramo (FR-015). Producto **sin** costo de lote → `valoracion = NULL` ("no calculable"), **nunca 0** (SC-005). La merma **nunca** lleva `id_operador` (FR-011). |
| 4 | Merma: rama libre ✓ y rama de conteo ⛔ | `tests/integracion/test_merma.py` | `POST /caja/mermas` **sin** `id_conteo_renglon` (rotura declarada) registra la merma con causa, cantidad y valor, y marca "conciliar con próximo conteo"; **no** escribe en `existencia` (FR-012, FR-034). `GET /caja/alertas-caducidad` lista los lotes de `001` cuya caducidad entra en `VENTANA_ALERTA_CADUCIDAD_DIAS` con su valor en riesgo (FR-014). **`xfail`**: `POST /caja/mermas` **con** `id_conteo_renglon` clasifica la `diferencia` de `001` — `@pytest.mark.xfail(reason="001 User Story 5 / conteo_renglon sin implementar — T065–T071", strict=True)`. |
| 5 | Indicadores por operador: derivados, como desviación de pares | `tests/unidad/test_indicadores_operador.py` + `tests/integracion/test_deteccion_fraude.py` | Tasa de anulaciones y concentración bajo precio de lista calculadas contra `001` (atribución `anulacion_venta.id_operador` y `venta → turno.id_operador`, FR-049 de `001`). Un operador con < `UMBRAL_MINIMO_VENTAS_INDICADOR` ventas **no** entra en la mediana de pares ni recibe señal. Un operador se señala solo si su valor ≥ `RAZON_DESVIACION_* ×` mediana de pares comparables de su sucursal y período. La respuesta **nunca** dice "fraude": dice "se desvía de la línea base de sus pares" con los datos que lo sustentan (FR-023, SC-007, SC-008). **`xfail`**: el cruce contra el faltante de `conteo_renglon` (FR-020). |
| 6 | Anomalía: solo sin explicación, nunca cerrada por el sistema | `tests/integracion/test_anomalias.py` | Un arqueo con faltante **con** `motivo_conocido` anotado → **0 anomalías**; **sin** motivo → una `anomalia_caja` de origen efectivo en `sin_explicacion` (FR-004, FR-031, SC-010). Un faltante de inventario que coincide con una merma ya clasificada → **0 anomalías** (SC-012). Pasado cualquier plazo simulado, una anomalía `sin_explicacion` **sigue** `sin_explicacion` (FR-029, SC-009). `POST /caja/anomalias/{id}/resolucion` exige `id_operador`, registra `estado_anterior` y el instante en `historial`, y solo entonces pasa a `resuelta` (FR-030). |
| 7 | Contrato público | `tests/contrato/test_contrato_caja.py` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados, con el formato de error `{codigo, mensaje}` unificado en `001`–`005`. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `Arqueo.tsx`,
`Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx`.

## Sistema de diseño en el frontend

**Registro visual mixto** (research.md #15), confirmado contra `DESIGN.md`:

- **`Arqueo.tsx` — OPERACIÓN**. La constitución y `DESIGN.md` listan literalmente "**Operación**
  (punto de venta, inventario, **arqueo**)". Alta densidad, la tabla como elemento principal, sin
  tarjetas, radio **2px**, IBM Plex Sans con cifras tabulares reales (efectivo contado y esperado
  alinean por dígito), **sin animación** salvo la confirmación de cerrar el arqueo. Vive junto al
  cierre de turno.
- **`Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx` — ANÁLISIS**. Una decisión por
  bloque, aire visual, líneas bajo 80 caracteres, radio **6px**, Source Serif 4. Un único momento de
  animación deliberado por pantalla (al revelar el detalle de una anomalía o el desglose de un
  indicador), nunca hover por fila ni fade-in por bloque.

**Reglas nombradas de `DESIGN.md` aplicadas sin tocar el documento** (el `documenter` lo actualiza
al final):

- **La Regla del Registro Sin Dinero**: **ninguna** de las cuatro pantallas tiene una acción que
  comprometa dinero → **cero apariciones del Verde Rasero `#0F5132`**, igual que `Clientes.tsx`.
- **La Regla de la Sola Voz**: no aplica por ausencia de acción de dinero.
- **La Regla del Significado** (los tres semánticos, uso reservado):
  - **crítico `#8E2A2A`** — una `anomalia_caja` en `sin_explicacion` y un lote **ya caducado** en la
    alerta. Es el caso de uso literal que la constitución cita ("caducado, anomalía").
  - **atención `#9A5B08`** — un lote **próximo a caducar** (aún no vencido) y una diferencia de
    arqueo con `motivo_conocido` anotado (dato en seguimiento, no crítico).
  - **estimado `#1F5673`** — todo valor **calculado, no observado**: el faltante repartido
    proporcionalmente a un turno, la señal de desviación de un indicador, la `valoracion` de una
    merma. El dato **observado** (la `diferencia` bruta del conteo de `001`, el efectivo contado, la
    tasa de anulaciones cruda) va en tinta normal.
- **La Regla de los Tres Portadores**: "sin explicación", "no calculable", "sin ventas suficientes
  para comparar" y "lote caducado" se comunican con color semántico + forma (punto lleno / medio /
  hueco) + texto explícito. Una `anomalia_caja` `sin_explicacion` usa el **punto hueco** (como
  `senal_fuga` `confirmada` en `002`): ese dato está pendiente de que una persona lo cierre.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado en `001`); este módulo no repite
`init`. Se invoca `new-work` de Impeccable para las cuatro pantallas con el mundo visual fijado (los
dos registros, la paleta y la tipografía de `DESIGN.md`, sin cambio). El agente `documenter`
actualiza `DESIGN.md` al finalizar, derivándolo de las pantallas construidas.

## Complexity Tracking

*Sin desviaciones que requieran justificación.* Este módulo no introduce ninguna segunda tecnología
(en particular, **ninguna librería estadística** — la línea base de los indicadores por operador es
una razón sobre la mediana de un conjunto de pares, decisión de research.md #16 anclada en el
Principio I y en el Principio V "explicable"), **no requiere ninguna enmienda constitucional** (las
tres entidades ya están en la tabla de propiedad y coinciden con el spec), no viola ninguna frontera
de propiedad de datos (solo lee de `001`, nunca escribe) y no necesita ningún mecanismo (disparador
de base de datos, cola, servicio externo) más allá de endpoints HTTP y, opcionalmente, una tarea
invocable a mano para el barrido de alertas de caducidad — mismo patrón que `tareas/` de `002` y
`005`.
