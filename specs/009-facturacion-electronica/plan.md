# Implementation Plan: Facturación Electrónica (Simulada)

**Branch**: `009-facturacion-electronica` — sobre `master`, sin rama dedicada.

**Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

## Summary

Un documento con la **forma de una factura electrónica ecuatoriana**, generado **después** de
cada cobro confirmado y mostrado en la pantalla de "venta registrada". **Simulado y declarado
como tal**: sin SRI, sin firma, sin XML regulatorio. Cualquier `cajero` lo genera y lo ve.

- **US1 (P1)** — la factura aparece al cerrar la venta: emisor (razón social/RUC de
  configuración), secuencial `EEE-PPP-NNNNNNNNN` correlativo por sucursal, renglones, subtotal,
  IVA (tarifa configurable, 15 % por defecto), total, comprador ("Consumidor Final" si no se
  identificó), aviso de simulación visible.
- **US2 (P2)** — volver a ver / regenerar; idempotente por `id_venta`; una factura emitida es un
  snapshot inmutable.
- **US3 (P3)** — al anular la venta (flujo de 001 ya existente), la factura se marca anulada y se
  emite una nota de crédito simulada mínima.

**Una entidad nueva**: `factura_simulada` (tipo `factura` | `nota_credito`, todo snapshot),
declarada como propiedad de 009 en la constitución **v2.7.0** (ya hecha). 009 **consulta**
`venta` / `renglon_venta` de 001 y `cliente` de 002 sin poseerlos; **no escribe** contra ellos.

Extensión del mismo backend Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic sobre PostgreSQL 16
(puerto 5442) y el mismo frontend React 18 + TS + Vite. Migración `0013_factura_simulada`.

**Ejes del plan**:

1. **Enmienda v2.7.0 hecha antes de este plan** (patrón v2.2.3–v2.2.6): `factura_simulada`
   declarada, frontera "009 consume 001/002 sin modificarlos; la factura se genera tras el cobro
   y nunca lo bloquea; ningún dato de pago en la factura".
2. **Principio II**: la generación de la factura NO es camino crítico del cobro. El backend la
   expone como `POST /facturas` (a partir de `id_venta`) que el frontend llama **después** de
   `POST /ventas`, en el mismo patrón donde hoy llama `registrarVisita` / `registrarRedencion`
   (`Venta.tsx`, función `cobrar`). Si falla, se muestra un botón "Generar factura".
3. **Todo snapshot**: una factura emitida guarda su emisor, comprador, renglones y totales tal
   como estaban al emitir; cambiar la configuración o la venta después no la altera.
4. **Nada bloqueado**: 001–008 están todos (001–007 implementados; 008 sólo spec). 009 sólo
   necesita 001 y 002, ambos implementados.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend) — mismas
versiones que 001–007. Sin librería nueva: el cálculo de IVA es aritmética `Decimal` (mismo
`ROUND_HALF_UP` que 001); el secuencial es un `INTEGER` con `UNIQUE`.

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic; React 18, Vite, el sistema de
componentes base. Sin dependencias nuevas.

**Storage**: PostgreSQL 16 (5442). Una tabla nueva, `factura_simulada`, migración `0013`.

**Testing**: `pytest` contra PostgreSQL real. Suites obligatorias del Principio III: contrato de
`POST /facturas` / `GET /facturas/venta/{id_venta}`; integración del flujo (genera al cobrar,
idempotencia, correlativo sin huecos, "Consumidor Final", anulación → nota de crédito, cobro que
no se bloquea si la factura falla); unidad del cálculo de IVA y del formateo del secuencial.

**Target Platform**: servidor Linux (backend), navegador (frontend).

**Project Type**: web, extensión de la app existente.

**Performance Goals**: la generación de la factura es una operación de una fila + una consulta a
la venta; no cambia la percepción de tiempo del cobro (SC-007).

**Constraints**: solo lectura sobre 001/002 (SC-005); no bloquea el cobro (Principio II, SC-007);
idempotencia por `id_venta` (SC-004); secuencial correlativo sin huecos por sucursal (SC-003);
nunca datos de pago (FR-020); aviso de simulación en toda superficie (FR-001, SC-006); razón
social / RUC / IVA de configuración (FR-004).

**Scale/Scope**: una factura por venta; volumen de un minimarket de dos tiendas. El correlativo
por `(establecimiento, punto)` se protege con `UNIQUE` y se asigna en la transacción de
generación (`SELECT max+1` con bloqueo, o secuencia por combinación — research §3).

## Constitution Check

*GATE: debe pasar antes de la fase 0.*

| Principio | Estado | Nota |
|---|---|---|
| I — Dominio primero, contratos explícitos | ✅ | Sin librería nueva. `POST /facturas` / `GET /facturas/venta/{id}` con contrato OpenAPI. |
| II — Fiabilidad en el punto de venta | ✅ | La factura se genera DESPUÉS de la venta confirmada, con una llamada que no la bloquea ni revierte (mismo patrón que `visita`/`redencion`). |
| III — Pruebas proporcionales al riesgo | ✅ | Contrato + integración del flujo + unidad de IVA/secuencial. Sin pruebas de UI. |
| IV — Trazabilidad | ✅ | `factura_simulada` referencia su `venta` (única). Todo snapshot; regenerable de la venta si falta. Ningún dato de pago (FR-020). |
| V — Inteligencia explicable y reversible | N/A | 009 no tiene componente de inteligencia. |
| VI — Autorización y roles | ✅ | Rol `cajero` (constitución v2.5.0: la factura es flujo de caja, no pantalla de encargado). `exige_rol` no es necesario más allá de exigir sesión de turno válida. |
| Propiedad de datos | ✅ | v2.7.0 declara `factura_simulada` como propiedad de 009; frontera "009 consume 001/002 sin modificarlos". |
| Restricciones — datos de pago | ✅ | La factura NO contiene PAN/CVV/banda; a lo sumo el medio como etiqueta (FR-020). |
| Sistema de diseño | ⚠️ nueva regla | Una factura es una superficie de documento formal que hoy no existe en DESIGN.md. Se añade una regla de presentación de documento (bloque con tratamiento propio + aviso de simulación destacado) en el plan de detalle / al construir. Registro de Operación. Sin Verde Rasero. |

**Sin violaciones bloqueantes.** La regla de diseño nueva es aditiva (misma clase que las specs
anteriores añadieron reglas a DESIGN.md); se registra como enmienda MENOR de DESIGN.md al
construir US1, no requiere enmienda constitucional.

## Project Structure

### Documentation (this feature)

```text
specs/009-facturacion-electronica/
├── plan.md, research.md, data-model.md, quickstart.md, analysis.md
├── contracts/openapi.yaml
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/rasero/
├── persistencia/modelos.py            # + FacturaSimulada
├── configuracion.py                   # + RUC_COMERCIO, RAZON_SOCIAL_COMERCIO, DIRECCION_COMERCIO,
│                                      #   TARIFA_IVA, ESTABLECIMIENTO_SRI, PUNTO_EMISION_SRI
├── dominio/
│   ├── factura.py                     # cálculo de subtotal/IVA/total (Decimal, ROUND_HALF_UP);
│                                      # formateo del secuencial EEE-PPP-NNNNNNNNN; función pura
├── servicios/
│   └── facturacion.py                 # generar_factura(sesion, id_venta) idempotente;
│                                      # anular_factura_de_venta(sesion, id_venta) -> nota crédito;
│                                      # obtener_factura_de_venta(sesion, id_venta)
└── api/
    └── facturas.py                    # POST /facturas {id_venta}; GET /facturas/venta/{id_venta};
                                       # GET /facturas/{id_factura}/documento (vista imprimible: datos, no PDF)

backend/alembic/versions/
└── 0013_factura_simulada.py           # 1 tabla; UNIQUE (id_venta), UNIQUE (establecimiento, punto, numero)

# Punto de enganche de la anulación (US3): el servicio de anulación de 001 NO cambia. 009 se
# entera de la anulación de una de dos formas (research §5): (a) el frontend, tras anular, llama
# a POST /facturas/nota-credito/{id_venta}; o (b) un endpoint de 009 que el frontend llama en el
# mismo punto. NO se añade un hook dentro de servicios/ventas.py de 001.

frontend/src/
├── servicios/facturas.ts              # cliente de /facturas/*
├── componentes/
│   ├── FacturaSimulada.tsx            # render del documento (factura o nota de crédito) + aviso
│   └── DocumentoImprimible.tsx        # vista imprimible (window.print), reutilizable
├── pantallas/Venta.tsx                # tras cobrar: llamar generarFactura(venta.id_venta) sin
│                                      # bloquear; en la vista de "venta registrada" mostrar
│                                      # <FacturaSimulada> o el botón "Generar factura" si falló;
│                                      # al anular: emitir la nota de crédito y mostrarla
└── (sin cambio de nav: la factura vive dentro de Venta)

tests/
├── contrato/test_contrato_facturas.py
├── integracion/test_facturacion_flujo.py
└── unidad/test_factura_dominio.py     # IVA, redondeo, formato de secuencial
```

**Structure Decision**: extensión de la app. La factura vive **dentro del flujo de Venta**
(pantalla de "venta registrada" ampliada), sin entrada de nav propia. El servicio de 009 consume
los servicios/consultas de lectura de 001/002 (`sesion.get(Venta)`, renglones, la `visita`
identificada) y **nunca** llama a un servicio de escritura de esos módulos.

## Complexity Tracking

*Sin violaciones bloqueantes de la Constitución.* La única adición es una regla de presentación
de documento en DESIGN.md (enmienda MENOR de DESIGN.md, no de la constitución), justificada
porque una factura no encaja en ningún componente ni registro visual actual.
