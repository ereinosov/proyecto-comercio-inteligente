# Implementation Plan: Reportes e Inteligencia

**Branch**: `008-reportes-inteligencia` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-reportes-inteligencia/spec.md`

## Summary

Una **capa de solo lectura** sobre 001–007. No captura ningún dato del operador ni ejecuta
ninguna acción de negocio: cruza, agrega y presenta lo que los otros módulos ya calcularon, a la
escala de la semana y el mes. Cuatro vistas independientes:

1. **Comparativo entre sucursales** (P1) — una columna por sucursal activa (nunca "dos" en
   código, FR-046 de 001), filas de ventas / tickets / ticket promedio / margen ponderado /
   merma valorada / diferencia de arqueo; diferencia relativa contra la mejor del grupo con
   color de atención sólo cuando significa un peor resultado.
2. **Tendencias** (P2) — las series de 001/003/004/006 agregadas por semana o mes local de la
   sucursal, con los períodos parciales de los bordes marcados como incompletos.
3. **Tablero de KPIs** (P2) — una tarjeta por módulo con 2–3 cifras y su período de referencia
   propio; "datos insuficientes" nunca "0".
4. **Segmentos de clientes** (P3) — k-means (algoritmo de Lloyd, k ∈ {3,4}) sobre tres ejes
   normalizados (frecuencia, margen, recencia) derivados de `visita` / `intervalo_compra` de
   002. Determinista con semilla fija. Recálculo por lote disparado por una persona; los
   clientes con < 3 visitas quedan "sin clasificar". La etiqueta de grupo aparece como **dato de
   lectura** en el detalle del cliente de 002.

**Tres entidades nuevas**, todas derivadas y regenerables (constitución v2.6.0):
`agregado_reporte` (caché de una vista), `segmento_cliente` (definición de un grupo del último
clustering), `asignacion_segmento` (cliente ↔ grupo). Borrar las tres y recalcular reproduce el
mismo estado desde 001–006.

Se construye como extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic
sobre PostgreSQL 16 (puerto 5442) y del mismo frontend React 18 + TS + Vite que 001–007.
Migración `0012_reportes_inteligencia`.

**Ejes que condicionan el plan**:

1. **Enmienda constitucional v2.6.0 hecha ANTES de este plan** (mismo patrón que v2.2.3–v2.2.6):
   las tres entidades ya están declaradas en "Propiedad de Datos" como derivadas/regenerables, y
   la frontera "008 sólo lee de 001–007, nada alimenta de vuelta" ya está escrita. Este plan no
   necesita otra enmienda.
2. **Sin librería estadística pesada** (Principio I, mismo criterio que 006 rechazó
   `scipy`/`numpy`): el k-means es **Python puro** —lista de tuplas de tres floats, distancia
   euclídea, media aritmética por eje— (research.md §2). Las agregaciones son `SUM`/`AVG`/
   `GROUP BY` de SQL sobre datos que 001–006 ya exponen o vistas de lectura que ya tienen.
3. **Nada bloqueado**: 001–007 están todos implementados. 008 sólo consume.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend) — mismas
versiones que 001–007. Introducir `scikit-learn`, `numpy`, `pandas` o cualquier librería de
análisis para esto está PROHIBIDO por el Principio I; ver research.md §2.

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic (backend); React 18, Vite, el sistema
de componentes base `Boton`/`Campo`/`EncabezadoPantalla`/`Segmentado` y `EstadoVacio`,
`Paginador`, los componentes de gráfico ya usados por Precios/Pronóstico/Clientes (frontend).
Sin dependencias nuevas.

**Storage**: PostgreSQL 16 (puerto 5442). Tres tablas nuevas en el mismo esquema
(`agregado_reporte`, `segmento_cliente`, `asignacion_segmento`), migración `0012`.

**Testing**: `pytest` contra PostgreSQL real (mismo patrón que 001–007). Suites obligatorias
del Principio III: contrato de los endpoints de lectura, y unidad del k-means (determinismo,
separación de patrones, umbral de historial). Sin pruebas de interfaz salvo excepción puntual
(no se prevé).

**Target Platform**: servidor Linux (backend), navegador (frontend), como 001–007.

**Project Type**: web (backend + frontend), extensión de la app existente.

**Performance Goals**: comparativo y tablero con percepción de "casi inmediato" en la primera
carga de un período (agregaciones SQL sobre decenas de miles de ventas); el recálculo de
segmentos puede tardar unos segundos y muestra progreso. La caché (`agregado_reporte`) evita
repetir el cálculo para el mismo (tipo, ámbito, período).

**Constraints**: solo lectura sobre 001–007 (cero escrituras sobre sus tablas, SC-006); sin
trabajo programado (todo recálculo lo dispara una persona, FR-020/FR-028); determinismo del
clustering (semilla fija, FR-019).

**Scale/Scope**: minimarket de dos tiendas — decenas de miles de ventas, cientos de clientes,
decenas de productos. Sin paginación ni muestreo en los cálculos; si el volumen creciera un
orden de magnitud se revisa la caché.

## Constitution Check

*GATE: debe pasar antes de la fase 0.*

| Principio | Estado | Nota |
|---|---|---|
| I — Dominio primero, contratos explícitos | ✅ | Sin lenguaje ni librería nueva. k-means en Python puro. Endpoints de lectura con contrato OpenAPI. |
| II — Fiabilidad en el punto de venta | ✅ | 008 NO es camino crítico de ningún cobro (no toca `POST /ventas`). Si sus cálculos fallan, la caja sigue. |
| III — Pruebas proporcionales al riesgo | ✅ | Suites obligatorias: contrato de lectura + unidad del k-means. Sin pruebas de UI. |
| IV — Trazabilidad de cada transacción | ✅ | 008 no genera transacciones. `agregado_reporte` y la asignación de segmento llevan su instante de cálculo; son regenerables desde la fuente de verdad de 001–006. |
| V — Inteligencia explicable y reversible | ✅ | El clustering es explicable (algoritmo de pocos pasos, sin datos externos ni entrenamiento supervisado), reversible (borrar y recalcular) y determinista (semilla fija). La descripción de cada grupo se deriva del centroide, no es un texto fijo. |
| VI — Autorización y roles | ✅ | Toda la pantalla y todos los endpoints exigen `encargado` vía `exige_rol` (mecanismo central, constitución v2.5.0 ya asigna "Reportes e inteligencia" a `encargado`). |
| Propiedad de datos | ✅ | v2.6.0 declara las tres entidades de 008 como derivadas. 008 no escribe contra 001–007. |
| Sistema de diseño | ✅ | Registro de Análisis; `EstadoVacio` con `despensa-logo-mono-800w.png` (ya reservado en DESIGN.md); sin Verde Rasero. |

**Sin violaciones. Complexity Tracking vacío.**

## Project Structure

### Documentation (this feature)

```text
specs/008-reportes-inteligencia/
├── plan.md              # Este archivo
├── research.md          # Decisiones (k-means puro, granularidad temporal, caché, frontera de lectura)
├── data-model.md        # agregado_reporte, segmento_cliente, asignacion_segmento
├── quickstart.md        # Escenarios e2e de las 4 vistas
├── contracts/
│   └── openapi.yaml     # GET /reportes/comparativo, /reportes/tendencia, /reportes/tablero,
│                        # GET /reportes/segmentos, POST /reportes/segmentos/recalculo
├── checklists/
│   └── requirements.md  # Checklist de calidad de la spec (ya creado)
└── tasks.md             # Salida de /speckit-tasks
```

### Source Code (repository root)

```text
backend/rasero/
├── persistencia/
│   └── modelos.py                    # + AgregadoReporte, SegmentoCliente, AsignacionSegmento
├── servicios/
│   ├── reportes_comparativo.py       # comparativo entre sucursales (SUM/AVG sobre 001/003/006)
│   ├── reportes_tendencia.py         # agregación temporal por semana/mes local
│   ├── reportes_tablero.py           # reúne los KPIs de cada módulo
│   ├── segmentacion_clientes.py      # extracción de features + orquestación del recálculo
│   └── reportes_cache.py             # leer/escribir/invalidar agregado_reporte
├── dominio/
│   ├── kmeans.py                     # algoritmo de Lloyd, Python puro, función pura
│   └── periodo_local.py              # límites de semana/mes en la zona horaria de una sucursal
├── config/
│   └── reportes.py                   # k, umbral de historial mínimo, semilla, rangos por defecto,
│                                     # umbrales de color de KPI
└── api/
    └── reportes.py                   # router /reportes, todo exige_rol("encargado")

backend/alembic/versions/
└── 0012_reportes_inteligencia.py     # 3 tablas; downgrade elimina las 3 (dato regenerable)

frontend/src/
├── servicios/reportes.ts             # cliente de /reportes/*
├── pantallas/
│   ├── Reportes.tsx                  # contenedor + Segmentado (Comparativo | Tendencias | Tablero | Segmentos)
│   ├── ReporteComparativo.tsx
│   ├── ReporteTendencias.tsx
│   ├── ReporteTablero.tsx
│   └── ReporteSegmentos.tsx
├── componentes/
│   └── EtiquetaSegmento.tsx          # etiqueta de grupo para el detalle de Clientes (002)
└── App.tsx                           # + opción "Reportes", rol "encargado" (ya previsto en v2.5.0)

tests/
├── contrato/test_contrato_reportes.py
├── integracion/test_reportes_comparativo.py
├── integracion/test_reportes_tendencia.py
├── integracion/test_reportes_tablero.py
├── integracion/test_segmentacion_clientes.py
└── unidad/test_kmeans.py             # determinismo, separación de patrones, k > n clasificables
```

**Structure Decision**: extensión de la app existente (backend `rasero` + frontend React). Los
servicios de 008 viven junto a los de 001–007 y **consumen sus servicios de lectura** donde ya
existen (`servicios/margenes.listar_margenes_sucursal`, `servicios/mermas.resumen_mermas_por_causa`,
`servicios/clientes.resumen_fuga_por_segmento`, la serie de 004) en vez de re-consultar sus
tablas base — research.md §5.

## Complexity Tracking

*Sin violaciones de la Constitución. Sección vacía a propósito.*
