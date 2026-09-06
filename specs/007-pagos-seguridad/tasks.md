---

description: "Task list template for feature implementation"
---

# Tasks: Pagos y Seguridad

**Input**: Documentos de diseño desde `/specs/007-pagos-seguridad/`

**Prerequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md — todos aprobados contra la constitución **v2.2.6**. Requiere que `001-core-ventas-inventario` Setup + Foundational + User Story 1 ya esté migrada y en ejecución: este módulo **sólo lee** de `001` (`venta`, `turno`, `sucursal`, `operador` — nunca `pin_hash`) y **nunca escribe en ninguna tabla ajena**, ni siquiera vía función-puente (a diferencia de `003`). En particular **no escribe `venta.referencia_terminal_pago`**: ese campo lo puebla el propio servicio de venta de `001` con el token cuando `007` responde a tiempo (FR-007 de `001`); el vínculo autoritativo venta↔token es `token_pago.id_venta` (research.md #7). **Este módulo motivó la enmienda constitucional v2.2.6** (2026-09-05, ya aprobada y aplicada, informe de impacto en `constitution.md`), que añadió `token_pago` a su entrada en la tabla de Propiedad de Datos (de 4 a 5 entidades: `medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`).

**✅ SIN BLOQUEO — sin `xfail` en este módulo**: a diferencia de `006` (parcialmente bloqueado por `001` User Story 5), **ninguna User Story de `007` está bloqueada** por datos de `001` faltantes (`venta`, `turno`, `sucursal`, `operador` están entregadas; `research.md #11`) ni por la enmienda (v2.2.6 ya aplicada). **Si durante la implementación alguna tarea terminara necesitando `@pytest.mark.xfail`, es una DESVIACIÓN de lo establecido en plan.md ("Sin bloqueo") y DEBE señalarse explícitamente antes de introducirla, no resolverse en silencio.** T052 verifica por `grep` que `tests/` no contiene ningún `xfail` de este módulo.

**Pruebas**: se incluyen las **8 suites obligatorias** de la tabla "Pruebas obligatorias" de plan.md (Principio III — el riesgo central es doble: (a) que un PAN, un CVV o datos de banda/chip acaben persistidos, registrados o devueltos en algún punto —la violación más grave que este módulo puede cometer, prohibida por la constitución "Datos de pago" y el Principio IV—; (b) que una señal de firmware deshabilite una terminal o bloquee un cobro, convirtiendo una alerta consultiva en una interrupción de caja). **Todas corren contra PostgreSQL real en el puerto 5442, nunca contra mocks ni SQLite** — mismo criterio que `001`–`006`. No se generan pruebas de interfaz, maquetación ni componentes visuales.

**Organización**: por historia de usuario, en el **orden de prioridad ya fijado por spec.md y no renegociable**: US1 cobertura de medios de pago por sucursal (P1) → US2 terminales y vigilancia de firmware (P2) → US3 tokenización de los datos de pago (P3) → US4 bitácora de auditoría de pagos (P4). Backend antes que frontend dentro de cada historia. Fundamento (esquema de las cinco entidades, modelos, router, parámetros, helper de día local, servicio de anexado a la bitácora) antes de cualquier historia.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencia de una tarea incompleta). Dos tareas que editan el **mismo** archivo no llevan ambas `[P]`: la segunda depende de la primera.
- **[Story]**: historia de usuario a la que pertenece (US1 … US4)
- Cada tarea va en una sola línea, con la ruta de archivo exacta y, entre paréntesis, de qué tarea depende
- Cada tarea que toca datos indica explícitamente de dónde:
  - **[007]** — tabla propia de este módulo (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`)
  - **[001-lectura: ...]** — consulta de **solo lectura** a una o más tablas de `001` (nunca se altera su esquema ni se duplica). Los tests de frontera cuentan filas antes y después para verificar 0 escrituras
- **No existe ninguna etiqueta `[001-escritura]`** y **no hay ninguna tarea `⛔ BLOQUEADA`**.

## Convención de rutas (fijada en plan.md, extiende la de 001–006, no negociable)

- Backend: `backend/rasero/` (`dominio/`, `persistencia/`, `servicios/`, `api/`, `config/`, `tareas/`) y `backend/migraciones/versions/`
- Frontend: `frontend/src/` (`pantallas/`, `servicios/`) — **registro de Operación** para `TerminalesPago.tsx` y `BitacoraPagos.tsx` (radio 2px, IBM Plex Sans con cifras tabulares, sin animación salvo confirmación); **registro de Análisis** para `CoberturaPago.tsx` (radio 6px, Source Serif 4, una decisión por bloque). **Regla del Registro Sin Dinero**: cero apariciones del Verde Rasero en las tres pantallas (`007` no mueve dinero, FR-036)
- Pruebas: `tests/` en la raíz (`unidad/`, `integracion/`, `contrato/`)

---

## Phase 1: Foundational (bloqueante para las cuatro historias)

**Propósito**: esquema de las cinco entidades propias, modelos ORM, el router compartido, el módulo único de parámetros de configuración, el helper de día local y el servicio de anexado a la bitácora que las cuatro historias usan.

**⚠️ CRÍTICO**: no iniciar ninguna historia de usuario hasta terminar esta fase.

- [X] T001 Crear `backend/migraciones/versions/0007_pagos_seguridad.py`. `upgrade`: `CREATE EXTENSION IF NOT EXISTS btree_gist`; los `ENUM` (`marca_tarjeta('visa','mastercard','amex','diners','otra')`, `tipo_tarjeta('debito','credito','desconocido')`, `iniciador_bitacora('operador','proceso')`, `tipo_evento_bitacora` con los 14 valores de data-model.md, `referencia_recurso_bitacora('token_pago','venta','terminal_pago','medio_pago','cobertura_pago')`); y las cinco tablas de data-model.md: `medio_pago` (`nombre TEXT NOT NULL UNIQUE`, `requiere_terminal`/`admite_tokenizacion`/`activo BOOLEAN NOT NULL`); `terminal_pago` (`identificador TEXT NOT NULL UNIQUE`, `modelo`, `id_sucursal` FK→`sucursal`, `version_firmware TEXT NOT NULL CHECK (~ '^[0-9]+\.[0-9]+\.[0-9]+$')`, `fecha_ultima_actualizacion_firmware DATE NULL`, `historial_ubicacion`/`historial_firmware JSONB NOT NULL DEFAULT '[]'`, `id_operador_registro` FK→`operador` NOT NULL, `instante_registro`, `activa BOOLEAN NOT NULL DEFAULT TRUE`, índice `(id_sucursal)`); `cobertura_pago` (`id_medio_pago` FK, `id_sucursal` FK, `fecha_desde DATE NOT NULL`, `fecha_hasta DATE NULL CHECK (fecha_hasta IS NULL OR fecha_hasta >= fecha_desde)`, `id_operador` FK NOT NULL, `instante_registro`, restricción de exclusión `EXCLUDE USING gist (id_medio_pago WITH =, id_sucursal WITH =, daterange(fecha_desde, COALESCE(fecha_hasta,'infinity'::date), '[]') WITH &&)`, índice `(id_sucursal, fecha_desde)`); `token_pago` (`token TEXT NOT NULL UNIQUE`, `id_venta INTEGER NOT NULL UNIQUE` FK→`venta` (solo lectura), `clave_idempotencia TEXT NOT NULL UNIQUE`, `ultimos_digitos CHAR(4) NOT NULL CHECK (~ '^[0-9]{4}$')`, `marca marca_tarjeta NOT NULL`, `tipo tipo_tarjeta NOT NULL`, `id_terminal_pago` FK NOT NULL, `id_sucursal` FK NOT NULL, `instante`/`marca_tiempo_origen TIMESTAMPTZ NOT NULL`, `dia_local DATE NOT NULL`, **sin ningún campo de PAN/CVV/banda**, índice `(id_sucursal, dia_local)`); `bitacora_auditoria` (`id_bitacora_auditoria BIGINT PK`, `tipo_evento tipo_evento_bitacora NOT NULL`, `instante TIMESTAMPTZ NOT NULL`, `dia_local DATE NOT NULL`, `id_sucursal` FK NOT NULL, `id_terminal_pago` FK NULL, `id_medio_pago` FK NULL, `iniciador_tipo iniciador_bitacora NOT NULL`, `id_operador` FK NULL, `proceso TEXT NULL`, `resultado TEXT NOT NULL`, `referencia_recurso_tipo referencia_recurso_bitacora NULL`, `referencia_recurso_id TEXT NULL`, `clave_idempotencia TEXT NULL`, índices `(id_sucursal, dia_local)`, `(tipo_evento, id_sucursal, dia_local)`, `(id_terminal_pago) WHERE id_terminal_pago IS NOT NULL`, `UNIQUE (clave_idempotencia) WHERE clave_idempotencia IS NOT NULL`). `REVOKE UPDATE, DELETE ON bitacora_auditoria FROM rasero_app` (solo anexado, FR-025). Sembrar `medio_pago` desde `MEDIOS_PAGO_BASE` (T003). `downgrade`: `GRANT` de vuelta los privilegios, elimina las cinco tablas y los `ENUM` en orden inverso **[007]**
- [X] T002 [P] Crear los modelos SQLAlchemy 2.x `MedioPago`, `TerminalPago`, `CoberturaPago`, `TokenPago`, `BitacoraAuditoria` en `backend/rasero/persistencia/modelos.py` con los `CheckConstraint` de `data-model.md` (`ultimos_digitos ~ '^[0-9]{4}$'`, `version_firmware`, `fecha_hasta >= fecha_desde`) (depende de T001) **[007]**
- [X] T003 [P] Crear el módulo único de parámetros de configuración `backend/rasero/config/pagos.py` con los valores de arranque de research.md #10, sobrescribibles por variable de entorno — mismo patrón que `config/caja.py` de `006`: `MEDIOS_PAGO_BASE` (los 5 medios, cada uno con `requiere_terminal` / `admite_tokenizacion`), `DIGITOS_CONSERVADOS = 4`, `RETENCION_BITACORA_ANIOS = 2`, `ULTIMA_VERSION_FIRMWARE: dict[str, str] = {}`, `LISTA_FIRMWARE_VULNERABLE: list[dict] = []`, `BIN_MARCA: dict[str, str]` (prefijo → marca). Sin ninguna constante mágica dispersa (Principio V "acotada"); la justificación de cada valor vive en research.md #10, no en comentarios de código
- [X] T004 [P] Crear el router base `backend/rasero/api/pagos.py` con prefijo `/pagos` y montarlo en `backend/rasero/api/aplicacion.py`; incluir el manejador de error `{codigo, mensaje}` unificado con `001`–`006` (mensaje redactado para el operador, nunca una traza técnica) (depende de T002)
- [X] T005 [P] Helper de día local en `backend/rasero/dominio/pagos.py`: `dia_local(instante, zona_horaria) -> date` = `(instante AT TIME ZONE zona)::date` — mismo criterio que `001`/`004`/`005`/`006` (research.md #8); `007` implementa el suyo, no importa el de otro módulo
- [X] T006 Servicio de anexado a la bitácora `bitacora_pagos.anexar_entrada(sesion, *, tipo_evento, id_sucursal, iniciador_tipo, id_operador=None, proceso=None, resultado, id_terminal_pago=None, id_medio_pago=None, referencia_recurso_tipo=None, referencia_recurso_id=None, clave_idempotencia=None, instante=None)` en `backend/rasero/servicios/bitacora_pagos.py`: **sólo `INSERT`**; resuelve `dia_local` vía `dominio/pagos.py` (T005) y `sucursal.zona_horaria` de `001`; `resultado` se construye desde una **plantilla por `tipo_evento`**, nunca desde texto libre del cliente (research.md #6); si `clave_idempotencia` viene y ya existe una entrada con esa clave, devuelve la existente sin insertar (FR-037). Es la función que US1–US4 llaman para dejar rastro (depende de T002, T003, T005) **[007] [001-lectura: sucursal]**

**Checkpoint**: fundamento listo. Las historias de usuario pueden empezar.

---

## Phase 2: User Story 1 - Conocer y mantener la cobertura de medios de pago por sucursal (Priority: P1) 🎯 MVP

**Goal**: catálogo global de medios de pago; aceptación **histórica** por sucursal (tramos `[fecha_desde, fecha_hasta]`, sin solape); registro de eventos de intención de compra no atendida en la bitácora; y la cuota de intención no atendida **derivada** por sucursal y período. Es una métrica de cobertura (Lectura Crítica n.º 4), **no** un faltante de inventario ni una `consulta_no_atendida` de `001`. Establece el router `/pagos` y el cliente `pagos.ts` que las otras historias amplían. **No bloqueada** — sólo necesita `sucursal` de `001`.

**Independent Test**: `PUT /pagos/cobertura` abre un tramo de aceptación y cierra el anterior; `GET /pagos/cobertura` de un período pasado refleja los medios disponibles **entonces**, no los actuales; `POST /pagos/intencion-no-atendida` anexa un evento a la bitácora y **no** crea `venta` ni `consulta_no_atendida`; `GET /pagos/cobertura` exige `id_sucursal` y nunca agrega dos sucursales; la cuota de intención no atendida se desglosa por medio deseado.

### Pruebas obligatorias para User Story 1

- [X] T007 [P] [US1] Prueba unitaria de las funciones puras de cobertura en `tests/unidad/test_cobertura_dominio.py`: `cobertura_en_fecha(tramos, fecha) -> bool` (resuelve si un `(medio, sucursal)` estaba aceptado en una fecha dada), `cuota_no_atendida(eventos_por_medio: dict, total: int) -> dict[str, str]` (razón como cadena decimal con hasta 4 decimales; `"0"` si `total == 0`) (depende de T005) **[007]**
- [X] T008 [P] [US1] **[Obligatoria #7 — cobertura por sucursal, nunca faltante de inventario]** Prueba de integración en `tests/integracion/test_cobertura.py`, contra PostgreSQL real (puerto 5442): se cuentan las filas de `venta` y `consulta_no_atendida` de `001`; `POST /pagos/intencion-no-atendida` tres veces (claves distintas) → **0 filas nuevas** en `venta` y `consulta_no_atendida` (FR-005, SC-002), tres entradas `intencion_no_atendida` en la bitácora; `GET /pagos/cobertura?id_sucursal=` **exige** `id_sucursal` (`400 pagos_sucursal_requerida`) y nunca mezcla dos sucursales (FR-006, SC-003); la cobertura de un período anterior a `fecha_desde` de un medio lo muestra `cubierto: false` (FR-002, SC-001) (depende de T001, T002, T006) **[007] [001-lectura: venta, sucursal]**

### Implementación backend para User Story 1

- [X] T009 [P] [US1] Funciones puras en `backend/rasero/dominio/cobertura.py`: `cobertura_en_fecha(tramos, fecha)`, `cuota_no_atendida(eventos_por_medio, total)`, `cerrar_tramo_anterior(tramos, nueva_fecha_desde) -> date | None` (research.md #5) (depende de T005; implementa T007) **[007]**
- [X] T010 [US1] Servicio `cobertura_pago.declarar_cobertura(sesion, *, id_sucursal, id_medio_pago, acepta, fecha_desde, id_operador)` en `backend/rasero/servicios/cobertura_pago.py`: valida que `id_operador` sea `es_encargado` en `001` (`400 pagos_operador_no_encargado`, FR-007); cierra el tramo vigente en `fecha_desde − 1 día` (T009) y abre uno nuevo si `acepta`; la restricción de exclusión `gist` rechaza cualquier solape (`400 pagos_solape_de_tramos`); anexa `cobertura_declarada` a la bitácora vía `bitacora_pagos.anexar_entrada` (T006). **No** escribe en ninguna tabla de `001` (depende de T002, T006, T009) **[007] [001-lectura: sucursal, operador]**
- [X] T011 [US1] Servicios `cobertura_pago.listar_medios(sesion)` (catálogo, FR-001), `cobertura_pago.resumen_cobertura(sesion, *, id_sucursal, desde=None, hasta=None)` (exige `id_sucursal` → `400 pagos_sucursal_requerida`; para cada medio, si la sucursal lo aceptaba en el período; **deriva** la cuota de intención no atendida contando los eventos `intencion_no_atendida` de la bitácora de esa sucursal y período agrupados por `id_medio_pago` — research.md #5; devuelve `"sucursal inexistente en el período"` cuando corresponde) y `cobertura_pago.registrar_intencion_no_atendida(sesion, *, id_sucursal, id_medio_pago_deseado, id_operador, nota=None, clave_idempotencia)` (idempotente por `clave_idempotencia`; **sólo** anexa a la bitácora, **nunca** crea `venta` ni `consulta_no_atendida`, FR-005) en `backend/rasero/servicios/cobertura_pago.py` (depende de T010; implementa T008) **[007] [001-lectura: sucursal, operador]**
- [X] T012 [US1] Endpoints `GET /pagos/medios`, `PUT /pagos/cobertura`, `GET /pagos/cobertura` y `POST /pagos/intencion-no-atendida` en `backend/rasero/api/pagos.py` (depende de T010, T011, T004)
- [X] T013 [P] [US1] Prueba de contrato de los cuatro endpoints contra `contracts/openapi.yaml` (forma feliz + `400 pagos_sucursal_requerida` / `pagos_solape_de_tramos` / `pagos_operador_no_encargado` / `pagos_rango_invalido` + `404` medio/sucursal/operador + `200` de idempotencia de `intencion-no-atendida`), con el formato de error `{codigo, mensaje}` unificado con `001`–`006`, en `tests/contrato/test_contrato_pagos.py` (depende de T012)

### Implementación frontend para User Story 1

- [X] T014 [P] [US1] Cliente HTTP `listarMedios`, `declararCobertura`, `obtenerCobertura`, `registrarIntencionNoAtendida` en `frontend/src/servicios/pagos.ts` (depende de T012)
- [X] T015 [US1] Pantalla `CoberturaPago.tsx` (**registro de ANÁLISIS**: radio 6px, Source Serif 4, una decisión por bloque, líneas bajo 80 caracteres): por sucursal, qué medios acepta y desde cuándo; la cuota de intención de compra no atendida por medio deseado (**valor calculado** → `estimado` `#1F5673` + texto explícito); un momento de animación deliberado al revelar el desglose por medio deseado, nunca hover por fila; nueva pestaña "Pagos" en `frontend/src/App.tsx` que agrupará Cobertura / (más adelante) Bitácora. **Cero Verde Rasero** (Regla del Registro Sin Dinero). Invoca `new-work` de Impeccable (mundo visual de Análisis ya fijado por la constitución, `PRODUCT.md` existente, no se repite `init`) (depende de T014)
- [X] T016 [US1] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la pestaña Pagos → Cobertura (depende de T015)

**Checkpoint**: User Story 1 funcional y demostrable de forma independiente — cobertura histórica por sucursal y cuota de intención no atendida, sin crear ninguna `venta`. MVP.

---

## Phase 3: User Story 2 - Registrar las terminales de pago y vigilar su firmware y su exposición a clonación (Priority: P2)

**Goal**: registro de datáfonos físicos con su versión de firmware e historia de ubicación; indicadores **derivados y consultivos** ("desactualizada", "expuesta a clonación", "versión de referencia desconocida") calculados contra la configuración; el sistema **nunca** deshabilita una terminal. **No bloqueada** — sólo necesita su propio registro y `sucursal`.

**Independent Test**: para terminales con versiones de firmware conocidas y una config conocida de última versión y lista de vulnerabilidad, `GET /pagos/terminales` marca desactualizada cada una por debajo de la última versión, expuesta cada una en la lista de vulnerabilidad (con la referencia enumerada), "versión de referencia desconocida" cuando no hay última versión del modelo (nunca "al día"); ninguna señal deshabilita la terminal; una terminal movida atribuye su señal a la sucursal del tramo vigente en el momento evaluado.

### Pruebas obligatorias para User Story 2

- [X] T017 [P] [US2] **[Obligatoria #5 — unidad]** Prueba unitaria en `tests/unidad/test_firmware_dominio.py` de las funciones puras: `comparar_version("3.0.1", "3.2.0") -> -1` (tupla de enteros, sin librería de versionado); `evaluar_terminal(version, modelo, ultima_version_referencia, lista_vulnerable) -> {desactualizada, expuesta_a_clonacion, version_referencia_desconocida, referencias_vulnerabilidad}`; casos: lista de vulnerabilidad **vacía** → 0 expuestas; **sin** última versión de referencia del modelo → `version_referencia_desconocida = True`, `desactualizada = False`, **nunca** "al día" (FR-010) (depende de T005) **[007]**
- [X] T018 [P] [US2] **[Obligatoria #5 — integración]** Prueba de integración en `tests/integracion/test_terminales.py`, contra PostgreSQL real: cuatro terminales (al día / expuesta+desactualizada / desactualizada / modelo desconocido); `GET /pagos/terminales?id_sucursal=` marca cada una con el motivo enumerado (`referencias_vulnerabilidad` para la expuesta, versiones para la desactualizada); **ninguna** queda `activa = false`, bloqueada ni impedida de uso (FR-012, SC-005); una terminal movida de sucursal 1 a 2 aparece en `?id_sucursal=1` sólo para el tramo anterior y en `?id_sucursal=2` desde el movimiento (FR-014); `GET` exige `id_sucursal` (FR-034) (depende de T001, T002) **[007] [001-lectura: sucursal]**

### Implementación backend para User Story 2

- [X] T019 [P] [US2] Funciones puras en `backend/rasero/dominio/firmware.py`: `comparar_version(a, b)`, `evaluar_terminal(...)`, `sucursal_en_fecha(historial_ubicacion, fecha) -> int` (research.md #3) — **sin ninguna librería de versionado ni de terceros** (depende de T005; implementa T017) **[007]**
- [X] T020 [US2] Servicio `terminales_pago.registrar_terminal(sesion, *, identificador, modelo, id_sucursal, version_firmware, fecha_ultima_actualizacion_firmware=None, id_operador)` (valida `es_encargado`, `400 pagos_operador_no_encargado`, FR-015; `version_firmware` con formato `major.minor.patch`, `400 pagos_version_firmware_invalida`; `identificador` único, `400 pagos_identificador_duplicado`; inicializa `historial_ubicacion` con el tramo `[hoy, NULL]`; anexa `terminal_registrada` a la bitácora) en `backend/rasero/servicios/terminales_pago.py` (depende de T002, T006, T019) **[007] [001-lectura: sucursal, operador]**
- [X] T021 [US2] Servicios `terminales_pago.mover_o_retirar_terminal(sesion, *, id_terminal_pago, id_sucursal_destino=None, fecha_movimiento=None, retirar=False, id_operador)` (cierra el tramo vigente de `historial_ubicacion` y abre uno nuevo, o marca `activa = false` — **nunca borra**, Principio IV; anexa `terminal_movida`) y `terminales_pago.registrar_actualizacion_firmware(sesion, *, id_terminal_pago, version, fecha, id_operador)` (añade a `historial_firmware`, fija `version_firmware` y `fecha_ultima_actualizacion_firmware`, valida que la versión **avance**, `400 pagos_version_no_avanza`; anexa `firmware_actualizado`) en `backend/rasero/servicios/terminales_pago.py` (depende de T020) **[007] [001-lectura: sucursal, operador]**
- [X] T022 [US2] Servicio `terminales_pago.listar_terminales(sesion, *, id_sucursal, solo_con_senal=False)` en `backend/rasero/servicios/terminales_pago.py`: exige `id_sucursal` (`400 pagos_sucursal_requerida`); para cada terminal **calcula al leer** los indicadores con `dominio/firmware.py::evaluar_terminal` (T019) contra `ULTIMA_VERSION_FIRMWARE` y `LISTA_FIRMWARE_VULNERABLE` (config, T003) — **no hay tabla de indicadores** (research.md #3); ninguna consulta escribe nada (depende de T021; implementa T018) **[007] [001-lectura: sucursal]**
- [X] T023 [US2] Endpoints `POST /pagos/terminales`, `GET /pagos/terminales`, `PATCH /pagos/terminales/{id_terminal_pago}` y `POST /pagos/terminales/{id_terminal_pago}/firmware` en `backend/rasero/api/pagos.py` — `api/pagos.py` se **amplía**, no se reescribe (depende de T020, T021, T022, T012)
- [X] T024 [P] [US2] Ampliar la prueba de contrato con los cuatro endpoints de terminales (forma feliz + `400 pagos_version_firmware_invalida` / `pagos_identificador_duplicado` / `pagos_version_no_avanza` / `pagos_operador_no_encargado` / `pagos_sucursal_requerida` + `404` terminal/sucursal) en `tests/contrato/test_contrato_pagos.py` (depende de T023, T013)

### Implementación frontend para User Story 2

- [X] T025 [P] [US2] Cliente HTTP `registrarTerminal`, `listarTerminales`, `moverTerminal`, `registrarActualizacionFirmware` añadidos a `frontend/src/servicios/pagos.ts` (funciones nuevas, sin solape con las de T014) (depende de T023, T014)
- [X] T026 [US2] Pantalla `TerminalesPago.tsx` (**registro de OPERACIÓN**: radio 2px, IBM Plex Sans con cifras tabulares reales — versiones de firmware y fechas alinean por dígito—, sin tarjetas, **sin animación** salvo la confirmación de registrar una terminal o una actualización): tabla de terminales por sucursal con su versión de firmware (**dato observado**, tinta normal) y su estado; **expuesta a clonación** en crítico `#8E2A2A` + **punto lleno** con la referencia de la vulnerabilidad, **desactualizada** en atención `#9A5B08` + **punto medio**, **versión de referencia desconocida** en atención + **punto hueco** (Regla de los Tres Portadores); nueva pestaña "Terminales" en `frontend/src/App.tsx`. **Cero Verde Rasero**. Invoca `new-work` de Impeccable (mundo visual de Operación ya fijado) (depende de T025)
- [X] T027 [US2] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar la pestaña Terminales (depende de T026)

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente; el registro de terminales y las señales de firmware quedan demostradas sin que ninguna señal deshabilite una terminal.

---

## Phase 4: User Story 3 - Tokenizar los datos de pago de cada cobro con tarjeta (Priority: P3)

**Goal**: cuando una `venta` de `001` se cobra con tarjeta, conservar **únicamente** {token opaco, últimos 4 dígitos, marca, tipo, terminal, referencia de venta, clave de idempotencia}; **el PAN, el CVV y los datos de banda/chip nunca se almacenan, registran ni transmiten** (FR-017); un intento de persistir un PAN se **rechaza** y se registra sin el número (FR-018); idempotente por `id_venta` (un token por cobro, research.md #15); **no camino crítico** de un cobro (FR-020). **No bloqueada** — necesita `venta` y `terminal_pago` (US2), ambas disponibles.

**Independent Test**: `POST /pagos/tokens` devuelve un token opaco y persiste sólo los campos mínimos; un barrido de Luhn sobre columnas, logs, bitácora y respuestas no encuentra ningún PAN; un intento de PAN → `400 pagos_pan_detectado` + evento `pan_rechazado` sin el número; 10 `POST` con la misma `id_venta` → un solo `token_pago`; los 3 casos de reintento de research #15 (misma clave / clave distinta / clave reusada); una falla de tokenización deja la `venta` de `001` completada y `GET .../pago` → `404 pagos_venta_sin_tokenizacion`, con 0 escrituras en `001`.

### Pruebas obligatorias para User Story 3

- [X] T028 [P] [US3] **[Obligatoria #1 — unidad]** Prueba unitaria en `tests/unidad/test_token_dominio.py`: `generar_token()` devuelve un UUID v4 (opaco, sin relación derivable con la entrada, **dos llamadas para la misma tarjeta dan tokens distintos** — sin estabilidad entre ventas, research.md #4); `extraer_metadato("4111111111111111") -> ("1111", "visa", ...)` (últimos 4 + marca por BIN); `detectar_pan(texto) -> bool` (una secuencia de 13–19 dígitos que pasa Luhn en un lugar indebido); `es_luhn_valido` (depende de T005) **[007]**
- [X] T029 [P] [US3] **[Obligatoria #1 — integración: el PAN nunca se persiste ni se expone]** Prueba de integración en `tests/integracion/test_tokenizacion.py`, contra PostgreSQL real: tokenizar 20 cobros con números válidos distintos; barrer **todas** las columnas de las cinco tablas, el log de la aplicación y **todas** las respuestas de `GET /pagos/...` — **cero** secuencias de 13–19 dígitos que pasen Luhn (SC-006); cada `token_pago` tiene exactamente los 11 campos de data-model.md y nada más (SC-007); `GET /pagos/ventas/{id}/pago` devuelve `token` + `ultimos_digitos` (4), nunca el número; dos cobros con la **misma** tarjeta en dos ventas → dos `token` distintos (depende de T001, T002, T020) **[007] [001-lectura: venta, turno, sucursal]**
- [X] T030 [US3] **[Obligatoria #2 — rechazo de PAN sin registrar el número]** Prueba de integración en `tests/integracion/test_tokenizacion.py`: `POST /pagos/tokens` con `numero_tarjeta` colocado por error en un campo que no corresponde, o `ultimos_digitos` con 16 dígitos → `400 pagos_pan_detectado`; `GET /pagos/bitacora?tipo_evento=pan_rechazado` incluye una entrada cuyo `resultado` y `referencia_recurso_id` **no** contienen ningún dígito del número más allá de los 4 permitidos (FR-018, SC-008) (depende de T029) **[007]**
- [X] T031 [US3] **[Obligatoria #3 — idempotencia con los 3 casos de reintento de research #15]** Prueba de integración en `tests/integracion/test_tokenizacion.py`: (a) 10 `POST /pagos/tokens { id_venta: 42, clave_idempotencia: "k1" }` → la primera `201`, las 9 siguientes `200` con el **mismo** `token`, **una** fila en `token_pago` para `id_venta = 42` (SC-009); (b) `POST { id_venta: 42, clave_idempotencia: "k2" }` (clave nueva, bug del cliente) → `200` con el mismo `token` + entrada `token_idempotencia_divergente` en la bitácora; (c) `POST { id_venta: 99, clave_idempotencia: "k1" }` (clave reusada) → `409 pagos_clave_idempotencia_reusada` (depende de T030) **[007] [001-lectura: venta]**
- [X] T032 [US3] **[Obligatoria #4 — la tokenización no es camino crítico]** Prueba de integración en `tests/integracion/test_tokenizacion.py`: se cuentan las filas de `venta`, `turno` y `operador` de `001`; se simula una falla de la tokenización (captura cancelada) → la `venta` de `001` se completa con su comportamiento base y `referencia_terminal_pago` queda `NULL`; `GET /pagos/ventas/{id}/pago` → `404 pagos_venta_sin_tokenizacion` (FR-020, SC-010); el conteo de filas de las tres tablas de `001` es **idéntico** antes y después (`POST /pagos/tokens` no toca `001`, SC-013); al procesar el cobro pendiente después, se crea `token_pago` y la consulta pasa a `200` (depende de T031) **[007] [001-lectura: venta, turno, operador]**

### Implementación backend para User Story 3

- [X] T033 [P] [US3] Funciones puras en `backend/rasero/dominio/token.py`: `generar_token()` (`uuid.uuid4()`), `extraer_metadato(numero_tarjeta, bin_marca) -> (ultimos_digitos, marca, tipo)`, `es_luhn_valido(numero)`, `detectar_pan(texto)` — **sin ninguna librería de criptografía ni de terceros**; el número **no** se guarda en ninguna variable de larga vida ni se registra (research.md #4) (depende de T005; implementa T028) **[007]**
- [X] T034 [US3] Servicio `tokenizacion.emitir_token(sesion, *, id_venta, id_terminal_pago, numero_tarjeta, tipo="desconocido", clave_idempotencia, marca_tiempo_origen)` en `backend/rasero/servicios/tokenizacion.py`: valida `numero_tarjeta` con `es_luhn_valido` y longitud 13–19 (`400 pagos_numero_tarjeta_invalido`); si `detectar_pan` encuentra un PAN donde no corresponde → `400 pagos_pan_detectado` + `bitacora_pagos.anexar_entrada(tipo_evento="pan_rechazado", ...)` **sin** el número (T006); extrae {`ultimos_digitos`, `marca`, `tipo`} con `dominio/token.py` (T033) y **descarta `numero_tarjeta`**; genera el token; denormaliza `id_sucursal` y `dia_local` desde `venta → turno` de `001`; **idempotencia** (research.md #15): si existe `token_pago` para `id_venta` → devuelve `200` con el token existente (misma `clave_idempotencia` o distinta; si distinta, anexa `token_idempotencia_divergente`); si `clave_idempotencia` ya se usó para otra `id_venta` → `409 pagos_clave_idempotencia_reusada`; en el camino feliz anexa `token_emitido`. **No** ejecuta ningún `UPDATE` sobre `venta` de `001` (depende de T002, T003, T006, T033; implementa T029, T030, T031) **[007] [001-lectura: venta, turno, sucursal]**
- [X] T035 [US3] Servicio `tokenizacion.consultar_pago_de_venta(sesion, *, id_venta)` en `backend/rasero/servicios/tokenizacion.py`: responde **siempre** desde `token_pago` (nunca desde `venta.referencia_terminal_pago`); `404 pagos_venta_no_existe` si la venta no existe, `404 pagos_venta_sin_tokenizacion` si existe pero no hay `token_pago` (cobro en efectivo o tokenización no completada, FR-020). Devuelve `token` + `ultimos_digitos` + `marca` + `tipo`; **nunca** el número completo (depende de T034; implementa T032) **[007] [001-lectura: venta]**
- [X] T036 [US3] Endpoints `POST /pagos/tokens` (`numero_tarjeta` es `writeOnly` en el contrato — nunca en ninguna respuesta; el cuerpo de la petición **no** se registra literalmente) y `GET /pagos/ventas/{id_venta}/pago` en `backend/rasero/api/pagos.py` (depende de T034, T035, T023)
- [X] T037 [P] [US3] Ampliar la prueba de contrato con `POST /pagos/tokens` (forma feliz `201` + `200` de idempotencia + `400 pagos_pan_detectado` / `pagos_numero_tarjeta_invalido` + `404` venta/terminal + `409 pagos_clave_idempotencia_reusada`; verificar que la respuesta valida contra el schema `Pago` con `additionalProperties: false` y **no** contiene `numero_tarjeta`) y `GET /pagos/ventas/{id_venta}/pago` (forma feliz + `404 pagos_venta_no_existe` / `pagos_venta_sin_tokenizacion`) en `tests/contrato/test_contrato_pagos.py` (depende de T036, T024)

### Implementación frontend para User Story 3

- [X] T038 [US3] Cliente HTTP `consultarPagoDeVenta` añadido a `frontend/src/servicios/pagos.ts` (función nueva). **US3 no añade pantalla propia** (plan.md, Project Structure): el token y los últimos 4 dígitos de una venta se hacen **visibles** (Principio V) a través de `BitacoraPagos.tsx` (evento `token_emitido`, US4) y de este cliente, que el detalle de venta de `001` consumirá — no se toca ninguna pantalla de `001` en este módulo (depende de T036, T025)

**Checkpoint**: User Stories 1 a 3 funcionan de forma independiente; la tokenización conserva sólo el metadato mínimo, rechaza cualquier PAN, es idempotente por cobro y no bloquea la venta de `001`. **Sin `xfail`.**

---

## Phase 5: User Story 4 - Auditar la actividad de pagos en una bitácora consultable (Priority: P4)

**Goal**: exponer la bitácora de **solo anexado** de los hechos de pago que US1–US3 ya generan (`bitacora_pagos.anexar_entrada`, T006), consultable y filtrable por sucursal, terminal y tipo de evento; garantizar por el motor que una entrada no se modifica ni se borra (FR-025); y la tarea de purga de tokens huérfanos. **No bloqueada.**

**Independent Test**: para una secuencia conocida de hechos (emisión de token, rechazo de PAN, actualización de firmware, cambio de cobertura, intención no atendida) cada uno queda en la bitácora con su tipo, día local, sucursal, iniciador y resultado; un `UPDATE` o `DELETE` con el rol de aplicación falla; ninguna entrada contiene un PAN; los filtros por sucursal/terminal/tipo funcionan; la purga de un token huérfano deja rastro `token_purgado`.

### Pruebas obligatorias para User Story 4

- [X] T039 [P] [US4] **[Obligatoria #6 — bitácora de solo anexado, sin datos sensibles]** Prueba de integración en `tests/integracion/test_bitacora.py`, contra PostgreSQL real: ejecutar un ciclo completo (emitir token, rechazar un PAN, actualizar firmware, cambiar cobertura, registrar intención no atendida) → cada hecho genera una entrada con `tipo_evento`, `instante`, `dia_local`, `id_sucursal`, `iniciador_tipo` y `resultado` (SC-011); un `UPDATE bitacora_auditoria SET resultado = ...` y un `DELETE FROM bitacora_auditoria` con el rol `rasero_app` **fallan** con error de permiso (`REVOKE UPDATE, DELETE`, FR-025, SC-012); barrer todas las entradas → **ninguna** contiene una secuencia que pase Luhn ni un CVV (FR-026); `GET /pagos/bitacora` filtra por `id_sucursal` (obligatorio), `id_terminal_pago` y `tipo_evento` (FR-027) (depende de T001, T002, T006, T034) **[007] [001-lectura: sucursal]**

### Implementación backend para User Story 4

- [X] T040 [US4] Servicio `bitacora_pagos.consultar_bitacora(sesion, *, id_sucursal, id_terminal_pago=None, tipo_evento=None, desde=None, hasta=None)` en `backend/rasero/servicios/bitacora_pagos.py` (mismo archivo que `anexar_entrada` de T006 → en secuencia): exige `id_sucursal` (`400 pagos_sucursal_requerida`, FR-027); devuelve las entradas más recientes primero, filtradas; **no** existe ningún método de edición ni de borrado en este servicio ni en ningún otro (depende de T006; implementa T039) **[007] [001-lectura: sucursal]**
- [X] T041 [US4] Endpoint `GET /pagos/bitacora` en `backend/rasero/api/pagos.py` (depende de T040, T036)
- [X] T042 [P] [US4] Tarea invocable a mano `purgar_tokens_huerfanos` en `backend/rasero/tareas/purgar_tokens.py` (mismo patrón que `tareas/` de `002`/`005`/`006`): elimina las filas de `token_pago` cuyo `id_venta` ya no resuelve en `001` (venta archivada/borrada); por cada borrado anexa `token_purgado` a la bitácora (conserva sólo `id_venta`, `ultimos_digitos`, `marca` — nada sensible); **no** dispara ningún archivado en `001` (Principio V, research.md #4) (depende de T006, T034) **[007] [001-lectura: venta]**
- [X] T043 [P] [US4] Ampliar la prueba de contrato con `GET /pagos/bitacora` (forma feliz + filtros + `400 pagos_sucursal_requerida` / `pagos_rango_invalido`; verificar que **no** existe ningún endpoint `PATCH`/`PUT`/`DELETE` sobre `/pagos/bitacora` en `contracts/openapi.yaml`) en `tests/contrato/test_contrato_pagos.py` (depende de T041, T037)

### Implementación frontend para User Story 4

- [X] T044 [P] [US4] Cliente HTTP `consultarBitacora` añadido a `frontend/src/servicios/pagos.ts` (función nueva) (depende de T041, T038)
- [X] T045 [US4] Pantalla `BitacoraPagos.tsx` (**registro de OPERACIÓN**: radio 2px, IBM Plex Sans con cifras tabulares, sin tarjetas, **sin animación**): rastro consultable de los hechos de pago, filtros por sucursal / terminal / tipo de evento; las entradas `token_emitido` muestran el token y los últimos 4 dígitos (nunca más); las entradas `pan_rechazado` y `terminal_expuesta_detectada` en crítico `#8E2A2A`; **solo lectura** — ninguna acción de edición ni de borrado; integrada en la pestaña "Pagos" junto a Cobertura. **Cero Verde Rasero**. Invoca `new-work` de Impeccable (mundo visual de Operación ya fijado) (depende de T044, T015)
- [X] T046 [US4] Verificación `tsc -b`, `eslint` y `vite build` del frontend sin errores tras integrar Bitácora de pagos (depende de T045)

**Checkpoint**: las cuatro historias funcionan de forma independiente; la bitácora recoge de extremo a extremo los hechos de las tres historias anteriores, no admite edición ni borrado, y ninguna entrada contiene datos de pago completos. **Sin `xfail`.**

---

## Phase Final: Polish & Cross-Cutting Concerns

**Propósito**: validación de extremo a extremo y cumplimiento transversal.

- [X] T047 [P] Ejecutar los 16 escenarios de `quickstart.md` de extremo a extremo y confirmar el resultado esperado de cada uno. **Ninguno es `xfail`**: si alguno no puede comprobarse en verde, es una desviación de plan.md ("Sin bloqueo") y se señala explícitamente
- [X] T048 [P] Auditar `CoberturaPago.tsx` (Análisis) y `TerminalesPago.tsx` / `BitacoraPagos.tsx` (Operación): **cero apariciones del Verde Rasero `#0F5132`** (Regla del Registro Sin Dinero — `007` no mueve dinero); color, radio y tipografía sólo desde los tokens del sistema; los tres semánticos usados **sólo** por significado (crítico para terminal expuesta y PAN rechazado; atención para terminal desactualizada y versión de referencia desconocida; estimado para la cuota de intención no atendida y el indicador de exposición); "expuesta a clonación", "desactualizada", "versión de referencia desconocida" y "venta sin tokenización" con los tres portadores simultáneos (color + forma + texto)
- [X] T049 Actualizar `DESIGN.md` con la skill de Impeccable (agente `documenter`), derivándolo de las tres pantallas ya construidas — añade la descripción de `Pagos y Seguridad` a los componentes; sidecar `.impeccable/design.json` actualizado en el mismo cambio. **No** se añaden reglas nombradas nuevas en este pase
- [X] T050 Ejecutar `pytest tests` completo contra PostgreSQL real (puerto 5442) — las **8 suites obligatorias** (T029/T030/T031/T032 → `test_tokenizacion.py`; T028 → `test_token_dominio.py`; T017 → `test_firmware_dominio.py`; T018 → `test_terminales.py`; T039 → `test_bitacora.py`; T007 → `test_cobertura_dominio.py`; T008 → `test_cobertura.py`; contrato T013/T024/T037/T043 → `test_contrato_pagos.py`) — y `tsc -b`, `eslint`, `vite build` del frontend, **todo en verde y sin ningún `xfail`**
- [X] T051 Verificar que **todos** los parámetros de research.md #10 viven **sólo** en `backend/rasero/config/pagos.py` con sus valores de arranque, sin ninguna constante mágica dispersa (Principio V "acotada"); confirmar por `grep` que `backend/rasero/` **no importa ninguna librería de criptografía ni de terceros** para el token — es `uuid.uuid4()` de la biblioteca estándar (`dominio/token.py`); ni ninguna librería de versionado para el firmware — es comparación de tuplas de enteros (`dominio/firmware.py`)
- [X] T052 **Verificación explícita de "Sin bloqueo"**: por `grep` sobre `tests/`, confirmar que **ninguna** prueba de `007` (`test_cobertura*.py`, `test_terminales.py`, `test_firmware_dominio.py`, `test_tokenizacion.py`, `test_token_dominio.py`, `test_bitacora.py`, `test_contrato_pagos.py`) contiene `@pytest.mark.xfail` ni `pytest.skip`. Si aparece alguno, es una desviación de plan.md y debe estar documentada y aprobada
- [X] T053 [P] Verificar la frontera completa por `grep` sobre `backend/rasero/servicios/cobertura_pago.py`, `servicios/terminales_pago.py`, `servicios/tokenizacion.py` y `servicios/bitacora_pagos.py`: **cero** escrituras (`INSERT`/`UPDATE`/`add`/`merge`) sobre `venta`, `turno`, `operador`, `sucursal` ni ninguna otra tabla de `001` (FR-029, SC-013); **cero** `UPDATE` sobre `venta.referencia_terminal_pago` (no hay `[001-escritura]`, research.md #7); ninguna operación que deshabilite, bloquee o marque `activa = false` una terminal a partir de una señal de firmware (FR-012); **ningún cliente HTTP hacia un adquirente, pasarela o procesador de pago**, ningún endpoint de autorización/captura/settlement, ningún campo ni tabla de importe de pago (FR-036, SC-014)
- [X] T054 Verificar por consulta directa a PostgreSQL que el rol `rasero_app` **no tiene** privilegio `UPDATE` ni `DELETE` sobre `bitacora_auditoria` (`REVOKE` de T001 aplicado), y por `grep` sobre `contracts/openapi.yaml` y `backend/rasero/api/pagos.py` que **no existe** ningún endpoint que modifique o borre una entrada de bitácora (FR-025, SC-012)

---

## Dependencies & Execution Order

### Dependencias de fase

- **Foundational (Fase 1)**: sin dependencias externas salvo que `001` Setup + Foundational + User Story 1 ya esté migrada y en ejecución. **Bloquea** las cuatro historias de usuario.
- **Historias de usuario (Fases 2–5)**: todas dependen de Foundational. Dentro de cada una, pruebas antes que implementación, dominio puro antes que servicio, servicio antes que endpoint, backend completo antes que frontend.
- **Polish (Fase final)**: depende de que las cuatro historias estén completas. **No hay ninguna parte diferida ni bloqueada.**

### Dependencias entre historias

El orden **US1 → US2 → US3 → US4 está fijado por spec.md y no se reordena** (plan.md, "Estado de implementación por historia"). **Ninguna historia está bloqueada** (a diferencia de `006`):

- **US1 (cobertura)** establece el router `api/pagos.py`, el cliente `pagos.ts` y la pestaña "Pagos" de `App.tsx` que las demás amplían. Genera eventos `cobertura_declarada` e `intencion_no_atendida` en la bitácora (vía `anexar_entrada` de Foundational). Archivos propios: `dominio/cobertura.py`, `servicios/cobertura_pago.py`.
- **US2 (terminales y firmware)** añade `dominio/firmware.py` y `servicios/terminales_pago.py` (archivos nuevos) y amplía `api/pagos.py` y `pagos.ts`. `terminal_pago` es además la entidad que la tokenización (US3) referencia como terminal de captura → **US3 depende de US2** para esa FK.
- **US3 (tokenización)** añade `dominio/token.py` y `servicios/tokenizacion.py` (archivos nuevos) y amplía `api/pagos.py` y `pagos.ts`. Necesita `terminal_pago` (US2) y `venta` (`001`, disponible). No añade pantalla.
- **US4 (bitácora)** añade `consultar_bitacora` a `servicios/bitacora_pagos.py` (mismo archivo que `anexar_entrada` de Foundational → en secuencia) y `tareas/purgar_tokens.py` (nuevo); amplía `api/pagos.py`, `pagos.ts` y `App.tsx`. Consume los eventos que US1–US3 ya anexaron.

### Sin dependencia externa bloqueante

- **Ninguna tarea depende de trabajo pendiente de `001` ni de ningún otro módulo.** `venta`, `turno`, `sucursal` y `operador` están entregadas desde el checkpoint de `001` Setup + Foundational + User Story 1. La entidad `token_pago` la añadió la enmienda v2.2.6, ya aplicada. **No hay `xfail` en este módulo** — T052 y T050 lo verifican.

### Dentro de cada historia

- Pruebas obligatorias antes que la implementación que verifican; **ninguna prueba de integración antes de la migración T001 y los modelos T002**.
- Funciones de dominio puras antes que servicios; servicios antes que endpoints; **ningún endpoint antes de su modelo y su servicio**.
- Backend completo de la historia antes que su frontend.
- Toda historia con superficie de frontend termina con la verificación `tsc -b` / `eslint` / `vite build`.

### Oportunidades de paralelismo

- T002, T003, T004 y T005 de Foundational pueden ejecutarse en paralelo tras T001 (T004 espera a T002; T006 espera a T002/T003/T005).
- Dentro de una historia, las pruebas marcadas `[P]` entre sí y las funciones de dominio marcadas `[P]` entre sí son paralelizables. Las que editan el mismo archivo van en secuencia por dependencia declarada, **no** en paralelo: `test_tokenizacion.py` (T029→T030→T031→T032); `api/pagos.py` (T012→T023→T036→T041); `servicios/bitacora_pagos.py` (T006→T040); `frontend/src/servicios/pagos.ts` (T014→T025→T038→T044); `test_contrato_pagos.py` (T013→T024→T037→T043); `App.tsx` (T015→T026→T045).
- **US2 y US3 no pueden solaparse del todo**: US3 necesita la FK a `terminal_pago` de US2. US4 puede empezar en cuanto US1 haya generado los primeros eventos de bitácora, pero su prueba obligatoria T039 necesita también un `token_emitido` (US3).

---

## Parallel Example: User Story 3

```bash
# Lanzar juntas las pruebas independientes de esta historia:
Task: "Prueba unitaria de generar_token / extraer_metadato / detectar_pan / es_luhn_valido en tests/unidad/test_token_dominio.py"
Task: "Prueba de integración del barrido de Luhn sobre columnas/logs/bitácora/respuestas en tests/integracion/test_tokenizacion.py"

# Lanzar juntas las funciones puras nuevas de US3:
Task: "generar_token, extraer_metadato, es_luhn_valido, detectar_pan en backend/rasero/dominio/token.py"
```

---

## Implementation Strategy

### MVP primero (User Story 1 únicamente)

1. Completar Fase 1: Foundational — crítica, bloquea todo lo demás.
2. Completar Fase 2: User Story 1, con sus pruebas obligatorias en verde.
3. **Detenerse y validar**: ejecutar los escenarios 9, 10, 14 de `quickstart.md`.
4. Demostrar: una sucursal declara qué medios acepta con su fecha de inicio; un período pasado refleja el estado de entonces; tres eventos de intención no atendida producen una cuota por medio deseado sin crear ninguna venta.

### Entrega incremental

1. Foundational → esquema de las 5 tablas, parámetros, router, helper de día local y `anexar_entrada` listos.
2. + US1 (cobertura) → probar de forma independiente → **MVP demostrable**.
3. + US2 (terminales y firmware) → probar de forma independiente (escenarios 6–8 de `quickstart.md`).
4. + US3 (tokenización) → probar de forma independiente (escenarios 1–5 de `quickstart.md` — el barrido de Luhn es el más importante).
5. + US4 (bitácora) → probar de forma independiente (escenarios 11–13).
6. Fase final: `quickstart.md` completo, auditoría de pantallas, `DESIGN.md` actualizado, suite completa en verde **sin ningún `xfail`**, verificación de frontera y de "sin pasarela real".

### Estrategia de equipo en paralelo

Con más de una persona disponible:

1. El equipo completa Foundational en conjunto.
2. Una persona construye US1 (router `api/pagos.py`, `CoberturaPago.tsx`, pestaña "Pagos").
3. Cerrada US1, una persona construye US2 (terminales) y otra prepara US3 (tokenización) en cuanto la tabla `terminal_pago` exista; `dominio/token.py` y `servicios/tokenizacion.py` son archivos nuevos que no colisionan con los de US2.
4. US4 va al final porque su prueba obligatoria necesita hechos de US1–US3 ya registrados, y `consultar_bitacora` comparte archivo con `anexar_entrada`.

---

## Notes

- Las tareas `[P]` tocan archivos distintos y no dependen de una tarea incompleta. Dos tareas que editan el mismo archivo nunca llevan ambas `[P]`: la segunda declara `(depende de <la primera>)`.
- La etiqueta `[Story]` traza cada tarea a su historia de usuario en spec.md.
- Las **8 suites obligatorias** de la tabla "Pruebas obligatorias" de plan.md están marcadas `[Obligatoria #N]` y deben pasar antes de fusionar, **todas contra PostgreSQL real en el puerto 5442**; no hay pruebas de interfaz, maquetación ni componentes visuales.
- **[007]** = tabla propia de este módulo (`medio_pago`, `terminal_pago`, `cobertura_pago`, `bitacora_auditoria`, `token_pago`); **[001-lectura: ...]** = consulta de solo lectura (nunca se altera su esquema ni se duplica). **No existe ninguna etiqueta `[001-escritura]`**: `007` **no escribe en ninguna tabla ajena**, ni siquiera `venta.referencia_terminal_pago` (la puebla el servicio de venta de `001`, research.md #7). Los indicadores de firmware y la cuota de intención no atendida **no son entidad** — son cálculo derivado (research.md #3, #5).
- **El riesgo rector es el PAN**: FR-017/FR-018 y las pruebas T028–T030 (barrido de Luhn en columnas, logs, bitácora y respuestas; rechazo de PAN sin registrar el número) son la razón de ser del módulo. `token_pago.ultimos_digitos` es `CHAR(4)` con `CHECK` de exactamente 4 dígitos: barrera de esquema, no sólo de servicio.
- **`clave_idempotencia` la genera el cliente** (el flujo de captura de `001`), no el backend de `007` — misma convención que `venta.clave_idempotencia` de `001` (research.md #15). La idempotencia primaria es `UNIQUE (id_venta)` (un token por cobro, como `006` usa `UNIQUE (id_turno)` para el arqueo).
- **`007` no motiva ningún `xfail`**: a diferencia de `006` (bloqueado por `001` User Story 5), ninguna historia de `007` depende de trabajo pendiente. La enmienda v2.2.6 que añadió `token_pago` ya está aplicada. Cualquier `xfail` que aparezca es una desviación que debe señalarse. **Verificado en la implementación**: 0 `xfail` / 0 `skip` en las suites de `007` (T052); los 4 `xfail` de `004`/`006` siguen intactos.
- **DESVIACIÓN DOCUMENTADA de T001 — append-only de `bitacora_auditoria`**: en vez de `REVOKE UPDATE, DELETE ON bitacora_auditoria FROM rasero_app`, la migración `0007` instala un **TRIGGER `BEFORE UPDATE OR DELETE`** que lanza excepción. Motivo: en este entorno el rol de BD es `rasero` (dueño de las tablas y superusuario en desarrollo), sobre el que un `REVOKE` no surte efecto. El trigger cumple la misma intención —"rechazo del motor, no sólo de la aplicación"— de forma portable, y T039 lo verifica intentando un `UPDATE`/`DELETE` directo y esperando el error del motor (`DBAPIError`).
- **DESVIACIÓN menor de T049**: la entrada de "Pagos y seguridad" en `DESIGN.md` se redactó a mano a partir de las tres pantallas ya construidas (siguiendo el formato de la entrada de Promociones), no ejecutando el agente `documenter` de Impeccable. El sidecar `.impeccable/design.json` queda pendiente de `/impeccable document` — mismo estado en que está `006` hoy.
- Fuera de alcance de este desglose, evaluados y rechazados en research.md: cualquier pasarela, adquirente o procesador de pago real (FR-036); cualquier librería de criptografía para el token (research.md #4 — es `uuid.uuid4()`); cualquier librería de versionado para el firmware (research.md #3 — es comparación de tuplas); una 6.ª entidad para los eventos de intención no atendida (research.md #5 — son filas de `bitacora_auditoria`) o para los indicadores de firmware (research.md #3 — cálculo derivado).
