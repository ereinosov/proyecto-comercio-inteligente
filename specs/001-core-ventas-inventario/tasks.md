---

description: "Task list template for feature implementation"
---

# Tasks: Core de Ventas e Inventario

**Input**: Documentos de diseño desde `/specs/001-core-ventas-inventario/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados.

**Pruebas**: se incluyen únicamente las 6 suites obligatorias del Principio III (proporcional al riesgo), intercaladas junto a la funcionalidad que verifican. No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario (P1 → P8 de spec.md), backend antes que frontend dentro de cada historia. Fundamento completo (esquema, conexión, tokens) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta)
- **[Story]**: historia de usuario a la que pertenece (US1 … US8)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende

## Convención de rutas (fijada en plan.md, no negociable)

- Backend: `backend/rasero/` (dominio/, persistencia/, servicios/, api/) y `backend/migraciones/`
- Frontend: `frontend/src/` (estilos/, componentes/, pantallas/, servicios/)
- Pruebas: `tests/` en la raíz (unidad/, integracion/, contrato/) — nunca dentro de `backend/` ni `frontend/`

---

## Phase 1: Setup

**Propósito**: inicialización del repositorio y de los dos proyectos.

- [X] T001 Crear `backend/rasero/{dominio,persistencia,servicios,api}/`, `backend/migraciones/`, `frontend/src/{estilos,componentes,pantallas,servicios}/` y `tests/{unidad,integracion,contrato}/` en la raíz del repositorio
- [X] T002 [P] Inicializar `backend/pyproject.toml` con Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic y Pydantic v2 (depende de T001)
- [X] T003 [P] Inicializar `frontend/package.json` con React 18, TypeScript 5.x y Vite, sin librería de componentes de terceros (depende de T001)
- [X] T004 [P] Configurar ruff y black en `backend/pyproject.toml` (depende de T002)
- [X] T005 [P] Configurar eslint y prettier en `frontend/eslint.config.js` (ESLint 9 usa config plana, no `.eslintrc.cjs`) y `frontend/.prettierrc` (depende de T003)

---

## Phase 2: Foundational (bloqueante para todas las historias)

**Propósito**: esquema completo de base de datos, conexión a PostgreSQL nativo en el puerto 5442, y tokens de diseño.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T006 Configurar `DATABASE_URL` hacia PostgreSQL nativo puerto 5442 en `backend/rasero/configuracion.py`, sin ninguna rama de SQLite (depende de T002)
- [X] T007 Inicializar Alembic en `backend/migraciones/alembic.ini` apuntando a T006 (depende de T006)
- [X] T008 Crear `backend/migraciones/versions/0001_esquema_inicial.py` con las 20 tablas de data-model.md, tipos `NUMERIC`/`INTEGER`/`TIMESTAMPTZ` exactos, `moneda CHAR(3) NOT NULL DEFAULT 'USD'` en `venta`, `renglon_venta`, `lote`, `producto`, `producto_precio_sucursal` y `observacion_precio`, los `CHECK` de origen único y cantidad positiva, y `downgrade` implementado (depende de T007)
- [X] T009 [P] Crear los modelos SQLAlchemy 2.x de las 20 tablas en `backend/rasero/persistencia/modelos.py` (depende de T008)
- [X] T010 [P] Configurar engine y sesión en `backend/rasero/persistencia/sesion.py` (depende de T006)
- [X] T011 Crear el esqueleto FastAPI con enrutador base y manejo de errores sin trazas técnicas en `backend/rasero/api/aplicacion.py` (depende de T002)
- [X] T012 [P] Crear datos semilla de "Despensa Los Ríos" (sucursales "Quevedo Centro" y "Buena Fe") en `backend/rasero/semilla.py`, el nombre solo como valor de fila (depende de T009)
- [X] T013 [P] Crear `frontend/src/estilos/tokens.css` con la paleta (#F1F4F1, #FFFFFF, #1B2621, #5A6862, #0F5132, #D5DCD6, #9A5B08, #8E2A2A, #1F5673) y radios 2px/6px como variables CSS (depende de T003)
- [X] T014 [P] Cargar IBM Plex Sans (cifras tabulares) y Source Serif 4 en `frontend/index.html` y declararlas en `frontend/src/estilos/tokens.css`; sin Inter (depende de T013)
- [X] T015 Ejecutar el paso `teach` de Impeccable con el contenido íntegro de la sección "Sistema de Diseño" de la constitución (paleta, tipografía por registro, radios, regla de tres portadores, los dos registros visuales), generando `PRODUCT.md` y `DESIGN.md` en la raíz de `frontend/`. Precede a toda tarea de frontend; omitirlo hace que la herramienta derive a sus valores por defecto genéricos (depende de T013, T014)
- [X] T016 Crear el cliente HTTP base en `frontend/src/servicios/clienteHttp.ts` (depende de T015, T011)

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Registrar una venta en caja (Priority: P1) 🎯 MVP

**Goal**: cobrar una venta mixta (unidad y peso), atribuida a operador y terminal, idempotente ante reintentos, sin bloquearse aunque exceda el saldo.

**Independent Test**: con catálogo y existencias precargadas, abrir turno, cobrar una venta mixta y verificar el descuento de existencias, la atribución a operador y terminal, y que un reintento con la misma clave no genera una segunda venta.

### Pruebas obligatorias para User Story 1

- [X] T017 [P] [US1] Prueba unitaria de totales de venta con producto a peso y redondeo a 2 decimales (suma de importes ya redondeados, no redondeo de la suma) en `tests/unidad/test_totales_venta.py`
- [X] T018 [P] [US1] Prueba unitaria de selección FEFO, incluido lote posterior que caduca antes que uno más antiguo, en `tests/unidad/test_seleccion_fefo.py`
- [X] T019 [P] [US1] Prueba de integración de idempotencia: diez reintentos con la misma `clave_idempotencia` producen una sola venta, en `tests/integracion/test_idempotencia_venta.py`
- [X] T020 [P] [US1] Prueba de integración de saldo: `existencia` coincide con la suma de `movimiento_inventario`, incluido saldo negativo, en `tests/integracion/test_saldo_existencia.py`

### Implementación backend para User Story 1

- [X] T021 [P] [US1] Prueba unitaria de resolución de precio efectivo por sucursal: override de `producto_precio_sucursal` si existe, si no el precio base del producto, en `tests/unidad/test_resolucion_precio.py`
- [X] T022 [P] [US1] Regla de dominio de resolución de precio efectivo por sucursal (`COALESCE` override/base) en `backend/rasero/dominio/resolucion_precio.py` (implementa T021)
- [X] T023 [P] [US1] Regla de dominio de totales con `Decimal` y `ROUND_HALF_UP` en `backend/rasero/dominio/totales.py` (implementa T017)
- [X] T024 [P] [US1] Regla de dominio de selección de lote por `fecha_caducidad NULLS LAST, instante_entrada` en `backend/rasero/dominio/seleccion_lote.py` (implementa T018)
- [X] T025 [US1] Servicio de apertura y cierre de turno con verificación de PIN contra `operador.pin_hash` en `backend/rasero/servicios/turnos.py` (depende de T009)
- [X] T026 [US1] Servicio de registro de venta: transacción atómica, resolución de precio efectivo por sucursal, consumo FEFO con `SELECT FOR UPDATE`, actualización de `existencia` por delta, saldo negativo admitido, en `backend/rasero/servicios/ventas.py` (depende de T022, T023, T024, T025)
- [X] T027 [US1] Servicio de anulación de venta: turno propio o `operador.es_encargado`, repone existencia en el lote de origen, en `backend/rasero/servicios/ventas.py` (depende de T026)
- [X] T028 [US1] Endpoint `POST /turnos` en `backend/rasero/api/turnos.py` (depende de T025)
- [X] T029 [US1] Endpoint `POST /turnos/{id_turno}/cierre` en `backend/rasero/api/turnos.py` (depende de T028)
- [X] T030 [US1] Endpoint `POST /ventas` con validación de `clave_idempotencia` (200 en reintento, 201 en la primera) en `backend/rasero/api/ventas.py` (depende de T026)
- [X] T031 [US1] Endpoint `GET /ventas/{id_venta}` en `backend/rasero/api/ventas.py` (depende de T030)
- [X] T032 [US1] Endpoint `POST /ventas/{id_venta}/anulacion` en `backend/rasero/api/ventas.py` (depende de T027, T030)
- [X] T033 [P] [US1] Prueba de contrato de `POST /ventas` contra el esquema `Venta` de contracts/openapi.yaml en `tests/contrato/test_contrato_ventas.py` (depende de T030)

- [X] T034 [P] [US1] Servicio de catálogo: lista de productos activos con precio efectivo resuelto por sucursal, reutilizando la regla de T022 (`COALESCE` override/base), en `backend/rasero/servicios/catalogo.py` (depende de T009, T022)
- [X] T035 [US1] Endpoint `GET /productos` con `id_sucursal` opcional, añadido a contracts/openapi.yaml porque US1 necesita listar el catálogo para construir una venta y el contrato no exponía ninguna lectura de `producto`, en `backend/rasero/api/productos.py` (depende de T034)

- [X] T036 [P] [US1] Servicio de listado de operadores activos (sin `pin_hash`) en `backend/rasero/servicios/operadores.py` (depende de T009)
- [X] T037 [US1] Endpoint `GET /operadores` añadido a contracts/openapi.yaml porque FR-005 exige elegir operador "de una lista" y el contrato no lo exponía, en `backend/rasero/api/operadores.py` (depende de T036)

### Implementación frontend para User Story 1

- [X] T038 [P] [US1] Componente de apertura de turno (selector de operador + PIN de 4 dígitos) en `frontend/src/componentes/AperturaTurno.tsx` (depende de T015, T013)
- [X] T039 [P] [US1] Pantalla de venta: tabla como elemento principal, sin tarjetas, radio 2px, cifras tabulares, en `frontend/src/pantallas/Venta.tsx` (depende de T015, T013)
- [X] T040 [US1] Componente de renglón a granel: captura en kg, conversión a gramos enteros, en `frontend/src/componentes/RenglonGranel.tsx` (depende de T015, T039)
- [X] T041 [US1] Servicio de cliente para `POST /ventas`, generando `clave_idempotencia` antes del primer intento, en `frontend/src/servicios/ventas.ts` (depende de T015, T016, T030)
- [X] T042 [US1] Animación de confirmación al cerrar el cobro, única animación del registro de Operación, en `frontend/src/pantallas/Venta.tsx` (depende de T015, T039)
- [X] T043 [US1] Acción de anulación de venta desde la pantalla de venta, con mensaje de acción correctiva si el turno está cerrado y el operador no es encargado, en `frontend/src/pantallas/Venta.tsx` (depende de T015, T032, T041)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente. MVP.

---

## Phase 4: User Story 2 - Recibir mercancía del proveedor en lotes (Priority: P2)

**Goal**: registrar una entrada de compra que crea o alimenta un lote con su costo y, si aplica, su fecha de caducidad.

**Independent Test**: registrar una compra de tres productos, uno perecedero, y verificar que se crean los lotes con costo y caducidad, y que las existencias suben.

- [X] T044 [P] [US2] Prueba de integración: una entrada crea el lote con costo y caducidad y sube la existencia, en `tests/integracion/test_entrada_inventario.py`
- [X] T045 [US2] Servicio de registro de entrada de inventario, crea o alimenta lote, solo costo, nunca margen, en `backend/rasero/servicios/inventario.py` (depende de T009)
- [X] T046 [US2] Endpoint `POST /entradas-inventario` en `backend/rasero/api/inventario.py` (depende de T045)
- [X] T047 [P] [US2] Endpoint `GET /existencias`, exponiendo el saldo incluido negativo, en `backend/rasero/api/inventario.py` (depende de T009)
- [X] T048 [P] [US2] Pantalla de registro de entrada (producto, cantidad, costo, caducidad opcional) en `frontend/src/pantallas/EntradaInventario.tsx` (depende de T015, T013)
- [X] T049 [US2] Servicio de cliente para `POST /entradas-inventario` en `frontend/src/servicios/inventario.ts` (depende de T015, T016, T046)

**Checkpoint**: User Story 2 funcional junto con User Story 1.

---

## Phase 5: User Story 3 - Registrar una consulta no atendida (Priority: P3)

**Goal**: registrar en dos toques, sin datos del cliente, que un producto se consultó y no se vendió.

**Independent Test**: desde la pantalla de venta, marcar un producto agotado como consultado y no atendido, y verificar producto, sucursal, instante y saldo del momento.

- [X] T050 [P] [US3] Prueba de integración: la consulta registra el saldo del instante y no acepta ningún campo de cliente, en `tests/integracion/test_consulta_no_atendida.py`
- [X] T051 [US3] Servicio de registro de consulta no atendida, congelando `saldo_en_el_instante`, en `backend/rasero/servicios/senales.py` (depende de T009)
- [X] T052 [US3] Endpoint `POST /consultas-no-atendidas` en `backend/rasero/api/senales.py` (depende de T051)
- [X] T053 [US3] Acción de dos toques "consulta no atendida" en la pantalla de venta, sin pedir datos del cliente, en `frontend/src/pantallas/Venta.tsx` (depende de T015, T039, T052)

**Checkpoint**: User Story 3 funcional junto con las anteriores.

---

## Phase 6: User Story 4 - Comparar el precio propio contra la competencia (Priority: P4)

**Goal**: capturar observaciones de precio de competencia y compararlas contra el precio propio, con su antigüedad siempre visible.

**Independent Test**: capturar tres observaciones de canales distintos, una en otra presentación, y verificar la comparación normalizada con antigüedad por observación.

- [X] T054 [P] [US4] Prueba unitaria de normalización a precio por unidad de medida y de `comparable = false` cuando no aplica, en `tests/unidad/test_normalizacion_precio.py`
- [X] T055 [P] [US4] Prueba de integración: el catálogo de canales evita duplicados por nombre normalizado, en `tests/integracion/test_canal_competencia.py`
- [X] T056 [P] [US4] Servicio de catálogo de canales de competencia (crear o devolver existente) en `backend/rasero/servicios/competencia.py` (depende de T009)
- [X] T057 [US4] Servicio de captura de observación de precio, `origen_captura` limitado a manual/archivo, en `backend/rasero/servicios/competencia.py` (depende de T056)
- [X] T058 [P] [US4] Regla de dominio de normalización y antigüedad calculada al leer en `backend/rasero/dominio/comparacion_precios.py` (implementa T054)
- [X] T059 [US4] Endpoint `GET/POST /canales-competencia` en `backend/rasero/api/competencia.py` (depende de T056)
- [X] T060 [US4] Endpoint `POST /observaciones-precio` en `backend/rasero/api/competencia.py` (depende de T057)
- [X] T061 [US4] Endpoint `GET /productos/{id_producto}/comparacion-precios` con `id_sucursal` obligatorio, resolviendo el precio propio con la regla de T022, en `backend/rasero/api/competencia.py` (depende de T022, T058)
- [X] T062 [P] [US4] Pantalla de captura de observación de precio en `frontend/src/pantallas/ObservacionPrecio.tsx` (depende de T015, T013)
- [X] T063 [US4] Componente de antigüedad con tres portadores (color, forma, texto), nunca solo color, en `frontend/src/componentes/AntiguedadDato.tsx` (depende de T015, T013)
- [X] T064 [US4] Pantalla de comparación de precios, registro de Análisis, radio 6px, Source Serif 4, sin ajustar precios, en `frontend/src/pantallas/ComparacionPrecios.tsx` (depende de T015, T061, T063)

**Checkpoint**: User Story 4 funcional junto con las anteriores.

---

## Phase 7: User Story 5 - Cuadrar el inventario con un conteo físico (Priority: P5)

**Goal**: iniciar un conteo, capturar cantidades contadas y ver la diferencia bruta por producto y lote, sin clasificar su causa.

**Independent Test**: iniciar un conteo sobre un subconjunto de productos, capturar diferencias y verificar el ajuste trazable al conteo.

- [X] T065 [P] [US5] Prueba de integración: al resolver un conteo, cada diferencia genera un `ajuste_conteo` trazable y el saldo anterior sigue siendo reconstruible, en `tests/integracion/test_conteo_fisico.py`
- [X] T066 [US5] Servicio de inicio de conteo físico con alcance opcional en `backend/rasero/servicios/conteos.py` (depende de T009)
- [X] T067 [US5] Servicio de resolución de conteo: diferencia por producto y lote sin clasificar, genera el ajuste, en `backend/rasero/servicios/conteos.py` (depende de T066)
- [X] T068 [US5] Endpoint `POST /conteos-fisicos` en `backend/rasero/api/conteos.py` (depende de T066)
- [X] T069 [US5] Endpoint `POST /conteos-fisicos/{id_conteo_fisico}/resolucion` en `backend/rasero/api/conteos.py` (depende de T067)
- [X] T070 [P] [US5] Pantalla de inicio de conteo con selección de alcance en `frontend/src/pantallas/ConteoFisico.tsx` (depende de T015, T013)
- [X] T071 [US5] Pantalla de captura y resolución de conteo, mostrando la diferencia por producto y lote, en `frontend/src/pantallas/ResolucionConteo.tsx` (depende de T015, T069)

**Checkpoint**: User Story 5 funcional junto con las anteriores.

---

## Phase 8: User Story 6 - Traspasar mercancía entre las dos sucursales (Priority: P6)

**Goal**: despachar un traspaso, mantener la mercancía en tránsito sin que desaparezca del total, y confirmar la recepción exponiendo cualquier discrepancia.

**Independent Test**: despachar un traspaso, verificar que el inventario total no cambia mientras está en tránsito, y confirmar la recepción.

- [X] T072 [P] [US6] Prueba de integración: la existencia total del sistema es idéntica antes y después de despachar un traspaso, en `tests/integracion/test_traspaso_invariante.py`
- [X] T073 [P] [US6] Prueba de integración: una recepción distinta de lo despachado expone la discrepancia por producto sin clasificarla, en `tests/integracion/test_traspaso_discrepancia.py`
- [X] T074 [US6] Servicio de despacho: crea `traspaso` y sus movimientos `salida_traspaso` en `backend/rasero/servicios/traspasos.py` (depende de T009)
- [X] T075 [US6] Servicio de recepción: crea movimientos `entrada_traspaso` conservando costo y caducidad del lote de origen, calcula discrepancia, en `backend/rasero/servicios/traspasos.py` (depende de T074)
- [X] T076 [US6] Endpoint `POST /traspasos` en `backend/rasero/api/traspasos.py` (depende de T074)
- [X] T077 [US6] Endpoint `POST /traspasos/{id_traspaso}/recepcion` en `backend/rasero/api/traspasos.py` (depende de T075)
- [X] T078 [P] [US6] Pantalla de despacho de traspaso en `frontend/src/pantallas/DespachoTraspaso.tsx` (depende de T015, T013)
- [X] T079 [US6] Pantalla de recepción de traspaso, mostrando la discrepancia cuando exista, en `frontend/src/pantallas/RecepcionTraspaso.tsx` (depende de T015, T077)

**Checkpoint**: User Story 6 funcional junto con las anteriores.

---

## Phase 9: User Story 7 - Ver el capital inmovilizado (Priority: P7)

**Goal**: listar los lotes cuya última salida excede el umbral de su categoría, con su valor, sin proponer ninguna acción.

**Independent Test**: con lotes de categorías y antigüedades distintas, verificar que el listado señala exactamente los que superan el umbral de su categoría.

- [X] T080 [P] [US7] Prueba de integración: umbral corto señala, umbral largo no señala, categoría sin umbral hereda el global, lote sin costo aparece no calculable, en `tests/integracion/test_capital_inmovilizado.py`
- [X] T081 [US7] Consulta de capital inmovilizado con `COALESCE(categoria.dias_umbral_inmovilizado, umbral_global)` y `cantidad_restante × costo_unitario` en `backend/rasero/servicios/inventario.py` (depende de T009)
- [X] T082 [US7] Endpoint `GET /capital-inmovilizado` en `backend/rasero/api/inventario.py` (depende de T081)
- [X] T083 [US7] Pantalla de listado de capital inmovilizado, de solo lectura, sin ninguna acción, en `frontend/src/pantallas/CapitalInmovilizado.tsx` (depende de T015, T082)

**Checkpoint**: User Story 7 funcional junto con las anteriores.

---

## Phase 10: User Story 8 - Sincronizar lo trabajado sin conexión (Priority: P8)

**Goal**: aplicar en el servidor, en orden de marca de tiempo de origen, las operaciones registradas sin conectividad, resolviendo conflictos sin ocultar la operación desplazada.

**Independent Test**: desconectar la red, registrar operaciones, reconectar y verificar que suben en orden y que ninguna se pierde.

> Nota constitucional (v2.0.2, Principio II): esta historia no es opcional pese a ir última en secuencia. Mientras no esté entregada, cualquier demostración depende de conectividad continua y debe declararlo.

- [X] T084 [P] [US8] Prueba de integración: dos operaciones en conflicto resuelven por la marca de tiempo más antigua en ambas direcciones, y la desplazada queda visible en `conflicto_resuelto`, en `tests/integracion/test_reconciliacion_offline.py`
- [X] T085 [US8] Servicio de sincronización: ordena por `marca_tiempo_origen` ascendente y resuelve conflictos por `recurso_afectado` en ambas direcciones, en `backend/rasero/servicios/sincronizacion.py` (depende de T009)
- [X] T086 [US8] Endpoint `POST /operaciones-pendientes/sincronizacion` en `backend/rasero/api/sincronizacion.py` (depende de T085)
- [X] T087 [P] [US8] Cola local de operaciones pendientes (IndexedDB) con `marca_tiempo_origen` generada en el dispositivo, en `frontend/src/servicios/colaOffline.ts` (depende de T015, T016)
- [X] T088 [US8] Disparador de sincronización al recuperar conectividad, contra el endpoint de T086, en `frontend/src/servicios/colaOffline.ts` (depende de T015, T086, T087)

**Checkpoint**: las 8 historias de usuario funcionan de forma independiente.

---

## Phase 11: User Story 9 - Corregir el carrito antes de cobrar (Priority: P9)

**Goal**: que el cajero edite la cantidad/peso de un renglón del carrito o lo elimine, antes de
"Cobrar", con recálculo inmediato del total y sin endpoint nuevo.

**Independent Test**: con un carrito de varios renglones sin cobrar, editar la cantidad de uno y
eliminar otro; el total refleja de inmediato ambos cambios y la venta cobrada contiene exactamente
lo que quedó en pantalla.

> Añadida por auditoría de uso posterior a la certificación de US1. Es estrictamente anterior a la
> confirmación del cobro: el carrito, hasta "Cobrar", es estado local de `Venta.tsx`
> (`renglones` en `useState`), verificado — no se persiste nada en backend antes de confirmar. Por
> eso US9 **no toca backend**, no reabre el checkpoint de US1 y no tiene pruebas de `tests/`
> (la interfaz está exenta por el Principio III, igual que el resto del frontend de 001).

- [X] T093 [US9] Control de eliminar por renglón (ícono papelera SVG de línea, Regla del Ícono) al final de cada fila del carrito, sin confirmación, en `frontend/src/pantallas/Venta.tsx` (FR-051; depende de T043)
- [X] T094 [US9] Edición inline de cantidad/peso de un renglón del carrito reusando el mismo patrón de input que al agregar el producto (`RenglonGranel` para granel), con recálculo del importe del renglón y del total al vuelo, en `frontend/src/pantallas/Venta.tsx` (FR-052; depende de T093)
- [X] T095 [US9] Verificar que "Cobrar" queda deshabilitado cuando el carrito queda vacío o sin renglón válido tras editar, y que la venta enviada usa los renglones/cantidades resultantes (FR-053), en `frontend/src/pantallas/Venta.tsx`

**Checkpoint**: User Story 9 funcional junto con las anteriores; US1 intacta.

---

## Phase 12: User Story 10 - Roles de operador, sucursal fija y autorización centralizada (Priority: P10)

**Goal**: `operador` gana `id_sucursal` (FK, uno-a-uno) y `rol` (ENUM `cajero`/`encargado`/`admin`)
en reemplazo de `es_encargado`; la autorización pasa por un mecanismo central de backend
(`requiere_rol`) y un hook único de frontend (`useRol`); la navegación oculta lo que el rol no
puede usar; `admin` gestiona operadores.

**Independent Test**: ver User Story 10 de spec.md (escenarios 1–9).

> Ejerce el Principio VI (enmienda constitucional **v2.3.0**). Toca `operador` y `turno`,
> entidades certificadas de US1 — de ahí las tareas de línea base de pruebas antes y después de
> la migración. Es autorización, no autenticación: el PIN + hash (FR-006) no cambia.

### Línea base (antes de tocar el modelo)

- [X] T096 [US10] Correr la suite completa (`backend/.venv/Scripts/pytest tests`) y registrar el resultado como línea base en el mensaje de commit / PR: qué pasa hoy, antes del cambio de esquema
- [X] T097 [US10] Grep de línea base: listar toda referencia a `es_encargado` y a `_encargado_o_error` en `backend/` y `frontend/src/`, y todo endpoint sin ningún control de identidad de operador, para el resumen final (FR-057, spec §B4)

### Migración de datos

- [X] T098 [US10] Migración de Alembic en `backend/migraciones/versions/` que: añade `operador.id_sucursal` (FK → `sucursal`, NOT NULL) y `operador.rol` (`TEXT NOT NULL CHECK (rol IN ('cajero','encargado','admin'))`); convierte datos con **comentario explícito de la regla**: `es_encargado=FALSE → 'cajero'`, `es_encargado=TRUE → 'encargado'`, ningún `admin`; deriva `id_sucursal` del último turno del operador o de la primera sucursal activa; elimina la columna `es_encargado`; incluye `downgrade()` que revierte (recrea `es_encargado`, `'encargado'/'admin' → TRUE`, resto `FALSE`, elimina `rol` e `id_sucursal`) (FR-054, FR-055, FR-056)
- [X] T099 [US10] Actualizar `backend/rasero/persistencia/modelos.py`: `Operador` gana `id_sucursal: Mapped[int]` (FK, nullable=False) y `rol: Mapped[str]` con `CheckConstraint`; se retira `es_encargado` (depende de T098)

### Backend — mecanismo central

- [X] T100 [US10] Extender `backend/rasero/seguridad.py` (NO duplicarlo) con `RANGO_ROL` (jerarquía `cajero`<`encargado`<`admin`) y `requiere_rol(sesion, id_operador, rol_minimo) -> Operador`: resuelve el operador, valida existencia y `activo`, valida `rol >= rol_minimo`; levanta el `ErrorDominio` apropiado con los códigos ya existentes del sistema (reutiliza `ErrorAdministracion` / `ErrorPagos` según el router; no inventa tipo nuevo) (FR-057; depende de T099)
- [X] T101 [US10] Factory de dependency de FastAPI en `backend/rasero/seguridad.py` (o `api/dependencias.py` si encaja mejor con el patrón): `exige_rol(rol_minimo)` devuelve una dependency que lee `id_operador` del cuerpo/query igual que hoy y llama `requiere_rol` (FR-057; depende de T100)
- [X] T102 [P] [US10] Reemplazar `_encargado_o_error` en `backend/rasero/servicios/administracion.py` por `requiere_rol(..., "encargado")`; eliminar la función local (FR-057, FR-058; depende de T100)
- [X] T103 [P] [US10] Ídem en `backend/rasero/servicios/cobertura_pago.py` (FR-057, FR-058; depende de T100)
- [X] T104 [P] [US10] Ídem en `backend/rasero/servicios/terminales_pago.py` (FR-057, FR-058; depende de T100)
- [X] T105 [US10] `backend/rasero/servicios/ventas.py` / anulación: la anulación de venta de turno cerrado pasa a `requiere_rol(..., "encargado")` (data-model.md, regla de autorización FR-049; depende de T100)
- [X] T106 [US10] Restricción de sucursal en `backend/rasero/servicios/turnos.py::abrir_turno`: si `operador.rol` ∈ {`cajero`,`encargado`} y `id_sucursal != operador.id_sucursal` → `ErrorDominio` `{codigo: "turno_sucursal_no_asignada", mensaje: "Este operador está asignado a [sucursal], no puede abrir turno en otra sucursal."}`; `admin` sin restricción (FR-060, FR-061; depende de T099)

### Backend — gestión de operadores (admin-only)

- [X] T107 [US10] `backend/rasero/servicios/operadores.py`: `crear_operador`, `actualizar_operador` (nombre, rol, id_sucursal), `fijar_activo_operador`, todos tras `requiere_rol(..., "admin")`; valida sucursal existente y rol del ENUM; `listar_operadores_activos` devuelve `rol` e `id_sucursal` (no `pin_hash`) (FR-059; depende de T100)
- [X] T108 [US10] `backend/rasero/api/operadores.py`: `GET /operadores` devuelve `rol`/`id_sucursal`; `POST /operadores`, `PUT /operadores/{id}`, `POST /operadores/{id}/activo` con la dependency `exige_rol("admin")` (FR-059; depende de T101, T107)

### Backend — pruebas obligatorias (contrato + transición de estado, Principio III)

- [X] T109 [US10] `tests/integracion/test_autorizacion.py`: `requiere_rol` acepta/rechaza por jerarquía; un `cajero` y un `encargado` son rechazados en acciones de admin; un `encargado` puede administrar maestros; operador inactivo rechazado (FR-057, FR-058, FR-059)
- [X] T110 [US10] `tests/integracion/test_turno_sucursal.py`: `cajero`/`encargado` sólo abren turno en su sucursal (código y mensaje exactos); `admin` abre en cualquiera (FR-060, FR-061)
- [X] T111 [US10] `tests/integracion/test_migracion_operador.py` (o extensión de una suite existente): tras migrar la semilla, `Ana Cajera → cajero`, `Luis Encargado → encargado`, 0 `admin` automáticos, toda `id_sucursal` no nula (FR-056, SC-012)
- [X] T112 [US10] Actualizar las suites que asumían el modelo viejo (`tests/integracion/test_administracion.py`, `test_cobertura.py`, `test_terminales.py`, `tests/apoyo*.py`, `test_quickstart_001.py`): `Operador(es_encargado=…)` → `Operador(rol=…, id_sucursal=…)`. Documentar en el commit cuáles se tocaron y por qué (test que asumía el modelo viejo, no regresión)

### Frontend — hook y ocultamiento

- [X] T113 [US10] `frontend/src/hooks/useRol.ts`: consume la fuente de verdad existente del operador del turno (hoy `App.tsx` estado `esEncargado`); expone `rol`, `puedeVer(rolMinimo)`, `esAdmin()`, `esEncargadoOMas()`. Migrar `App.tsx` para exponer `rol`/`id_sucursal` del operador en vez de `esEncargado` (FR-062)
- [X] T114 [US10] `frontend/src/servicios/operadores.ts`: tipo `Operador` con `rol`/`id_sucursal` (quitar `es_encargado`); funciones `crearOperador`, `actualizarOperador`, `fijarActivoOperador` (FR-059, FR-062)
- [X] T115 [P] [US10] Migrar toda lectura de `es_encargado` en `frontend/src/`: `App.tsx` (nav "Administración"), `pantallas/Administracion.tsx`, `componentes/CrearProductoModal.tsx` y el atajo "+ Crear producto" en `pantallas/Venta.tsx` → consumir `useRol` (`esEncargadoOMas()`) (FR-062, SC-013)
- [X] T116 [US10] Nav global: ítem "Administración" oculto si `!esEncargadoOMas()`; ningún ítem de encargado/admin renderizado para `cajero` (FR-062, SC-014)
- [X] T117 [US10] `frontend/src/pantallas/AperturaTurno.tsx`: selector de sucursal sólo visible si `esAdmin()`; para `cajero`/`encargado` la sucursal se fija a `operador.id_sucursal` (nombre mostrado como texto, no selector) (FR-060)

### Frontend — 6.ª pestaña de Administración (admin-only)

- [X] T118 [US10] `frontend/src/pantallas/Administracion.tsx`: 6.ª pestaña segmentada "Operadores", presente en el segmentado **sólo si** `esAdmin()` (para `encargado` no aparece). Lista de operadores con rol y sucursal, acciones Editar/Desactivar (FR-059, FR-062)
- [X] T119 [US10] Alta/edición de operador con `frontend/src/componentes/ModalAdministrable.tsx` (componente existente, La Regla del Modal Administrable): campos nombre, selector de sucursal (obligatorio) y selector de rol `cajero`/`encargado`/`admin` (obligatorio) (FR-059)

### Semilla

- [X] T120 [US10] `backend/rasero/semilla.py`: `Ana Cajera` con `rol="cajero"`, `id_sucursal=quevedo`; `Luis Encargado` con `rol="encargado"`, `id_sucursal=quevedo`; **nuevo** `Marta Administradora` con `rol="admin"`, `id_sucursal=quevedo`, `pin_hash` como los demás. Actualizar los `print` del resumen. Ídem cualquier `Operador(...)` en `semilla_reactivacion.py` u otras semillas

### Cierre

- [X] T121 [US10] Volver a correr la suite completa; comparar con la línea base de T096. Todo lo que pasaba antes pasa después, o está documentado como test actualizado (T112) — ninguna regresión real sin corregir
- [X] T122 [US10] Grep final: `es_encargado` no aparece en ningún archivo de `backend/` ni `frontend/src/`; `_encargado_o_error` eliminada; `requiere_rol` es la única vía de verificación de rol en backend (SC-013)

**Checkpoint**: User Story 10 funcional junto con las anteriores; US1 y el resto intactos; migración reversible verificada.

---

## Phase 13: User Story 11 - Sesión de turno con token verificable (Priority: P11)

**Goal**: la identidad del operador en cada petición sujeta a rol se deriva de un token de sesión
de turno (JWT HS256 emitido en `POST /turnos` tras validar el PIN), no del `id_operador` del
cuerpo. Verificación centralizada en `backend/rasero/seguridad.py` (dependency `operador_de_sesion`);
doble invalidación (expiración a 12 h + cierre de turno) + rechazo inmediato de operador
desactivado. **Sin migración ni cambio de esquema.**

**Independent Test**: ver User Story 11 de spec.md (escenarios 1–9).

> Ejerce la sub-sección "Identidad de sesión" del Principio VI (enmienda constitucional
> **v2.4.0**). Corrige una brecha de US10 heredada de `007-pagos-seguridad`. Cambia el mecanismo
> central de autorización — de ahí la línea base de pruebas antes y después.

### Línea base y dependencia

- [X] T123 [US11] Correr la suite completa (`backend/.venv/Scripts/pytest tests`) y registrar el resultado como línea base en el commit/PR (línea base conocida: 401 passed)
- [X] T124 [US11] `backend/pyproject.toml`: añadir `pyjwt>=2.9` a `dependencies`; `pip install -e .` en el venv. `backend/rasero/configuracion.py`: `JWT_SECRET_KEY` (default sólo de desarrollo, override por entorno, mismo patrón que `DATABASE_URL`) y `JWT_HORAS_EXPIRACION = 12` (FR-069, FR-072)

### Backend — mecanismo central de sesión

- [X] T125 [US11] `backend/rasero/errores.py`: `SesionInvalida` (`codigo="sesion_invalida"`, 401) y `SesionExpirada` (`codigo="sesion_expirada"`, 401), ambas `ErrorDominio`, mensaje "Tu turno expiró o fue cerrado. Abre turno de nuevo." — verificar que no colisionan con códigos existentes (FR-068)
- [X] T126 [US11] `backend/rasero/seguridad.py`: `emitir_token_turno(*, id_operador, id_turno, rol) -> str` (JWT HS256, claims `id_operador`/`id_turno`/`rol`/`exp`/`iat`, `exp = now + JWT_HORAS_EXPIRACION`) (FR-065, FR-066)
- [X] T127 [US11] `backend/rasero/seguridad.py`: dependency `operador_de_sesion(authorization: str = Header(...), sesion) -> Operador` — parsea `Bearer`, `jwt.decode` (firma + `exp`); `ExpiredSignatureError → SesionExpirada`; cualquier otro `InvalidTokenError` o header ausente/mal formado → `SesionInvalida`; carga `Turno` del claim → si `None` o `instante_cierre is not None` → `SesionInvalida`; carga `Operador` del claim → si `None` o `not activo` → `SesionInvalida`; devuelve el `Operador` (FR-067, FR-068)
- [X] T128 [US11] `backend/rasero/seguridad.py`: `requiere_rol` cambia su firma a `requiere_rol(operador: Operador, rol_minimo: str) -> Operador` (chequeo de rango puro; `OperadorInvalido` si `not activo`, `RolInsuficiente` si rango insuficiente). `exige_rol(rol_minimo)` se recompone: `Depends(operador_de_sesion)` → `requiere_rol(operador, rol_minimo)` (FR-067; depende de T127)
- [X] T129 [US11] `backend/rasero/api/turnos.py`: `abrir_turno` llama `emitir_token_turno` tras el `commit` y añade `token` a `TurnoRespuesta`. `POST /turnos/{id}/cierre` sin cambios (ya deja `instante_cierre`; sigue sin exigir token) (FR-065, FR-069; depende de T126)

### Backend — migrar los routers/servicios sujetos a rol a la nueva identidad

- [X] T130 [P] [US11] `backend/rasero/servicios/administracion.py`: las funciones `crear_*`/`actualizar_*`/`fijar_activo` reciben `operador: Operador` en vez de `id_operador: int`; `requiere_rol(operador, "encargado")`. `backend/rasero/api/administracion.py`: `operador: Operador = Depends(exige_rol("encargado"))`; retirar `id_operador` de los schemas de cuerpo (FR-067; depende de T128)
- [X] T131 [P] [US11] Ídem `backend/rasero/servicios/cobertura_pago.py` + `backend/rasero/servicios/terminales_pago.py` y `backend/rasero/api/pagos.py` (`PUT /pagos/cobertura`, `POST /pagos/terminales`, `PATCH /pagos/terminales/{id}`, `POST /pagos/terminales/{id}/firmware`): identidad del token; retirar `id_operador` del cuerpo; usar `operador.id_operador` donde se registra en bitácora (FR-067; depende de T128)
- [X] T132 [P] [US11] `backend/rasero/api/operadores.py` + `servicios/operadores.py`: `POST /operadores`, `PUT /operadores/{id}`, `POST /operadores/{id}/activo` → `Depends(exige_rol("admin"))`; retirar `id_operador_solicitante` del cuerpo (FR-067; depende de T128)
- [X] T133 [US11] `backend/rasero/api/ventas.py` + `servicios/ventas.py::anular_venta`: `POST /ventas/{id}/anulacion` deriva `id_operador_ejecuta` de `Depends(operador_de_sesion)` (no exige rol mínimo — un `cajero` puede anular su propia venta de turno abierto); retirar `id_operador` del cuerpo `AnulacionNueva`. La `anulacion_venta` sigue guardando ese id como auditoría (FR-067; depende de T127)
- [X] T134 [US11] `backend/rasero/api/aplicacion.py`: verificar que el `exception_handler(ErrorDominio)` ya cubre `SesionInvalida`/`SesionExpirada` (mismo formato `{codigo, mensaje}`, status del error). Ajuste sólo si hace falta

### Backend — pruebas obligatorias (Principio III: contrato de autorización + transición de estado)

- [X] T135 [US11] `tests/integracion/test_sesion_turno.py`: **regresión del hallazgo** — `cajero` autenticado con su token + `id_operador` de `admin` en el cuerpo de `POST /operadores` → `403 rol_insuficiente` (el cuerpo no tuvo efecto) (SC-015, FR-067)
- [X] T136 [US11] `test_sesion_turno.py`: token sin firmar / ausente → `401 sesion_invalida`; token con `exp` pasado → `401 sesion_expirada`; token de turno con `instante_cierre` no nulo → `401 sesion_invalida`; token de operador desactivado tras emisión → `401 sesion_invalida` (FR-068, SC-016)
- [X] T137 [US11] `test_sesion_turno.py`: happy path — abrir turno devuelve `token`; usar el token en un endpoint `encargado` → `201`; identidad registrada = la del token (FR-065, FR-067)
- [X] T138 [US11] Actualizar las suites que enviaban `id_operador` en el cuerpo o llamaban `requiere_rol(sesion, id, rol)` (`tests/integracion/test_autorizacion.py`, `test_turno_sucursal.py`, `test_administracion.py`, `test_cobertura.py`, `test_terminales.py`, `test_contrato_pagos.py`, `tests/apoyo*.py`): helper de apoyo que abre turno y devuelve el header `Authorization`; `requiere_rol` con `Operador`. Documentar en el commit cuáles y por qué (contrato cambiado, no regresión)

### Frontend — token en memoria y header automático

- [X] T139 [US11] `frontend/src/servicios/turnos.ts`: `Turno` gana `token: string`; `abrirTurno` lo devuelve
- [X] T140 [US11] `frontend/src/servicios/clienteHttp.ts`: registro en memoria del token de sesión (`fijarTokenSesion` / `limpiarTokenSesion`); `peticion` adjunta `Authorization: Bearer` cuando hay token; un `401` con `codigo` ∈ {`sesion_invalida`,`sesion_expirada`} dispara un callback de "sesión perdida" (FR-070, FR-071)
- [X] T141 [US11] `frontend/src/App.tsx`: guardar `turno.token` en el estado junto al `Turno`; `fijarTokenSesion` al abrir, `limpiarTokenSesion` al cerrar; registrar el callback de sesión perdida que hace `setTurno(null)` y muestra "Tu turno expiró o fue cerrado. Abre turno de nuevo." en la pantalla de apertura (FR-070, FR-071)
- [X] T142 [P] [US11] Retirar `id_operador` / `id_operador_solicitante` de los cuerpos en `frontend/src/servicios/{administracion,operadores,pagos,ventas}.ts` y en las pantallas que los arman (`Administracion.tsx`, `GestionOperadores.tsx`, `TerminalesPago.tsx`, `CoberturaPago.tsx`, `Venta.tsx` anulación). No romper campos que se usen para *mostrar* datos (FR-067)
- [X] T143 [US11] `frontend/src/componentes/AperturaTurno.tsx`: pasar `token` en el objeto `Turno` a `onTurnoAbierto` (si no fluye ya por el tipo)

### Cierre

- [X] T144 [US11] `tsc -b`, `eslint .`, `vite build` en `frontend/` en verde
- [X] T145 [US11] Suite completa; comparar con la línea base de T123. Toda regresión real corregida; los tests actualizados por T138 documentados
- [X] T146 [US11] Grep final acotado (hallazgo N2 de /speckit.analyze): sobre `backend/rasero/api/`, ningún modelo Pydantic de **cuerpo de INPUT de escritura** (POST/PUT/PATCH que no sea `/turnos`) declara `id_operador` / `id_operador_solicitante` para resolver `requiere_rol`/`exige_rol`. Se excluyen explícitamente: `POST /turnos` (cuerpo de autenticación con PIN, anterior al token), los query params de listados (`GET .../?id_operador=`), y `id_operador` en cuerpos de RESPUESTA (`_venta_a_respuesta`, `Anulacion`, `historial_firmware`…). Fuera de alcance y sin tocar: los endpoints de 006 (`caja.py`) y `/pagos/intencion-no-atendida`, que no verificaban rol. `operador_de_sesion` es la única fuente de identidad en endpoints sujetos a rol (SC-017)

**Checkpoint**: User Story 11 funcional; la suplantación por cuerpo ya no funciona; US1–US10 intactas; sin cambio de esquema.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T089 [P] Ejecutar los 10 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno
- [X] T090 [P] Auditar que "Despensa Los Ríos", "Quevedo Centro" y "Buena Fe" no aparecen en ningún identificador técnico, solo como valor de fila en `backend/rasero/semilla.py`
- [X] T091 Auditar `frontend/` en busca de color, radio o tipografía incrustados fuera de `frontend/src/estilos/tokens.css`, y confirmar que Inter no aparece en ninguna parte
- [X] T092 Ejecutar `pytest tests` completo y confirmar en verde las 6 suites obligatorias (T017, T018, T019, T020, T072, T084) antes de considerar el módulo fusionable

---

## Dependencies & Execution Order

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias, empieza de inmediato.
- **Foundational (Fase 2)**: depende de Setup. **Bloquea** todas las historias de usuario.
- **Historias de usuario (Fases 3-10)**: todas dependen de Foundational. Dentro de cada una, backend antes que frontend, como exige el enunciado.
- **Polish (Fase final)**: depende de que las historias que se vayan a entregar estén completas.

### Dependencias entre historias

Las 8 historias son independientemente entregables una vez completada Foundational. No hay dependencia dura de una historia sobre otra: comparten esquema y servicios base, pero cada una puede probarse y demostrarse por separado, según sus criterios de "Independent Test" en spec.md. El orden P1→P8 es el de construcción recomendado, no una cadena de bloqueo — con capacidad suficiente, US2 a US8 podrían desarrollarse en paralelo tras el checkpoint de Foundational.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican.
- Reglas de dominio antes que servicios; servicios antes que endpoints; endpoints antes que su cliente de frontend.
- Backend completo de la historia antes que su frontend, según el enunciado de esta tarea.

### Oportunidades de paralelismo

- Todas las tareas [P] de Setup y Foundational pueden ejecutarse en paralelo.
- Tras el checkpoint de Foundational, las 8 historias pueden trabajarse en paralelo por distintas personas.
- Dentro de una historia, las pruebas [P] entre sí, y los componentes de frontend [P] entre sí, son paralelizables.

---

## Parallel Example: User Story 1

```bash
# Lanzar juntas las cuatro pruebas obligatorias de esta historia:
Task: "Prueba unitaria de totales de venta en tests/unidad/test_totales_venta.py"
Task: "Prueba unitaria de selección FEFO en tests/unidad/test_seleccion_fefo.py"
Task: "Prueba de integración de idempotencia en tests/integracion/test_idempotencia_venta.py"
Task: "Prueba de integración de saldo/negativo en tests/integracion/test_saldo_existencia.py"

# Lanzar juntas las tres reglas de dominio que esas pruebas verifican:
Task: "Cálculo de totales en backend/rasero/dominio/totales.py"
Task: "Selección FEFO en backend/rasero/dominio/seleccion_lote.py"
Task: "Resolución de precio efectivo en backend/rasero/dominio/resolucion_precio.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Setup.
2. Completar Fase 2: Foundational — crítica, bloquea todo lo demás.
3. Completar Fase 3: User Story 1, con sus 4 pruebas obligatorias en verde.
4. **Detenerse y validar**: ejecutar los escenarios 1 a 4 de quickstart.md.
5. Demostrar: caja funcional, idempotente, con saldo negativo admitido.

### Entrega incremental

1. Setup + Foundational → fundamento listo.
2. + US1 (venta) → probar de forma independiente → MVP demostrable.
3. + US2 (entradas) → + US3 (consultas) → + US4 (comparación de precios) → cada una se prueba y demuestra por separado.
4. + US5 (conteo) → + US6 (traspaso, con su prueba de invariante) → + US7 (capital inmovilizado).
5. + US8 (sincronización offline) — no opcional pese a ir última; cierra la exigencia del Principio II.
6. Fase final: quickstart.md completo, auditoría de nomenclatura y de tokens, suite completa en verde.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Setup + Foundational en conjunto — es la única sección estrictamente secuencial.
2. Completada Foundational, cada historia puede asignarse a una persona distinta, siguiendo el orden P1→P8 solo como prioridad de negocio, no como bloqueo técnico.
3. Cada historia se integra de forma independiente contra el esquema y los servicios compartidos de Foundational.

---

## Notes

- Las tareas [P] tocan archivos distintos y no dependen de una tarea incompleta.
- La etiqueta [Story] traza cada tarea a su historia de usuario en spec.md.
- Las 6 suites obligatorias del Principio III están marcadas y deben pasar antes de fusionar; no hay pruebas de interfaz, maquetación ni componentes visuales.
- Backend en `backend/`, frontend en `frontend/`, pruebas en `tests/` — las tres en la raíz. Ninguna tarea genera código en `specs/` ni crea `src/` en la raíz del repositorio.
- Fuera de alcance de este desglose: autenticación más allá del PIN de operador, devolución de mercancía con reembolso, contenedores Docker y despliegue. **Roles y permisos ya NO están fuera de alcance**: la enmienda constitucional v2.3.0 (Principio VI) los incorporó como User Story 10 / Phase 12 (autorización por rol `cajero`/`encargado`/`admin`, sucursal fija por operador, mecanismo central `requiere_rol`). **La identidad de sesión tampoco**: la enmienda v2.4.0 (sub-sección "Identidad de sesión" del Principio VI) la incorporó como User Story 11 / Phase 13 — token JWT de sesión de turno emitido al abrir turno, `id_operador` del cuerpo deprecado para autorización. La autenticación (PIN + hash, la credencial que se presenta) sigue sin cambios; el token es la consecuencia de presentarla.

### Adiciones y desviaciones registradas durante la implementación del Bloque B (US2–US8)

- **`GET /sucursales`** (`backend/rasero/api/sucursales.py`) — añadido: la pantalla de despacho de traspaso (US6) necesita elegir la sucursal de destino y el contrato no exponía ninguna lectura de `sucursal`. Mismo motivo por el que US1 añadió `GET /productos` y `GET /operadores`. Codificar que las sucursales son dos sigue PROHIBIDO (FR-046); esta lista es la fuente para poblar cualquier selector.
- **`backend/rasero/config/competencia.py`** — nuevo archivo de calibración (mismo patrón que `config/pronostico.py` de 004): umbrales de días para `indicador_forma` de una observación de competencia (`lleno` ≤ 7 d, `medio` 8–21 d, `hueco` > 21 d). Ningún artefacto los daba; ver research.md §12. Presentación pura, no entra en ningún cálculo.
- **`lote.costo_unitario = 0.00` como centinela de "sin costo registrado"** (US7, T080) — FR-035 y el contrato piden `valor_calculable: false` / `valor_inmovilizado: null` para un lote sin costo, pero `lote.costo_unitario` es `NUMERIC(12,4) NOT NULL`. Se resuelve con el centinela `0.00`, sin migración. Ver research.md §11 y la nota añadida a FR-035 en spec.md.
- **Registro visual de US4 (T064)**: `plan.md` (§Sistema de diseño) dice "el radio 6px de Análisis se define… aunque este módulo no lo use"; T064 y `DESIGN.md` sí asignan la comparación de precios al registro de Análisis (6px, Source Serif 4). Se siguió T064/DESIGN.md — es la única pantalla de Análisis de 001. `tokens.css` ya tenía `--radio-analisis` y Source Serif cargada, sin cambio de infraestructura.
- **T089 (quickstart e2e)** se implementó como `tests/integracion/test_quickstart_001.py`: los 10 escenarios contra la API real, ya que la interfaz está exenta de prueba automatizada (Principio III) y no hay automatización de UI.
