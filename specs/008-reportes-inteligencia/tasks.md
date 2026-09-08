# Tasks — 008-reportes-inteligencia

**Entrada**: [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/openapi.yaml](./contracts/openapi.yaml), [spec.md](./spec.md)

**Pruebas**: sólo las suites obligatorias del Principio III, proporcionales al riesgo:
contrato de los endpoints de lectura + unidad del k-means (determinismo, separación de
patrones, k > n). Sin pruebas de interfaz, maquetación ni componentes visuales.

**Convención `[P]`**: puede correr en paralelo (archivo distinto, sin dependencia pendiente).
**Convención `[Story]`**: traza a la User Story del spec.

**Prerrequisito ya cumplido**: enmienda constitucional **v2.6.0** (Propiedad de Datos para 008)
— hecha antes de este plan.

---

## Fase 0 — Setup y Foundational (secuencial, en conjunto)

- [X] T001 Migración `backend/migraciones/versions/0012_reportes_inteligencia.py`: crea
  `agregado_reporte`, `segmento_cliente`, `asignacion_segmento` según data-model.md (CHECKs,
  UNIQUEs, FKs, `ON DELETE CASCADE` de `asignacion_segmento` desde `cliente`). `downgrade`
  elimina las tres tablas. Verificar `upgrade`/`downgrade` reversible.
- [X] T002 `backend/rasero/persistencia/modelos.py`: modelos ORM `AgregadoReporte`,
  `SegmentoCliente`, `AsignacionSegmento`.
- [X] T003 `backend/rasero/config/reportes.py`: `K_SEGMENTOS` (3 o 4, tras calibración),
  `MIN_VISITAS_CLASIFICABLE = 3`, `SEMILLA_SEGMENTOS` (fija), `PERIODOS_TENDENCIA_DEFECTO`
  (semana=12, mes=6), umbrales de `atencion` de cada KPI (margen bajo, cuota no atendida, etc.).
- [X] T004 `backend/rasero/api/reportes.py`: router `APIRouter(prefix="/reportes",
  dependencies=[Depends(exige_rol("encargado"))])`, registrado en `api/aplicacion.py`. Sin
  endpoints todavía.
- [X] T005 [P] `backend/rasero/dominio/periodo_local.py`: función pura
  `periodos_locales(zona_horaria, granularidad, n) -> list[Periodo]` con
  `(inicio_utc, fin_utc, etiqueta, completo)`. Semana ISO local y mes calendario local.
- [X] T006 [P] Prueba de unidad `tests/unidad/test_periodo_local.py`: una venta a las 23:30
  local del domingo cae en esa semana; mes = mes calendario, no ventana de 30 días; período
  parcial en un borde → `completo=false`.

## Fase 1 — k-means (dominio puro) — bloque independiente

- [X] T007 [P] [US4] `backend/rasero/dominio/kmeans.py`: función pura `agrupar(puntos: list[tuple],
  k: int, semilla: int, max_iter=50) -> list[int]` (índice de grupo por punto). Lloyd:
  init k-means++ con RNG de semilla fija + orden determinista de puntos; asignación por distancia
  euclídea; recálculo de centroides como media; parada por convergencia o `max_iter`. Sin
  `numpy`/`sklearn`.
- [X] T008 [P] [US4] `dominio/kmeans.py`: helper `estandarizar(puntos) -> (puntos_z, medias, desv)`
  y `describir_centroide(centroide_z) -> str` (alto/medio/bajo por eje → frase, FR-022).
- [X] T009 [US4] **Prueba obligatoria** `tests/unidad/test_kmeans.py`: (a) determinismo — dos
  llamadas con la misma semilla y datos dan la misma partición (FR-019, SC-003); (b) separación —
  tres nubes de puntos deliberadamente separadas caen ≥ 80 % cada una en un grupo (SC-004);
  (c) `k > n` puntos distintos → no se fuerza k (FR-024); (d) `describir_centroide` traduce el
  signo/magnitud de cada eje, no devuelve un texto fijo.

## Fase 2 — User Story 1: Comparativo entre sucursales (P1) 🎯 MVP

- [X] T010 [US1] `backend/rasero/servicios/reportes_comparativo.py`:
  `comparativo(sesion, *, periodo_inicio, periodo_fin) -> dict`. Por sucursal activa o con
  actividad: ventas y tickets de `venta`/`renglon_venta` (001); ticket promedio; margen
  ponderado vía `servicios/margenes` (003); merma valorada vía
  `servicios/mermas.resumen_mermas_por_causa` (006); diferencia de arqueo de `arqueo` (006).
  Diferencia relativa contra la mejor sucursal de cada fila; `atencion=true` sólo si es un peor
  resultado. `comparable=false` y sin `diferencia_relativa` con una sola sucursal (FR-008).
  `sin_datos` (no cero) donde no hay base (FR-009).
- [X] T011 [US1] `servicios/reportes_cache.py`: `leer(tipo, ambito, periodo, granularidad)`,
  `guardar(...)`, `invalidar(...)` sobre `agregado_reporte` (UNIQUE). Usado por todos los GET.
- [X] T012 [US1] `api/reportes.py`: `GET /reportes/comparativo` (params + `actualizar`), conforme
  a `contracts/openapi.yaml`.
- [X] T013 [US1] **Prueba obligatoria de contrato** `tests/contrato/test_contrato_reportes.py`
  (parte comparativo): forma del cuerpo conforme al contrato; 401 sin token; 403 con cajero.
- [X] T014 [US1] Prueba de integración `tests/integracion/test_reportes_comparativo.py`
  (Escenarios 1 y 2 de quickstart): valores == agregado a mano; diferencia relativa contra la
  mejor; `atencion` sólo en el peor; una sola sucursal → `comparable=false`; segunda llamada
  desde caché (mismo `instante_calculo`), `actualizar=true` recalcula.

**Checkpoint US1**: comparativo funcional y demostrable solo.

## Fase 3 — User Story 2: Tendencias (P2)

- [X] T015 [US2] `backend/rasero/servicios/reportes_tendencia.py`:
  `tendencia(sesion, *, indicador, granularidad, id_sucursal=None, id_producto=None, periodos)`.
  Usa `dominio/periodo_local`. Indicadores: ventas, unidades, margen ponderado, merma valorada
  (001/003/006); `demanda_producto` vía el servicio de demanda de 004 — `disponible=false` +
  `razon` si el origen no calcula el indicador para el rango (FR sin ceros falsos). Ámbito
  "todas" = **suma** por período (FR-012). Períodos de borde `completo=false` (FR-011).
- [X] T016 [US2] `api/reportes.py`: `GET /reportes/tendencia` conforme al contrato.
- [X] T017 [US2] Contrato (parte tendencia) en `test_contrato_reportes.py`.
- [X] T018 [US2] Integración `tests/integracion/test_reportes_tendencia.py` (Escenarios 3 y 4):
  venta 23:30 domingo cae en la semana correcta; suma (no promedio) en "todas"; borde parcial
  marcado; indicador no disponible → `puntos=[]` + razón.

## Fase 4 — User Story 3: Tablero de KPIs (P2)

- [X] T019 [US3] `backend/rasero/servicios/reportes_tablero.py`: `tablero(sesion) -> dict`. Una
  tarjeta por módulo, cada una con su `periodo_referencia` propio (FR-014); cifras de los
  servicios de origen (001/002/003/005/006/007); `atencion` según umbrales de
  `config/reportes.py` (FR-017); `sin_datos` + razón donde no hay base (FR-016).
- [X] T020 [US3] `api/reportes.py`: `GET /reportes/tablero` conforme al contrato.
- [X] T021 [US3] Contrato (parte tablero) + integración `tests/integracion/test_reportes_tablero.py`
  (Escenarios 5 y 6): cada cifra == lo que reporta su módulo; períodos por tarjeta; datos
  insuficientes → razón, nunca "0".

## Fase 5 — User Story 4: Segmentos de clientes (P3)

- [ ] T022 [US4] `backend/rasero/servicios/segmentacion_clientes.py`:
  `extraer_features(sesion) -> list[(id_cliente, frecuencia, margen, recencia_dias)]` para
  clientes con ≥ `MIN_VISITAS_CLASIFICABLE` visitas (de `visita` / `intervalo_compra`, 002).
- [ ] T023 [US4] `segmentacion_clientes.recalcular(sesion) -> dict`: estandariza features, corre
  `dominio/kmeans.agrupar` con `SEMILLA_SEGMENTOS`, elige k (3 vs 4), reemplaza
  `segmento_cliente` + `asignacion_segmento` de la corrida anterior, graba `corrida`/`semilla`,
  `sin_clasificar` para los de < N visitas (FR-021). `409` si menos clasificables que el mínimo
  (FR-024). Determinista (FR-019).
- [ ] T024 [US4] `segmentacion_clientes.leer(sesion)` y `etiqueta_de_cliente(sesion, id_cliente)`
  — sólo lectura de la última corrida; `calculado=false` si nunca corrió.
- [ ] T025 [US4] `api/reportes.py`: `GET /reportes/segmentos`, `POST /reportes/segmentos/recalculo`,
  `GET /reportes/segmentos/cliente/{id_cliente}` conforme al contrato.
- [ ] T026 [US4] **Prueba obligatoria** `tests/integracion/test_segmentacion_clientes.py`
  (Escenarios 7, 8, 9): 3 patrones separados caen juntos ≥ 80 %; clientes de 1 visita en
  `sin_clasificar`; dos recálculos → asignación idéntica; base insuficiente → 409;
  `GET .../cliente/{id}` devuelve la etiqueta, `GET /clientes/{id}` de 002 sin campos nuevos.

## Fase 6 — Frontend

- [ ] T027 [P] `frontend/src/servicios/reportes.ts`: cliente de `/reportes/*` con los tipos del
  contrato.
- [ ] T028 `frontend/src/App.tsx`: opción "Reportes" en el grupo apropiado de `GRUPOS` con
  `rol: "encargado"` (el nav ya filtra por rol desde v2.5.0). Guarda de pantalla ya cubre el caso.
- [ ] T029 `frontend/src/pantallas/Reportes.tsx`: contenedor con `EncabezadoPantalla`
  (registro Análisis) + `Segmentado` (Comparativo · Tendencias · Tablero · Segmentos). Marca de
  agua / elemento visual con `despensa-logo-mono-800w.png` (FR-029). Sin Verde Rasero.
- [ ] T030 [P] `frontend/src/pantallas/ReporteComparativo.tsx`: tabla con una columna por
  sucursal; color de atención sólo donde `atencion=true`; nota de "sin otra sucursal" cuando
  `comparable=false`; botón "Actualizar".
- [ ] T031 [P] `frontend/src/pantallas/ReporteTendencias.tsx`: selector de indicador +
  granularidad + sucursal; gráfico de serie (reutiliza el patrón de gráfico de Pronóstico/
  Precios); períodos incompletos marcados; estado "no disponible" con razón.
- [ ] T032 [P] `frontend/src/pantallas/ReporteTablero.tsx`: grilla de tarjetas por módulo, cada
  una con su período de referencia; `atencion` → color; `sin_datos` → razón.
- [ ] T033 [P] `frontend/src/pantallas/ReporteSegmentos.tsx`: lista de grupos con descripción,
  conteo y clientes de ejemplo; botón "Recalcular segmentos" con progreso; `EstadoVacio` (Hueco
  que Enseña) cuando `calculado=false`.
- [ ] T034 [US4] `frontend/src/componentes/EtiquetaSegmento.tsx` + integrar en el detalle de
  cliente de `Clientes.tsx` (002): llama a `GET /reportes/segmentos/cliente/{id}`; muestra la
  etiqueta + fecha del recálculo como dato de lectura. 002 no gana escritura.

## Fase 7 — Verificación y cierre

- [ ] T035 Auditoría de solo lectura (SC-006): `grep` sobre `backend/rasero/servicios/reportes_*`,
  `segmentacion_clientes.py` — cero `INSERT`/`UPDATE`/`DELETE` sobre tablas de 001–007. Sólo
  `SELECT` de ellas; escrituras sólo sobre las tres tablas de 008.
- [ ] T036 Auditoría de literales (FR-004): "Quevedo Centro"/"Buena Fe"/"Despensa Los Ríos" no
  aparecen en código, config ni identificador — sólo como valor de fila.
- [ ] T037 Suite completa `pytest tests` en verde (contrato de reportes, integración de las 4
  vistas, unidad de k-means y período local). Frontend `tsc -b` + `eslint .` + `vite build` en
  verde.
- [ ] T038 Ejecutar los 11 escenarios de `quickstart.md` de extremo a extremo.
- [ ] T039 Registrar la enmienda v2.6.0 en el historial de la constitución (ya hecha) y anotar
  008 en el conteo de entidades por módulo.

## Dependencias entre fases

- Fase 0 (secuencial) → todo lo demás.
- Fase 1 (k-means) es independiente; puede hacerse en paralelo con Fase 2.
- US1 (Fase 2) es el MVP; entregable solo.
- US2, US3 (Fase 3–4) dependen de Fase 0 y de `reportes_cache` (T011); independientes entre sí.
- US4 (Fase 5) depende de Fase 1 (k-means) + Fase 0.
- Frontend (Fase 6): cada pantalla depende de su servicio backend; T034 depende de US4.
