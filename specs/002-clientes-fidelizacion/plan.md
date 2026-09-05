# Implementation Plan: Clientes y Fidelización

**Branch**: `002-clientes-fidelizacion` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-clientes-fidelizacion/spec.md`

## Summary

Mide el valor real de cada cliente —combinando frecuencia, monto y margen, nunca solo gasto
total— y detecta señales de fuga silenciosa derivando un intervalo de compra esperado por cliente
a partir de su propio historial. No decide promociones ni descuentos: expone ambas señales para
que `005-promociones-inteligentes` las consuma. Se construye como extensión del mismo backend
Python/FastAPI sobre PostgreSQL y del mismo frontend React/Vite que ya levantó
`001-core-ventas-inventario`, sin introducir una segunda tecnología para la misma función
(Principio I).

El eje técnico es doble: (1) toda la aritmética de ritmo de compra y de fuga se deriva
**exclusivamente del historial propio de cada cliente** — nunca de un umbral compartido — y (2) la
retención de datos personales está atada a esa misma aritmética (FR-014/FR-015), no a un plazo
fijo, lo que convierte la anonimización en una tarea de fondo programada, nunca en el camino
crítico de una lectura o de una venta.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que `001`; introducir un segundo lenguaje o framework para la misma función está
PROHIBIDO por el Principio I.

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic, Pydantic v2 (backend);
Vite + React sin librería de componentes de terceros (frontend). Todas ya presentes en el
repositorio; este plan no añade ninguna dependencia nueva.

**Storage**: la misma base PostgreSQL 16 de `001`, nativa en desarrollo, puerto **5442**. Las
cuatro entidades de este módulo (`cliente`, `visita`, `intervalo_compra`, `senal_fuga`) se agregan
al mismo esquema mediante una nueva migración Alembic; no se crea una base ni un esquema aparte.
SQLite sigue PROHIBIDO.

**Testing**: pytest, en `tests/unidad`, `tests/integracion` y `tests/contrato` en la raíz del
repositorio — misma ubicación y convención que `001`.

**Target Platform**: mismo servidor de un solo nodo (Linux o Windows) y mismo navegador de
escritorio para las pantallas de Operación y Análisis.

**Project Type**: extensión de la aplicación web existente (backend + frontend separados); no se
crea un servicio nuevo.

**Performance Goals**: identificar a un cliente durante una venta (búsqueda + vinculación) responde
en menos de 300 ms p95, para cumplir SC-006 ("no añade tiempo perceptible al cobro"); la
anonimización (FR-015) corre como tarea de fondo diaria, sin presupuesto de tiempo perceptible por
ningún usuario.

**Constraints**: identificar al cliente NUNCA es bloqueante ni obligatorio (FR-003, Principio II);
ninguna validación ni cálculo de este módulo puede ser camino crítico de un cobro; el margen de una
visita depende de `003-precios-margenes`, que todavía no existe (ver research.md #2 para la
resolución) y se expresa como **ratio** (`margen_relativo`), no como monto, precisamente para que
ese reemplazo no reordene clientes por un cambio de escala; el importe `monto_total` sigue la misma
regla de precisión decimal exacta que `001` — coma flotante binaria PROHIBIDA, también en el propio
`margen_relativo` (`NUMERIC`, nunca `float`).

**Scale/Scope**: mismo orden de magnitud que `001` — del orden de cientos de clientes activos por
las dos sucursales del alcance de examen, con como mucho una visita por cada venta que identifique
cliente (subconjunto de las ventas de `001`). No se requiere ninguna infraestructura adicional de
cómputo o almacenamiento respecto a la ya prevista para `001`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.5**.

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio (`cliente`, `visita`, `intervalo_compra`, `senal_fuga`) se define en `data-model.md` y el contrato observable en `contracts/openapi.yaml` antes de escribir código. Reutiliza el stack ya presente en `001`; no introduce una segunda tecnología para backend, frontend ni base de datos. |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | FR-003: identificar al cliente es opcional y nunca bloqueante. El registro de una visita ocurre **después** de que la venta ya se confirmó (ver research.md #5); si la creación de la visita falla, la venta de `001` ya está consumada y no se revierte. Ninguna función de este módulo participa en la transacción de cobro. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Ver "Pruebas obligatorias" abajo: intervalo de compra, umbrales de fuga (activa y confirmada) y anonimización tienen suite obligatoria por el riesgo de datos personales que gestionan; el contrato público tiene su suite. Interfaz y maquetación quedan exentas. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | `visita` referencia `id_venta` de `001`, nunca duplica sus datos de origen salvo el snapshot de monto/margen (documentado como snapshot deliberado). `senal_fuga` conserva su histórico completo (activa → confirmada → resuelta) y nunca se borra; solo los datos personales del `cliente` se anonimizan, y solo tras el proceso documentado en FR-014/FR-015. |
| V. Inteligencia Explicable y Reversible | **Cumple** | **Explicable**: el valor de cliente se descompone en sus tres factores en el registro de Análisis (FR-011b); la fuga muestra el intervalo esperado que la sustenta. **Consultiva por defecto**: este módulo no ejecuta ninguna acción sobre el cliente — ni descuento, ni contacto — solo expone datos (FR-013); no hay nada que "deshacer" porque no hay acción. **Con línea base**: la línea base explícita es el criterio que hoy usa el negocio —ordenar por gasto total—, y SC-002 exige que el valor compuesto se aparte de ese orden cuando corresponda. **Acotada**: un cliente con historial insuficiente se marca así explícitamente (FR-007), nunca con un valor o riesgo inventado. **Visible**: ver "Sistema de diseño" abajo. |

**Nota sobre el Principio I y el resolver de margen**: `003-precios-margenes` no existe todavía, y
FR-005 exige que la visita registre el margen "ya calculado" por ese módulo. Este plan resuelve la
brecha con una función interna aislada, no con una segunda fuente de verdad del margen — ver
research.md #2 y la fila correspondiente en Complexity Tracking.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Mismo motor, misma instancia que `001`. Nueva migración Alembic sobre el mismo esquema. |
| Precisión exacta en dinero | `monto_total` en `NUMERIC(12,2)`, igual que `venta.total` en `001`; `margen_relativo` en `NUMERIC(6,4)` (es un ratio, no un importe, pero la misma prohibición de coma flotante aplica). Ningún `float` en el esquema ni en el código de cálculo. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | `cliente`, `visita`, `intervalo_compra`, `senal_fuga` ya respetaban la regla en la constitución; `data-model.md` la aplica también a sus columnas (`id_cliente`, `id_venta`). |
| Propiedad de datos: exactamente las 4 entidades de 002 | `data-model.md` define únicamente `cliente`, `visita`, `intervalo_compra`, `senal_fuga`. `venta` (FK de `visita`) y `margen_calculado` (fuente conceptual del margen) se consultan/referencian, nunca se redefinen. |
| Sistema de diseño: dos registros | Ver "Sistema de diseño en el frontend" abajo: resumen en Operación, desglose en Análisis, mapeo explícito exigido por FR-011. |
| Migraciones versionadas y reversibles | Alembic, una migración nueva (`0002_clientes_fidelizacion`) con `downgrade` implementado. |
| Datos personales: finalidad y retención documentadas | FR-002, FR-014, FR-015, FR-016 documentan finalidad (valor y fuga, ninguna otra) y retención (atada a la propia fuga del cliente, nunca un plazo fijo global). |

**Resultado de la puerta**: PASA. Una desviación registrada en Complexity Tracking (resolver de
margen interino).

## Project Structure

### Documentation (this feature)

```text
specs/002-clientes-fidelizacion/
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

Misma estructura de primer nivel que `001`, fijada y no negociable. Este módulo **extiende**
`backend/rasero`, `frontend/src` y `tests/`; no crea carpetas nuevas de primer nivel.

```text
proyecto-comercio-inteligente/
├── backend/
│   ├── rasero/
│   │   ├── dominio/
│   │   │   ├── valor_cliente.py       # NUEVO — percentiles, puntuación compuesta, línea base
│   │   │   └── fuga_cliente.py        # NUEVO — umbral activa (1×), confirmada (5×/piso 12 meses)
│   │   ├── persistencia/
│   │   │   └── modelos.py             # AMPLIADO — Cliente, Visita, IntervaloCompra, SenalFuga
│   │   ├── servicios/
│   │   │   ├── clientes.py            # NUEVO — registrar cliente/visita, recalcular, listar valor
│   │   │   ├── margen_resolver.py     # NUEVO — interino hasta que exista 003 (ver research.md #2)
│   │   │   └── anonimizacion.py       # NUEVO — tarea de fondo (FR-015)
│   │   └── api/
│   │       └── clientes.py            # NUEVO — routers de clientes/visitas/cumpleaños
│   └── migraciones/versions/
│       └── 0002_clientes_fidelizacion.py   # NUEVO
├── frontend/src/
│   ├── pantallas/
│   │   ├── Venta.tsx                  # AMPLIADO — identificación opcional + resumen compuesto
│   │   └── Clientes.tsx               # NUEVO — registro de Análisis: listado + desglose + fuga
│   ├── componentes/
│   │   ├── IdentificarCliente.tsx     # NUEVO — buscador opcional, no bloqueante, para Venta.tsx
│   │   └── ValorClienteResumen.tsx    # NUEVO — puntuación compuesta, reusado en ambos registros
│   └── servicios/
│       └── clientes.ts                # NUEVO — cliente HTTP de los endpoints de este módulo
└── tests/
    ├── unidad/
    │   ├── test_intervalo_compra.py   # NUEVO
    │   ├── test_fuga_cliente.py       # NUEVO
    │   └── test_valor_cliente.py      # NUEVO
    ├── integracion/
    │   ├── test_visita_desde_venta.py # NUEVO
    │   └── test_anonimizacion.py      # NUEVO
    └── contrato/
        └── test_contrato_clientes.py  # NUEVO
```

**Structure Decision**: extensión pura de la estructura ya fijada por `001`. Ningún archivo de
`001` cambia de propiedad; `Venta.tsx` se **amplía por composición** (un componente opcional que
se añade), no se reescribe, y `venta`/`renglon_venta` no ganan ninguna columna nueva — la
vinculación con `cliente` vive enteramente en `visita`, propiedad de este módulo (ver research.md
#5).

## Pruebas obligatorias

Derivadas del Principio III. El riesgo que justifica cada suite no es solo monetario: `senal_fuga`
y la anonimización gestionan datos personales cuya pérdida es irreversible, lo que las hace
proporcionalmente tan obligatorias como un cálculo de dinero.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Intervalo de compra por cliente | `tests/unidad/` | Cliente con 2 visitas (1 intervalo) queda `datos_insuficientes`; con 3 (2 intervalos) queda `calculado`. |
| 2 | Umbrales de fuga | `tests/unidad/` | Cliente que supera 1× su intervalo → `activa`; que supera 5× (o 12 meses, el mayor) → `confirmada`; nueva visita en cualquiera de los dos estados → `resuelta`. |
| 3 | Valor de cliente compuesto | `tests/unidad/` | Cliente A (monto alto, frecuencia baja, margen bajo) y cliente B (monto menor, frecuencia y margen mayores) con el mismo monto total no quedan en el mismo orden que un ranking por monto simple (SC-002). |
| 4 | Visita desde una venta | `tests/integracion/` | Venta que identifica cliente crea exactamente una visita con `monto_total`/`margen_relativo` congelados (este último como ratio, no como monto); venta sin cliente no crea ninguna visita ni afecta a nadie. |
| 5 | Anonimización | `tests/integracion/` | Fuga confirmada + 90 días sin visita → `cliente` anonimizado, métricas agregadas conservadas; nueva visita antes del vencimiento cancela la anonimización programada. |
| 6 | Contrato público | `tests/contrato/` | Respuestas de `contracts/openapi.yaml` en su forma feliz y en sus modos de fallo declarados. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales de `Clientes.tsx` y del
resumen en `Venta.tsx`.

## Sistema de diseño en el frontend

Este módulo es el primero en construirse que usa **los dos registros visuales a la vez**, mapeo
que la propia sesión de clarificación de `spec.md` ya fijó (FR-011):

- **Operación** (dentro de `Venta.tsx`, vía `ValorClienteResumen.tsx`): una única puntuación
  compuesta, sin desglose, junto al nombre del cliente identificado. Radio 2px, IBM Plex Sans con
  cifras tabulares, sin tarjetas. Ninguna animación al mostrarla — no es una confirmación de acción
  del operador, es información de contexto; solo se anima si el propio cliente se identifica como
  resultado de una acción del cajero (búsqueda confirmada), y esa animación sigue la regla de
  Operación: confirma la acción, no decora el dato.
- **Análisis** (`Clientes.tsx`, pantalla nueva): el desglose de frecuencia, monto y margen, uno por
  bloque, líneas de texto por debajo de 80 caracteres, radio 6px, Source Serif 4. Aquí vive el
  **momento de animación deliberado por pantalla** que la constitución cita textualmente como
  ejemplo de este registro: "al revelar el detalle de un cliente en riesgo de fuga" (Sistema de
  Diseño, sección Análisis). Un solo momento orquestado al abrir el detalle; ningún hover por fila
  ni fade-in por tarjeta.
- **Redundancia de portadores**: el estado de fuga (activa/confirmada/datos insuficientes) y la
  antigüedad de la última visita se muestran siempre con los tres portadores exigidos — color
  semántico, indicador de forma y texto explícito ("hace 40 d") — nunca solo color. `activa` usa el
  semántico de atención (`#9A5B08`); `confirmada` usa el crítico (`#8E2A2A`), coherente con que esa
  etapa dispara un proceso irreversible.

**Herramienta de ejecución**: `PRODUCT.md` ya existe (capturado durante `001`); este módulo **no**
repite el paso `init`. Se invoca únicamente `new-work` de Impeccable, una vez para `Clientes.tsx`
(mundo visual ya fijado: registro de Análisis, tokens de `frontend/src/estilos/tokens.css`
reutilizados sin cambio) y una vez para la ampliación de `Venta.tsx` (mundo visual: registro de
Operación, ya vigente desde `001`). El agente documenter actualiza `DESIGN.md` al finalizar, no
antes.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `margen_resolver.py`: resolver interno de margen por visita, con fórmula de respaldo — margen bruto **relativo al precio de venta** (`(monto_total − costo_total) / monto_total`, no un monto absoluto), leyendo `lote.costo_unitario` de `001` vía `movimiento_inventario` — en lugar de consultar `margen_calculado` de `003-precios-margenes` | `003-precios-margenes` no existe todavía. Sin un valor de margen, `visita` (FR-005) y el valor de cliente (FR-010) no pueden entregarse de forma independiente, como exige que cada historia de usuario sea desplegable por sí sola. | Bloquear la construcción de `002` hasta que `003` exista — rechazado: la constitución no declara a `003` como prerrequisito de `002` en la tabla de propiedad de datos, y el propio orden de historias de usuario del spec asume que 002 se puede construir ya. Un margen **absoluto** en moneda — rechazado: acopla la dimensión "margen" a la dimensión "monto" (ambas escalarían con el tamaño del ticket) y, cuando `003` reemplace esta fórmula por una expresada como ratio (la convención estándar de margen bruto), reordenaría clientes solo por el cambio de unidad, no por un criterio de negocio distinto. El resolver se aísla detrás de una única función con un nombre estable; sustituirla por la consulta real a `003` no toca `data-model.md` de `visita` ni a ningún consumidor del valor de cliente. El costo de la decisión es que el margen mostrado hoy es una aproximación (margen bruto simple, sin asignación de costos indirectos que `003` pueda añadir); se documenta explícitamente como interino en el código y en `research.md`, junto con la frontera de propiedad de datos (002 lee, no posee, `lote.costo_unitario`) en `data-model.md`. |
