# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React 18 + Vite + TypeScript. Sin librería de componentes de terceros (Bootstrap, Material UI,
shadcn y equivalentes quedan excluidos): el sistema de diseño es propio y se implementa sobre
tokens definidos por el proyecto, no sobre los valores por defecto de un kit ajeno. Ya presente
en el repositorio (`frontend/package.json`, `frontend/vite.config.ts`), no una decisión abierta.

## Users

Esta superficie (el punto de venta de 001-core-ventas-inventario) tiene dos usuarios:

- **Cajero (primario)**: cobra en caja durante la jornada. Su situación es un local con
  clientes esperando; su trabajo es registrar la venta —mezclando unidades y productos a
  peso— sin que ninguna validación de inventario lo detenga. Se identifica al abrir turno
  eligiéndose de una lista y confirmando un PIN de 4 dígitos.
- **Encargado (secundario)**: interviene solo para reasignar un PIN olvidado y para anular una
  venta de un turno ya cerrado. No hay una jerarquía de roles más allá de esta distinción.

## Product Purpose

Registrar, en el punto de venta de un minimarket de dos sucursales, los hechos de venta e
inventario de los que dependen los demás módulos del sistema: qué se vendió, a quién se
atribuye, qué existencia queda y con qué precio. No decide acciones —no calcula margen, no
clasifica causa de merma, no ajusta precio—; registra hechos para que otros módulos decidan
sobre ellos. Éxito es que la caja nunca se detenga por una validación de inventario, y que el
inventario total sea siempre reconstruible desde su historial de movimientos.

## Positioning

Frente a un punto de venta genérico, este registra el hecho económico con precisión decimal
exacta (nunca coma flotante, ni en dinero ni en gramos), es idempotente ante reintentos de red,
y admite que el mismo producto tenga precio distinto por sucursal — todo antes de que ningún
otro módulo del sistema exista. Es infrecuente que un punto de venta genérico modele la venta a
peso con selección de lote por caducidad (FEFO) como regla de primera clase.

## Operating Context

Local físico de comercio de barrio, con sección de frescos vendidos a peso en báscula. Dos
sucursales (cardinalidad no acotada en el modelo; dos es el alcance de esta demostración). El
cajero trabaja en una caja física con conectividad potencialmente inestable. El encargado no
está siempre presente en el mismo local que el cajero.

## Capabilities and Constraints

Ya construido y verificado contra PostgreSQL real: registrar venta mixta (unidad + peso),
consumo de lote por caducidad con desempate por entrada (FEFO), resolución de precio efectivo
por sucursal (override opcional sobre un precio base), venta idempotente por clave, saldo de
existencia que admite negativo sin bloquear el cobro, anulación de venta atada al turno o a un
encargado. Pendiente de construir en esta superficie: las pantallas —apertura de turno, venta,
renglón a granel, anulación— aún no existen; este documento se escribe antes de la primera.
Pendiente también: aceptar cobros sin conexión y reconciliar después por orden real de
ocurrencia — lo exige el Principio II de la constitución, pero este módulo no lo tiene
implementado ni probado todavía; ninguna de las 17 pruebas automatizadas actuales cubre el
escenario sin conectividad.

Restricciones no negociables (constitución del proyecto): una sola moneda (USD); ninguna
validación de existencias bloquea un cobro; los mensajes de error deben indicar la acción
correctiva, nunca una traza técnica; el nombre del comercio ficticio de demostración
("Despensa Los Ríos", sucursales "Quevedo Centro" y "Buena Fe") vive solo como dato de fila y
no debe aparecer en ningún identificador técnico ni copy de interfaz.

## Brand Commitments

El sistema se llama **Rasero** — de la tabla que nivela una medida de grano al ras; la tesis
del producto es aplicar el mismo criterio objetivo a datos que hoy se juzgan por impresión. Es
una herramienta genérica, no construida para un comercio específico: ningún nombre de comercio
de demostración debe filtrarse a la marca visible de la interfaz.

## Evidence on Hand

Sin capturas, datos de uso real ni testimonios. El backend de esta superficie está construido y
verificado (17 pruebas automatizadas en verde contra PostgreSQL 18 real; flujo de venta
verificado a mano de extremo a extremo). No hay ninguna interfaz visual todavía —la evidencia
visual de "madurez" que exploraría un `init` normal no existe aquí.

## Product Principles

1. La caja no se detiene: ninguna validación de inventario o de red es camino crítico de un
   cobro.
2. El sistema registra hechos; no decide acciones de precio, reposición o clasificación de
   causa — eso pertenece a otros módulos.
3. Precisión exacta siempre: dinero y peso nunca se representan ni se comunican con
   redondeos silenciosos.
4. Todo dato mostrado con antigüedad o incertidumbre lo dice explícitamente, nunca solo con
   color.
5. El nombre del comercio de demostración es un dato, nunca una decisión de marca.

## Accessibility & Inclusion

Ninguna necesidad de usuario específica fue establecida más allá de la regla ya vigente en el
sistema de diseño: todo dato con antigüedad o incertidumbre debe comunicarse con tres
portadores simultáneos (color, forma, texto), no solo color, para no fallar ante daltonismo,
impresión en blanco y negro o reflejo de pantalla.
