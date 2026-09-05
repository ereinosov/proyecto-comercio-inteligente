# Implementation Plan: Core de Ventas e Inventario

**Branch**: `001-core-ventas-inventario` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-core-ventas-inventario/spec.md`

## Summary

Módulo base de Rasero: registra los hechos de venta e inventario de los que dependen los otros seis
módulos. Se construye como servicio web con backend Python/FastAPI sobre PostgreSQL 16 y frontend
React/Vite sin librería de componentes de terceros.

El eje técnico es que **el inventario es un libro de movimientos, no un contador**. Toda existencia
se deriva de `movimiento_inventario`; el saldo consultable es una agregación derivada que se
mantiene en la misma transacción que el movimiento y que una prueba obligatoria verifica contra la
recomputación desde el histórico. Sobre esa base descansan las cuatro reglas difíciles del módulo:
idempotencia de venta, consumo de lote por caducidad, saldo negativo admitido y traspaso con
mercancía en tránsito que no desaparece del total.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x sobre React 18 (frontend)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2.x con Alembic para migraciones, Pydantic
v2; Vite como herramienta de construcción del frontend. Sin librería de componentes de terceros
(Bootstrap, Material UI, shadcn y equivalentes quedan excluidos por decisión de la constitución).

**Storage**: PostgreSQL 16, en desarrollo de forma nativa —no en contenedor— escuchando en el
puerto **5442**. SQLite está PROHIBIDO en toda fase. El empaquetado en Docker Compose con volumen
nombrado corresponde a la fase final del proyecto y queda fuera de este plan.

**Testing**: pytest para backend y para las pruebas de integración contra base de datos real; las
pruebas viven en `tests/` en la raíz del repositorio. Sin pruebas de interfaz, maquetación ni
componentes visuales, conforme al Principio III.

**Target Platform**: servidor Linux o Windows de un solo nodo; navegador de escritorio para el
punto de venta.

**Project Type**: aplicación web con backend y frontend separados.

**Performance Goals**: registrar una venta de cinco renglones en menos de 45 s de reloj de operador
(SC-001), de los cuales el sistema no debe consumir más de una fracción perceptible; consulta de
saldo de existencia en tiempo constante respecto al histórico acumulado.

**Constraints**: la caja no puede bloquearse por ninguna validación de existencias (Principio II);
importes y gramos con precisión exacta, coma flotante PROHIBIDA; instantes en UTC con presentación
y agregación por día local de sucursal; operación sin conectividad con cola local y reconciliación
por marca de tiempo de origen.

**Scale/Scope**: 2 sucursales, del orden de cientos de productos activos y unas pocas centenas de
ventas por sucursal y día. Histórico completo conservado sin política de purga. A ese ritmo, el
volumen a cinco años queda por debajo del millón de filas de movimiento. NO se requiere
particionado, cache distribuido, réplicas de lectura ni arquitectura de alta concurrencia; un único
servidor de base de datos es suficiente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verificación explícita contra la constitución **v2.2.4**.

### Principios

| Principio | Veredicto | Evidencia en este plan |
|---|---|---|
| I. Dominio Primero, Contratos Explícitos | **Cumple** | El modelo de dominio se define en `data-model.md` y los contratos observables en `contracts/openapi.yaml` antes de escribir código. El stack se justifica frente al dominio, no a la familiaridad: ver la nota de lenguaje único más abajo. |
| II. Fiabilidad Operativa en el Punto de Venta | **Cumple** | Ninguna validación de existencias bloquea el cobro (FR-047, saldo negativo admitido sin restricción de esquema). Idempotencia por clave única sobre `venta`. Cola `operacion_pendiente` con desempate por marca de tiempo más antigua y operación desplazada visible. |
| III. Pruebas Proporcionales al Riesgo | **Cumple** | Seis suites obligatorias sobre dinero, existencias y contratos (ver "Pruebas obligatorias"). Interfaz y maquetación sin pruebas, por decisión expresa. |
| IV. Trazabilidad de Cada Transacción | **Cumple** | Todo movimiento referencia el hecho que lo originó y el lote del que se descontó. Traspaso con dos asientos enlazados por `id_traspaso` y mercancía en tránsito contabilizada. Ningún saldo se sobrescribe sin movimiento que lo origine. |
| V. Inteligencia Explicable y Reversible | **Cumple (por omisión activa)** | Este módulo no contiene función predictiva alguna: registra hechos y no decide acciones. La parte aplicable del principio es la visible: la comparación de precios de competencia muestra la antigüedad con los tres portadores exigidos (color, forma y texto), y el capital inmovilizado se limita a mostrar. |

**Nota sobre el Principio I y el lenguaje único**: el Principio I prohíbe introducir una segunda
tecnología que cumpla la misma función que una ya presente, salvo justificación registrada. Se elige
Python para el backend transaccional porque los módulos 004 (pronóstico de demanda) y 005 (medición
de incrementalidad promocional) son trabajo estadístico, y mantener un solo lenguaje entre el
registro transaccional y el cálculo analítico evita exactamente esa segunda tecnología. La
justificación queda registrada aquí, como exige el principio.

### Decisiones técnicas fijadas por la constitución

| Regla constitucional | Cómo la cumple este plan |
|---|---|
| Motor PostgreSQL, nativo en desarrollo, puerto 5442, SQLite PROHIBIDO | Adoptado literalmente. Ver "Storage". |
| Precisión exacta en dinero y gramos | Importes en `NUMERIC(12,2)`; pesos en `INTEGER` de gramos. Ningún tipo de coma flotante aparece en el esquema. |
| UTC almacenado, día local de sucursal para agregar | Todos los instantes en `TIMESTAMPTZ`; `sucursal.zona_horaria` en identificador IANA; agregación por `(instante AT TIME ZONE zona_horaria)::date`. |
| Nomenclatura: español, `snake_case`, singular, sin "ñ", claves foráneas `id_` + tabla | Aplicada en todo `data-model.md`. `campania` y `senal_fuga` ya respetaban la regla; aquí aplica a `anulacion_venta`, `operacion_pendiente` y `conteo_fisico`. |
| Propiedad de datos: las 20 entidades de 001 | `data-model.md` define exactamente esas 20 y ninguna ajena. `terminal_pago` se guarda como referencia opaca sin definir la entidad, que es propiedad de 007. |
| Sistema de diseño: registro de Operación | Tokens como variables CSS propias desde el inicio; tabla como elemento principal, sin tarjetas, radio 2px, animación solo como confirmación de acción. IBM Plex Sans con cifras tabulares. Inter PROHIBIDA. |
| Migraciones versionadas y reversibles | Alembic, una migración por cambio de esquema, con `downgrade` implementado. |

**Resultado de la puerta**: PASA. Una desviación registrada en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-ventas-inventario/
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

La estructura de primer nivel está **fijada externamente y no es negociable**. No se crea `src/` en
la raíz, no se mueve código dentro de `specs/`, y no se sustituyen estas carpetas por una
organización por funcionalidad.

```text
proyecto-comercio-inteligente/
├── .specify/
├── specs/                      # 001 a 007, cada uno con sus artefactos
├── backend/
│   ├── rasero/
│   │   ├── dominio/            # entidades, reglas puras (FEFO, totales, redondeo)
│   │   ├── persistencia/       # modelos SQLAlchemy, repositorios, sesión
│   │   ├── servicios/          # casos de uso transaccionales (venta, traspaso, conteo)
│   │   ├── api/                # routers FastAPI, esquemas Pydantic
│   │   └── configuracion.py
│   ├── migraciones/            # Alembic
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── estilos/            # tokens.css: paleta, tipografía, radios
│   │   ├── componentes/        # propios; sin librería de terceros
│   │   ├── pantallas/          # venta, entradas, traspasos, conteo, comparacion
│   │   └── servicios/          # cliente HTTP, cola offline
│   ├── index.html
│   └── package.json
└── tests/
    ├── unidad/                 # reglas puras: totales, redondeo, selección FEFO
    ├── integracion/            # contra PostgreSQL real: idempotencia, saldos, traspaso, cola
    └── contrato/               # respuestas conformes a contracts/openapi.yaml
```

**Structure Decision**: aplicación web con backend y frontend separados, sobre las tres carpetas
fijas de primer nivel. Se aparta de la plantilla en un punto: la plantilla ubica las pruebas dentro
de `backend/tests/` y `frontend/tests/`, y aquí van en `tests/` en la raíz por requisito externo del
proyecto. Dentro de `backend/` y `frontend/` la organización sí es libre y se elige por capas:
`dominio` sin dependencias de infraestructura —para que las reglas de redondeo y de FEFO se prueben
sin base de datos—, `persistencia` y `api` como bordes.

## Pruebas obligatorias

Derivadas del Principio III. Estas seis suites deben existir y estar en verde antes de fusionar; su
ausencia bloquea la fusión y `/speckit-tasks` debe generarlas como tareas explícitas.

| # | Qué verifica | Ubicación | Caso que no puede faltar |
|---|---|---|---|
| 1 | Totales de venta | `tests/unidad/` | Producto a peso: 0,7 kg a precio por kg impar, con redondeo a dos decimales de la moneda. |
| 2 | Selección de lote FEFO | `tests/unidad/` | Un lote que entró después caduca antes: debe salir primero. |
| 3 | Idempotencia de venta | `tests/integracion/` | Mismo reintento con la misma clave: una sola venta y un solo juego de movimientos. |
| 4 | Saldo reconstruido | `tests/integracion/` | Saldo consultado == suma de movimientos, incluido el caso de saldo negativo. |
| 5 | Traspaso entre sucursales | `tests/integracion/` | La existencia total del sistema no cambia durante el tránsito. |
| 6 | Reconciliación offline | `tests/integracion/` | Dos operaciones en conflicto: gana la más antigua y la desplazada queda visible. |

Sin pruebas obligatorias: interfaz, maquetación y componentes visuales.

**Alcance de la suite 6 (decisión registrada)**: SC-006 exige, además de la resolución de
conflicto, que la sincronización tras 30 minutos sin conectividad con al menos 50 operaciones
no pierda ninguna. La suite 6 prueba la lógica de conflicto en sí —dos operaciones sobre el
mismo recurso—, no un caso de volumen a 50+ operaciones: a ese volumen no hay riesgo adicional
que una prueba de carga cubra y el Principio III (pruebas proporcionales al riesgo) no la exige.
La cobertura cualitativa del escenario 6 de `quickstart.md` es suficiente. Decisión deliberada,
no pendiente.

## Sistema de diseño en el frontend

El módulo 001 es registro de **Operación**. Los tokens de la constitución se implementan como
variables CSS propias en `frontend/src/estilos/tokens.css` desde la primera pantalla, nunca como
valores incrustados en componentes:

- Superficies `#F1F4F1` y `#FFFFFF`; tinta `#1B2621` y `#5A6862`; marca `#0F5132`; borde `#D5DCD6`.
- Semánticos reservados a su significado: atención `#9A5B08`, crítico `#8E2A2A`, estimado `#1F5673`.
- Radio de borde 2px (Operación). El radio 6px de Análisis se define en el mismo archivo aunque este
  módulo no lo use, para que los módulos 003 a 005 hereden la escala completa.
- IBM Plex Sans con cifras tabulares reales, de modo que las columnas de dinero y de peso alineen
  por dígito. Source Serif 4 declarada para Análisis. **Inter PROHIBIDA.**
- Tabla como elemento principal, alta densidad, sin tarjetas. Animación permitida solo como
  confirmación de una acción del usuario; nada disparado por scroll ni por hover pasivo.
- Antigüedad e incertidumbre siempre con tres portadores simultáneos: color, forma y texto.

La skill Impeccable se invoca en **Foundational**, inmediatamente después de crear `tokens.css` y
cargar las tipografías: su paso `teach` recibe el contenido íntegro de esta sección y genera
`PRODUCT.md` y `DESIGN.md`. La constitución no admite diferirlo — el paso `teach` es OBLIGATORIO
**antes de generar cualquier interfaz**, no en una fase de pulido posterior — así que toda tarea
de frontend de este plan depende explícitamente de él.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tabla derivada `existencia`, mantenida en la misma transacción que el movimiento, en lugar de calcular el saldo por agregación en cada lectura | Requisito explícito de este plan: consultar el saldo actual sin recorrer el histórico, que la constitución conserva sin purga. Cada pantalla de venta consulta saldo por renglón. | Una vista `SUM` sobre `movimiento_inventario` **sería suficiente al volumen declarado** (por debajo del millón de filas a cinco años) y es más simple. Se descarta por el requisito anterior, no por rendimiento medido. El coste de la decisión es que existe un dato derivado que puede divergir; se compensa con la prueba obligatoria n.º 4, que verifica igualdad entre la tabla y la recomputación desde movimientos, y con la regla de que `existencia` nunca es autoritativa: ante discrepancia gana el histórico. |
