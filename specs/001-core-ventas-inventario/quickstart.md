# Quickstart: Core de Ventas e Inventario

**Fase 1** · 2026-09-04 · Plan: [plan.md](./plan.md) · Contrato:
[contracts/openapi.yaml](./contracts/openapi.yaml) · Modelo: [data-model.md](./data-model.md)

Guía para levantar el módulo y comprobar de extremo a extremo que las seis reglas difíciles se
cumplen. No contiene código de implementación: eso pertenece a `tasks.md` y a la fase de
implementación.

## Requisitos previos

- **PostgreSQL 16 nativo**, no en contenedor, escuchando en el puerto **5442**. Docker Compose se
  resuelve en la fase final del proyecto, no aquí. SQLite está PROHIBIDO en toda fase.
- Python 3.12 y Node.js 20.
- Una base de datos vacía y un usuario con permiso para crear esquema.

Comprobación de que el motor está donde debe:

```bash
psql -h localhost -p 5442 -U <usuario> -d rasero -c "SELECT version();"
```

Si esto responde en el 5432 y no en el 5442, la instalación no cumple la constitución: el puerto no
es un detalle, existe para no colisionar con otros proyectos del curso en la misma máquina.

## Puesta en marcha

```bash
# Backend — desde la raíz del repositorio
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
alembic upgrade head                                 # crea el esquema
python -m rasero.semilla                             # carga el juego de datos de demostración
uvicorn rasero.api.aplicacion:app --reload --port 8000

# Frontend — en otra terminal, desde la raíz
cd frontend
npm install
npm run dev
```

El juego de datos de demostración carga el comercio ficticio **Despensa Los Ríos** con sus dos
sucursales, **Quevedo Centro** y **Buena Fe**. Ese nombre vive solo como valor de fila: no debe
aparecer en ningún nombre de tabla, endpoint, componente ni variable.

## Pruebas

```bash
# Desde la raíz. Las pruebas viven en tests/, no dentro de backend/ ni frontend/
pytest tests/unidad                 # reglas puras: totales, redondeo, selección de lote
pytest tests/integracion            # contra PostgreSQL real
pytest tests/contrato               # respuestas conformes a contracts/openapi.yaml
pytest tests                        # todo
```

Las seis suites obligatorias del Principio III deben estar en verde antes de fusionar. No hay
pruebas de interfaz, maquetación ni componentes visuales, por decisión expresa.

## Escenarios de validación

Cada escenario prueba una regla que no puede fallar. Los identificadores entre paréntesis remiten a
los requisitos del [spec](./spec.md).

### 1. Venta mixta con producto a peso (FR-001 a FR-003, SC-001)

Abre turno con PIN, cobra una venta que mezcle un producto por unidad y 0,7 kg de un producto a
granel.

**Esperado**: la venta queda registrada con su operador y su terminal; el renglón a granel descuenta
700 g del inventario; la interfaz muestra kilogramos aunque el almacenamiento sea en gramos enteros;
el importe del renglón está redondeado a dos decimales y el total es la suma de los importes ya
redondeados, no el redondeo de la suma.

### 2. Idempotencia (FR-008, SC-005)

Repite diez veces la misma petición de venta con la **misma** `clave_idempotencia`.

**Esperado**: exactamente una venta, un solo juego de renglones y un solo juego de movimientos de
inventario. La primera llamada responde `201`; las nueve siguientes, `200` con la venta original.
Ningún error.

### 3. Selección de lote por caducidad (FR-048)

Carga dos lotes del mismo producto: el lote **A** entra hoy y caduca en tres días; el lote **B**
entró la semana pasada y caduca en un mes. Vende.

**Esperado**: se consume primero el lote **A**, el de caducidad más próxima, aunque haya entrado
después. Este es el caso que distingue el criterio implementado de un FIFO puro; si se consume el
lote B, la implementación es incorrecta.

### 4. Saldo negativo y reconstrucción (FR-047, SC-004)

Con saldo 3 de un producto, vende 5.

**Esperado**: la venta **se registra** —ninguna validación de existencias bloquea el cobro—, la
respuesta incluye una advertencia, y la existencia queda en **−2**, visible como tal. A
continuación, recomputa el saldo sumando `movimiento_inventario` para ese producto y sucursal: debe
coincidir exactamente con el saldo consultado, incluido el valor negativo.

### 5. Traspaso con mercancía en tránsito (FR-017 a FR-019, SC-004)

Anota el inventario total del sistema. Despacha 8 unidades de Quevedo Centro a Buena Fe. Vuelve a
anotarlo. Confirma la recepción de 7.

**Esperado**: tras el despacho, el origen baja en 8, el destino no cambia, y **el total del sistema
es idéntico al de antes**: las 8 unidades pertenecen a la operación de traspaso, no desaparecen. Tras
confirmar 7, el destino sube en 7 y el sistema expone una discrepancia de 1 asociada a ese traspaso,
sin clasificarla ni absorberla.

### 6. Reconciliación offline (FR-037 a FR-041, SC-006)

Detén el backend, registra varias operaciones desde el punto de venta, vuelve a levantarlo y
sincroniza. Incluye dos operaciones sobre el mismo recurso con marcas de tiempo de origen distintas.

**Esperado**: las operaciones suben en orden de `marca_tiempo_origen`; sobre el mismo recurso
prevalece la **más antigua**; la desplazada queda en `conflicto_resuelto` con referencia a la que
prevaleció y **sigue siendo consultable**. Ninguna desaparece.

### 7. Consulta no atendida en dos toques (FR-020, FR-021, SC-002)

Desde la pantalla de venta, marca un producto agotado como consultado y no atendido.

**Esperado**: dos toques, menos de cinco segundos, sin pedir ningún dato del cliente y sin sacar al
cajero del flujo de cobro. El registro guarda el saldo del producto en ese instante.

### 8. Comparación de precios con antigüedad (FR-022 a FR-028, SC-007)

Captura tres observaciones de canales distintos, una de ellas en otra presentación (500 g frente a
tu kilogramo). Abre la comparación.

**Esperado**: cada observación aparece normalizada a precio por unidad de medida, con su antigüedad
mostrada mediante **tres portadores simultáneos** —color semántico, indicador de forma y texto del
tipo "hace 3 d"—. Ninguna antigüedad se comunica solo por color. El sistema no ajusta ningún precio.

### 9. Conteo físico y diferencia (FR-029 a FR-032, SC-008)

Inicia un conteo sobre un subconjunto de productos y captura cantidades distintas de las esperadas.

**Esperado**: la diferencia se expone por producto y por lote, **sin clasificar su causa**. Al
resolver, cada diferencia distinta de cero genera un ajuste trazable al conteo, y el saldo anterior
sigue siendo reconstruible.

### 10. Capital inmovilizado por categoría (FR-033 a FR-036)

Ten dos lotes con la misma antigüedad de última salida: uno de una categoría de frescos con umbral
corto, otro de no perecedero con umbral largo.

**Esperado**: solo aparece señalado el de frescos. Una categoría sin umbral propio hereda el umbral
global de respaldo. Un lote sin costo registrado aparece con valor **no calculable**, nunca cero. El
sistema no propone ninguna acción sobre lo señalado.

### 11. Roles, sucursal fija y autorización centralizada (FR-054 a FR-064, SC-012 a SC-014)

Con la semilla migrada: `Ana Cajera` (`cajero`, Quevedo Centro), `Luis Encargado` (`encargado`,
Quevedo Centro), `Marta Administradora` (`admin`, Quevedo Centro).

**Esperado**:
- `Ana` abre turno sin ver selector de sucursal (se fija a Quevedo Centro); un `POST /turnos` con
  otra sucursal responde `422` `codigo: "turno_sucursal_no_asignada"` y no crea turno.
- `Marta` ve el selector y puede abrir turno en Buena Fe.
- Con turno de `Ana`, el nav no muestra "Administración" ni el atajo "+ Crear producto"; un
  `POST /pagos/terminales` directo se rechaza por rol.
- Con turno de `Luis`, Administración muestra las 5 pestañas de maestros pero no "Operadores".
- Con turno de `Marta`, aparece la 6.ª pestaña "Operadores"; puede crear un `cajero` nuevo y
  cambiarle la sucursal. Un `PUT /operadores/{id}` firmado por `Luis` que suba a alguien a
  `encargado` se rechaza.
- `grep -r es_encargado backend/ frontend/src/` no devuelve nada; `requiere_rol` es la única vía
  de verificación de rol en el backend.

## Comprobaciones de diseño

No llevan prueba automatizada —la interfaz está exenta por el Principio III— pero se verifican a
ojo antes de dar el módulo por terminado:

- Los colores, tipografías y radios salen de variables CSS en `frontend/src/estilos/tokens.css`. No
  hay valores incrustados en componentes.
- Registro de **Operación**: tabla como elemento principal, alta densidad, sin tarjetas, radio de
  borde 2px.
- Tipografía IBM Plex Sans con **cifras tabulares reales**: las columnas de dinero y de peso alinean
  por dígito. **Inter no aparece en ninguna parte.**
- La única animación presente confirma una acción del usuario. Nada se anima por scroll ni por hover
  pasivo.
- Los mensajes de error indican la acción correctiva y no vuelcan trazas técnicas en la caja.
