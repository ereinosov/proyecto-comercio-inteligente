---

description: "Task list template for feature implementation"
---

# Tasks: Caja, Mermas y Fraude

**Input**: Documentos de diseño desde `/specs/006-caja-mermas-fraude/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados contra la constitución **v2.2.6** (sin cambios para `006` desde v2.2.5). Requiere que `001-core-ventas-inventario` User Story 1 ya esté migrada y en ejecución: este módulo **sólo lee** de `001` (`turno`, `venta`, `renglon_venta`, `anulacion_venta`, `producto`, `producto_precio_sucursal`, `sucursal`, `lote`, `operador` — nunca `pin_hash`) y **nunca escribe en ninguna tabla ajena**, ni siquiera vía función-puente (a diferencia de `003`). **Este módulo NO motiva ninguna enmienda constitucional**: sus tres entidades (`arqueo`, `merma`, `anomalia_caja`) coinciden con la tabla de Propiedad de Datos v2.2.6. La revisión #18 de research.md (trade-off de `anomalia_caja.resolucion` como texto libre) no cambia las tres entidades.

**BLOQUEO PARCIAL por `001` User Story 5 — RESUELTO**: `001` implementó `conteo_fisico` / `conteo_renglon` (servicio + endpoints, T065–T071). Las tareas que estaban marcadas **⛔ BLOQUEADA por 001 (User Story 5)** —T021, T023 (rama con `id_conteo_renglon`), T033, T036, T037, T044— quedaron desbloqueadas: se quitaron los `xfail` y se completó la lógica de servicio. Ver "Punto de reactivación — RESUELTO" al final.

**Pruebas**: se incluyen las **7 suites obligatorias** de la tabla "Pruebas obligatorias" de plan.md (Principio III — el riesgo central es doble: un arqueo que trate una diferencia de cero como "sin novedad" enmascara el fraude de sub-registro que la Lectura Crítica n.º 1 describe; una señal por operador presentada como conclusión de fraude, o un faltante imputado sin descontar la merma declarada, acusa a una persona con un cálculo mal hecho). **Todas corren contra PostgreSQL real en el puerto 5442, nunca contra mocks ni SQLite** — mismo criterio que `001`–`005`. No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario, en el **orden de prioridad ya fijado por spec.md y no renegociable**: US1 arqueo de caja por turno (P1, no bloqueada) → US2 clasificar mermas físicas + alerta de caducidad (P2, parcialmente bloqueada) → US3 detectar el sub-registro cruzando inventario vs ventas por operador (P3, parcialmente bloqueada) → US4 gestionar las anomalías sin explicación (P4, parcialmente bloqueada). Backend antes que frontend dentro de cada historia. Fundamento (esquema, modelos, router, parámetros, helper de día local) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta). Dos tareas que editan el **mismo** archivo no llevan ambas `[P]`: la segunda depende de la primera.
- **[Story]**: historia de usuario a la que pertenece (US1 … US4)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende
- Cada tarea que toca datos indica explícitamente de dónde:
  - **[006]** — tabla propia de este módulo (`arqueo`, `merma`, `anomalia_caja`)
  - **[001-lectura: ...]** — consulta de **solo lectura** a una o más tablas de `001` (nunca se altera su esquema ni se duplica). Los tests de frontera cuentan filas antes y después para verificar 0 escrituras
- **⛔ BLOQUEADA por 001 (User Story 5, T065–T071)** — la tarea depende de `conteo_fisico`/`conteo_renglon` implementadas en `001`; hasta entonces devuelve `409 caja_bloqueado_por_001` y su prueba es `xfail`

## Convención de rutas (fijada en plan.md, extiende la de 001–005, no negociable)

- Backend: `backend/rasero/` (`dominio/`, `persistencia/`, `servicios/`, `api/`, `config/`) y `backend/migraciones/versions/`
- Frontend: `frontend/src/` (`pantallas/`, `servicios/`) — **registro de Operación** para `Arqueo.tsx` (radio 2px, IBM Plex Sans con cifras tabulares, sin animación salvo confirmación); **registro de Análisis** para `Mermas.tsx`, `AnomaliasCaja.tsx`, `IndicadoresOperador.tsx` (radio 6px, Source Serif 4). **Regla del Registro Sin Dinero**: cero apariciones del Verde Rasero en las cuatro pantallas
- Pruebas: `tests/` en la raíz (`unidad/`, `integracion/`, `contrato/`)

---

## Phase 1: Foundational (bloqueante para las cuatro historias)

**Propósito**: esquema de las tres entidades propias, modelos ORM, el router compartido, el módulo único de parámetros de configuración y el helper de día local.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T001 Crear `backend/migraciones/versions/0006_caja_mermas_fraude.py` con los `ENUM` (`causa_merma('vencimiento','dano','robo_externo','error_conteo','merma_granel','pendiente_clasificar')`, `estado_merma('pendiente_clasificar','clasificada')`, `origen_anomalia('efectivo','inventario')`, `estado_anomalia('sin_explicacion','resuelta')`) y las tres tablas de data-model.md: `arqueo` con `id_turno INTEGER NOT NULL UNIQUE` FK→`turno` (idempotencia FR-005), columnas denormalizadas `id_operador`/`id_sucursal`/`dia_local`, `monto_esperado`/`monto_contado NUMERIC(12,2)`, `diferencia NUMERIC(12,2)` calculada, `motivo_conocido TEXT NULL`, `ajustes JSONB NOT NULL DEFAULT '[]'`, `marca_tiempo_origen`, e índice `(id_sucursal, dia_local)`; `merma` con `id_conteo_renglon INTEGER NULL` FK→`conteo_renglon` (**la tabla destino existe en el esquema `0001` aunque su servicio no** — research.md #10), `causa causa_merma`, `cantidad_faltante NUMERIC(14,0)` `CHECK (> 0)` (**escala idéntica a `conteo_renglon.diferencia` de `001`**, data-model.md), `valoracion NUMERIC(12,2) NULL` ("no calculable", nunca cero), `moneda CHAR(3) DEFAULT 'USD'`, `periodo_desde`/`periodo_hasta DATE` `CHECK (hasta >= desde)`, `estado estado_merma`, `conciliar_con_conteo BOOLEAN`, `id_operador_registro NOT NULL`, índices `(id_sucursal, periodo_hasta)`, `(id_producto, periodo_hasta)` y `(id_conteo_renglon) WHERE id_conteo_renglon IS NOT NULL`; `anomalia_caja` con `origen origen_anomalia`, `estado estado_anomalia DEFAULT 'sin_explicacion'`, FKs `NULL` `id_arqueo`/`id_turno`/`id_operador`/`id_producto`/`id_conteo_fisico`, `monto NUMERIC(12,2) NULL`, `magnitud NUMERIC(14,0) NULL`, `valor_estimado NUMERIC(12,2) NULL`, `periodo_desde`/`periodo_hasta DATE NULL`, `dia_local DATE NOT NULL`, `indicador_snapshot JSONB NULL`, `historial JSONB NOT NULL DEFAULT '[]'`, `resolucion TEXT NULL`, `id_operador_resolucion NULL`, `instante_resolucion NULL`, `CHECK` (`id_operador_resolucion` e `instante_resolucion` no nulos ⟺ `estado = 'resuelta'`), índices `(id_sucursal, estado)`, `(origen, estado)`, `(id_arqueo) WHERE id_arqueo IS NOT NULL`; `downgrade` que elimina las tres tablas y los cuatro `ENUM` en orden inverso **[006]**
- [X] T002 [P] Crear los modelos SQLAlchemy 2.x `Arqueo`, `Merma`, `AnomaliaCaja` en `backend/rasero/persistencia/modelos.py` con los `CheckConstraint` de `data-model.md` (depende de T001) **[006]**
- [X] T003 [P] Crear el módulo único de parámetros de configuración `backend/rasero/config/caja.py` con los valores de arranque de research.md #16, sobrescribibles por variable de entorno — mismo patrón que `config/pronostico.py` de `004` y `config/promociones.py` de `005`: `VENTANA_ALERTA_CADUCIDAD_DIAS = 14`, `TOLERANCIA_CUADRE_ARQUEO = Decimal("0.00")`, `UMBRAL_MINIMO_VENTAS_INDICADOR = 20`, `RAZON_DESVIACION_ANULACIONES = Decimal("2.0")`, `RAZON_DESVIACION_PRECIO_BAJO_LISTA = Decimal("2.0")`. Sin ninguna constante mágica dispersa (Principio V "acotada"); la justificación de cada valor vive en research.md #16, no en comentarios de código
- [X] T004 [P] Crear el router base `backend/rasero/api/caja.py` con prefijo `/caja` y montarlo en `backend/rasero/api/aplicacion.py`; incluir el manejador que traduce la excepción de bloqueo a `409 {codigo: "caja_bloqueado_por_001", mensaje: ...}` (depende de T002)
- [X] T005 [P] Helper de día local en `backend/rasero/dominio/arqueo.py`: `dia_local(instante, zona_horaria) -> date` = `(instante AT TIME ZONE zona)::date` — mismo criterio de día local que `001`/`004`/`005` (research.md #12); `006` implementa el suyo, no importa el de otro módulo

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 2: User Story 1 - Arquear la caja al cierre de cada turno (Priority: P1) 🎯 MVP

**Goal**: registrar un `arqueo` por turno cerrado con el efectivo contado frente a `SUM(venta.total)` del turno (congelado), atribuido al operador y al día local; idempotente por `id_turno`; una diferencia sin motivo conocido crea una `anomalia_caja` de origen efectivo. Establece la tabla `arqueo` y el router `/caja` que las otras historias amplían. **No bloqueada** — sólo necesita `turno` y `venta` de `001`.

**Independent Test**: para un turno cerrado con ventas por un total conocido, `POST /caja/arqueos` calcula `monto_esperado` = suma de esos cobros y lo congela; anular una venta después no cambia la diferencia registrada; 10 `POST` con el mismo `id_turno` producen exactamente un `arqueo`; un turno sin ventas produce `monto_esperado = "0.00"`; una diferencia sin `motivo_conocido` crea una `anomalia_caja` de origen efectivo; con motivo, no.

### Pruebas obligatorias para User Story 1

- [X] T006 [P] [US1] Prueba unitaria de las funciones puras del arqueo: `diferencia_con_signo(contado, esperado)` (negativa = faltante), `debe_generar_anomalia(diferencia, motivo_conocido, tolerancia)` (`True` sólo si `|diferencia| > tolerancia` y `motivo_conocido` es `None`), `dia_local` — en `tests/unidad/test_arqueo_dominio.py` (depende de T005) **[006]**
- [X] T007 [P] [US1] **[Obligatoria #1 — congelación de `monto_esperado`]** Prueba de integración: `registrar_arqueo` fija `monto_esperado = SUM(venta.total)` de las ventas del turno y lo **congela** en la fila; **anular una venta después del arqueo NO cambia `monto_esperado` ni `diferencia`** (research.md #4); `diferencia` con signo correcto — contra PostgreSQL real, puerto 5442, en `tests/integracion/test_arqueo.py` (depende de T001, T002) **[006] [001-lectura: venta, turno, sucursal]**
- [X] T008 [US1] Prueba de integración de idempotencia y turno vacío: 10 `POST /caja/arqueos` con el mismo `id_turno` → exactamente una fila en `arqueo` (la primera `201`, las demás `200` con el mismo `id_arqueo`, SC-003); un turno sin ninguna venta → `monto_esperado = "0.00"`, no error (FR-007); por conteo directo de filas, `POST /caja/arqueos` no toca `venta`, `renglon_venta` ni `movimiento_inventario` (SC-002, SC-011) — contra PostgreSQL real, en `tests/integracion/test_arqueo.py` (depende de T007) **[006] [001-lectura: venta]**
- [X] T009 [US1] Prueba de integración de la regla de anomalía: un arqueo con `diferencia != "0.00"` (fuera de `TOLERANCIA_CUADRE_ARQUEO`) y **sin** `motivo_conocido` crea en la misma transacción una `anomalia_caja` de `origen = "efectivo"`, `estado = "sin_explicacion"`, atribuida al turno, operador, sucursal y día local (FR-004, FR-027); con `motivo_conocido` anotado, **no** se crea ninguna anomalía (FR-031, SC-010) — contra PostgreSQL real, en `tests/integracion/test_arqueo.py` (depende de T008) **[006]**

### Implementación backend para User Story 1

- [X] T010 [P] [US1] Implementar `diferencia_con_signo(...)` y `debe_generar_anomalia(...)` en `backend/rasero/dominio/arqueo.py` (depende de T005; implementa T006) **[006]**
- [X] T011 [US1] Servicio `arqueos.registrar_arqueo(sesion, *, id_turno, monto_contado, motivo_conocido=None, marca_tiempo_origen)` en `backend/rasero/servicios/arqueos.py`: valida que el turno exista (`404 caja_turno_no_existe`) y esté cerrado (`400 caja_turno_abierto`); calcula `monto_esperado = SELECT SUM(total) FROM venta WHERE id_turno = :id_turno` de `001` y lo congela; denormaliza `id_operador`/`id_sucursal` de `turno` y `dia_local` vía `dominio/arqueo.py::dia_local` (T005) sobre `turno.instante_cierre` y `sucursal.zona_horaria`; calcula `diferencia` (T010); **idempotente** por `UNIQUE (id_turno)` — un segundo `POST` devuelve la fila existente con `200`; si `debe_generar_anomalia` (T010) crea una `AnomaliaCaja` de origen efectivo en la misma transacción. **No** escribe en ninguna tabla de `001` (depende de T002, T003, T010; implementa T007, T008, T009) **[006] [001-lectura: venta, turno, sucursal]**
- [X] T012 [US1] Servicios `arqueos.listar_arqueos(sesion, *, id_sucursal=None, id_turno=None, desde=None, hasta=None, solo_descuadrados=False)` (exige `id_sucursal` salvo que venga `id_turno` → `400 caja_sucursal_requerida`, FR-038) y `arqueos.ajustar_arqueo(sesion, *, id_arqueo, monto_contado_nuevo, id_operador, nota)` (añade una entrada a `ajustes` JSONB, recalcula `diferencia`, **nunca** reescribe `monto_esperado`) en `backend/rasero/servicios/arqueos.py` (depende de T011) **[006]**
- [X] T013 [US1] Endpoints `POST /caja/arqueos`, `GET /caja/arqueos`, `GET /caja/arqueos/{id_arqueo}` y `PATCH /caja/arqueos/{id_arqueo}` en `backend/rasero/api/caja.py` (depende de T011, T012, T004)
- [X] T014 [P] [US1] Prueba de contrato de los cuatro endpoints de arqueos contra `contracts/openapi.yaml` (forma feliz + `400` turno abierto / monto inválido / `caja_sucursal_requerida` + `404` turno o arqueo inexistente + `200` de idempotencia), con el formato de error `{codigo, mensaje}` unificado con `001`–`005`, en `tests/contrato/test_contrato_caja.py` (depende de T013)

### Implementación frontend para User Story 1

- [X] T015 [P] [US1] Cliente HTTP `registrarArqueo`, `listarArqueos`, `obtenerArqueo`, `ajustarArqueo` en `frontend/src/servicios/caja.ts` (depende de T013)
- [X] T016 [US1] Pantalla `Arqueo.tsx` (**registro de OPERACIÓN**: radio 2px, IBM Plex Sans con cifras tabulares reales — efectivo contado y esperado alinean por dígito—, sin tarjetas, **sin animación** salvo la confirmación de cerrar el arqueo): tabla de arqueos por turno, captura del efectivo contado, `diferencia` con signo, una diferencia con `motivo_conocido` anotado en atención `#9A5B08`; nueva pestaña "Arqueo" en `frontend/src/App.tsx`. **Cero Verde Rasero** (Regla del Registro Sin Dinero). Invoca `new-work` de Impeccable (mundo visual de Operación ya fijado por la constitución, `PRODUCT.md` existente, no se repite `init`) (depende de T015)
- [X] T017 [US1] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la pestaña Arqueo (depende de T016)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente — arqueo por turno con su diferencia atribuida y su anomalía de origen efectivo, sin ninguna dependencia de `conteo_fisico`. MVP.

---

## Phase 3: User Story 2 - Clasificar la causa de una diferencia de conteo físico como merma (Priority: P2)

**Goal**: clasificar la `diferencia` bruta que `001` expone en un `conteo_renglon` (**⛔ bloqueado**), declarar una merma fuera de conteo (**✓**), y alertar de los lotes próximos a caducar (**✓**); valorar la pérdida al costo del lote FEFO de `001`, atribuida a la sucursal y al período entre conteos, **nunca a un operador**.

**Independent Test**: `POST /caja/mermas` **sin** `id_conteo_renglon` registra una merma con causa, cantidad y valor (`cantidad × lote.costo_unitario`, o "no calculable" sin costo), marca `conciliar_con_conteo = true` y **no** escribe en `existencia`; `GET /caja/alertas-caducidad` lista los lotes de `001` dentro de la ventana con su valor en riesgo y marca los ya caducados; `POST /caja/mermas` **con** `id_conteo_renglon` devuelve hoy `409 caja_bloqueado_por_001` (prueba `xfail`).

### Pruebas obligatorias para User Story 2

- [X] T018 [P] [US2] **[Obligatoria #3 — valoración "no calculable"]** Prueba unitaria de `valorar_merma(cantidad_faltante, costo_unitario_lote)`: con costo conocido → `cantidad × costo`; **sin costo (`None`) → `None` ("no calculable"), NUNCA `Decimal("0.00")`** (SC-005); producto granel → sobre gramos al costo por kilogramo — función pura, en `tests/unidad/test_merma_valoracion.py` (depende de T005) **[006]**
- [X] T019 [P] [US2] **[Obligatoria #4 — rama libre]** Prueba de integración: `POST /caja/mermas` **sin** `id_conteo_renglon` registra la merma con causa, `cantidad_faltante`, `valoracion` y `conciliar_con_conteo = true` (FR-012); por conteo directo, **no** escribe en `existencia` ni `movimiento_inventario` (FR-034, SC-011); la merma **nunca** lleva un `id_operador` de imputación (FR-011); `GET /caja/mermas` desglosa por causa, producto y sucursal y exige `id_sucursal` (FR-016, FR-038) — contra PostgreSQL real, en `tests/integracion/test_merma.py` (depende de T001, T002) **[006] [001-lectura: lote, producto]**
- [X] T020 [US2] Prueba de integración de la alerta de caducidad (FR-014): `GET /caja/alertas-caducidad?id_sucursal=&dentro_de_dias=14` lista los `lote` de `001` con `fecha_caducidad` dentro de la ventana y `existencia > 0`, con `valor_en_riesgo` (o "no calculable"); marca `ya_caducado = true` los de `fecha_caducidad < hoy_local`; **cero** escrituras en `lote` ni `existencia` — contra PostgreSQL real, en `tests/integracion/test_merma.py` (depende de T019) **[006] [001-lectura: lote, existencia, producto]**
- [X] T021 [US2] **⛔ BLOQUEADA por 001 (User Story 5, T065–T071)** — **[Obligatoria #4 — rama de conteo]** Prueba de integración `@pytest.mark.xfail(reason="bloqueado por 001 US5 T065-T071", strict=True)`: `POST /caja/mermas` **con** `id_conteo_renglon` clasifica la `diferencia` que `001` expone en esa línea (FR-009, FR-015), la valora y **no** recalcula la diferencia bruta (FR-033). **Hoy**: `409 caja_bloqueado_por_001`. **Al implementar `001` T065–T071**: quitar el `xfail`, `201` con la merma clasificada — en `tests/integracion/test_merma.py` (depende de T019) **[006] [001-lectura: conteo_renglon]**

### Implementación backend para User Story 2

- [X] T022 [P] [US2] Funciones puras en `backend/rasero/dominio/merma.py`: `valorar_merma(cantidad_faltante, costo_unitario_lote: Decimal | None) -> Decimal | None` (research.md #11; `None` → "no calculable"), `periodo_entre_conteos(fecha_conteo_actual, fecha_conteo_anterior | None, fecha_declaracion) -> tuple[date, date]` (research.md #5) (depende de T005; implementa T018) **[006]**
- [X] T023 [US2] Servicio `mermas.clasificar_merma(sesion, *, id_producto, id_sucursal, cantidad_faltante, causa, id_operador_registro, id_conteo_renglon=None, id_lote=None, nota=None)` en `backend/rasero/servicios/mermas.py`. **Rama sin `id_conteo_renglon` (✓)**: resuelve el lote FEFO de `001` (caducidad primero, entrada como desempate — FR-048 de `001`) si `id_lote` no viene, valora con `dominio/merma.py::valorar_merma` (T022), fija `conciliar_con_conteo = true`, `periodo_*` con `periodo_entre_conteos` (T022), inserta `Merma`. **Rama con `id_conteo_renglon` (⛔ BLOQUEADA por 001 User Story 5, T065–T071)**: hoy lanza la excepción de bloqueo → `409 caja_bloqueado_por_001`; al implementar `001` T065–T071, lee `conteo_renglon.diferencia` para validar la cantidad y clasifica. **Nunca** escribe en `existencia` ni `movimiento_inventario`; **nunca** asigna un `id_operador` de imputación (FR-011). **Incluye en su propio alcance una prueba EN VERDE (no `xfail`)** en `tests/integracion/test_merma.py` de que `POST /caja/mermas` **con** `id_conteo_renglon` devuelve hoy `409 caja_bloqueado_por_001` con el cuerpo `{codigo, mensaje}` esperado — el `409` es comportamiento controlado y esperado, no un fallo conocido; esta prueba **debe pasar ahora** y se mantiene tras el desbloqueo verificando que ya **no** se devuelve el `409` (depende de T002, T003, T022; implementa T019, T021) **[006] [001-lectura: lote, producto, conteo_renglon]**
- [X] T024 [US2] Servicios `mermas.listar_mermas(sesion, *, id_sucursal, causa=None, id_producto=None, desde=None, hasta=None)` (desglose y total valorado + conteo de "no calculable", FR-016; exige `id_sucursal`) y `mermas.alertas_caducidad(sesion, *, id_sucursal, dentro_de_dias=None)` (consulta derivada sobre `lote`/`existencia` de `001`; `dentro_de_dias` por defecto `VENTANA_ALERTA_CADUCIDAD_DIAS`; `valor_en_riesgo = existencia.cantidad × lote.costo_unitario` o "no calculable"; `ya_caducado` para `fecha_caducidad < hoy_local`; **no** escribe nada, FR-014) en `backend/rasero/servicios/mermas.py` (depende de T023; implementa T020) **[006] [001-lectura: lote, existencia, producto]**
- [X] T025 [US2] Endpoints `POST /caja/mermas`, `GET /caja/mermas` y `GET /caja/alertas-caducidad` en `backend/rasero/api/caja.py` — `api/caja.py` se **amplía**, no se reescribe (depende de T023, T024, T013)
- [X] T026 [P] [US2] Ampliar la prueba de contrato con `POST /caja/mermas` (forma feliz rama libre + `400` cantidad/causa inválida + `404` producto/lote + `409 caja_bloqueado_por_001` para la rama con `id_conteo_renglon`), `GET /caja/mermas` y `GET /caja/alertas-caducidad` en `tests/contrato/test_contrato_caja.py` (depende de T025, T014)

### Implementación frontend para User Story 2

- [X] T027 [P] [US2] Cliente HTTP `registrarMerma`, `listarMermas`, `listarAlertasCaducidad` añadidos a `frontend/src/servicios/caja.ts` (funciones nuevas, sin solape con las de T015) (depende de T025, T015)
- [X] T028 [US2] Pantalla `Mermas.tsx` (**registro de ANÁLISIS**: radio 6px, Source Serif 4, una decisión por bloque, líneas bajo 80 caracteres): declarar una merma libre con su causa; clasificar diferencias de conteo (**la sección de clasificación de conteo se muestra deshabilitada con el texto explícito "requiere el conteo físico de 001" mientras `001` User Story 5 no exista** — no se oculta, se marca); lista de alertas de caducidad — lote **ya caducado** en crítico `#8E2A2A` + punto hueco, **próximo a caducar** en atención `#9A5B08` + punto medio, `valor` "no calculable" en texto (Regla de los Tres Portadores); nueva pestaña "Caja y fraude" en `frontend/src/App.tsx` que agrupará Mermas / Anomalías / Indicadores. **Cero Verde Rasero**. Invoca `new-work` de Impeccable (mundo visual de Análisis ya fijado) (depende de T027)
- [X] T029 [US2] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar Mermas y la pestaña "Caja y fraude" (depende de T028)

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente; la declaración de merma libre y la alerta de caducidad quedan demostradas sin escritura contra `001`; la clasificación de diferencias de conteo espera a `001` User Story 5 (T021 `xfail`, documentado).

---

## Phase 4: User Story 3 - Detectar el sub-registro cruzando inventario contra ventas por operador (Priority: P3)

**Goal**: calcular por operador la tasa de anulaciones y la concentración de ventas bajo precio de lista (**✓**), presentadas **siempre** como desviación respecto de la línea base de pares (mediana + razón, sin librería), y cruzar el faltante de inventario no explicado por merma contra las ventas registradas, repartido por turno (**⛔ bloqueado**). **El arqueo de efectivo, por sí solo, NO es señal de este fraude** (FR-008, Lectura Crítica n.º 1).

**Independent Test**: `GET /caja/indicadores-operador` calcula la tasa de anulaciones (atribución `anulacion_venta.id_operador` vs `turno.id_operador`) y la concentración bajo precio de lista; un operador con menos de `UMBRAL_MINIMO_VENTAS_INDICADOR` ventas no entra en la mediana ni recibe señal; un operador se marca `se_desvia` sólo si su valor `≥ razón × mediana de pares`; la respuesta **nunca** dice "fraude"; un turno con arqueo cuadrado pero tasa atípica **sigue** señalado. `POST /caja/cruce-operador` devuelve hoy `409 caja_bloqueado_por_001` (prueba `xfail`).

### Pruebas obligatorias para User Story 3

- [X] T030 [P] [US3] **[Obligatoria #5 — unidad]** Prueba unitaria de las funciones puras de indicadores: `tasa_anulaciones`, `concentracion_bajo_lista`, `mediana(valores)`, `se_desvia(valor, mediana_pares, razon)`, `reparto_proporcional_faltante(faltante, unidades_por_turno) -> dict`; casos: un operador con `< UMBRAL_MINIMO_VENTAS_INDICADOR` ventas **no** entra en la mediana; la mediana es **robusta** a un único operador con valor extremo (no la arrastra como haría la media); toda la aritmética con `Decimal` — en `tests/unidad/test_indicadores_operador.py` (depende de T005) **[006]**
- [X] T031 [P] [US3] **[Obligatoria #5 — integración]** Prueba de integración: tres operadores con volumen comparable, uno con tasa de anulaciones muy superior → `GET /caja/indicadores-operador` devuelve `mediana_pares_*`, marca `se_desvia = true` sólo al operador atípico con `detalle_desviacion` que enumera los datos ("tasa 0,20 vs mediana de pares 0,03 (×6,7)"), y **en ningún campo** aparece la palabra "fraude" (FR-022, FR-023, SC-007, SC-008); un cuarto operador con 8 ventas → `comparable = false`, `se_desvia = false` — contra PostgreSQL real, en `tests/integracion/test_deteccion_fraude.py` (depende de T001, T002) **[006] [001-lectura: venta, anulacion_venta, renglon_venta, turno, producto, producto_precio_sucursal]**
- [X] T032 [US3] **[Obligatoria #2 — el arqueo cuadrado no descarta el fraude]** Prueba de integración: un turno del operador atípico con `arqueo.diferencia = "0.00"` pero tasa de anulaciones sobre la línea base → `GET /caja/indicadores-operador` **sigue** señalando a ese operador; la respuesta indica explícitamente que un arqueo con diferencia cero **no** es evidencia de ausencia de sub-registro (FR-008, FR-026, SC-004) — contra PostgreSQL real, en `tests/integracion/test_deteccion_fraude.py` (depende de T031) **[006] [001-lectura: venta, anulacion_venta]**
- [X] T033 [US3] **⛔ BLOQUEADA por 001 (User Story 5, T065–T071)** Prueba de integración `@pytest.mark.xfail(reason="bloqueado por 001 US5 T065-T071", strict=True)`: `POST /caja/cruce-operador` calcula `faltante_no_explicado = faltante_bruto − Σ merma clasificada − Σ anulaciones registradas`, lo reparte proporcional entre los turnos que movieron el producto y crea una `anomalia_caja` de `origen = "inventario"` con `indicador_snapshot` (FR-020); si la merma y las anulaciones explican el faltante, **no** crea nada (FR-025, FR-031, SC-012). **Hoy**: `409 caja_bloqueado_por_001` — en `tests/integracion/test_deteccion_fraude.py` (depende de T032) **[006] [001-lectura: conteo_fisico, conteo_renglon, movimiento_inventario]**

### Implementación backend para User Story 3

- [X] T034 [P] [US3] Funciones puras en `backend/rasero/dominio/indicadores_operador.py`: `tasa_anulaciones(n_anulaciones, n_ventas)`, `concentracion_bajo_lista(n_renglones_bajo_lista, n_renglones)`, `mediana(valores)`, `se_desvia(valor, mediana_pares, razon)`, `reparto_proporcional_faltante(faltante, unidades_por_turno)` — toda aritmética con `Decimal`, **sin `scipy`/`statsmodels`/`numpy`** (research.md #7d, #16) (depende de T005; implementa T030) **[006]**
- [X] T035 [US3] Servicio `deteccion_fraude.indicadores_operador(sesion, *, id_sucursal, desde, hasta)` en `backend/rasero/servicios/deteccion_fraude.py`: consulta derivada sobre `001`; por operador y período (día local) calcula la tasa de anulaciones (`anulacion_venta.id_operador` para quién anuló, `venta → turno.id_operador` para quién vendió — FR-049 de `001`) y la concentración de `renglon_venta.precio_aplicado < COALESCE(producto_precio_sucursal.precio_vigente, producto.precio_vigente)`; excluye del cálculo de la **mediana de pares** a los operadores con `< UMBRAL_MINIMO_VENTAS_INDICADOR` ventas; marca `se_desvia` con `RAZON_DESVIACION_*` (T034); la respuesta enumera `detalle_desviacion` (FR-022) y **nunca** usa la palabra "fraude" (FR-023). Solo lectura (depende de T002, T003, T034; implementa T031, T032) **[006] [001-lectura: venta, anulacion_venta, renglon_venta, turno, producto, producto_precio_sucursal]**
- [X] T036 [US3] **⛔ BLOQUEADA por 001 (User Story 5, T065–T071)** Servicio `deteccion_fraude.cruce_inventario_ventas(sesion, *, id_sucursal, desde, hasta, id_conteo_fisico=None)` en `backend/rasero/servicios/deteccion_fraude.py`: hoy lanza la excepción de bloqueo → `409 caja_bloqueado_por_001`. Al implementar `001` T065–T071: por cada producto del conteo, `faltante_bruto` de `conteo_renglon.diferencia`, descuenta `Σ merma.cantidad_faltante` clasificada del producto/período (T024) y `Σ |movimiento_inventario.cantidad|` de tipo `entrada_anulacion`; reparte el `faltante_no_explicado > 0` por turno (`reparto_proporcional_faltante`, T034), crea una `AnomaliaCaja` de origen inventario con `magnitud`, `valor_estimado` e `indicador_snapshot` (todo el desglose); si `faltante_no_explicado <= 0` no crea nada (FR-020, FR-025). **No** escribe en `001` (depende de T024, T035; implementa T033) **[006] [001-lectura: conteo_fisico, conteo_renglon, movimiento_inventario]**
- [X] T037 [US3] Endpoints `GET /caja/indicadores-operador` (✓) y `POST /caja/cruce-operador` (**⛔ devuelve `409 caja_bloqueado_por_001` mientras `001` User Story 5 no exista**) en `backend/rasero/api/caja.py`. **Incluye en su propio alcance una prueba EN VERDE (no `xfail`)** en `tests/integracion/test_deteccion_fraude.py` de que `POST /caja/cruce-operador` devuelve hoy `409 caja_bloqueado_por_001` con el cuerpo `{codigo, mensaje}` esperado — comportamiento controlado y esperado, **debe pasar ahora**; se mantiene tras el desbloqueo verificando que ya **no** se devuelve el `409` (depende de T035, T036, T013)
- [X] T038 [P] [US3] Ampliar la prueba de contrato con `GET /caja/indicadores-operador` (forma feliz + `400 caja_sucursal_requerida` / `caja_rango_invalido`) y `POST /caja/cruce-operador` (`409 caja_bloqueado_por_001` hoy; al desbloquear, forma feliz + `400`) en `tests/contrato/test_contrato_caja.py` (depende de T037, T026)

### Implementación frontend para User Story 3

- [X] T039 [P] [US3] Cliente HTTP `obtenerIndicadoresOperador`, `ejecutarCruceOperador` añadidos a `frontend/src/servicios/caja.ts` (funciones nuevas) (depende de T037, T027)
- [X] T040 [US3] Pantalla `IndicadoresOperador.tsx` (**registro de ANÁLISIS**: 6px, Source Serif 4): la tasa de anulaciones y la concentración bajo precio de lista de cada operador (**dato observado**, tinta normal) frente a la **mediana de pares** y el factor, y qué operadores **se desvían** (señal en `estimado` `#1F5673` + indicador de forma + texto explícito, p. ej. "tasa 0,18 vs mediana de pares 0,04 (×4,5) — se desvía de la línea base de sus pares"); **nunca** la palabra "fraude"; el botón del cruce muestra el texto "requiere el conteo físico de 001" mientras esté bloqueado; integrado en la pestaña "Caja y fraude". **Cero Verde Rasero** (depende de T039, T028)
- [X] T041 [US3] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar Indicadores por operador (depende de T040)

**Checkpoint**: User Stories 1 a 3 funcionan de forma independiente; los indicadores por operador se calculan y se presentan como desviación de pares sin ninguna librería estadística y sin llamar a nada "fraude"; el cruce contra el faltante de inventario espera a `001` User Story 5 (T033, T036 `xfail`/bloqueados, documentados).

---

## Phase 5: User Story 4 - Gestionar las anomalías de caja sin explicación (Priority: P4)

**Goal**: exponer la cola de `anomalia_caja` en `sin_explicacion` (efectivo desde US1 **✓**; inventario desde US3 **⛔**), permitir que una persona asigne una `resolucion` (texto libre — research.md #18), registrar el historial de cambios de estado, y garantizar que el sistema **nunca** cierra una anomalía por el paso del tiempo (FR-029).

**Independent Test**: una `anomalia_caja` de origen efectivo (creada por US1) aparece en `GET /caja/anomalias?estado=sin_explicacion`; una diferencia totalmente explicada no genera ninguna anomalía; pasado cualquier plazo simulado la anomalía sigue `sin_explicacion`; `POST /caja/anomalias/{id}/resolucion` exige `id_operador`, registra el estado anterior en `historial` y sólo entonces pasa a `resuelta`; un segundo `POST` de resolución → `400`.

### Pruebas obligatorias para User Story 4

- [X] T042 [P] [US4] **[Obligatoria #6 — anomalía sólo sin explicación, nunca cerrada por el sistema]** Prueba de integración: una `anomalia_caja` de origen efectivo (de US1) aparece en `GET /caja/anomalias?estado=sin_explicacion&id_sucursal=`; una diferencia con `motivo_conocido`, o un faltante que coincide con una merma ya `clasificada`, → **0 anomalías** (FR-031, SC-010, SC-012); tras avanzar el reloj de prueba 90 días y correr las tareas de mantenimiento, la anomalía **sigue** `sin_explicacion` — ninguna transición automática (FR-029, SC-009) — contra PostgreSQL real, en `tests/integracion/test_anomalias.py` (depende de T001, T002, T011) **[006]**
- [X] T043 [US4] Prueba de integración de la resolución (FR-030): `POST /caja/anomalias/{id}/resolucion { resolucion, id_operador, nota }` fija `estado = "resuelta"`, `id_operador_resolucion` e `instante_resolucion`, y añade a `historial` una entrada que conserva el `estado` anterior (`sin_explicacion`) y el instante; un segundo `POST` sobre la misma anomalía → `400 caja_anomalia_ya_resuelta`; `resolucion` vacía → `400 caja_resolucion_vacia` — contra PostgreSQL real, en `tests/integracion/test_anomalias.py` (depende de T042) **[006] [001-lectura: operador]**
- [X] T044 [US4] **⛔ BLOQUEADA por 001 (User Story 5, T065–T071)** Prueba de integración `@pytest.mark.xfail(reason="bloqueado por 001 US5 T065-T071", strict=True)`: tras `POST /caja/cruce-operador` (⛔), `GET /caja/anomalias?origen=inventario` devuelve la anomalía con `magnitud`, `valor_estimado`, `indicador_snapshot` y el reparto por turno; su `historial` arranca en `sin_explicacion` — en `tests/integracion/test_anomalias.py` (depende de T043, T036) **[006]**

### Implementación backend para User Story 4

- [X] T045 [US4] Servicios `deteccion_fraude.listar_anomalias(sesion, *, id_sucursal, estado=None, origen=None, desde=None, hasta=None)` (exige `id_sucursal`, FR-038) y `deteccion_fraude.resolver_anomalia(sesion, *, id_anomalia_caja, resolucion, id_operador, nota=None)` en `backend/rasero/servicios/deteccion_fraude.py`: `resolver_anomalia` valida `estado = "sin_explicacion"` (`400 caja_anomalia_ya_resuelta`) y `resolucion` no vacía (`400 caja_resolucion_vacia`); añade `{estado: "sin_explicacion", instante, id_operador, nota}` a `historial` (JSONB) y fija `estado = "resuelta"`, `id_operador_resolucion`, `instante_resolucion`. **No** existe ninguna ruta, tarea ni disparador que cambie el estado de una anomalía sin la acción de una persona (FR-029) (depende de T035; implementa T042, T043) **[006] [001-lectura: operador]**
- [X] T046 [US4] Endpoints `GET /caja/anomalias`, `GET /caja/anomalias/{id_anomalia_caja}` y `POST /caja/anomalias/{id_anomalia_caja}/resolucion` en `backend/rasero/api/caja.py` (depende de T045, T013)
- [X] T047 [P] [US4] Ampliar la prueba de contrato con los tres endpoints de anomalías (forma feliz + `400 caja_anomalia_ya_resuelta` / `caja_resolucion_vacia` + `404 caja_anomalia_no_existe` / `caja_operador_no_existe`) en `tests/contrato/test_contrato_caja.py` (depende de T046, T038)

### Implementación frontend para User Story 4

- [X] T048 [P] [US4] Cliente HTTP `listarAnomalias`, `obtenerAnomalia`, `resolverAnomalia` añadidos a `frontend/src/servicios/caja.ts` (funciones nuevas) (depende de T046, T039)
- [X] T049 [US4] Pantalla `AnomaliasCaja.tsx` (**registro de ANÁLISIS**: 6px, Source Serif 4, una decisión por bloque): cola de anomalías `sin_explicacion` (crítico `#8E2A2A` + **punto hueco** — dato pendiente de que una persona lo cierre, mismo patrón que `senal_fuga` `confirmada` de `002`); panel de detalle junto a la lista (nunca modal) con el `historial` y el `indicador_snapshot`; formulario de resolución con `resolucion` como **texto libre** (no un desplegable cerrado — research.md #18); momento de animación deliberado al revelar el detalle; integrado en la pestaña "Caja y fraude". **Cero Verde Rasero** (depende de T048, T028)
- [X] T050 [US4] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar Anomalías de caja (depende de T049)

**Checkpoint**: las cuatro historias funcionan de forma independiente; la cola de anomalías de origen efectivo se trabaja de extremo a extremo, y el sistema nunca cierra una anomalía por su cuenta; las de origen inventario esperan a `001` User Story 5 (T044 `xfail`, documentado).

---

## Phase 6: User Story 5 - Visualizar las mermas por causa en el tiempo (Priority: P5)

**Propósito**: barras apiladas por semana y causa (FR-042..FR-045). Lectura pura sobre `merma`
(US2); no reabre el checkpoint de US1–US4. Añadida 2026-09-07. **Puerta de propiedad de datos**:
no introduce ni modifica ninguna entidad — sólo añade un endpoint de lectura sobre `merma`, ya
propiedad de 006; no requiere enmienda constitucional (verificado contra la entrada de 006 en la
tabla de Propiedad de Datos: `arqueo`, `merma`, `anomalia_caja`).

- [X] T057 [US5] Servicio `resumen_mermas_por_causa(sesion, *, id_sucursal, desde, hasta) -> list[dict]` en `backend/rasero/servicios/mermas.py`: agrega `merma.valoracion` por `date_trunc('week', periodo_hasta)` y por causa, excluye `pendiente_clasificar`, cuenta aparte las mermas sin valoración calculable (`sin_valor`). Una sola consulta agregada, sin N+1 ni agregación en el frontend.
- [X] T058 [US5] Endpoint `GET /caja/mermas/resumen?id_sucursal=&desde=&hasta=` en `backend/rasero/api/caja.py` (ruta literal `mermas/resumen`, no colisiona con `/caja/mermas`).
- [X] T059 [P] [US5] Prueba de integración en `tests/integracion/test_resumen_mermas.py`: mermas de varias causas y semanas se agregan a los buckets correctos; `pendiente_clasificar` no aparece; una merma sin valoración cuenta en `sin_valor` y no en la valoración.
- [X] T060 [P] [US5] Cliente HTTP `obtenerResumenMermas()` + tipo `ResumenMermaSemana` en `frontend/src/servicios/caja.ts`.
- [X] T061 [US5] `frontend/src/componentes/graficos/MermasPorCausaGrafico.tsx`: `<BarChart>` de barras apiladas por semana sobre `GraficoContenedor` (registro Análisis, borde 2px). Una serie por causa, color de `SERIES_NEUTRAS` (variaciones de opacidad de #1F5673 / #5A6862) — nunca colores semánticos como paleta. Leyenda en Tinta Suave, `TooltipPropio`, estado vacío del contenedor. Integrado en `Mermas.tsx` sobre la lista.
- [X] T062 [US5] Verificación `pytest tests/integracion/test_resumen_mermas.py`, `tsc -b`, `eslint`, `vite build` sin errores.

**Checkpoint US5**: Mermas muestra el gráfico de barras apiladas por causa y semana; la lista de mermas individuales sigue igual.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T051 [P] Ejecutar los 16 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno; los escenarios **9** (rama de `conteo_renglon`) y **12** (cruce inventario-ventas) se comprueban como **`xfail` documentado**, no como fallo
- [X] T052 [P] Auditar `Arqueo.tsx` (Operación) y `Mermas.tsx` / `AnomaliasCaja.tsx` / `IndicadoresOperador.tsx` (Análisis): **cero apariciones del Verde Rasero `#0F5132`** (Regla del Registro Sin Dinero); color, radio y tipografía sólo desde los tokens del sistema; los tres semánticos usados **sólo** por significado (Regla del Significado — crítico para anomalía `sin_explicacion` y lote caducado, atención para lote por caducar y diferencia con motivo, estimado para todo valor calculado); "sin explicación", "no calculable", "sin ventas suficientes para comparar" y "lote caducado" con los tres portadores simultáneos
- [X] T053 Actualizar `DESIGN.md` con la skill de Impeccable (agente `documenter`), derivándolo de las cuatro pantallas ya construidas — añade la descripción de `Caja, Mermas y Fraude` a los componentes; sidecar `.impeccable/design.json` actualizado en el mismo cambio. **No** se añaden reglas nombradas nuevas en este pase (la "Regla del Ícono" es un cambio independiente)
- [X] T054 Ejecutar `pytest tests` completo contra PostgreSQL real (puerto 5442) — las **7 suites obligatorias** (T007/T008/T009 → `test_arqueo.py`; T018 → `test_merma_valoracion.py`; T019/T020/T021 → `test_merma.py`; T030 → `test_indicadores_operador.py`; T031/T032/T033 → `test_deteccion_fraude.py`; T042/T043/T044 → `test_anomalias.py`; contrato T014/T026/T038/T047 → `test_contrato_caja.py`) más la unidad `test_arqueo_dominio.py` (T006) — y `tsc -b`, `eslint`, `vite build` del frontend, todo en verde. **Re-ejecutado tras el desbloqueo de `001` T065–T071: T021, T033 y T044 ya no llevan `xfail`; 0 `xfail` en la suite**
- [X] T055 Verificar que **todos** los parámetros de research.md #16 viven **sólo** en `backend/rasero/config/caja.py` con sus valores de arranque, sin ninguna constante mágica dispersa (Principio V "acotada"); confirmar por `grep` que `backend/rasero/` **no importa `scipy`, `statsmodels` ni `numpy`** para nada de `006` — la línea base de los indicadores es `mediana` + razón (`dominio/indicadores_operador.py`)
- [X] T056 [P] Verificar la frontera completa por `grep` sobre `backend/rasero/servicios/arqueos.py`, `servicios/mermas.py` y `servicios/deteccion_fraude.py`: cero escrituras (`INSERT`/`UPDATE`/`add`/`merge`) sobre `venta`, `renglon_venta`, `anulacion_venta`, `existencia`, `movimiento_inventario`, `lote`, `conteo_fisico`, `conteo_renglon`, `turno`, `operador` ni ningún precio; ninguna llamada que ejecute un conteo físico ni ajuste `existencia` (FR-032, FR-033, FR-034); ninguna operación automática sobre un operador (FR-024) — mismo espíritu que las pruebas de frontera de `003`, `004` y `005`

---

## Punto de reactivación — RESUELTO (`001` implementó su User Story 5, T065–T071)

`001` entregó `conteo_fisico` / `conteo_renglon` (servicio `backend/rasero/servicios/conteos.py`
+ endpoints `POST /conteos-fisicos` y `.../resolucion`). Los 7 pasos, aplicados:

1. **T021** — `@pytest.mark.xfail` retirado; la prueba de la rama con `id_conteo_renglon` pasa.
2. **T023** — rama con `id_conteo_renglon` de `clasificar_merma` implementada (`_clasificar_diferencia_de_conteo`): lee `conteo_renglon.diferencia` sin recalcularla (FR-033), valida que la cantidad no exceda el faltante bruto, `conciliar_con_conteo = false`. La prueba del `409` pasó a verificar que ya **no** se devuelve.
3. **T033** — `@pytest.mark.xfail` retirado; la prueba del cruce inventario-ventas pasa con un escenario real (conteo resuelto + `conteo_renglon` con diferencia negativa).
4. **T036** — `cruce_inventario_ventas` implementada: faltante bruto por producto − mermas clasificadas del período − anulaciones registradas; reparto por turno; `anomalia_caja` de `origen = "inventario"` con `magnitud`, `valor_estimado` e `indicador_snapshot`; nada si `faltante_no_explicado ≤ 0`.
5. **T037** — `POST /caja/cruce-operador` devuelve `200` con `{id_conteo_fisico, anomalias_creadas, detalle}`; ya no `409 caja_bloqueado_por_001` (la excepción `CajaBloqueadoPor001` se retiró de `errores.py`).
6. **T044** — `@pytest.mark.xfail` retirado; la anomalía de origen inventario aparece con su `magnitud` e `indicador_snapshot`.
7. **T054** re-ejecutado: suite completa en verde, **0 `xfail`**.

El esquema ya estaba creado desde T001: no hubo migración nueva.

---

## Dependencies & Execution Order

### Dependencias de fase

- **Foundational (Fase 1)**: sin dependencias externas salvo que `001` User Story 1 ya esté migrada y en ejecución. **Bloquea** las cuatro historias de usuario.
- **Historias de usuario (Fases 2–5)**: todas dependen de Foundational. Dentro de cada una, pruebas antes que implementación, dominio puro antes que servicio, servicio antes que endpoint, backend completo antes que frontend.
- **Polish (Fase final)**: depende de que las cuatro historias estén completas (con las partes bloqueadas por `001` en `xfail`).

### Dependencias entre historias

El orden **US1 → US2 → US3 → US4 está fijado por spec.md y no se reordena** (plan.md, "Estado de implementación por historia"):

- **US1 (arqueo de caja)** establece la tabla `arqueo`, el router `api/caja.py` y el helper de día local que las demás amplían. Crea la `anomalia_caja` de origen efectivo. **No bloqueada.**
- **US2 (clasificar mermas)** añade `servicios/mermas.py` y `dominio/merma.py` (archivos nuevos) y amplía `api/caja.py`. La rama de declaración libre y la alerta de caducidad **no** están bloqueadas; la rama de clasificación de `conteo_renglon` (T021, T023-parcial) **sí**.
- **US3 (cruce por operador)** añade `servicios/deteccion_fraude.py` y `dominio/indicadores_operador.py` (archivos nuevos) y amplía `api/caja.py`. Los indicadores por operador (T030–T035) **no** están bloqueados; el cruce contra el faltante de inventario (T033, T036, y la parte de `POST /caja/cruce-operador` de T037) **sí**. La prueba T032 (arqueo cuadrado no descarta el fraude) usa el `arqueo` de US1 — dependencia **hacia atrás**.
- **US4 (anomalías)** añade `listar_anomalias` / `resolver_anomalia` a `servicios/deteccion_fraude.py` (mismo archivo que US3 → en secuencia) y amplía `api/caja.py`. Las anomalías de origen efectivo (T042, T043) **no** están bloqueadas; las de origen inventario (T044) **sí**.

### Dependencia externa bloqueante (declarada, no oculta)

- **6 tareas afectadas por `001` User Story 5** (`conteo_fisico` / `conteo_renglon`, T065–T071 de `001/tasks.md`, en `[ ]`): **T021** (prueba `xfail`), **T023** (rama con `id_conteo_renglon`), **T033** (prueba `xfail`), **T036** (servicio del cruce), **T037** (endpoint `POST /caja/cruce-operador`), **T044** (prueba `xfail`). Mismo tratamiento que `004` dio a `consulta_no_atendida` (T014/T009 de `004`). Ver "Punto de reactivación".

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican; **ninguna prueba de integración antes de la migración T001 y los modelos T002**.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; **ningún endpoint antes de su modelo y su servicio**.
- Backend completo de la historia antes que su frontend.
- Toda historia con superficie de frontend termina con la verificación `tsc -b` / `eslint` / `vite build`.

### Oportunidades de paralelismo

- T002, T003, T004 y T005 de Foundational pueden ejecutarse en paralelo tras T001 (T004 espera a T002).
- Dentro de una historia, las pruebas marcadas `[P]` entre sí y las funciones de dominio marcadas `[P]` entre sí son paralelizables. Las que editan el mismo archivo van en secuencia por dependencia declarada, **no** en paralelo: `test_merma.py` (T019→T020→T021); `test_deteccion_fraude.py` (T031→T032→T033); `test_anomalias.py` (T042→T043→T044); `api/caja.py` (T013→T025→T037→T046); `servicios/deteccion_fraude.py` (T035→T036→T045); `frontend/src/servicios/caja.ts` (T015→T027→T039→T048); `test_contrato_caja.py` (T014→T026→T038→T047); `App.tsx` (T016→T028).
- **US3 puede empezar en paralelo con US2** una vez cerrada US1: `dominio/indicadores_operador.py` y `servicios/deteccion_fraude.py` son archivos nuevos que no colisionan con los de US2. Sólo `api/caja.py` y `App.tsx` se editan en varias historias — coordinar esas ediciones.

---

## Parallel Example: User Story 3

```bash
# Lanzar juntas las pruebas independientes de esta historia:
Task: "Prueba unitaria de tasa_anulaciones / concentracion_bajo_lista / mediana / se_desvia en tests/unidad/test_indicadores_operador.py"
Task: "Prueba de integración de indicadores por operador como desviación de pares en tests/integracion/test_deteccion_fraude.py"

# Lanzar juntas las funciones puras nuevas de US3:
Task: "tasa_anulaciones, concentracion_bajo_lista, mediana, se_desvia, reparto_proporcional_faltante en backend/rasero/dominio/indicadores_operador.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Foundational — crítica, bloquea todo lo demás.
2. Completar Fase 2: User Story 1, con sus pruebas obligatorias en verde.
3. **Detenerse y validar**: ejecutar los escenarios 1–5, 13–15 de `quickstart.md`.
4. Demostrar: un turno cierra → se registra el arqueo con la diferencia atribuida al operador y al día local; anular una venta después no cambia la diferencia; 10 `POST` producen un arqueo; un faltante sin motivo genera una `anomalia_caja` de origen efectivo. Sin ninguna dependencia de `conteo_fisico`.

### Entrega incremental

1. Foundational → esquema propio, parámetros, router y helper de día local listos.
2. + US1 (arqueo de caja) → probar de forma independiente → **MVP demostrable**.
3. + US2 (clasificar mermas + alerta de caducidad) → probar de forma independiente (escenarios 6–8; el 9 queda `xfail` hasta `001` US5).
4. + US3 (indicadores por operador) → probar de forma independiente (escenarios 10, 11; el 12 queda `xfail`).
5. + US4 (anomalías sin explicación) → probar de forma independiente (escenarios 13, 14).
6. Fase final: `quickstart.md` completo, auditoría de tokens, `DESIGN.md` actualizado, suite completa en verde (con los tres `xfail` de `001` US5).
7. **`001` implementó su User Story 5**: se siguió el "Punto de reactivación" — se quitaron los tres `xfail`, se completaron T023/T036/T037 y se re-ejecutó T054; suite en verde con 0 `xfail`.

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Foundational en conjunto.
2. Una persona construye US1 (tabla `arqueo`, router `api/caja.py`, `Arqueo.tsx`).
3. Cerrada US1, US2 y US3 pueden repartirse: viven en archivos nuevos propios (`servicios/mermas.py` + `dominio/merma.py` vs `servicios/deteccion_fraude.py` + `dominio/indicadores_operador.py`) y sólo comparten `api/caja.py` y `App.tsx`.
4. US4 va después de US3 porque `listar_anomalias` / `resolver_anomalia` viven en el mismo archivo que el servicio de US3.

---

## Notes

- Las tareas `[P]` tocan archivos distintos y no dependen de una tarea incompleta. Dos tareas que editan el mismo archivo nunca llevan ambas `[P]`: la segunda declara `(depende de <la primera>)`.
- La etiqueta `[Story]` traza cada tarea a su historia de usuario en spec.md.
- Las **7 suites obligatorias** de la tabla "Pruebas obligatorias" de plan.md están marcadas `[Obligatoria #N]` y deben pasar antes de fusionar, **todas contra PostgreSQL real en el puerto 5442**; no hay pruebas de interfaz, maquetación ni componentes visuales.
- **[006]** = tabla propia de este módulo (`arqueo`, `merma`, `anomalia_caja`); **[001-lectura: ...]** = consulta de solo lectura (nunca se altera su esquema ni se duplica). **No existe ninguna etiqueta `[001-escritura]`**: `006` **no escribe en ninguna tabla ajena**, ni siquiera vía función-puente (a diferencia de `003`, que escribía en `producto_precio_sucursal`). Los indicadores por operador **no son entidad** — son cálculo derivado sobre `001` (research.md #2, #7).
- **La Lectura Crítica n.º 1 es el principio rector**: FR-008 y la prueba T032 impiden que un arqueo con `diferencia = "0.00"` se presente como evidencia de ausencia de fraude por sub-registro. Ese fraude se detecta **sólo** por el cruce inventario-ventas y los indicadores por operador (T030–T036).
- **`anomalia_caja.resolucion` es texto libre** (research.md #18): se acepta perder la agregación por categoría de resoluciones a cambio de no imponer una taxonomía que el enunciado no pidió; la regla de reversión (añadir `categoria_resolucion` `ENUM` abierto + conservar el texto) es trabajo aditivo, no cambia las tres entidades.
- **`006` no ejecuta conteos ni ajusta existencia**: una merma declarada fuera de conteo (T023 rama libre) queda con `conciliar_con_conteo = true` a la espera de que `001` la resuelva en el próximo conteo (FR-034). `006` no tiene ningún contrato que dispare un conteo en `001` (FR-036, Principio V).
- Fuera de alcance de este desglose, evaluados y rechazados en research.md: cualquier librería estadística externa (`scipy`, `statsmodels`, `numpy`) para la línea base de los indicadores (research.md #16 — es `mediana` + razón); una cuarta entidad `senal_fraude_operador` (research.md #2 — cálculo derivado, no tabla); el desglose del arqueo por medio de pago (research.md #4 — espera a `007-pagos-seguridad`); un `ENUM` cerrado para `anomalia_caja.resolucion` (research.md #18).
