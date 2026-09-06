# Implementation Plan: Precios y Márgenes

**Branch**: `003-precios-margenes` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-precios-margenes/spec.md`

## Summary

Calcula el margen real de cada producto (reemplazando la aproximación provisional de `002`),
permite clasificar su rol comercial (gancho de tráfico / generador de margen) y, a partir de
ambos, sugiere un precio (con su posible override por sucursal, capacidad ya provista por `001`,
FR-050) y una colocación en zona de exhibición (catálogo ya provisto por `001`). El sistema nunca
aplica sus propias sugerencias: toda aplicación exige una acción explícita del encargado. Se
construye como extensión del mismo backend Python/FastAPI sobre PostgreSQL y del mismo frontend
React/Vite que ya usan `001` y `002`, sin introducir una segunda tecnología (Principio I).

El eje técnico es doble: (1) el margen real se recalcula **en cada lectura** a partir del costo y
precio vigentes de `001` — nunca vía disparador de base de datos ni tarea de fondo — porque ninguno
de esos dos insumos es un evento que `003` controle; y (2) `002-clientes-fidelizacion` migra su
resolver de margen interino para consumir esta definición canónica (FR-022 de este spec), cerrando
la única fuente de verdad de margen que la clarificación del 2026-09-05 ya decidió.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001` y `002`; introducir un segundo lenguaje o framework para la misma función está
PROHIBIDO por el Principio I.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend);
Vite + React sin librería de componentes de terceros (frontend). Todas ya presentes en el
repositorio; este plan no añade ninguna dependencia nueva.

**Storage**: la misma base PostgreSQL 16 de `001`/`002`, nativa en desarrollo, puerto **5442**. Las
cuatro entidades de este módulo (`rol_producto`, `margen_calculado`, `sugerencia_precio`,
`sugerencia_colocacion`) se agregan al mismo esquema mediante una nueva migración Alembic; no se
crea una base ni un esquema aparte. SQLite sigue PROHIBIDO.

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`/`002`.

**Target Platform**: mismo servidor de un solo nodo (Linux o Windows) y mismo navegador de
escritorio para la pantalla de Análisis.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se
crea un servicio nuevo.

**Performance Goals**: consultar el margen real o una sugerencia de un producto responde en menos
de 300 ms p95 — es una lectura de Análisis, no camino crítico de cobro (Principio II), pero no debe
sentirse más lenta que el resto de la pantalla. Aplicar una sugerencia (escribir el override) es una
escritura puntual sin presupuesto de tiempo especial.

**Constraints**: ninguna sugerencia de precio o colocación se aplica sin una acción explícita del
encargado (FR-012, FR-017, Principio V "consultiva por defecto"); ninguna función de este módulo es
camino crítico de un cobro; el margen se expresa como **ratio** sobre precio de venta, igual
convención que ya fijó `002` para que el reemplazo de su fórmula interina no reordene clientes por
un cambio de escala; toda cifra de dinero, costo o margen sigue la regla de precisión decimal exacta
— coma flotante binaria PROHIBIDA.

**Scale/Scope**: mismo orden de magnitud que `001`/`002` — del orden de cientos de productos por
sucursal, con un margen recalculado por lectura (sin tabla de eventos que crezca sin límite salvo
`sugerencia_precio`/`sugerencia_colocacion`, que sí acumulan histórico append-only, del mismo orden
que las decisiones que un encargado revisa por semana, no por transacción).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.6** (vigente). La enmienda que esta misma
funcionalidad motivó fue la v2.2.3 (ver "Nota sobre la enmienda v2.2.3" abajo); v2.2.4 (sobre
`004-pronostico-demanda`), v2.2.5 (sobre `005-promociones-inteligentes`) y v2.2.6 (sobre
`007-pagos-seguridad`) son correcciones posteriores sobre entradas de otros módulos, sin efecto
sobre este módulo.

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`rol_producto`, `margen_calculado`, `sugerencia_precio`, `sugerencia_colocacion`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack ya presente en `001`/`002`; no introduce una segunda tecnología. |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna función de este módulo participa en `POST /ventas` ni en ningún flujo de cobro; es una funcionalidad de Análisis consultada fuera de la caja. Aplicar una sugerencia escribe en `producto_precio_sucursal` (FR-050 de `001`) por la misma vía que ya resuelve el precio en una venta — nunca bloquea ni retrasa una venta en curso. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias" abajo: margen real, sugerencia de precio (afecta directamente el dinero cobrado si se aplica) y el contrato de migración con `002` tienen suite obligatoria. Interfaz y maquetación quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `sugerencia_precio` y `sugerencia_colocacion` son append-only (nunca se sobrescriben ni se borran): cada sugerencia generada queda con sus insumos y, si se aplicó, su instante de aplicación. `margen_calculado` registra el costo y precio exactos usados en su último cálculo. |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: cada sugerencia se genera con sus insumos (margen, rol, observación de competencia si la hubo) grabados junto a ella (FR-014, FR-002 de las Lecturas Críticas). **Consultiva por defecto**: FR-012/FR-017 — ninguna sugerencia se aplica sola; aplicar una de precio es una operación reversible (editar o quitar el override de `producto_precio_sucursal`, que ya admite ausencia de fila = vuelve al precio base) y aplicar una de colocación es solo una confirmación de que el encargado ya la ejecutó físicamente, no una reubicación que el sistema controle. **Con línea base**: la línea base es el precio y la colocación actuales, ya vigentes antes de cualquier sugerencia; una sugerencia que no se aplica no cambia nada. **Acotada**: un producto sin costo vigente o sin `rol_producto` se marca explícitamente como tal (FR-003, FR-007), nunca con un valor inventado. **Visible**: ver "Sistema de diseño" abajo — registro de Análisis exclusivamente, coherente con que la propia constitución clasifica "márgenes" en ese registro. |

**Nota sobre la enmienda v2.2.3**: al escribir `data-model.md` de esta funcionalidad se detectó que
la lista de entidades de `003` en la constitución (`costo_producto`, `margen_calculado`,
`rol_producto`, `sugerencia_colocacion`) contradecía la propia frontera de propiedad que la misma
sección ya declaraba ("el costo... pertenece a 001; el margen... pertenece a 003") y omitía
`sugerencia_precio`, que el spec exige (FR-008, FR-013, FR-014). Se corrigió por enmienda antes de
escribir este plan — mismo tipo de corrección que v2.1.1/v2.1.2 hicieron sobre `001`. Ver el informe
de impacto de sincronización al inicio de `constitution.md`.

**Lecturas Críticas del Enunciado aplicadas** (decisiones de análisis ya tomadas, no reabiertas
aquí — ver research.md #5 y #6 para su traducción a algoritmo):

- **Lectura n.º 2**: "El precio depende del rol del producto, no de una regla única" — gobierna la
  dirección de la sugerencia de precio por `rol_producto`.
- **Lectura n.º 3**: "La colocación física es parte de la decisión de precio" — gobierna que la
  salida de este módulo incluya sugerencia de zona, no solo de precio, y que el ranking de
  colocación se derive del margen real.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`/`002`. Nueva migración Alembic sobre el mismo esquema. |
| Precisión exacta en dinero | `costo_vigente`/`precio_vigente` en `NUMERIC(12,4)` (misma escala que `producto.precio_vigente` y `lote.costo_unitario` de `001`); `margen` en `NUMERIC(6,4)`, mismo patrón de ratio que `visita.margen_relativo` de `002`. Ningún `float` en el esquema ni en el código de cálculo. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `rol_producto`, `margen_calculado`, `sugerencia_precio`, `sugerencia_colocacion` ya respetan la regla; `data-model.md` la aplica también a columnas (`id_producto`, `id_sucursal`, `id_zona_exhibicion`). |
| Propiedad de datos: exactamente las 4 entidades de 003 (corregidas en v2.2.3) | `data-model.md` define únicamente `rol_producto`, `margen_calculado`, `sugerencia_precio`, `sugerencia_colocacion`. `producto`, `producto_precio_sucursal`, `zona_exhibicion`, `lote`, `existencia`, `observacion_precio`, `canal_competencia` (todas de `001`) se consultan, nunca se redefinen. |
| Sistema de diseño: registro de Análisis | Ver "Sistema de diseño en el frontend" abajo: única pantalla nueva, sin uso del registro de Operación (este módulo no participa de la caja). |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0003_precios_margenes`) con `downgrade` implementado. |
| Inteligencia explicable y reversible (Principio V) | Ver tabla de Principios arriba. |

**Resultado de la puerta**: PASA. Sin desviaciones que requieran Complexity Tracking (ver esa
sección abajo).

## Project Structure

### Documentation (this feature)

```text
specs/003-precios-margenes/
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

Misma estructura de primer nivel que `001`/`002`, fijada y no negociable. Este módulo **extiende**
`backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel.

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── dominio/
│   │   │   ├── margenes.py                # NUEVO — fórmula de margen real, piso de costo
│   │   │   └── sugerencias.py             # NUEVO — algoritmo de precio y colocación (research.md #5, #6)
│   │   ├── persistencia/
│   │   │   └── modelos.py                 # AMPLIADO — RolProducto, MargenCalculado, SugerenciaPrecio, SugerenciaColocacion
│   │   ├── servicios/
│   │   │   ├── margenes.py                # NUEVO — resolver_margen_producto (research.md #8, contrato con 002)
│   │   │   ├── precios.py                 # NUEVO — generar/aplicar sugerencia de precio; llama a fijar_precio_sucursal (research.md #7)
│   │   │   ├── catalogo.py                # AMPLIADO en 001 — nueva función fijar_precio_sucursal, cumple FR-050 de 001 (research.md #7)
│   │   │   └── margen_resolver.py         # AMPLIADO en 002 — deja de calcular su propia fórmula, consulta a servicios/margenes.py de 003 (FR-022)
│   │   └── api/
│   │       └── precios.py                 # NUEVO — routers de margen, rol, sugerencias
│   └── migraciones/versions/
│       └── 0003_precios_margenes.py       # NUEVO
├── frontend/src/
│   ├── pantallas/
│   │   └── Precios.tsx                    # NUEVO — registro de Análisis: margen, rol, sugerencias por producto
│   ├── componentes/
│   │   ├── RolProductoSelector.tsx        # NUEVO — asignar/cambiar gancho de tráfico | generador de margen
│   │   └── SugerenciaPrecioColocacion.tsx # NUEVO — tarjeta de sugerencia con insumos visibles y botón de aplicar
│   ├── servicios/
│   │   └── precios.ts                     # NUEVO — cliente HTTP de los endpoints de este módulo
│   └── App.tsx                            # AMPLIADO — nueva pestaña "Precios"
└── tests/
    ├── unidad/
    │   ├── test_margen_calculado.py       # NUEVO
    │   └── test_sugerencias.py            # NUEVO
    ├── integracion/
    │   ├── test_aplicar_sugerencia.py     # NUEVO
    │   └── test_migracion_margen_visita.py # NUEVO — contrato con 002 (FR-022)
    └── contrato/
        └── test_contrato_precios.py       # NUEVO
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001` cambia de propiedad ni de esquema; `001` gana una función nueva,
`fijar_precio_sucursal`, en su propio `servicios/catalogo.py` (cumple una capacidad que su FR-050
ya declaraba sin implementar), y `servicios/precios.py` de `003` la **llama** en proceso para
aplicar una sugerencia — nunca escribe sobre el modelo ORM `ProductoPrecioSucursal` directamente
(research.md #7, corregido tras revisión: la primera versión de esta decisión proponía acceso ORM
directo y se descartó por acoplar `003` a los detalles internos de `001` sin ningún punto de
control). `backend/rasero/servicios/margen_resolver.py`, propiedad de `002`, se modifica **por
dentro** de esa misma funcionalidad (research.md #8): es un refactor de implementación de `002`
que esta funcionalidad exige (FR-022), no un cambio de alcance de `002` ni una entidad que `003`
posea.

## Pruebas obligatorias

Derivadas del Principio III. El riesgo no es solo el cálculo de margen: una sugerencia de precio
aplicada cambia directamente lo que se cobra en la sucursal, y el contrato de migración con `002`
puede reordenar el valor de cliente si se rompe silenciosamente.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Margen real | `tests/unidad/` | Producto con costo y precio conocidos da el ratio esperado; producto a granel (costo y precio ya en la misma base de medida, sin conversión — ver research.md); sin costo vigente → no calculable (FR-003); costo ≤ 0 → no confiable (FR-004). |
| 2 | Sugerencia de precio y colocación | `tests/unidad/` | Gancho de tráfico con observación de competencia reciente sugiere igualar/bajar sin cruzar el piso de costo; generador de margen sin observación no baja de precio; sin `rol_producto` → sugerencia marcada "sin clasificar" (FR-007); colocación ordena por margen real contra `grado_privilegio` (Lectura Crítica n.º 3). |
| 3 | Aplicar una sugerencia | `tests/integracion/` | Aplicar una sugerencia de precio crea o actualiza `producto_precio_sucursal` de `001` y dejar registro de qué sugerencia lo originó (FR-013); una sugerencia de colocación aplicada no mueve nada físico, solo se marca confirmada (FR-017). |
| 4 | Migración del margen de `002` (FR-022) | `tests/integracion/` | `resolver_margen_visita` de `002`, tras el refactor, produce el mismo valor que `servicios/margenes.resolver_margen_producto` de `003` para el/los productos de esa venta — regresión explícita del contrato documentado en research.md #8. |
| 5 | Contrato público | `tests/contrato/` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `Precios.tsx`.

## Sistema de diseño en el frontend

Este módulo vive **enteramente en el registro de Análisis** — la propia constitución clasifica
"márgenes" ahí explícitamente, junto a pronóstico, clientes y promociones. A diferencia de `002`,
no hay ninguna superficie en el registro de Operación: ninguna función de precios y márgenes se
consulta desde `Venta.tsx` ni participa del cobro.

- **`Precios.tsx`** (pantalla nueva, registro de Análisis): una decisión por bloque, radio 6px,
  Source Serif 4, líneas de texto por debajo de 80 caracteres. Lista productos con su margen real,
  su rol (o "sin clasificar") y, al expandir uno, sus sugerencias de precio y colocación con los
  insumos visibles (FR-014, Principio V "Explicable"): margen usado, rol usado, observación de
  competencia usada si la hubo con sus tres portadores de antigüedad (color, forma, texto — mismo
  patrón que `001` ya exige para su comparación de precios).
- **Momento de animación deliberado**: al aplicar una sugerencia (confirmar precio o confirmar
  colocación ejecutada), un único momento orquestado que confirma la acción — no una animación de
  revelación pasiva. Ningún hover por fila ni fade-in por tarjeta.
- **Redundancia de portadores**: "sin clasificar" (rol), "no calculable"/"no confiable" (margen) y
  "sin referencia de competencia" (sugerencia) se comunican siempre con texto explícito, nunca solo
  con la ausencia de un número o con color.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado durante `001`); este módulo no
repite el paso `init`. Se invoca únicamente `new-work` de Impeccable, una vez para `Precios.tsx`
(mundo visual ya fijado: registro de Análisis, tokens de `frontend/src/estilos/tokens.css`
reutilizados sin cambio). El agente documenter actualiza `DESIGN.md` al finalizar.

## Complexity Tracking

*Sin desviaciones que requieran justificación.* Este módulo no introduce ninguna segunda
tecnología, no viola ninguna frontera de propiedad de datos (una vez corregida por la enmienda
v2.2.3) y no requiere ningún mecanismo (disparador, cola, servicio externo) más allá de los que
`001` y `002` ya establecieron como patrón aceptado.
