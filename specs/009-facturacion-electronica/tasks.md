# Tasks — 009-facturacion-electronica

**Entrada**: [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/openapi.yaml](./contracts/openapi.yaml), [spec.md](./spec.md)

**Pruebas**: sólo las suites obligatorias del Principio III: contrato de los endpoints de
factura, integración del flujo (generar al cobrar, idempotencia, correlativo sin huecos,
"Consumidor Final", anulación → nota de crédito, cobro que no se bloquea), y unidad del cálculo
de IVA y del formateo del secuencial. Sin pruebas de interfaz.

**Prerrequisito ya cumplido**: enmienda constitucional **v2.7.0** (Propiedad de Datos para 009).

---

## Fase 0 — Setup y Foundational (secuencial)

- [X] T001 `backend/rasero/configuracion.py`: `RUC_COMERCIO`, `RAZON_SOCIAL_COMERCIO`,
  `DIRECCION_COMERCIO` (opcional), `TARIFA_IVA` (default `"0.15"` → `Decimal`),
  `ESTABLECIMIENTO_SRI` (default `"001"`), `PUNTO_EMISION_SRI` (default `"001"`). Valores de
  demostración; ningún literal de la razón social/RUC reales (FR-004, FR-021).
- [X] T002 Migración `backend/alembic/versions/0013_factura_simulada.py`: tabla `factura_simulada`
  según data-model.md (CHECKs de `tipo`/`estado`, `UNIQUE (establecimiento, punto_emision, tipo,
  numero)`, `UNIQUE (id_venta) WHERE tipo='factura'`, FK `id_venta`→`venta`, FK
  `id_factura_referida`→`factura_simulada`). `downgrade` elimina la tabla. Reversible verificado.
- [X] T003 `backend/rasero/persistencia/modelos.py`: modelo ORM `FacturaSimulada`.
- [X] T004 `backend/rasero/api/facturas.py`: router registrado en `api/aplicacion.py`. Exige
  sesión de turno válida (`operador_de_sesion`), rol `cajero` (sin `exige_rol` extra). Sin
  endpoints todavía.

## Fase 1 — Dominio puro (independiente)

- [X] T005 [P] `backend/rasero/dominio/factura.py`: funciones puras
  `descomponer_iva(total: Decimal, tarifa: Decimal) -> (subtotal, monto_iva)` con
  `subtotal = round(total/(1+tarifa); 2)`, `monto_iva = total - subtotal` (research §6, sin
  céntimo perdido); `formatear_secuencial(establecimiento, punto, numero) -> str`
  (`EEE-PPP-NNNNNNNNN`).
- [X] T006 [P] **Prueba obligatoria** `tests/unidad/test_factura_dominio.py`: `descomponer_iva`
  para varios totales (incl. uno que da 3+ decimales) → `subtotal + monto_iva == total` siempre;
  `formatear_secuencial(1, 1, 42) == "001-001-000000042"`; tarifa 0.15 sobre 8.63 → (7.50, 1.13).

## Fase 2 — User Story 1: Factura al cerrar la venta (P1) 🎯 MVP

- [X] T007 [US1] `backend/rasero/servicios/facturacion.py`:
  `generar_factura(sesion, *, id_venta) -> FacturaSimulada`. Lee `venta`+`renglon_venta`+`producto`
  (001) y la `visita` identificada (002). Rechaza `venta` inexistente (404) y `venta.total == 0`
  (422, FR-010). **Idempotente**: si ya hay factura de esa venta, la devuelve (FR-012). Asigna el
  correlativo por `(establecimiento, punto_emision, 'factura')` con `MAX+1` bajo bloqueo
  (research §3). Graba todos los snapshots (emisor de config, comprador, renglones, subtotal/iva/
  total de `dominio/factura`, `medio_pago` etiqueta desde 007 — nunca datos de tarjeta, FR-020).
  **Cero escrituras sobre 001/002.**
- [X] T008 [US1] `servicios/facturacion.py`: `obtener_facturas_de_venta(sesion, id_venta) -> dict`
  (`{factura, nota_credito}`) y `obtener_factura(sesion, id_factura) -> FacturaSimulada`.
- [X] T009 [US1] `api/facturas.py`: `POST /facturas` (201/200 idempotente, 404, 422),
  `GET /facturas/venta/{id_venta}`, `GET /facturas/{id}/documento` — conforme a
  `contracts/openapi.yaml`. `aviso_simulacion` como texto fijo en toda respuesta `Factura`.
- [X] T010 [US1] **Prueba obligatoria de contrato** `tests/contrato/test_contrato_facturas.py`:
  forma del cuerpo `Factura`; `aviso_simulacion` siempre presente; 401 sin token; 422 con venta
  de total 0; 404 con venta inexistente.
- [X] T011 [US1] Prueba de integración `tests/integracion/test_facturacion_flujo.py` (Escenarios
  1–5, 12 de quickstart): factura al generar tras el cobro; total == `venta.total`;
  `subtotal + iva == total`; "Consumidor Final" sin cliente; identificado con cédula; idempotencia
  (una fila); correlativo sin huecos por sucursal (Escenario 4); `venta`/`renglon_venta` sin
  cambios (SC-005).
- [X] T012 [US1] `frontend/src/servicios/facturas.ts`: `generarFactura(idVenta)`,
  `obtenerFacturasDeVenta(idVenta)`.
- [X] T013 [US1] `frontend/src/componentes/FacturaSimulada.tsx`: render del documento (emisor,
  secuencial, comprador, tabla de renglones, subtotal/IVA/total, `medio_pago`) con el **aviso de
  simulación destacado** (FR-019), registro de Operación, sin Verde Rasero.
- [X] T014 [US1] `frontend/src/pantallas/Venta.tsx`: en `cobrar()`, tras `registrarVenta`, llamar
  `generarFactura(venta.id_venta).catch(...)` **sin bloquear** (mismo patrón que
  `registrarVisita`/`registrarRedencion`). En la vista de "venta registrada": mostrar
  `<FacturaSimulada>` si se generó, o un botón "Generar factura" si falló (Escenario 5).
- [X] T015 [US1] `DESIGN.md`: enmienda MENOR — regla "Presentación de documento formal" (bloque de
  documento con tratamiento propio + aviso de simulación destacado). No es enmienda
  constitucional (aditiva a DESIGN.md, misma clase que las specs anteriores).

**Checkpoint US1**: factura visible al cerrar la venta, demostrable sola.

## Fase 3 — User Story 2: Ver / regenerar (P2)

- [X] T016 [US2] `frontend/src/componentes/DocumentoImprimible.tsx`: envuelve `<FacturaSimulada>`
  en una vista con `window.print()` ("Ver como documento", FR-014). Sin PDF de servidor.
- [X] T017 [US2] `Venta.tsx` / vista de venta consultada: botón "Ver como documento" y, si no hay
  factura, "Generar factura" (reusa T012).
- [X] T018 [US2] Integración (Escenario 6 de quickstart): regenerar la factura de una venta
  antigua; segunda llamada devuelve la misma; una factura emitida no cambia al releerla (FR-013).

## Fase 4 — User Story 3: Anulación → nota de crédito (P3)

- [X] T019 [US3] `servicios/facturacion.py`: `emitir_nota_credito(sesion, *, id_venta)`. Exige
  que la `venta` esté anulada en 001 (409 si no). Si tiene factura `emitida`: la marca `anulada`,
  crea `nota_credito` con `id_factura_referida`, correlativo propio de `nota_credito`, totales que
  revierten. Si no hay factura: no hace nada (204, FR-016). Idempotente (FR-017).
- [X] T020 [US3] `api/facturas.py`: `POST /facturas/nota-credito/{id_venta}` (201/200/204/409).
- [X] T021 [US3] `Venta.tsx`: al anular (tras `anularVenta` de 001), llamar
  `emitirNotaCredito(venta.id_venta)` sin bloquear; mostrar la factura anulada + la nota de
  crédito en la vista de venta anulada.
- [X] T022 [US3] Integración (Escenarios 8, 9 de quickstart): anular con factura → nota de
  crédito que la referencia + factura `anulada`; anular sin factura → 204; `venta`/
  `anulacion_venta` de 001 sin cambios.

## Fase 5 — Verificación y cierre

- [X] T023 Auditoría de solo lectura (SC-005): `grep` sobre `servicios/facturacion.py` — cero
  `INSERT`/`UPDATE`/`DELETE` sobre `venta`, `renglon_venta`, `cliente`, `visita`; sólo `SELECT`.
- [X] T024 Auditoría de datos de pago (FR-020): ninguna factura contiene PAN, "últimos 4", ni
  ningún dato de instrumento — sólo `medio_pago` como etiqueta.
- [X] T025 Auditoría de literales (FR-021): "Despensa Los Ríos", el RUC real y los nombres de
  sucursales no aparecen en código, config ni identificador — sólo como valor de fila / valor de
  variable de entorno de un despliegue.
- [X] T026 Auditoría de aviso de simulación (SC-006): toda respuesta `Factura` y toda superficie
  del frontend que muestra un documento incluye `aviso_simulacion` visible.
- [X] T027 Suite completa `pytest tests` en verde (contrato + integración del flujo + unidad de
  dominio). Frontend `tsc -b` + `eslint .` + `vite build` en verde.
- [X] T028 Ejecutar los 13 escenarios de `quickstart.md` de extremo a extremo.
- [X] T029 Registrar la enmienda v2.7.0 en el historial de la constitución (ya hecha) y anotar
  009 en el conteo de entidades por módulo. Registrar la enmienda MENOR de DESIGN.md (regla de
  documento formal).

## Dependencias entre fases

- Fase 0 → todo.
- Fase 1 (dominio) independiente; en paralelo con Fase 2.
- US1 (Fase 2) es el MVP; entregable solo. `POST /facturas` + `<FacturaSimulada>` + el enganche
  en `Venta.tsx`.
- US2 (Fase 3) depende de US1 (necesita el componente y el servicio).
- US3 (Fase 4) depende de US1 (necesita la factura para anularla) y del flujo de anulación de 001
  (ya existe).
- Fase 5: tras todo lo demás.
