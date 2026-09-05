# Implementation Plan: Pronóstico de Demanda

**Branch**: `004-pronostico-demanda` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-pronostico-demanda/spec.md`

## Summary

Construye, por producto y sucursal, una serie histórica de demanda **corregida** de las cuatro
contaminaciones que el spec identifica —quiebre de stock (la central), precio, promoción y
sustitutos— y, sobre esa serie, un pronóstico de demanda para dos horizontes (corto de 7–14 días
para reposición, medio de 30 días para estacionalidad intramensual simple). Todo cálculo es
aritmética derivable a mano: método base de descensura por **máximo de los N períodos recientes sin
quiebre** (N ≈ 30), ajuste cruzado por sustituto declarado, y **suavizado exponencial simple**
(parámetro α ≈ 0,3) para el pronóstico. Ninguna librería estadística: eso sería una segunda
tecnología para la misma función (Principio I). El pronóstico es consultivo: el sistema propone,
la persona decide cuánto pedir o exhibir (Principio V).

Se construye como extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic
sobre PostgreSQL 16 (puerto 5442) y del mismo frontend React 18 + TS + Vite (sin librerías de
componentes de terceros) que ya usan `001`, `002` y `003`. Cuatro entidades nuevas
(`demanda_observada`, `demanda_corregida`, `pronostico`, `sustitucion_producto`) en el mismo
esquema mediante una migración Alembic nueva.

**Dos ejes que condicionan el plan**:

1. **Bloqueo real de `001`**: `consulta_no_atendida` (001 User Story 3, FR-020/FR-021) está
   especificada pero **no implementada** — tareas T050–T053 de `001/tasks.md` pendientes. Sin ese
   dato no hay **magnitud observada** de demanda no atendida, sólo su detección por existencia
   cero. El plan documenta explícitamente qué historias de `004` se pueden construir ya y cuáles
   esperan a `001` (ver "Estado de implementación por historia" abajo).
2. **Enmienda constitucional v2.2.4**: la entrada de `004` en la tabla de Propiedad de Datos sólo
   listaba tres entidades; `sustitucion_producto` (que FR-032, User Story 6 y FR-009 b exigen como
   tabla propia) se añadió por enmienda **antes** de escribir `data-model.md`, tras verificar que
   la entrada no tenía ninguna otra inconsistencia (research.md #2). Mismo procedimiento que
   v2.2.3 sobre `003`.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001`/`002`/`003`; introducir un segundo lenguaje, framework o **librería de
pronóstico/estadística** (statsmodels, Prophet, scikit-learn) para la misma función está PROHIBIDO
por el Principio I y se descarta explícitamente en research.md #7.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend);
Vite + React sin librería de componentes de terceros (frontend). Todas ya presentes en el
repositorio. Este plan **no añade ninguna dependencia nueva**: el suavizado exponencial, el máximo
de una ventana y los promedios por tramo del mes son operaciones de la biblioteca estándar y de
SQL de agregación.

**Storage**: la misma base PostgreSQL 16 de `001`/`002`/`003`, nativa en desarrollo, puerto
**5442**. Las cuatro entidades de este módulo se agregan al mismo esquema mediante la migración
`0004_pronostico_demanda`; no se crea una base ni un esquema aparte. SQLite sigue PROHIBIDO
(carece de `NUMERIC` real).

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`/`002`/`003`.

**Target Platform**: mismo servidor de un solo nodo (Linux o Windows) y mismo navegador de
escritorio para la pantalla de Análisis.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se
crea un servicio nuevo.

**Performance Goals**: consultar la serie corregida o el pronóstico de un producto responde en
menos de 500 ms p95 sobre la ventana de datos relevante (≤ 90 días diarios por producto/sucursal
— research.md #3). Es una lectura de Análisis, nunca camino crítico de cobro (Principio II).
Reconstruir la serie de una sucursal completa para la pantalla de listado es una consulta de
conjunto, no un bucle por producto (research.md #3, mismo error N+1 que `003` corrigió para
`margen_calculado`).

**Constraints**: ningún pronóstico dispara una orden de compra ni un cambio de exhibición
automático (FR-024, Principio V "consultiva por defecto"); ningún pronóstico se presenta como
vigente si no supera su línea base determinista (FR-022, SC-004); los datos sintéticos de la
User Story 2 nunca se mezclan con datos reales en una consulta de pronóstico de producción
(FR-017); toda cantidad de demanda sigue la regla de precisión decimal exacta — coma flotante
binaria PROHIBIDA, tanto en el esquema como en el código de cálculo.

**Scale/Scope**: mismo orden de magnitud que `001`/`002`/`003` — cientos de productos por
sucursal, dos sucursales en el alcance de examen (cifra de entrega, no del modelo). Serie diaria;
la ventana de trabajo por producto/sucursal es de decenas a ~90 días, no años. `pronostico` es
append-only (una fila por generación, del orden de las decisiones de reposición que un encargado
revisa por semana). `demanda_observada`/`demanda_corregida` se materializan por upsert sobre esa
ventana (research.md #3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.5** (vigente). La enmienda que esta misma
funcionalidad motivó fue la v2.2.4 (ver "Nota sobre la enmienda v2.2.4" abajo); v2.2.5 es una
corrección posterior sobre la entrada de `005-promociones-inteligentes`, sin efecto sobre este
módulo.

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`demanda_observada`, `demanda_corregida`, `pronostico`, `sustitucion_producto`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack de `001`/`002`/`003`; **no** introduce librería de pronóstico ni de estadística — el método (máximo de ventana + suavizado exponencial + promedios por tramo) es aritmética de biblioteca estándar (research.md #7). |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna función de este módulo participa en `POST /ventas` ni en ningún flujo de cobro. `consulta_no_atendida` la escribe el punto de venta de `001` (su User Story 3, en dos toques); `004` sólo la **lee**. Si el pronóstico no está disponible, la reposición sigue con juicio humano y la línea base determinista — degradación, nunca bloqueo. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias" abajo: la matemática de descensura (dirige la compra → inmoviliza capital si sobrecorrige, deja quiebres si subcorrige), el arnés de validación sintética (SC-002) y la comparación contra línea base (SC-004) tienen suite obligatoria. Interfaz y maquetación de `Pronostico.tsx` quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `pronostico` es append-only: cada generación guarda sus factores (nivel del suavizado, α, multiplicadores por tramo), el período de datos y el valor de la línea base (FR-021). `demanda_corregida` guarda, por período, el valor observado de partida y qué correcciones se aplicaron con qué respaldo (FR-010). Toda serie y pronóstico se identifica por `id_sucursal`; agregar varias sucursales sin discriminar está PROHIBIDO (FR-037). |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: cada pronóstico y cada corrección llevan sus factores y su período de datos grabados junto a ellos (FR-010, FR-021). **Consultiva por defecto**: FR-024 — ningún pronóstico dispara compra ni exhibición; no hay ninguna acción que revertir porque el módulo nunca actúa. **Con línea base**: FR-022 — promedio móvil de la demanda observada sin corregir; un pronóstico que no la supera no se presenta como vigente (SC-004). **Acotada**: límites documentados en el spec y en research.md #6 — sin estacionalidad anual/festiva, estado "datos insuficientes" (FR-023), estado "no estimable por censura total" (FR-012), separación sintético/real (FR-017). **Visible**: registro de Análisis, con distinción visual entre demanda **observada** (dato) y demanda **corregida/pronóstico** (estimado, color `#1F5673` + forma + texto) — ver "Sistema de diseño" abajo. |

**Nota sobre la enmienda v2.2.4**: al preparar `data-model.md` de esta funcionalidad se contrastó
la entrada completa de `004` en la tabla de "Propiedad de Datos y Nomenclatura"
(`demanda_observada`, `demanda_corregida`, `pronostico`) contra las fronteras de la propia sección.
A diferencia de `003` (donde v2.2.3 encontró que `costo_producto` contradecía una frontera y que
faltaba `sugerencia_precio`), la entrada de `004` **no tenía ninguna contradicción**: las tres son
artefactos analíticos derivados, coherentes con la misma lógica que asigna `margen_calculado` a
`003`. La **única** omisión era `sustitucion_producto`, que FR-032, User Story 6 y —tras
`/speckit-clarify`— FR-009 (b) exigen como tabla propia (mismo patrón que `rol_producto` de `003`:
una declaración de negocio sobre un producto que no es atributo de `producto` de `001`). Se
corrigió por enmienda **v2.2.4** antes de escribir este plan, que además saneó un desliz de
sincronización de v2.2.3 (el pie de `constitution.md` había quedado en 2.2.2). Ver research.md #2 y
el informe de impacto de sincronización al inicio de `constitution.md`.

**Lecturas Críticas del Enunciado aplicadas** (decisiones de análisis ya tomadas, no reabiertas
aquí):

- **Identidad del proyecto** ("demanda corregida por censura" como uno de los tres criterios
  objetivos de Rasero): gobierna que la salida central del módulo sea la serie corregida, no la
  observada, y que la corrección sea explicable en esos términos.
- **Lectura n.º 5** ("el umbral de inactividad no puede ser global"): aunque es una regla de
  `002`, su espíritu —derivar el parámetro del historial propio de cada producto, no de un número
  fijo para todos— se aplica aquí a la ventana N y a la "demanda típica" de cada producto
  (research.md #5).
- **Principio V completo**: este es **el** módulo predictivo del sistema; la tabla de Principios
  arriba traza cada una de sus cinco exigencias (explicable, consultiva, con línea base, acotada,
  visible) a un requisito o a una decisión de research.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`/`002`/`003`. Nueva migración Alembic sobre el mismo esquema. |
| Precisión exacta en dinero y en peso en gramos | Cantidades de demanda observada en `NUMERIC(14,0)` (misma escala que `movimiento_inventario.cantidad` de `001`: unidades o gramos); demanda corregida, pronóstico, multiplicadores y α en `NUMERIC` de escala fija (`data-model.md`). Ningún `float` en el esquema ni en el código de cálculo. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `demanda_observada`, `demanda_corregida`, `pronostico`, `sustitucion_producto`. Claves foráneas `id_producto`, `id_sucursal`; la segunda referencia a `producto` en `sustitucion_producto` es `id_producto_sustituto` (research.md #9). |
| Tiempo en UTC, agregaciones por día local de la sucursal | Cada período de la serie es un **día local** de la sucursal: `(instante AT TIME ZONE sucursal.zona_horaria)::date`, nunca `::date` sobre el instante crudo (`data-model.md`, mismo criterio que el cierre por día local de `001`). |
| Propiedad de datos: exactamente las 4 entidades de 004 (tras v2.2.4) | `data-model.md` define únicamente `demanda_observada`, `demanda_corregida`, `pronostico`, `sustitucion_producto`. `venta`, `renglon_venta`, `movimiento_inventario`, `existencia`, `lote`, `consulta_no_atendida`, `producto`, `producto_precio_sucursal`, `observacion_precio`, `canal_competencia`, `sucursal` (todas de `001`) se consultan, nunca se redefinen. La marca de "promoción activa" se consumirá de `005` cuando exista. |
| Sistema de diseño: registro de Análisis | Ver "Sistema de diseño en el frontend": única pantalla nueva, sin uso del registro de Operación (este módulo no participa de la caja). Distinción obligatoria observado/estimado con tres portadores. |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0004_pronostico_demanda`) con `downgrade` que elimina las cuatro tablas. |
| Inteligencia explicable y reversible (Principio V) | Ver tabla de Principios arriba. Línea base determinista obligatoria (FR-022); nada que "deshacer" porque el módulo nunca actúa sobre inventario ni precio. |

**Resultado de la puerta**: PASA. Sin desviaciones que requieran Complexity Tracking (ver esa
sección abajo).

**Re-verificación tras la Fase 1 (data-model.md, contracts/, quickstart.md)**: sin cambios en el
veredicto. El diseño confirma que (a) las cuatro tablas son las de la tabla de propiedad tras
v2.2.4 y ninguna columna de `001` se duplica; (b) no hay `float` en el esquema —cantidades en
`NUMERIC(14,0)`, valores derivados en `NUMERIC(14,4)`, parámetros en `NUMERIC(4,3)`—; (c) el
contrato no expone ningún endpoint de "aplicar" (Principio V, consultiva); (d) `pronostico` es
append-only y toda serie lleva `id_sucursal` (Principio IV); (e) el arnés sintético usa las mismas
tablas con un discriminador, de modo que ejercita el mismo código de descensura que producción
(FR-017).

## Estado de implementación por historia (dependencia de `001` documentada, no oculta)

El spec exige (sección "Dependencias entre módulos") que este plan diga qué se puede construir ya
y qué espera a `001`. `consulta_no_atendida` (001 User Story 3) **no está implementada**: tareas
T050–T053 de `001/tasks.md` pendientes. Además, `001` User Story 2 (entradas de inventario,
T044–T049) y User Story 4 (captura de competencia, T054–T061) tampoco están implementadas.

| Historia de `004` | ¿Construible ahora? | Depende de `001` |
|---|---|---|
| **US1 – Descensura por quiebre**, nivel (a) método base | **Sí** | Sólo `movimiento_inventario`/`existencia`, ya presentes (los generan las ventas de `001` US1). Detecta intervalos de existencia cero y estima con el máximo de los N períodos recientes sin quiebre. |
| **US1 – Descensura por quiebre**, uso de evidencia real de `consulta_no_atendida` (FR-007) | **No — bloqueada** | `001` User Story 3 (T050–T053). Hasta entonces, todo intervalo se descensura por método base (FR-008) y se marca como estimación de menor confianza. |
| **US2 – Validación con datos sintéticos** | **Sí** | Nada. Es precisamente la ruta que no depende de datos reales de `001`. Genera series con demanda latente **conocida** y mide el error de la descensura contra ella. |
| **US3 – Pronóstico desde la serie corregida** | **Sí** (sobre serie sintética o sobre serie real corregida por método base) | El pronóstico de **producción sobre datos reales de alta fidelidad** hereda el bloqueo de FR-007; el pronóstico sobre serie corregida por método base no. |
| **US4 – Corrección por precio** | **Sí** | El precio vigente por período se reconstruye de `renglon_venta.precio_aplicado` de `001` (copiado por venta, ya disponible — research.md #8). NO depende de `producto_precio_sucursal` histórico (que `001` no conserva). Las observaciones de competencia (`001` US4, no implementada) son un insumo de contexto opcional, no un bloqueo. |
| **US5 – Neutralizar promociones** | **Parcial** | El gancho de integración se implementa ahora; la fuente de la marca "promoción activa" llega con `005`. Hasta entonces todos los períodos se tratan como sin promoción (FR-030). |
| **US6 – Declarar sustitutos y señalar** | **Sí** | Sólo `sustitucion_producto` (propia) y la demanda observada. No depende de `001` US3. |

**Conclusión para `/speckit-tasks`**: el plan de tareas puede ordenar US1(a) → US2 → US3 → US4 →
US6 sin bloqueo, dejar US5 en su forma parcial, y marcar la sub-tarea de FR-007 (evidencia real de
`consulta_no_atendida`) como **bloqueada por `001` T050–T053**, con su prueba de contrato lista
para activarse cuando `001` la implemente.

## Project Structure

### Documentation (this feature)

```text
specs/004-pronostico-demanda/
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

Misma estructura de primer nivel que `001`/`002`/`003`, fijada y no negociable. Este módulo
**extiende** `backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel.
(La ruta real de migraciones es `backend/migraciones/versions/`, verificada en el repositorio —
`0001_esquema_inicial`, `0002_clientes_fidelizacion`, `0003_precios_margenes` ya existen ahí.)

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── dominio/
│   │   │   ├── censura.py                  # NUEVO — detección de intervalo de quiebre, método base (máx de N), ajuste cruzado por sustituto (research.md #5, #6)
│   │   │   ├── pronostico.py               # NUEVO — suavizado exponencial simple, multiplicadores por tramo del mes, línea base determinista (research.md #7, #8b)
│   │   │   └── serie_demanda.py            # NUEVO — agregación diaria por día local, anotación de quiebre/precio/promo por período (research.md #3, #8)
│   │   ├── persistencia/
│   │   │   └── modelos.py                  # AMPLIADO — DemandaObservada, DemandaCorregida, Pronostico, SustitucionProducto
│   │   ├── servicios/
│   │   │   ├── demanda.py                  # NUEVO — reconstruir_serie (recompute-on-read + upsert de ventana acotada), aplica correcciones en orden fijo (research.md #3, #4)
│   │   │   ├── pronostico.py               # NUEVO — generar_pronostico, comparar_contra_linea_base (research.md #7, #8b)
│   │   │   ├── sustitucion.py              # NUEVO — declarar/consultar relación de sustitución
│   │   │   └── demanda_sintetica.py        # NUEVO — cargar serie sintética, reporte de error de descensura (FR-013 a FR-017)
│   │   └── api/
│   │       └── pronostico.py               # NUEVO — routers de serie, pronóstico, sustituciones, validación sintética
│   └── migraciones/versions/
│       └── 0004_pronostico_demanda.py      # NUEVO — 4 tablas, con downgrade
├── frontend/src/
│   ├── pantallas/
│   │   └── Pronostico.tsx                  # NUEVO — registro de Análisis: serie observada vs corregida, pronóstico de dos horizontes, línea base, factores
│   ├── componentes/
│   │   ├── SerieDemanda.tsx                # NUEVO — gráfico observado/estimado con los tres portadores de incertidumbre
│   │   ├── DeclararSustituto.tsx           # NUEVO — formulario de relación de sustitución
│   │   └── ValidacionDescensura.tsx        # NUEVO — vista de error de descensura sobre serie sintética (herramienta de analista)
│   ├── servicios/
│   │   └── pronostico.ts                   # NUEVO — cliente HTTP de los endpoints de este módulo
│   └── App.tsx                             # AMPLIADO — nueva pestaña "Pronóstico"
└── tests/
    ├── unidad/
    │   ├── test_censura.py                 # NUEVO — método base, ajuste cruzado, invariante corregida ≥ observada, censura total
    │   └── test_pronostico.py              # NUEVO — suavizado exponencial, multiplicadores por tramo, línea base
    ├── integracion/
    │   ├── test_descensura_sintetica.py    # NUEVO — SC-002: error de descensura < error de no corregir
    │   ├── test_pronostico_linea_base.py   # NUEVO — SC-004: un pronóstico que no supera la línea base no se presenta vigente
    │   └── test_serie_precio_promo.py      # NUEVO — reconstrucción de precio por período, exclusión de promo
    └── contrato/
        └── test_contrato_pronostico.py     # NUEVO — respuestas de contracts/openapi.yaml en forma feliz y modos de fallo
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001`/`002`/`003` cambia de propiedad ni de esquema. Este módulo **sólo lee** de `001` (ventas,
movimientos, existencia, consultas no atendidas, precio copiado en el renglón) — no escribe en
ninguna tabla ajena, a diferencia de `003`, que sí escribía en `producto_precio_sucursal` al
aplicar una sugerencia. Por eso `004` no necesita ninguna función-puente de servicio de `001` del
tipo `fijar_precio_sucursal` (research.md #7 de `003`): leer una tabla ajena ya es una operación
de bajo riesgo y sin ese problema, como `002` y `003` validaron.

## Pruebas obligatorias

Derivadas del Principio III. El riesgo central: una descensura que **sobrecorrige** hace pedir de
más e inmoviliza capital; una que **subcorrige** deja el sesgo de agotamiento que el módulo existe
para eliminar. El pronóstico alimenta decisiones de compra reales.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Método base de descensura | `tests/unidad/test_censura.py` | Período de quiebre → valor corregido = máximo de la demanda observada del producto entre los N días recientes sin quiebre; invariante `corregida ≥ observada` en todo período de quiebre (FR-006); período sin quiebre → sin corrección por este eje (FR-011); sin ningún período sin quiebre y sin consultas → "no estimable por censura total" (FR-012), nunca cero. |
| 2 | Ajuste cruzado por sustituto (FR-009 b) | `tests/unidad/test_censura.py` | Producto en quiebre con sustituto declarado que vendió por encima de su propio máximo de N → el estimado base sube por el exceso del sustituto, sin reemplazarlo; sustituto también en quiebre en el mismo período → no hay ajuste (FR-036); sin relación declarada → sólo método base. |
| 3 | Validación con serie sintética (SC-002) | `tests/integracion/test_descensura_sintetica.py` | Sobre una serie sintética con demanda latente verdadera conocida, el error medio de `demanda_corregida` frente al valor verdadero es **menor** que el de usar `demanda_observada` sin corregir, en el escenario con `consulta_no_atendida` sintética y en el que no la tiene (FR-014, FR-015, FR-016); datos sintéticos nunca aparecen en una consulta de pronóstico de producción (FR-017). |
| 4 | Pronóstico contra línea base (SC-004) | `tests/integracion/test_pronostico_linea_base.py` | Un `pronostico` generado incluye siempre sus factores, su período de datos y el valor de la línea base (FR-021); un pronóstico que no supera su línea base determinista no se marca como vigente (FR-022); producto sin histórico suficiente → "datos insuficientes" (FR-023), nunca un número. |
| 5 | Serie: precio por período y exclusión de promoción | `tests/integracion/test_serie_precio_promo.py` | El precio vigente de un período se reconstruye de `renglon_venta.precio_aplicado` (research.md #8); un período sin ventas y sin precio reconstruible → "sin corrección de precio" (FR-027); un período marcado de promoción se excluye de la serie corregida pero permanece intacto en la observada (FR-031); toda la serie filtra por `id_sucursal` (FR-037). |
| 6 | Contrato público | `tests/contrato/test_contrato_pronostico.py` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `Pronostico.tsx`,
`SerieDemanda.tsx`, `DeclararSustituto.tsx`, `ValidacionDescensura.tsx`.

## Sistema de diseño en el frontend

Este módulo vive **enteramente en el registro de Análisis** — la propia constitución clasifica
"pronóstico" ahí explícitamente, junto a márgenes, clientes y promociones. No hay ninguna
superficie en el registro de Operación: ninguna función de este módulo se consulta desde
`Venta.tsx` ni participa del cobro (la escritura de `consulta_no_atendida` en la pantalla de venta
pertenece a `001`, su User Story 3, no a este módulo).

- **`Pronostico.tsx`** (pantalla nueva, registro de Análisis): una decisión por bloque, radio 6px,
  Source Serif 4, líneas de texto por debajo de 80 caracteres. Por producto y sucursal: la serie
  **observada** frente a la **corregida**, el pronóstico de los dos horizontes (corto y medio), la
  línea base determinista superpuesta, y los factores del pronóstico (nivel del suavizado, α,
  multiplicadores por tramo del mes) visibles (FR-021, Principio V "Explicable").
- **Distinción observado / estimado (Principio V "Visible" + Sistema de Diseño)**: la demanda
  observada se dibuja con la tinta normal; la demanda **corregida** y el **pronóstico** usan el
  color `estimado` `#1F5673` **más** un indicador de forma (línea punteada / punto hueco) **más**
  texto explícito ("estimado", "pronóstico", "corregido por quiebre") — tres portadores
  simultáneos, nunca sólo color. Un período descensurado muestra en texto de cuánto y con qué
  respaldo ("+8 u estimadas · método base" / "+8 u · respaldado por 5 consultas no atendidas").
- **Momento de animación deliberado**: al revelar el detalle de por qué un período fue corregido
  (equivalente al "revelar el detalle de un cliente en riesgo de fuga" que la constitución cita
  como ejemplo permitido). Un único momento orquestado por pantalla — no hover por punto ni
  fade-in por bloque.
- **Redundancia de portadores**: "datos insuficientes", "no estimable por censura total", "sin
  corrección de precio" y "sin referencia de competencia" se comunican siempre con texto
  explícito, nunca sólo con la ausencia de un número o con color.
- **`ValidacionDescensura.tsx`**: vista de analista que muestra, sobre la serie sintética, la
  demanda verdadera contra la corregida y el error de descensura — claramente rotulada como
  **datos sintéticos**, sin posibilidad de confundirla con una vista de producción (FR-017).

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado durante `001`); este módulo no
repite el paso `init`. Se invoca únicamente `new-work` de Impeccable para `Pronostico.tsx` (mundo
visual ya fijado: registro de Análisis, tokens de `frontend/src/estilos/tokens.css` reutilizados
sin cambio). El agente documenter actualiza `DESIGN.md` al finalizar.

## Complexity Tracking

*Sin desviaciones que requieran justificación.* Este módulo no introduce ninguna segunda
tecnología (en particular, **ninguna librería de pronóstico o estadística** — el método completo
es aritmética derivable a mano, decisión de research.md #7 anclada en el Principio V "Explicable"),
no viola ninguna frontera de propiedad de datos (una vez añadida `sustitucion_producto` por la
enmienda v2.2.4) y no requiere ningún mecanismo (disparador de base de datos, cola, servicio
externo, tarea de fondo) más allá del recompute-on-read sobre ventana acotada que `003` ya
estableció como patrón aceptado para `margen_calculado` (research.md #3, #4).
