# Implementation Plan: Promociones Inteligentes

**Branch**: `005-promociones-inteligentes` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-promociones-inteligentes/spec.md`

## Summary

Genera y mide promociones dirigidas a clientes con **tres mecanismos distintos** (Lectura Crítica
n.º 6 de la constitución), cada uno con su propia entidad y sus propias exigencias:

1. **Cupón por fecha fija (cumpleaños)** — regla directa: la fecha del cliente entra en la ventana
   → se genera un `cupon`. Sin grupo de control, sin medición. Consume la consulta de cumpleañeros
   que `002` ya expone (`GET /clientes/cumpleanos`, FR-012 de `002`), nunca `cliente.fecha_nacimiento`
   directamente.
2. **Empuje por patrón de recompra con reserva de precio** — a un cliente cuyo tiempo desde la
   última compra se acerca a su `intervalo_compra.intervalo_esperado_dias` (de `002`), se le ofrece
   un producto que suele recomprar con una **reserva de precio**: un código que garantiza el precio
   ofertado dentro de una ventana. **No aparta stock**; `005` **no lee ni escribe** `existencia` /
   `movimiento_inventario` de `001` — la disponibilidad al vender la resuelve `001` (FR-010, FR-011,
   decidido en `## Clarifications` del spec).
3. **Reactivación de cliente inactivo con grupo de control** — el único mecanismo con diseño
   experimental. Toma los clientes con `senal_fuga` **activa** de `002` (reutiliza la detección de
   fuga silenciosa, no crea un criterio nuevo), los reparte por **aleatorización real con semilla
   fija** (`random.Random`, Mersenne Twister de la biblioteca estándar) en tratamiento / control,
   ofrece el descuento sólo al tratamiento, y al cerrar la ventana de medición calcula el % de
   retorno de cada grupo y su **incrementalidad**. La campaña se considera efectiva si y sólo si esa
   diferencia es **estadísticamente significativa por una prueba z de dos proporciones (p < 0,05)** —
   un umbral estadístico, no un número fijo (FR-021). Toda la estadística es aritmética de `math` de
   la biblioteca estándar: **ninguna librería estadística** (`scipy`, `statsmodels`), misma
   disciplina que `004` con el suavizado exponencial.

Un `redencion_promocion` transversal registra que cualquiera de los tres se usó en una `venta` de
`001` — **referencia de sólo lectura** a la venta, sin duplicar sus datos (mismo patrón que
`visita.id_venta` de `002`). El endpoint `POST /promociones/redenciones` y el servicio base
`registrar_redencion` (con `cupon.estado → 'redimido'`) se construyen **con el mecanismo 1 (US1)**,
como parte de cerrar el ciclo completo del cupón; US2 añade **una línea** de efecto
(`oferta_recompra.desenlace → 'comprado'`), y US3 no toca ese servicio (la validación del grupo de
tratamiento ya está en la base). De esas redenciones se deriva la **marca agregada de "promoción
activa"** por producto, sucursal y período que `004` consume — la única aportación propia de **US4**,
que **cierra el contrato** que `004` dejó abierto (FR-029 a FR-031, FR-039 de `004`).

Se construye como extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic
sobre PostgreSQL 16 (puerto 5442) y del mismo frontend React 18 + TS + Vite (sin librerías de
componentes de terceros) que ya usan `001`–`004`. Seis entidades nuevas (`campania`, `cupon`,
`oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`) en
el mismo esquema mediante una migración Alembic nueva (`0005_promociones_inteligentes`).

**Dos ejes que condicionan el plan**:

1. **Enmienda constitucional v2.2.5 — ya aplicada**: la entrada de `005` en la tabla de Propiedad de
   Datos listaba tres entidades genéricas (`campania`, `envio_promocional`, `grupo_control`);
   `envio_promocional` contradecía la Lectura Crítica n.º 6 (una entidad única de "envío" es
   exactamente el mecanismo genérico que la constitución prohíbe) y `grupo_control` era demasiado
   gruesa para la medición de incrementalidad. La enmienda **v2.2.5** (2026-09-05, commit `a2bb668`)
   las reconcilió con las **seis** que el spec exige, **antes** de escribir este plan — mismo
   procedimiento que v2.2.3 sobre `003` y v2.2.4 sobre `004` (research.md #2).
2. **Sin bloqueo de dependencias** (corrige la nota cautelar del checklist del spec): al escribir el
   spec se anotó que el mecanismo 3 "depende de datos reales de `senal_fuga`, User Story 3 de `002`,
   aún no implementada en el último checkpoint". **Verificado contra el repositorio: `002` está
   completo** (checkpoint `2fd6381`; `senal_fuga`, `intervalo_compra`, `evaluar_fugas_pendientes`,
   `GET /clientes/cumpleanos`, `registrar_visita` todos entregados). Todas las lecturas que `005`
   necesita —`venta`, `renglon_venta`, `producto`, `producto_precio_sucursal`, `sucursal`, `turno`
   de `001` (su User Story 1, entregada); `cliente`, `visita`, `intervalo_compra`, `senal_fuga` de
   `002` (completo)— están disponibles. **Ninguna historia de `005` está bloqueada** (ver "Estado de
   implementación por historia").

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001`–`004`. Introducir un segundo lenguaje, framework o **librería estadística**
(`scipy`, `statsmodels`, `numpy` para esto) para la misma función está PROHIBIDO por el Principio I
y se descarta explícitamente en research.md #10.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend);
Vite + React sin librería de componentes de terceros (frontend). Todas ya presentes. Este plan
**no añade ninguna dependencia nueva**: la aleatorización usa `random.Random` (Mersenne Twister,
biblioteca estándar); la prueba z de dos proporciones y el cálculo de tamaño mínimo de muestra
usan `math.erf` / `math.sqrt` y constantes (`z_{α/2} = 1,959964`, `z_β = 0,841621`) — aritmética
de una pantalla, derivable a mano (research.md #9, #10).

**Storage**: la misma base PostgreSQL 16 de `001`–`004`, nativa en desarrollo, puerto **5442**.
Las seis entidades se agregan al mismo esquema mediante la migración
`0005_promociones_inteligentes`; no se crea una base ni un esquema aparte. SQLite sigue PROHIBIDO.

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`–`004`.

**Target Platform**: mismo servidor de un solo nodo y mismo navegador de escritorio.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se
crea un servicio nuevo.

**Performance Goals**: generar los cupones de un rango de fechas, detectar las ofertas de recompra
de una sucursal, o crear / cerrar un experimento responde en menos de 1 s sobre la población
relevante (cientos de clientes por sucursal). La consulta de `marca-activa` que `004` consume
responde en menos de 500 ms p95 sobre una ventana de ≤ 90 días — es una consulta de conjunto sobre
`redencion_promocion`, nunca un bucle por producto.

**Constraints**: ninguna función de este módulo participa en `POST /ventas` ni es camino crítico de
un cobro (Principio II); `005` **nunca** ajusta un precio ni un inventario de forma automática
(FR-036, Principio V "consultiva por defecto"); la reserva del empuje por recompra es **de precio,
no de inventario** (FR-010); toda campaña, cupón, oferta y experimento se identifica por sucursal
cuando aplica (FR-035, Principio IV); ninguna afirmación de eficacia de reactivación sin grupo de
control (FR-023, Lectura Crítica n.º 6); toda cantidad monetaria en tipos decimales exactos — coma
flotante binaria PROHIBIDA en el esquema y en el código.

**Scale/Scope**: mismo orden de magnitud que `001`–`004` — cientos de clientes y de productos por
sucursal, dos sucursales en el alcance de examen (cifra de entrega, no del modelo). `cupon`,
`oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento` y `redencion_promocion` son
**append + máquina de estados** (nunca se recomputan al leer, a diferencia de `margen_calculado` de
`003` o `demanda_corregida` de `004`); `campania` es su paraguas. La `marca-activa` es la única
**consulta derivada** (no tabla) del módulo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.5** (vigente) — versión que esta misma
funcionalidad motivó (enmienda v2.2.5, ver "Nota sobre la enmienda v2.2.5" abajo).

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack de `001`–`004`; **no** introduce librería estadística — la prueba z de dos proporciones y el tamaño mínimo de muestra son `math.erf` + constantes (research.md #9, #10). |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna función participa en `POST /ventas` ni en ningún flujo de cobro. La redención de una promoción se registra **después** de que la venta se completó, por una llamada aparte e idempotente — mismo patrón que `registrar_visita` de `002`, que "nunca forma parte de la transacción de venta". Si `005` no responde, la caja cobra igual; el descuento lo aplica el operador con su criterio (FR-036). |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias": la aleatorización reproducible (SC-005, SC-006), la prueba z + veredicto de efectividad (SC-007, SC-008), la idempotencia de generación y de redención, y la corrección de la marca `marca-activa` que `004` consume (SC-009) tienen suite obligatoria. Interfaz y maquetación de `Promociones.tsx` quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento` y `redencion_promocion` son append + estado, nunca se borran. Cada experimento guarda su **semilla**, su ventana, su tamaño mínimo de muestra, las tasas por grupo, el estadístico z y el valor p (FR-022, FR-024). Toda campaña y experimento lleva `id_sucursal` cuando aplica; la consulta de marca activa se identifica siempre por sucursal (FR-035). |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: cada resultado de incrementalidad se reconstruye del registro (qué clientes en cada grupo, qué proporción retornó, la prueba z y su p) (FR-024, SC-007). **Consultiva por defecto**: FR-036 — `005` genera cupones, ofertas y asignaciones, y mide; **nunca** aplica un descuento ni aparta inventario. El operador aplica el descuento en caja; el encargado envía la comunicación de tratamiento con la lista que `005` exporta (mismo patrón que "el encargado ejecuta físicamente la reubicación" de `003`). **Con línea base**: el grupo de control **es** la línea base del mecanismo 3 (Lectura Crítica n.º 6); sin él no hay afirmación de eficacia (FR-023). **Acotada**: límites documentados en el spec y en research.md #7, #8, #10, #11 — `senal_fuga` activa como criterio, "muestra insuficiente" por poder estadístico, sesgo de identificación de retorno declarado. **Visible**: registro de Análisis, con la incrementalidad y su prueba de significancia mostradas con los tres portadores (research.md #12, "Sistema de diseño"). |

**Nota sobre la enmienda v2.2.5**: al preparar este plan se contrastó la entrada **completa** de
`005-promociones-inteligentes` en la tabla de "Propiedad de Datos y Nomenclatura"
(`campania`, `envio_promocional`, `grupo_control`) contra la Lectura Crítica n.º 6 y las fronteras
de la propia sección (research.md #2). A diferencia de `004` —donde v2.2.4 sólo añadió una entidad
omitida— y como `003` en v2.2.3 —que además retiró una mal asignada—, aquí se **retiraron dos**
entidades genéricas y se **añadieron cinco** específicas: `envio_promocional`, entidad única de
"envío de promoción", es literalmente el "mecanismo único" que la Lectura Crítica n.º 6 PROHÍBE;
`grupo_control` a secas no captura la semilla, la ventana ni el desenlace por cliente que el
mecanismo 3 exige. Se corrigió por enmienda **v2.2.5** (commit `a2bb668`) antes de este plan, que
además sincronizó las citas de "versión vigente" en los artefactos de `001`–`004` (las citas
históricas no se barren, por la excepción de la Puerta de sincronización de enmiendas). Ver
research.md #2 y el informe de impacto al inicio de `constitution.md`.

**Lecturas Críticas del Enunciado aplicadas** (decisiones de análisis ya tomadas, no reabiertas
aquí):

- **Lectura n.º 6** ("las promociones son tres mecanismos, no uno"): es **el** principio rector de
  este módulo. El esquema tiene una entidad por mecanismo (`cupon`, `oferta_recompra`,
  `experimento_reactivacion` + `asignacion_experimento`); no existe ninguna tabla "promoción"
  genérica. El grupo de control es OBLIGATORIO y estructural para el mecanismo 3 (`asignacion_experimento`
  con `grupo` no admite un tercer valor "sin grupo"); su ausencia hace imposible —no sólo
  desaconsejable— afirmar eficacia (FR-023).
- **Lectura n.º 5** ("el umbral de inactividad no puede ser global"): `005` **no define** ningún
  umbral de inactividad; reutiliza `senal_fuga` de `002`, que ya deriva el intervalo del historial
  propio de cada cliente (research.md #7). El "umbral" que `005` sí fija —el de incrementalidad— es
  estadístico (prueba z), no un número fijo arbitrario (FR-021, misma filosofía).
- **Identidad del proyecto** ("aplicar un mismo criterio objetivo, explícito y siempre el mismo"):
  la decisión de gastar margen en un descuento de reactivación se toma contra un criterio único y
  explícito —la incrementalidad medida supera la significancia estadística— y toda salida del
  módulo se explica en esos términos.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`–`004`. Nueva migración Alembic sobre el mismo esquema. |
| Precisión exacta en dinero y en peso en gramos | Porcentajes de descuento en `NUMERIC(5,2)`; precios garantizados y descuentos aplicados en `NUMERIC(12,4)` (misma escala que `renglon_venta.precio_aplicado` de `001`); proporciones de retorno e incrementalidad en `NUMERIC(6,4)`; estadístico z y valor p en `NUMERIC(8,5)` / `NUMERIC(7,6)`. Ningún `float` en el esquema; el cálculo de la prueba z usa `Decimal` salvo la evaluación final de `math.erf`, cuyo resultado se cuantiza a `NUMERIC` (research.md #9). |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`. Claves foráneas `id_cliente`, `id_producto`, `id_sucursal`, `id_venta`, `id_campania`, `id_experimento_reactivacion`, `id_senal_fuga`. |
| Tiempo en UTC, agregaciones por día local de la sucursal | `redencion_promocion.periodo` es el **día local** de la sucursal de la venta: `(venta.instante AT TIME ZONE sucursal.zona_horaria)::date`, resuelto vía `venta → turno → sucursal` (research.md #4). La ventana de validez de un cupón y de una reserva son fechas locales. |
| Propiedad de datos: exactamente las 6 entidades de 005 (tras v2.2.5) | `data-model.md` define únicamente `campania`, `cupon`, `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`. `cliente`, `visita`, `intervalo_compra`, `senal_fuga` (de `002`) y `venta`, `renglon_venta`, `producto`, `sucursal`, `producto_precio_sucursal`, `turno` (de `001`) se **consultan, nunca se redefinen ni se escriben**. `005` **no lee** `existencia` ni `movimiento_inventario` de `001` (la disponibilidad al vender la resuelve `001`, FR-011); los tests de frontera los consultan sólo para verificar que no hubo escritura. |
| Sistema de diseño: registro de Análisis | Ver "Sistema de diseño en el frontend". `Promociones.tsx` es de Análisis (decisión gerencial). El único toque de Operación es un componente pequeño en `Venta.tsx` para que el cajero marque un cupón como aplicado — no bloqueante, radio 2px, sin animación salvo confirmación de acción (mismo patrón que `IdentificarCliente.tsx` de `002`). |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0005_promociones_inteligentes`) con `downgrade` que elimina las seis tablas. |
| Inteligencia explicable y reversible (Principio V) | Ver tabla de Principios. El grupo de control es la línea base obligatoria del mecanismo 3; nada que "deshacer" porque el módulo nunca actúa sobre inventario ni precio — un cupón sin redimir simplemente vence. |

**Resultado de la puerta**: PASA. Sin desviaciones que requieran Complexity Tracking.

**Re-verificación tras la Fase 1 (data-model.md, contracts/, quickstart.md)**: sin cambios en el
veredicto. El diseño confirma que (a) las seis tablas son las de la tabla de propiedad tras v2.2.5
y ninguna columna de `001` / `002` se duplica —`redencion_promocion` referencia `venta` por FK de
sólo lectura y denormaliza sólo `id_sucursal` y `periodo`, ambos derivados de la venta y
justificados para la consulta de marca activa (research.md #4)—; (b) no hay `float` en el esquema;
(c) el contrato no expone ningún endpoint que ajuste un precio o un inventario (Principio V,
consultiva); (d) `asignacion_experimento.grupo` es un `ENUM` de dos valores sin tercer estado "sin
grupo" (Lectura Crítica n.º 6); (e) toda ruta de resultados lleva `id_sucursal` o lo deriva, y
`GET /promociones/marca-activa` lo exige como parámetro (Principio IV, FR-035).

## Estado de implementación por historia (dependencias verificadas contra el repositorio)

El spec (sección "Dependencias entre módulos") exige que este plan diga qué se puede construir ya.
**Verificación**: `git log` y los `tasks.md` de `001` y `002` en el árbol de trabajo.

| Dependencia | Estado real | Fuente |
|---|---|---|
| `002` — `cliente`, `visita`, `intervalo_compra`, `senal_fuga`, `evaluar_fugas_pendientes`, `GET /clientes/cumpleanos`, `registrar_visita` | **Entregado** (checkpoint `2fd6381`, "002-clientes-fidelizacion completo"; tareas T001–T038 de `002/tasks.md` en `[X]`) | `specs/002-clientes-fidelizacion/tasks.md`, `backend/rasero/servicios/clientes.py`, migración `0002` |
| `001` — `venta`, `renglon_venta`, `existencia`, `movimiento_inventario`, `producto`, `sucursal`, `turno`, `producto_precio_sucursal`, resolución de precio por sucursal | **Entregado** (checkpoint `873228d`, "001 Setup+Foundational+User Story 1"; `producto_precio_sucursal` en migración `0001`) | `specs/001-core-ventas-inventario/tasks.md` T001–T043, migración `0001` |
| `001` — `consulta_no_atendida` (User Story 3), entradas de inventario (US2), competencia (US4) | **No entregado** (T044–T064 en `[ ]`) | — pero **`005` no los necesita** |
| `004` — contrato de "promoción activa" | `004` **completo** (checkpoint `41ad08c`) y ya **espera** consumir `marca-activa` de `005` (FR-030 de `004`: hasta que `005` exista, trata todo período como sin promoción) | `specs/004-pronostico-demanda/spec.md` FR-029–031, FR-039 |

| Historia de `005` | ¿Construible ahora? | Nota |
|---|---|---|
| **US1 — Cupón por fecha fija + ciclo de redención** | **Sí** | `GET /clientes/cumpleanos` de `002` (entregado) y las tablas propias. Construye la **base compartida** de la redención (`redencion_promocion`, `registrar_redencion`, `POST /promociones/redenciones`, `cupon.estado → 'redimido'`) que reutilizan US2, US3 y US4. |
| **US2 — Empuje por recompra con reserva de precio + su redención** | **Sí** | `intervalo_compra` de `002` (entregado); historial de compra vía `visita → venta → renglon_venta` (entregado); precio por sucursal vía la resolución de `001` (entregada). La reserva es de precio: `005` no lee ni toca inventario. Añade **una línea** a `registrar_redencion` (`oferta_recompra.desenlace → 'comprado'`). |
| **US3 — Reactivación con grupo de control** | **Sí** | `senal_fuga` activa de `002` (entregado). "Retorno a compra" se observa como una nueva `visita` del cliente en la ventana (research.md #11), con el sesgo de identificación declarado como limitación conocida, no bloqueante. No añade lógica a `registrar_redencion` (la validación del grupo `control` ya está en la base de US1); su prueba de acceso de control usa el endpoint de US1 (dependencia hacia atrás). |
| **US4 — Exponer la marca agregada de "promoción activa" hacia `004`** | **Sí** | Sólo `consultar_marca_activa` (solo lectura) y `GET /promociones/marca-activa`, derivados de `redencion_promocion` (propia, poblada por US1–US3). `004` ya tiene el gancho listo (FR-030 de `004`). Cerrar este contrato **desbloquea** el eje de promoción de `004`, hoy inerte. Sin frontend propio. |

**Conclusión para `/speckit-tasks`**: el plan de tareas puede ordenar US1 → US2 → US3 → US4 sin
ningún bloqueo. La nota cautelar del checklist del spec ("aún no implementada en el último
checkpoint") queda **corregida aquí**: `002` está completo.

## Project Structure

### Documentation (this feature)

```text
specs/005-promociones-inteligentes/
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

Misma estructura de primer nivel que `001`–`004`, fijada y no negociable. Este módulo **extiende**
`backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel. (Rutas
reales verificadas: `backend/migraciones/versions/` contiene `0001`–`0004`; `backend/rasero/config/`
ya existe con `pronostico.py`.)

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── config/
│   │   │   └── promociones.py                # NUEVO — parámetros de calibración en un único lugar (research.md #13), patrón de config/pronostico.py
│   │   ├── dominio/
│   │   │   ├── promociones.py                # NUEVO — funciones puras: ventana de generación del cupón, selección del producto de recompra, filtro "cliente inactivo elegible" (research.md #6, #7, #8)
│   │   │   └── experimento.py                # NUEVO — funciones puras: asignación aleatoria con semilla (research.md #9), prueba z de dos proporciones y valor p con math.erf (research.md #10a), tamaño mínimo de muestra por poder estadístico (research.md #10b), veredicto
│   │   ├── persistencia/
│   │   │   └── modelos.py                    # AMPLIADO — Campania, Cupon, OfertaRecompra, ExperimentoReactivacion, AsignacionExperimento, RedencionPromocion
│   │   ├── servicios/
│   │   │   ├── promociones.py                # NUEVO — generar_cupones + registrar_redencion base (US1); detectar_ofertas_recompra + rama oferta de registrar_redencion (US2); consultar_marca_activa (US4). Todo en un archivo, editado en secuencia por historia
│   │   │   └── experimentos.py               # NUEVO (US3) — crear_experimento (asigna grupos o marca "muestra insuficiente"), cerrar_experimento (mide retorno + prueba z + veredicto)
│   │   ├── tareas/
│   │   │   └── generacion_cupones.py         # NUEVO — python -m rasero.tareas.generacion_cupones, mismo patrón que tareas/mantenimiento_clientes.py de 002 (fuera del camino crítico HTTP)
│   │   └── api/
│   │       └── promociones.py                # NUEVO — routers de cupones, ofertas-recompra, experimentos, redenciones, marca-activa
│   └── migraciones/versions/
│       └── 0005_promociones_inteligentes.py  # NUEVO — 6 tablas, con downgrade
├── frontend/src/
│   ├── pantallas/
│   │   └── Promociones.tsx                   # NUEVO — registro de Análisis: campañas por mecanismo, resultado del experimento con su prueba z, ofertas de recompra propuestas
│   ├── componentes/
│   │   ├── GeneracionCupones.tsx             # NUEVO — disparar la generación de cupones de un rango y ver los emitidos
│   │   ├── OfertasRecompra.tsx               # NUEVO — revisar y confirmar las ofertas de recompra propuestas
│   │   ├── ResultadoExperimento.tsx          # NUEVO — % de retorno por grupo, incrementalidad, estadístico z y p, veredicto — con los tres portadores de incertidumbre
│   │   └── AplicarPromocionVenta.tsx         # NUEVO (US2) — registro de OPERACIÓN: dentro de Venta.tsx, tras identificar al cliente, lista sus cupones (US1) y ofertas (US2) vigentes para que el cajero marque uno como aplicado (no bloqueante)
│   ├── servicios/
│   │   └── promociones.ts                    # NUEVO — cliente HTTP de los endpoints de este módulo
│   ├── pantallas/Venta.tsx                   # AMPLIADO — monta AplicarPromocionVenta cuando hay un cliente identificado (mismo punto de extensión que IdentificarCliente de 002)
│   └── App.tsx                               # AMPLIADO — nueva pestaña "Promociones"
└── tests/
    ├── unidad/
    │   ├── test_experimento_asignacion.py    # NUEVO — reproducibilidad con semilla (SC-005), independencia de la paridad del id y de otros atributos (SC-006)
    │   ├── test_prueba_z.py                  # NUEVO — z de dos proporciones y p contra valores calculados a mano; tamaño mínimo de muestra
    │   └── test_promociones_dominio.py       # NUEVO — ventana del cupón, selección del producto de recompra, filtro de elegibilidad
    ├── integracion/
    │   ├── test_generacion_cupones.py        # NUEVO — ciclo del cupón: generación (idempotencia FR-007, exclusión de anonimizados FR-003, vía GET /clientes/cumpleanos FR-002) + redención (frontera con 001, idempotencia, cupón fuera de ventana → 400)
    │   ├── test_oferta_recompra.py           # NUEVO — reserva de precio sin escritura ni lectura de inventario (FR-010/FR-011), una oferta activa por (cliente, producto) (FR-014), redención → desenlace 'comprado'
    │   ├── test_experimento_reactivacion.py  # NUEVO — ciclo de vida del experimento (asignación, muestra insuficiente FR-025, 400/409, cierre calcula z + veredicto FR-019–024), 005 no toca senal_fuga (FR-028), redención de reactivación: control → 400 vía el endpoint de US1 (FR-018)
    │   └── test_marca_promocion_activa.py    # NUEVO (US4) — la marca agregada de "promoción activa" para 004 a partir de las redenciones de US1/US2 (FR-031, FR-032, SC-009)
    └── contrato/
        └── test_contrato_promociones.py      # NUEVO — respuestas de contracts/openapi.yaml en forma feliz y modos de fallo
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001`–`004` cambia de propiedad ni de esquema. Este módulo **sólo lee** de `001` y `002` — no
escribe en ninguna tabla ajena, ni siquiera a través de una función-puente como la
`fijar_precio_sucursal` que `003` necesitó (`003` sí escribía en `producto_precio_sucursal`).
`005` no aplica descuentos: el `renglon_venta.precio_aplicado` lo fija el cajero en `001` con su
criterio, y `005` sólo **registra después** que hubo una redención vinculada a esa venta (mismo
patrón que `visita` de `002`, cuya creación "nunca forma parte de la transacción de venta"). Por
eso `005` no necesita ninguna función nueva en los servicios de `001` ni de `002`.

`frontend/src/pantallas/Venta.tsx` se **amplía** (no se reescribe) con un único punto de montaje
para `AplicarPromocionVenta.tsx` — exactamente el mismo tipo de extensión que `002` hizo al añadir
`IdentificarCliente.tsx` a esa pantalla. Es propiedad visual de `005`; no cambia el flujo de cobro.

## Pruebas obligatorias

Derivadas del Principio III. El riesgo central del módulo es doble: (a) una aleatorización que
**parezca** aleatoria pero esté correlacionada con un atributo del cliente invalida silenciosamente
toda afirmación de incrementalidad —y con ella la decisión de gastar margen en descuentos—; (b) una
prueba de significancia mal calculada declara "efectiva" una campaña que sólo tuvo suerte, o
descarta una que sí funcionó.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Aleatorización reproducible y no sesgada | `tests/unidad/test_experimento_asignacion.py` | Misma población + misma semilla → **exactamente** los mismos grupos, en dos corridas (SC-005). La proporción de ids pares en el grupo tratamiento no difiere significativamente de la del grupo control (χ² o comparación de proporciones sobre una población grande sintética) — la asignación **no** es predecible por la paridad del id, ni por orden alfabético, ni por antigüedad de alta (SC-006). Semilla distinta → grupos distintos. |
| 2 | Prueba z de dos proporciones y tamaño de muestra | `tests/unidad/test_prueba_z.py` | Para pares `(p_tratamiento, n_t, p_control, n_c)` con resultado calculado a mano: el estadístico z y el valor p coinciden hasta 4 decimales (research.md #10a); `p < 0,05` ⇒ veredicto `efectivo`, `p >= 0,05` ⇒ `no_efectivo`; incrementalidad negativa ⇒ nunca `efectivo` (Edge Case). El tamaño mínimo de muestra para `(p_control=0,15, MDE=15 pp, α=0,05, poder=0,80)` da ≈ 121 por grupo (research.md #10b). |
| 3 | Ciclo de vida del experimento de reactivación | `tests/integracion/test_experimento_reactivacion.py` | Crear el experimento asigna a cada elegible un `grupo` y registra la semilla; parámetros inválidos → `400`; segundo experimento con uno `en_curso` → `409`; población por debajo del mínimo → `veredicto = 'muestra_insuficiente'`, sin asignar grupos (FR-025). Cerrar tras la ventana calcula `retorno_tratamiento`, `retorno_control`, `incrementalidad`, `estadistico_z`, `valor_p` y `veredicto` (FR-019–024); cerrar dos veces = mismo resultado. **Sólo** el grupo tratamiento tiene derecho al descuento: `POST /promociones/redenciones` (el endpoint base de US1) con la `id_asignacion_experimento` de un **control** → `400` (FR-018); con la de un **tratamiento** → `201`/`200`. En ningún punto se modifica `senal_fuga` de `002` (FR-028) — se lee su estado y su `id`. |
| 4 | Ciclo del cupón: generación (frontera con `002`, idempotencia) y **redención** (frontera con `001`) | `tests/integracion/test_generacion_cupones.py` | La generación para un rango usa `GET /clientes/cumpleanos` de `002`, nunca `cliente.fecha_nacimiento` (FR-002); un cliente anonimizado no recibe cupón porque `002` ya lo excluye (FR-003); ejecutar la generación dos veces para el mismo rango **no** crea un segundo cupón por la misma fecha objetivo (FR-007). Redimir un cupón vigente en una venta de `001` lo deja `'redimido'` (FR-005); un cupón redimido fuera de su ventana de validez se rechaza con `400` (Edge Case); un segundo `POST /promociones/redenciones` con el mismo `id_cupon` devuelve `200` con la misma fila (idempotencia); por conteo directo, `POST /promociones/redenciones` **no** añade filas a `movimiento_inventario`, no cambia `existencia` ni modifica `venta`/`renglon_venta` (FR-029). |
| 5 | Reserva de precio, no de inventario | `tests/integracion/test_oferta_recompra.py` | Por conteo directo, generar una oferta de recompra **no** produce ningún `movimiento_inventario` ni cambia `existencia` de `001` (FR-010, FR-011); a lo sumo una oferta con `desenlace = 'pendiente'` por `(cliente, producto)` (FR-014); una oferta cuya reserva vence sin compra pasa a `desenlace = 'reserva_vencida'` sin liberar stock (no hay stock apartado); redimir una oferta `pendiente` la deja `'comprado'` reutilizando el mismo `POST /promociones/redenciones` de US1. |
| 6 | Marca de "promoción activa" para `004` (SC-009) | `tests/integracion/test_marca_promocion_activa.py` | Registrar una `redencion_promocion` sobre una venta de un producto en una sucursal y fecha hace que `GET /promociones/marca-activa?id_sucursal=&desde=&hasta=` devuelva ese `(id_producto, id_sucursal, periodo)` con el `tipo` de promoción (FR-031, FR-032); un producto sin ninguna redención en ese período no aparece; la consulta **exige** `id_sucursal` y nunca agrega dos sucursales sin discriminar (FR-035). |
| 7 | Contrato público | `tests/contrato/test_contrato_promociones.py` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados, con el formato de error `{codigo, mensaje}` unificado en `001`–`004`. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `Promociones.tsx`,
`GeneracionCupones.tsx`, `OfertasRecompra.tsx`, `ResultadoExperimento.tsx`,
`AplicarPromocionVenta.tsx`.

## Sistema de diseño en el frontend

**Confirmación explícita del registro visual** (el spec no sugiere lo contrario): este módulo vive
**principalmente en el registro de Análisis** — la propia constitución clasifica "promociones" en
Análisis, junto a márgenes, pronóstico y clientes. Decidir qué campaña correr, revisar la
incrementalidad de un experimento y su prueba de significancia, y aprobar las ofertas de recompra
propuestas son **decisiones gerenciales**, no operación de caja diaria: una decisión por bloque,
aire visual, radio 6px, Source Serif 4, líneas bajo 80 caracteres.

**Excepción acotada — un único toque de Operación**: `AplicarPromocionVenta.tsx`, montado dentro de
`Venta.tsx` cuando hay un cliente identificado, lista los cupones y ofertas vigentes de ese cliente
para que **el cajero** marque uno como aplicado (FR-036: "la aplicación de un descuento en el punto
de venta requiere la acción del operador"). Es registro de Operación: alta densidad, radio 2px, IBM
Plex Sans con cifras tabulares, **sin animación** salvo la confirmación de la acción. **No es
bloqueante**: si `005` no responde, el cajero cobra el precio que decida y la redención se puede
registrar después. Mismo patrón exacto que `IdentificarCliente.tsx` de `002`, que también vive en
`Venta.tsx` sin ser camino crítico del cobro.

- **`Promociones.tsx`** (Análisis): tres secciones, una por mecanismo. En la de reactivación, el
  resultado del experimento muestra el % de retorno de cada grupo, la incrementalidad, y —con los
  **tres portadores** obligatorios— si la diferencia es estadísticamente significativa: color
  `estimado` `#1F5673` para el resultado calculado, un indicador de forma, y texto
  explícito ("incrementalidad +12,4 pp · z = 2,63 · p = 0,004 · significativa" / "p = 0,21 · no
  significativa" / "muestra insuficiente: 84 elegibles, mínimo 242"). Nunca sólo color, nunca sólo
  un número sin su prueba.
- **Distinción dato / estimación (Principio V "Visible")**: el % de retorno **observado** de cada
  grupo es un dato (tinta normal); la incrementalidad, el estadístico z, el valor p y el veredicto
  son **inferencia** y se marcan como estimado (`#1F5673` + forma + texto).
- **Momento de animación deliberado**: al revelar el detalle de un experimento cerrado (equivalente
  al "revelar el detalle de un cliente en riesgo de fuga" que la constitución cita como permitido).
  Un único momento orquestado por pantalla — no hover por fila ni fade-in por tarjeta.
- **Redundancia de portadores**: "muestra insuficiente", "reserva vencida", "sin cupón vigente" y
  "no significativa" se comunican siempre con texto explícito, nunca sólo con la ausencia de un
  número o con color.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado durante `001`); este módulo no
repite el paso `init`. Se invoca únicamente `new-work` de Impeccable para `Promociones.tsx` (mundo
visual ya fijado: registro de Análisis, tokens de `frontend/src/estilos/tokens.css` reutilizados
sin cambio). El agente documenter actualiza `DESIGN.md` al finalizar.

## Complexity Tracking

*Sin desviaciones que requieran justificación.* Este módulo no introduce ninguna segunda tecnología
(en particular, **ninguna librería estadística** — la prueba z de dos proporciones, su valor p vía
`math.erf` y el tamaño mínimo de muestra por poder estadístico son aritmética de una pantalla,
decisión de research.md #10 anclada en el Principio I y en el Principio V "explicable"), no viola
ninguna frontera de propiedad de datos (una vez reconciliadas las seis entidades por la enmienda
v2.2.5) y no requiere ningún mecanismo (disparador de base de datos, cola, servicio externo) más
allá de dos tareas invocables a mano o por el planificador del sistema operativo
(`generacion_cupones`, y el cierre de experimentos), mismo patrón que `tareas/mantenimiento_clientes.py`
de `002`.
