<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.7.1 → 2.7.2
Tipo de cambio: MENOR — cambio de esquema ADITIVO PURO sobre `venta` (001) + actualización
de la frontera de "factura" (009). NO redefine ningún principio.

Motivo: una auditoría end-to-end del POS encontró que el sistema no registraba con qué
pagaba el cliente. La `venta` sólo llevaba `referencia_terminal_pago` (una cadena opaca que
el frontend nunca poblaba) y la factura simulada de 009 deducía el medio con una heurística
de dos valores. El enunciado del docente no PIDE registrar el medio por transacción (la
Lectura Crítica n.º 4 lo trata como métrica de cobertura por sucursal), pero la factura ya
mostraba el campo: se decide capturarlo de verdad en el POS.

Contenido añadido:
  - `venta` gana `id_medio_pago` (FK → `medio_pago` de 007, NULL-able, sin default). Es la
    CATEGORÍA del pago que el cliente elige en la pantalla de Venta, nunca un dato de
    instrumento (PAN/CVV/banda siguen fuera de todo módulo, Principio IV).
  - Migración `0014_venta_medio_pago`, aditiva y reversible. `NULL` en toda venta anterior.
  - La factura de 009 usa el nombre del medio declarado y cae a su heurística previa cuando
    la venta no lo trae. 009 no cambia su esquema.

Principios modificados: ninguno. `venta` es de 001; el cambio de esquema se hace en su módulo
propietario (regla de Propiedad de Datos). El catálogo `medio_pago` es de 007 y sólo se
consulta.
Secciones añadidas / eliminadas: ninguna. Se actualiza la entrada de 001 en "Propiedad de
Datos y Nomenclatura" (nota de cambio de esquema, igual que v2.3.0) y la frontera de
"factura".

Puerta de sincronización de enmiendas (v2.2.0): toca la nota de esquema de una entrada de la
tabla de Propiedad de Datos y una frontera, no el texto de ningún principio. Artefactos
afectados: `001-core-ventas-inventario` (modelo `Venta`, `api/ventas.py`, `servicios/ventas.py`,
`frontend` pantalla de Venta) y `009-facturacion-electronica` (`servicios/facturacion.py`).
Tests: `tests/integracion/test_facturacion_flujo.py`. No se barren las citas de 002–008.
`DESIGN.md` NO cambia (el selector de medio reutiliza el patrón de `<select>` ya presente en
Venta).

Historial: 2.7.2 (2026-09-08) — esta enmienda: `venta` gana `id_medio_pago` (FK NULL-able →
`medio_pago` de 007) para registrar el medio de pago que elige el cliente en el POS. Migración
0014, aditiva y reversible. La factura de 009 lo usa cuando existe. Sin redefinir principios.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.7.0 → 2.7.1
Tipo de cambio: PARCHE — corrige una contradicción interna, no redefine ninguna regla.

Motivo: una auditoría end-to-end encontró que el cuerpo del Principio VI ("Tres roles…")
decía "`encargado` añade la administración de datos maestros", mientras que la tabla de
"Autorización de pantalla" de la enmienda v2.5.0 —posterior— ya listaba "Administración:
gestión de operadores, alta/edición de datos maestros" bajo "`admin` (en exclusiva)". El
frontend (`App.tsx`) y el backend (`api/administracion.py` + `servicios/administracion.py`)
seguían la frase vieja y dejaban que un `encargado` administrara `sucursal` / `producto` /
`categoria` / `zona_exhibicion` / `medio_pago`. Esta enmienda corrige el cuerpo para que
coincida con la tabla y con `api/operadores.py` (que ya exige `admin`).

Principios modificados: ninguno redefinido. Se reescribe una frase descriptiva del Principio
VI, "Tres roles, jerarquía cerrada y acumulativa", para trasladar "administración de datos
maestros" de `encargado` a `admin` (en exclusiva) — coincide con la regla que la tabla de
v2.5.0 ya fijaba. El alta y la edición de `cliente` NO cambian (siguen sin restricción de rol).
Secciones añadidas / eliminadas: ninguna. Cambio de esquema: ninguno.

Puerta de sincronización de enmiendas (v2.2.0): toca el texto de un principio pero no cambia
el significado de ninguna regla ya escrita (la tabla de v2.5.0 ya decía esto) ni la tabla de
Propiedad de Datos. El artefacto materialmente afectado es `001-core-ventas-inventario` (el
nav y `Administracion.tsx` viven ahí; los routers `api/administracion.py` y el servicio pasan
de `exige_rol("encargado")` a `exige_rol("admin")`). Tests actualizados:
`tests/integracion/test_administracion.py`, `test_autorizacion.py`, `test_sesion_turno.py`.
No se barren las citas de versión de 002–009: nada de lo que especifican cambia. `DESIGN.md`
NO cambia.

Historial: 2.7.1 (2026-09-08) — esta enmienda: "administración de datos maestros" pasa de
`encargado` a `admin` (en exclusiva) en el cuerpo del Principio VI, alineándolo con la tabla
de Autorización de pantalla v2.5.0. `App.tsx`, `api/administracion.py` y
`servicios/administracion.py` pasan a exigir `admin`. Sin cambio de esquema.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.6.0 → 2.7.0
Tipo de cambio: MENOR — añade una entrada a la tabla de Propiedad de Datos y una
frontera nueva. NO redefine ningún principio.

Motivo: la especificación de `009-facturacion-electronica` introduce una entidad
propia, `factura_simulada` —el documento con la FORMA de una factura electrónica
ecuatoriana (RUC del comercio, razón social, secuencial `establecimiento-punto-
correlativo`, subtotal, IVA, total, datos del comprador o "Consumidor Final"),
SIN conexión real al SRI, sin firma electrónica y sin XML válido para el ente
regulador—. La Puerta de Sincronización de Enmiendas (v2.2.0) exige declararla en
la tabla de Propiedad de Datos ANTES de planificar 009, igual que v2.2.3–v2.2.6.

Contenido añadido:
  - Entrada `009-facturacion-electronica` en "Propiedad de Datos y Nomenclatura":
    `factura_simulada`, propiedad de 009.
  - Frontera nueva: 009 es CONSUMIDOR de 001 (`venta`, `renglon_venta`) y de 002
    (datos de `cliente` si se identificó), nunca dueño; no modifica ninguna tabla
    de 001–002. La factura se genera DESPUÉS de que la venta ya está confirmada y
    NUNCA bloquea el cobro (Principio II), mismo patrón que `redencion_promocion`
    (005) y `visita` (002).
  - Nota de alcance: la simulación es una limitación honesta, no un intento fallido
    de integración real — mismo criterio que 007 usó para "sin pasarela real".

Principios modificados: ninguno. El PAN/CVV/datos de tarjeta siguen sin
almacenarse en ningún módulo (Principio IV, Restricciones Técnicas): una factura
simulada NO contiene datos de pago, sólo el medio ("efectivo", "tarjeta") como
etiqueta.
Secciones añadidas: entrada y frontera en "Propiedad de Datos y Nomenclatura".
Secciones eliminadas: ninguna.
Cambio de esquema sobre entidades de 001–008: ninguno.

Puerta de sincronización de enmiendas (v2.2.0): toca la tabla de Propiedad de
Datos, no el texto de ningún principio. Se sincroniza esa sección y las citas de
`009` (nacen citando v2.7.0). NO se barren las citas de 001–008. `DESIGN.md`
gana, si acaso, una regla nueva para la presentación del documento de factura —
se decide en el plan de 009, no aquí (una factura es una superficie de lectura
formal que hoy el sistema no tiene).

Historial de versiones (resumen):
  - 2.7.0 (2026-09-07) — esta enmienda: entrada `009-facturacion-electronica`
    (`factura_simulada`) en Propiedad de Datos + frontera "009 consume 001/002,
    nunca los modifica; la factura se genera tras el cobro y nunca lo bloquea".
    Factura SIMULADA — sin SRI, sin firma, sin XML válido. Sin cambio de esquema
    sobre 001–008.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.5.0 → 2.6.0
Tipo de cambio: MENOR — añade una entrada a la tabla de Propiedad de Datos y una
frontera nueva. NO redefine ningún principio: el clustering de 008 encaja en el
Principio V ("Inteligencia Explicable y Reversible") tal como está escrito.

Motivo: la especificación de `008-reportes-inteligencia` introduce tres entidades
DERIVADAS y regenerables —`agregado_reporte` (caché de una vista), `segmento_cliente`
(definición de un grupo del clustering) y `asignacion_segmento` (cliente ↔ grupo)—.
La Puerta de Sincronización de Enmiendas (v2.2.0) exige declararlas en la tabla de
Propiedad de Datos ANTES de planificar 008, igual que v2.2.3–v2.2.6 hicieron para
las entidades reales de 003–007.

Contenido añadido:
  - Entrada `008-reportes-inteligencia` en "Propiedad de Datos y Nomenclatura", con
    las tres entidades marcadas como derivadas/regenerables.
  - Frontera nueva: "008 es capa de solo lectura sobre 001–007; nada de 008 alimenta
    de vuelta". La etiqueta de segmento en el detalle de `cliente` (002) es lectura
    de `asignacion_segmento` de 008, no una columna de `cliente`.
  - Nota de que el clustering (k-means / Lloyd, semilla fija, sin librería pesada ni
    datos externos) satisface el Principio V sin cambiarlo.

Principios modificados: ninguno.
Secciones añadidas: entrada y frontera en "Propiedad de Datos y Nomenclatura".
Secciones eliminadas: ninguna.
Cambio de esquema sobre entidades de 001–007: ninguno. Las tres entidades nuevas
son de 008 y no existen hasta que 008 se implemente.

Puerta de sincronización de enmiendas (v2.2.0): la enmienda toca la tabla de
Propiedad de Datos pero NO el texto de ningún principio. Se sincroniza esa sección
y las citas de versión vigente de `008` (su spec/plan/data-model nacen citando
v2.6.0). NO se barren las citas "v2.5.0"/"v2.4.0" de 001–007: su especificación no
cambia. `DESIGN.md` NO cambia: el activo `despensa-logo-mono-800w.png` YA está
reservado ahí para "reportes, dashboards y la marca de agua de los estados vacíos";
008 realiza esa reserva sin añadir ni redefinir ninguna regla de diseño.

Historial de versiones (resumen):
  - 2.6.0 (2026-09-07) — esta enmienda: entrada `008-reportes-inteligencia` en la
    tabla de Propiedad de Datos (`agregado_reporte`, `segmento_cliente`,
    `asignacion_segmento`, las tres derivadas y regenerables) + frontera "008 sólo
    lee de 001–007". El clustering encaja en el Principio V sin cambios. Sin cambio
    de esquema sobre 001–007.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.4.0 → 2.5.0
Tipo de cambio: MENOR — ampliación material de una guía existente. Añade al
Principio VI ("Autorización y Roles") una sub-sección nueva, "Autorización de
pantalla", con la tabla de rol mínimo por pantalla. NO redefine ni elimina
ninguna regla: los tres roles, la jerarquía acumulativa, `requiere_rol` /
`exige_rol`, "Ocultar, no deshabilitar", la identidad de sesión y la excepción
de `cliente` quedan exactamente como estaban.

Motivo: una auditoría encontró que "Ocultar, no deshabilitar" y "Autorización
centralizada, nunca duplicada" sólo se aplicaban a "Administración" (y
parcialmente a algunos endpoints de `007`). Las otras 13 pantallas del nav
—Traspasos, Capital, Precios, Competencia, Pronóstico, Clientes, Promociones,
Caja y fraude, Terminales, Pagos/Cobertura— eran visibles y llamables por
cualquier `cajero`, contra este mismo principio. La constitución YA asignaba a
`encargado` "las terminales de pago y la cobertura de medios de pago"; eso
tampoco se cumplía en el nav. Esta enmienda no crea una regla, cierra el
incumplimiento tácito (que la propia Gobernanza prohíbe mantener).

Contenido añadido: sub-sección "Autorización de pantalla" en el Principio VI —
tabla cajero/encargado/admin → pantallas; la nota de que la LECTURA de `cliente`
puede quedar en `cajero` si Venta la comparte; la nota de que los endpoints de
sólo-lectura que un flujo de cajero necesita (cupones/ofertas de recompra de
`AplicarPromocionVenta`, sucursales, productos, existencias) NO se cierran; y que
`Arqueo` sale del grupo de nav "Caja y seguridad" y va junto a `Venta`.

Principios modificados: ninguno redefinido (Principio VI ampliado, aditivo).
Secciones añadidas: sub-sección "Autorización de pantalla" dentro del Principio VI.
Secciones eliminadas: ninguna.
Cambio de esquema: ninguno. El conteo de entidades de 001 sigue en 20.

Puerta de sincronización de enmiendas (v2.2.0): la enmienda añade texto a un
principio, pero NO cambia el significado de ninguna regla ya escrita ni la tabla
de Propiedad de Datos — es enforcement de un principio existente. Por eso NO se
barren las citas "v2.4.0" de 002–007: nada de lo que esos módulos especifican
cambia. El único artefacto materialmente afectado es `001-core-ventas-inventario`
(el nav vive ahí, y la asignación pantalla→rol se implementa en sus routers y en
`App.tsx`); 001 registra la enmienda en sus tareas, sin reabrir su conteo
histórico. `DESIGN.md` NO cambia: la navegación por rol aplica La Regla del Grupo
de Navegación y el patrón del atajo "+ Crear producto nuevo" ya existentes, sin
añadir ni redefinir ninguna regla de diseño.

Historial de versiones (resumen):
  - 2.5.0 (2026-09-07) — esta enmienda: sub-sección "Autorización de pantalla"
    del Principio VI. Tabla de rol mínimo por pantalla (cajero: Venta, Conteo,
    Entradas, Arqueo; encargado: todo lo táctico/gerencial incl. Reportes de la
    spec 008; admin: gestión de operadores y datos maestros). Cierra un
    incumplimiento de "Ocultar, no deshabilitar" y "Autorización centralizada".
    Sin cambio de esquema. Se implementa en 001 (routers + `App.tsx`).

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.3.0 → 2.4.0
Tipo de cambio: MENOR — amplía el Principio VI ("Autorización y Roles") con una
sub-sección nueva, "Identidad de sesión". No elimina ni redefine ninguna regla de
autorización: los tres roles, la jerarquía acumulativa, el mecanismo central
`requiere_rol`, "ocultar, no deshabilitar" y la excepción de `cliente` quedan
exactamente como estaban. Lo que cambia es la mitad de IDENTIDAD del principio: la
frase descriptiva "no hay JWT, ni sesión de servidor, ni token; el `id_operador`
sigue viajando explícito" se sustituye por un mecanismo de sesión de turno. Como
toca el texto de un principio y la tabla de Propiedad de Datos (la frontera de
"autorización"), vuelve al formato de informe completo de v2.0.0 / v2.2.6 / v2.3.0.

Motivo: una auditoría de seguridad encontró que la autorización por rol (v2.3.0,
`requiere_rol`) valida el ROL correctamente pero resuelve la IDENTIDAD del operador
leyendo el `id_operador` que el propio cliente envía en el cuerpo de cada petición,
sin comprobar que quien llama sea de verdad ese operador. Con la consola de red
abierta, cualquiera cambia `id_operador` en el body y actúa como cualquier rol,
`admin` incluido, sin conocer ningún PIN. Ese patrón —`id_operador` en el cuerpo,
sin sesión— es ANTERIOR a v2.3.0: viene de `007-pagos-seguridad` (donde se
estableció para `POST /pagos/terminales` y la cobertura de medios) y la enmienda
v2.3.0 lo heredó sin cuestionarlo. v2.3.0 no introdujo la brecha; sólo la volvió
más grave al añadir una jerarquía de roles real que suplantar. Esta enmienda la
CORRIGE; no arregla un defecto propio de la última enmienda.

La decisión (cerrada; el detalle vive en el Principio VI y en la User Story 11 de
`001-core-ventas-inventario/spec.md`):
  (A) Al abrir turno, tras validar el PIN, el backend emite UN JSON Web Token
      firmado con clave simétrica (HS256). Un token por turno abierto. Claims
      mínimos: `id_operador`, `id_turno`, `rol` y `exp`. El backend NUNCA confía en
      el `rol` del claim para autorizar —sigue resolviéndolo desde la tabla
      `operador` en cada `requiere_rol`—; el claim es sólo para la interfaz.
  (B) El token viaja en el header `Authorization: Bearer <token>` en toda petición
      que hoy exige `id_operador` para verificar rol. El frontend lo guarda en
      memoria (estado de React, junto al turno), NUNCA en `localStorage` ni
      `sessionStorage` (convención del proyecto: sin browser storage). Se pierde al
      recargar, igual que hoy se pierde el turno abierto — no es una regresión.
  (C) Doble invalidación: expira por tiempo (12 horas desde la emisión, `exp`
      estándar) Y al cerrar turno. Como JWT es stateless, el cierre se comprueba
      contra el estado ya existente del turno (`turno.instante_cierre IS NOT NULL`):
      no se crea tabla de blocklist ni columna nueva. Un token cuyo `operador` pasó
      a `activo = false` se rechaza de inmediato en la siguiente petición, igual que
      ya hace `requiere_rol` con el operador inactivo.
  (D) CAMBIO DE CONTRATO INTENCIONAL: el `id_operador` (y `id_operador_solicitante`)
      que hoy viaja en el cuerpo de los endpoints de escritura sujetos a rol queda
      IGNORADO por el backend para efectos de autorización. La identidad se deriva
      EXCLUSIVAMENTE del token. No se valida cruce body-vs-token: una sola fuente de
      verdad es más simple de implementar, testear y defender que dos. El campo se
      retira del schema de esos cuerpos. Los endpoints que hoy NO verifican
      identidad alguna (entradas de inventario, traspasos, conteos físicos,
      sincronización de operaciones pendientes, la mayoría de precios/pronóstico/
      promociones) quedan FUERA DE ALCANCE de esta enmienda: no tenían control de
      identidad antes y cerrarlo sería expandir el alcance sin especificación. Se
      anotan como candidatos a una User Story futura.

Autorización ≠ autenticación, y esta enmienda tampoco las funde: `requiere_rol`
sigue siendo el único mecanismo de rol. Lo que se añade es la SESIÓN —cómo el
backend sabe qué operador llama— que hasta v2.3.0 se resolvía por un dato del
cuerpo en el que confiaba sin verificar. El PIN + hash (FR-006, SHA-256 + sal)
NO cambia: sigue siendo la credencial que se presenta al abrir turno. El token es
la consecuencia de presentarla, no una credencial nueva.

Principios modificados: Principio VI, "Autorización y Roles" — se reescribe el
párrafo de identidad y se añade la sub-sección "Identidad de sesión". Ninguna regla
de autorización se redefine.
Secciones añadidas: sub-sección "Identidad de sesión" dentro del Principio VI.
Secciones eliminadas: ninguna.

Cambio de esquema: NINGUNO. `operador` y `turno` (001) no ganan ni pierden
columnas; la invalidación por cierre reutiliza `turno.instante_cierre`, que existe
desde v2.1.0. El conteo de entidades de 001 sigue en 20.

Configuración nueva (Restricciones Técnicas, "Configuración y secretos", ya
vigente): la clave de firma del JWT se inyecta por entorno (`JWT_SECRET_KEY`), con
un valor por defecto SÓLO para desarrollo, igual que `DATABASE_URL`. Ningún secreto
real en el repositorio.

Nueva frontera en "Propiedad de Datos y Nomenclatura": la viñeta de "autorización"
se amplía para separar la verificación de rol (`requiere_rol`) de la resolución de
identidad de sesión (emisión y verificación del token de turno). Ambas viven en
`backend/rasero/seguridad.py`; ninguna pertenece a una funcionalidad concreta. El
token de turno NO es una entidad persistida: es un valor firmado y sin estado, sin
fila en ninguna tabla.

Puerta de sincronización de enmiendas (v2.2.0): esta enmienda cambia el texto de un
principio y la tabla de Propiedad de Datos, así que las citas que reclaman una
versión vigente de la constitución en los artefactos de funcionalidad (`spec.md`,
`plan.md`, `data-model.md`) de 001–007 se sincronizan de v2.3.0 a **v2.4.0** en
este mismo cambio. Las citas históricas —"la enmienda v2.3.0 que añadió el Principio
VI", "de 3 a 6 entidades por v2.2.5"— NO se barren. `DESIGN.md` NO cambia: el token
no tiene superficie visual propia; el único efecto de interfaz —volver a la pantalla
de apertura de turno cuando la sesión expira o se cierra— aplica el flujo de turno
ya existente sin añadir ni redefinir ninguna regla de diseño.

Historial de versiones (resumen; ver bloques siguientes para el detalle):
  - 2.2.9 (2026-09-07) — Regla de la Marca Persistente (DESIGN.md v1.3.1).
  - 2.3.0 (2026-09-06) — Principio VI, "Autorización y Roles"; `operador` (001)
    gana `id_sucursal` (FK) y cambia `es_encargado` por `rol`.
  - 2.4.0 (2026-09-06) — esta enmienda: sub-sección "Identidad de sesión" del
    Principio VI. Corrige una brecha identidad-vs-autorización heredada de
    `007-pagos-seguridad`: el operador se identificaba por un `id_operador` del
    cuerpo en el que el backend confiaba sin verificar. Se introduce un JWT de
    sesión de turno (HS256, header `Authorization: Bearer`, `exp` a 12 h,
    invalidado también al cerrar turno o desactivar al operador). El `id_operador`
    del cuerpo queda deprecado para autorización — una sola fuente de verdad, el
    token. Sin cambio de esquema (la invalidación por cierre reutiliza
    `turno.instante_cierre`). `JWT_SECRET_KEY` por entorno. Se especifica como
    User Story 11 de `001-core-ventas-inventario`. Citas de versión vigente de
    001–007 sincronizadas a v2.4.0.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.9 → 2.3.0
Tipo de cambio: MENOR — añade un principio nuevo (Principio VI, "Autorización y
Roles"). Es territorio nuevo: la constitución no tenía hasta hoy ningún principio
de roles o autorización, así que esta enmienda no resuelve una contradicción, la
crea desde cero. A diferencia de v2.2.7 a v2.2.9 —que vivían enteramente en
`DESIGN.md`—, esta enmienda toca un principio y la tabla de Propiedad de Datos, y
por eso vuelve al formato de informe completo de v2.0.0 / v2.2.6.

Motivo: hoy `operador` es global (sin sucursal asignada) y su única distinción de
capacidad es el booleano `es_encargado`. El chequeo de "es encargado" está
DUPLICADO en tres servicios (`servicios/administracion.py`,
`servicios/cobertura_pago.py`, `servicios/terminales_pago.py`), cada uno con su
propia función `_encargado_o_error` y su propio código de error. Esta enmienda:
  (A) ata cada `operador` a una sucursal fija (`id_sucursal`, FK, NOT NULL,
      relación uno-a-uno operador↔sucursal — NO una tabla de asociación: nadie
      pidió operadores que roten de sucursal, y la constitución ya declara "N
      sucursales sin cambios estructurales", así que una FK simple basta);
  (B) reemplaza el booleano `es_encargado` por `rol`, ENUM cerrado
      `cajero` | `encargado` | `admin`, con jerarquía acumulativa
      cajero < encargado < admin;
  (C) exige que la autorización se verifique en UN mecanismo central de backend
      (`requiere_rol` en `seguridad.py`) y se exponga por UN hook de frontend;
  (D) exige que la navegación oculte —no deshabilite— lo que el rol activo no
      puede usar, generalizando el patrón que ya existía sólo para el atajo
      "+ Crear producto nuevo" desde Venta.

Autorización ≠ autenticación. El mecanismo de PIN + hash (FR-006, SHA-256+sal)
NO cambia: sigue siendo identificación por PIN al abrir turno, con `id_operador`
viajando explícito en cada petición. Esta enmienda gobierna sólo QUÉ puede hacer
cada rol, no CÓMO se identifica el operador. No introduce JWT, sesión de
servidor ni ningún mecanismo de autenticación nuevo.

Principios modificados: ninguno redefinido.
Secciones añadidas: Principio VI, "Autorización y Roles".
Secciones eliminadas: ninguna.

Cambio de esquema sobre una entidad ya certificada de 001 (documentado como tal):
  - Propiedad de Datos y Nomenclatura, entrada de `001-core-ventas-inventario`:
    `operador` gana la columna `id_sucursal` (FK → `sucursal`, NOT NULL) y su
    columna booleana `es_encargado` se retira y se reemplaza por `rol`
    (ENUM cerrado `cajero` | `encargado` | `admin`). El CONTEO de entidades de
    001 no cambia (sigue en 20 desde v2.1.2): `operador` ya estaba listada; lo
    que cambia es su esquema, no la lista.
  - Migración de datos, OBLIGATORIA en el mismo script de Alembic, con la regla
    de conversión escrita como comentario explícito:
        es_encargado = FALSE  →  rol = 'cajero'
        es_encargado = TRUE   →  rol = 'encargado'
    NINGÚN operador existente pasa a 'admin' automáticamente. El rol 'admin' se
    crea siempre de forma explícita (semilla o alta desde la interfaz por otro
    admin). La migración lleva su procedimiento de reversión documentado
    (Restricciones Técnicas, "Migraciones").
  - `id_sucursal` de `operador` es un dato de registro para todos los roles y
    además una RESTRICCIÓN FUNCIONAL para `cajero` y `encargado`: la apertura de
    turno se resuelve a esa sucursal sin selector visible. Para `admin` es sólo
    dato de registro: `admin` abre turno en cualquier sucursal (mantiene el
    selector). Defensa en profundidad: el backend rechaza abrir turno en una
    sucursal distinta a la asignada con {codigo, mensaje}, aunque el frontend ya
    no lo permita para esos dos roles.
  - Nueva frontera en "Fronteras entre funcionalidades adyacentes": autorización
    (Principio VI, mecanismo central) vs. autenticación (PIN, FR-006, sin
    cambios).

Nueva sección/capacidad de interfaz (admin-only): gestión de `operador`
—crear / editar rol / desactivar / asignar sucursal— como 6.ª pestaña del
segmentado de Administración, visible SÓLO si el operador activo es `admin`.
Ningún `encargado` puede ascender a otro operador a `encargado` o `admin`. Esto
no crea ninguna entidad nueva ni cambia el conteo de 001.

Puerta de sincronización de enmiendas (v2.2.0): esta enmienda SÍ cambia un
principio y la tabla de Propiedad de Datos, así que las citas que reclaman una
versión vigente de la constitución en los artefactos de funcionalidad
(`spec.md`, `plan.md`, `data-model.md`) de 001–007 se sincronizan de v2.2.6 a
**v2.3.0** en este mismo cambio. Las citas históricas —"la enmienda v2.2.6 que
añadió `token_pago`", "de 3 a 6 entidades por v2.2.5"— NO se barren. `DESIGN.md`
NO cambia: la navegación por rol aplica reglas ya existentes (La Regla del Grupo
de Navegación, el patrón del atajo "+ Crear producto") sin añadir ni redefinir
ninguna; el formulario de alta/edición de operador usa `ModalAdministrable`
(La Regla del Modal Administrable, ya vigente).

Historial de versiones (resumen; ver bloques siguientes para el detalle):
  - 2.2.6 (2026-09-05) — `token_pago` añadida a 007.
  - 2.2.7 (2026-09-06) — sistema de diseño ampliado (DESIGN.md v1.2.0).
  - 2.2.8 (2026-09-06) — Regla de la Identidad del Comercio reescrita (v1.3.0).
  - 2.2.9 (2026-09-07) — Regla de la Marca Persistente (DESIGN.md v1.3.1).
  - 2.3.0 (2026-09-06) — esta enmienda: Principio VI, "Autorización y Roles";
    `operador` (001) gana `id_sucursal` (FK) y cambia `es_encargado` (BOOLEAN)
    por `rol` (ENUM cajero/encargado/admin), con migración de datos documentada
    (false→cajero, true→encargado, ningún admin automático); autorización
    centralizada en `requiere_rol` (backend) y un hook único (frontend);
    navegación que oculta lo que el rol no puede usar; gestión de operadores
    admin-only. Citas de versión vigente de 001–007 sincronizadas a v2.3.0.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.8 → 2.2.9
Tipo de cambio: MENOR — añade una regla al sistema de diseño. Como v2.2.7 y
v2.2.8, la enmienda vive enteramente en `DESIGN.md`; no toca ningún principio,
ni la tabla de Propiedad de Datos, ni ningún artefacto de funcionalidad.

Motivo: añade La Regla de la Marca Persistente — el ícono del comercio
(`despensa-icon-verde-512.png`, configurable por `VITE_ICONO_COMERCIO`) aparece
en el nav global al mismo nivel visual que el wordmark de Rasero, y un footer
nuevo muestra el nombre de la sucursal activa. Cierra la brecha de que la marca
del comercio sólo se veía en la pantalla de apertura de turno, un riesgo para la
defensa de la distinción "Rasero = herramienta / Despensa Los Ríos = negocio".

Principios modificados: ninguno.
Secciones añadidas: ninguna.
Secciones eliminadas: ninguna.

Regla nueva en `DESIGN.md` v1.3.1: La Regla de la Marca Persistente (aditiva; no
modifica ni elimina ninguna regla previa).

Puerta de sincronización de enmiendas (v2.2.0): esta enmienda no cita versiones
en artefactos de funcionalidad porque no cambia ninguna regla que ellos citen;
la única sincronización es `DESIGN.md` ↔ este historial, ya hecha en el mismo
cambio.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.7 → 2.2.8
Tipo de cambio: MENOR — reescribe una regla del sistema de diseño. Como v2.2.7,
la enmienda vive enteramente en `DESIGN.md`; no toca ningún principio, ni la
tabla de Propiedad de Datos, ni ningún artefacto de funcionalidad
(spec.md / plan.md / data-model.md / contracts).

Motivo: reescribe La Regla de la Identidad del Comercio — la cabecera de la
pantalla de apertura de turno pasa de un bloque con fondo Tinta y el nombre de
sucursal como elemento de mayor peso, a una cabecera de fondo blanco con el logo
a color del comercio como elemento principal (el logo a color no está diseñado
para fondo oscuro), con el nombre de sucursal y la caja como contexto secundario
debajo. Detectado al rediseñar `AperturaTurno.tsx` con captura del usuario que
mostraba el logo apagado sobre el bloque Tinta.

Principios modificados: ninguno.
Secciones añadidas: ninguna.
Secciones eliminadas: ninguna.

Regla reescrita en `DESIGN.md` v1.3.0: La Regla de la Identidad del Comercio. No
se elimina ni se añade ninguna otra regla. `DESIGN.md` v1.2.1 (PARCHE del mismo
día) aclaró además "Identificar cliente (Operación)" — alta/edición de cliente
usan `ModalAdministrable` — sin cambiar ninguna regla.

Puerta de sincronización de enmiendas (v2.2.0): esta enmienda no cita versiones
en artefactos de funcionalidad porque no cambia ninguna regla que ellos citen;
la única sincronización es `DESIGN.md` ↔ este historial, ya hecha en el mismo
cambio.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.6 → 2.2.7
Tipo de cambio: MENOR — amplía el sistema de diseño con reglas nuevas. No toca
ningún principio, ni la tabla de Propiedad de Datos, ni ningún artefacto de
funcionalidad (spec.md / plan.md / data-model.md / contracts): la enmienda vive
enteramente en `DESIGN.md`, que la constitución ya declara como el documento
derivado donde se ejecutan las decisiones de la sección "Sistema de Diseño".

Motivo: amplía el sistema de diseño con reglas de identidad de negocio, estados
vacíos, carga y componentes administrables — no reemplaza ninguna regla previa.

Principios modificados: ninguno.
Secciones añadidas: ninguna (la sección "Sistema de Diseño" queda igual; las
reglas nuevas se registran en `DESIGN.md` v1.2.0).
Secciones eliminadas: ninguna.

Reglas nuevas en `DESIGN.md` v1.2.0 (todas aditivas): La Regla de la Identidad
del Comercio, La Regla del Hueco que Enseña, La Regla del Pulso No el Brillo, La
Regla del Ícono por Categoría, La Regla del Modal Administrable, La Regla del
Filtro y la Página, La Regla del Grupo de Navegación.

Puerta de sincronización de enmiendas (v2.2.0): esta enmienda no cita versiones
en artefactos de funcionalidad porque no cambia ninguna regla que ellos citen;
la única sincronización es `DESIGN.md` ↔ este historial, ya hecha en el mismo
cambio.

TODOs pendientes: ninguno.
-->

<!--
INFORME DE IMPACTO DE SINCRONIZACIÓN
====================================
Cambio de versión: 2.2.5 → 2.2.6
Tipo de cambio: PARCHE — amplía la entrada de `007-pagos-seguridad` en la
tabla de Propiedad de Datos de 4 a 5 entidades, detectado al escribir su
`research.md` en `/speckit-plan` (research.md #1). Mismo tipo de corrección
que v2.1.1 y v2.1.2 sobre 001, v2.2.3 sobre 003, v2.2.4 sobre 004 y v2.2.5
sobre 005: la lista original de 007 era un supuesto anterior a la
especificación real del módulo —se ratificó en v2.0.0 sin que existiera el
spec de pagos y seguridad— y esta enmienda la completa con lo que su spec
realmente exige. No cambia ningún principio.

En línea con v2.2.4 —que sólo añadió una entidad omitida—, esta enmienda
añade una entidad (`token_pago`) y no retira ninguna.

Principios modificados: ninguno.
Secciones añadidas: ninguna.
Secciones eliminadas: ninguna.

Revisión de consistencia previa a la enmienda (exigida por la "Puerta de
propiedad de datos"; el mismo tipo de revisión que en v2.2.3 detectó el
error de `costo_producto` en 003 y en v2.2.5 detectó el problema de
`envio_promocional`/`grupo_control`): se contrastó la entrada COMPLETA de
`007-pagos-seguridad` —`terminal_pago`, `medio_pago`, `cobertura_pago`,
`bitacora_auditoria`— contra las cuatro preocupaciones acotadas del encargo
(tokenización de datos de pago, firmware de terminal, log de actividad de
pagos, cobertura de medios de pago) y contra la sección "Datos de pago" de
las Restricciones Técnicas. Resultado:
  - Tres de las cuatro preocupaciones caen limpiamente en las entidades ya
    listadas: firmware de terminal → `terminal_pago`; cobertura de medios →
    `medio_pago` + `cobertura_pago`; log de actividad → `bitacora_auditoria`.
  - La cuarta —la persistencia del token de un cobro con tarjeta— NO tiene
    entidad anticipada. No es el catálogo `medio_pago` (una instancia
    transaccional no es un catálogo), no es el dispositivo `terminal_pago`
    (el token pertenece al cobro, no al datáfono), no es la métrica agregada
    `cobertura_pago`, y NO es un evento de `bitacora_auditoria`: esta última
    es un rastro de solo anexado, y `token_pago` es el registro autoritativo
    de la relación venta↔token, con restricción UNIQUE por cobro, requisito
    de idempotencia y ciclo de purga propio, y es lo que rellena la
    `referencia_terminal_pago` opaca de 001. Un log de solo anexado no puede
    ser el sistema de registro de un dato con clave única.
  - La constitución ya fija la REGLA aplicable ("Datos de pago": los datos
    completos de tarjeta no se almacenan; se conservan únicamente
    identificadores y últimos dígitos) pero no la ENTIDAD que la implementa.
    Esta enmienda añade esa entidad. Mismo patrón que `rol_producto` de 003,
    `sustitucion_producto` de 004 y `cupon`/`oferta_recompra` de 005:
    declaración de negocio que el módulo modela en tabla propia con FK, sin
    alterar el esquema ajeno.

Secciones modificadas:
  - Propiedad de Datos y Nomenclatura, entrada de `007-pagos-seguridad`:
      * Se añade `token_pago`.
        `007-pagos-seguridad/spec.md` exige (FR-016 a FR-022, User Story 3)
        que, cuando una `venta` de 001 se cobra con tarjeta, el módulo
        conserve únicamente {token opaco, últimos cuatro dígitos, marca,
        tipo, terminal de captura, referencia de la venta, clave de
        idempotencia} y nunca el PAN, el CVV ni datos de banda/chip. Ese
        registro no cabe en las otras cuatro entidades (ver revisión de
        consistencia arriba). No estaba en la ratificación original porque
        esa lista se escribió antes de que existiera el spec de 007.
    Lista resultante de 007: `terminal_pago`, `medio_pago`, `cobertura_pago`,
    `bitacora_auditoria`, `token_pago` (5 entidades; antes 4).
  - Fronteras entre funcionalidades adyacentes: se añade una viñeta que
    separa la referencia de terminal de pago que 001 guarda como opaca de la
    tokenización que 007 posee: `token_pago` CONSULTA `venta` de 001 sin
    poseerla y RELLENA la `referencia_terminal_pago` opaca de 001 sin alterar
    el tipo ni la semántica de ese campo en el esquema de 001; el PAN nunca
    se persiste en ningún módulo.
  - Pie del documento: "Versión: 2.2.5" → "2.2.6".

Decisiones de alcance vigentes (sin cambio en 2.2.6):
  - `sucursal` es entidad de primera clase con cardinalidad no acotada; el
    alcance del examen cubre exactamente dos sucursales (Quevedo Centro y
    Buena Fe, del juego de datos Despensa Los Ríos).
  - La constitución fija un conjunto cerrado de decisiones técnicas (motor de
    datos, nomenclatura, tipografía y paleta); el resto se decide por
    funcionalidad en plan.md.
  - Las seis lecturas críticas del enunciado son sección propia, no un sexto
    principio.
  - Rigor de pruebas: pragmático y proporcional al riesgo (sin TDD estricto).
  - Reconciliación: no se exige estrategia de fusión más allá del desempate
    por marca de tiempo.
  - Propiedad de datos de 001-core-ventas-inventario: 20 entidades vigentes
    desde v2.1.2.
  - Propiedad de datos de 003-precios-margenes: 4 entidades vigentes desde
    v2.2.3 (`costo_producto` retirado, `sugerencia_precio` añadida).
  - Propiedad de datos de 004-pronostico-demanda: 4 entidades vigentes desde
    v2.2.4 (`sustitucion_producto` añadida).
  - Propiedad de datos de 005-promociones-inteligentes: 6 entidades vigentes
    desde v2.2.5 (`envio_promocional` y `grupo_control` retiradas; `cupon`,
    `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento` y
    `redencion_promocion` añadidas).
  - Propiedad de datos de 007-pagos-seguridad: 5 entidades vigentes desde
    v2.2.6 (`token_pago` añadida).
  - Puerta de sincronización de enmiendas (v2.2.0).

Historial de versiones:
  - 1.0.0 (2026-09-04) — ratificación inicial, 5 principios.
  - 1.0.1 (2026-09-04) — traducción completa al español y alcance multi-sucursal.
  - 2.0.0 (2026-09-04) — identidad Rasero; redefinición de los Principios I y IV;
    propiedad de datos, nomenclatura, sistema de diseño e infraestructura.
  - 2.0.1 (2026-09-04) — nombre del comercio de demostración y su prohibición
    como identificador técnico.
  - 2.0.2 (2026-09-04) — implementación mínima de reconciliación offline.
  - 2.1.0 (2026-09-04) — propiedad de datos corregida a partir de la
    especificación de 001.
  - 2.1.1 (2026-09-04) — `conteo_renglon` añadida a 001.
  - 2.1.2 (2026-09-04) — `producto_precio_sucursal` añadida a 001.
  - 2.2.0 (2026-09-04) — puerta de sincronización de enmiendas.
  - 2.2.1 (2026-09-04) — nombre del comando de Impeccable corregido de `teach`
    a `init`, tras verificar la herramienta instalada.
  - 2.2.2 (2026-09-04) — los tres pasos reales de Impeccable (init / new-work /
    documenter) documentados por separado; tercera corrección consecutiva
    sobre el mecanismo de la misma herramienta.
  - 2.2.3 (2026-09-05) — propiedad de datos de `003-precios-margenes`
    corregida a partir de su especificación real (`costo_producto` retirado,
    `sugerencia_precio` añadida), detectada al escribir `data-model.md` de
    003 en `/speckit-plan`.
  - 2.2.4 (2026-09-05) — `sustitucion_producto` añadida a
    `004-pronostico-demanda` a partir de su especificación real (FR-032,
    User Story 6, FR-009 b), detectada al escribir `data-model.md` de 004 en
    `/speckit-plan`; nueva viñeta de frontera demanda-observada/pronóstico;
    y corrección del pie del documento, que v2.2.3 dejó en 2.2.2.
  - 2.2.5 (2026-09-05) — propiedad de datos de
    `005-promociones-inteligentes` ampliada de 3 a 6 entidades
    (`envio_promocional` y `grupo_control` retiradas; `cupon`,
    `oferta_recompra`, `experimento_reactivacion`, `asignacion_experimento`
    y `redencion_promocion` añadidas) para cubrir los tres mecanismos de
    promoción —cupón por fecha fija, empuje por recompra, reactivación con
    experimento— más su registro de redención compartido, detectada al
    escribir `spec.md` de 005 en `/speckit-specify`; ampliación de la viñeta
    de frontera 002/005.
  - 2.2.6 (2026-09-05) — esta enmienda: propiedad de datos de
    `007-pagos-seguridad` ampliada de 4 a 5 entidades (`token_pago` añadida)
    para dar entidad autoritativa a la persistencia del token de un cobro con
    tarjeta —{token opaco, últimos cuatro dígitos, marca, tipo, terminal de
    captura, referencia de venta, clave de idempotencia}, nunca el PAN—, que
    no cabe en `medio_pago`, `terminal_pago`, `cobertura_pago` ni
    `bitacora_auditoria`; detectada al escribir `research.md` de 007 en
    `/speckit-plan` (research.md #1); nueva viñeta de frontera
    001/007 sobre la `referencia_terminal_pago` opaca.
  - 2.2.7 (2026-09-06) — amplía el sistema de diseño con reglas de identidad de
    negocio, estados vacíos, carga y componentes administrables — no reemplaza
    ninguna regla previa. Registrada en `DESIGN.md` v1.2.0 (siete reglas nuevas,
    todas aditivas: Identidad del Comercio, Hueco que Enseña, Pulso No el Brillo,
    Ícono por Categoría, Modal Administrable, Filtro y la Página, Grupo de
    Navegación). No toca ningún principio ni la tabla de Propiedad de Datos.
  - 2.2.8 (2026-09-06) — reescribe La Regla de la Identidad del Comercio: la
    cabecera de la pantalla de apertura de turno pasa de bloque con fondo Tinta y
    nombre de sucursal como elemento de mayor peso, a cabecera de fondo blanco con
    el logo a color del comercio como elemento principal (el logo a color no está
    diseñado para fondo oscuro), con nombre de sucursal y caja como contexto
    secundario. Registrada en `DESIGN.md` v1.3.0. No elimina ni añade ninguna
    otra regla; no toca ningún principio ni la tabla de Propiedad de Datos.
    (`DESIGN.md` v1.2.1, PARCHE del mismo día, aclaró "Identificar cliente
    (Operación)" sin cambio de regla.)
  - 2.2.9 (2026-09-07) — añade La Regla de la Marca Persistente: el ícono del
    comercio en el nav global al mismo nivel que el wordmark de Rasero, y un
    footer con el nombre de la sucursal activa. Registrada en `DESIGN.md`
    v1.3.1 (regla nueva, aditiva). No modifica ni elimina ninguna regla
    previa; no toca ningún principio ni la tabla de Propiedad de Datos.

Artefactos de funcionalidad afectados: las citas que reclaman una versión
vigente de la constitución ("constitución vX.Y.Z", "verificación contra la
constitución vX.Y.Z") en spec.md, plan.md y data-model.md de 001, 002, 003,
004, 005 y 006 se sincronizan a v2.2.6 en este mismo cambio (puerta de
sincronización de enmiendas, v2.2.0). `007-pagos-seguridad` nace citando
v2.2.6. Las citas históricas —"la enmienda v2.2.3 que añadió
`sugerencia_precio`", "`sustitucion_producto` añadida en v2.2.4", "de 3 a 6
entidades por v2.2.5", "tras la enmienda v2.2.3/v2.2.4/v2.2.5"— describen qué
enmienda introdujo qué regla y NO se barren (excepción explícita de la
puerta).

TODOs pendientes: ninguno.
-->

# Constitución de Rasero

Rasero es una plataforma de retail inteligente: punto de venta, gestión de inventario,
márgenes, previsión de demanda y fidelización para comercio físico multi-sucursal. Esta
constitución define las reglas no negociables que gobiernan cómo se especifica, diseña,
construye y revisa el producto.

## Identidad del Proyecto

Un rasero es la tabla que se pasa sobre una medida de grano para nivelarla al ras. De ahí
viene "medir con el mismo rasero", y de ahí viene la tesis del sistema: aplicar un mismo
criterio objetivo a productos y clientes que hoy el dueño juzga por impresión. Ese criterio
es explícito y siempre el mismo —margen real, demanda corregida por censura, valor de
cliente por frecuencia y margen— y toda funcionalidad DEBE poder explicar sus salidas en
esos términos.

El nombre del sistema es independiente del nombre del comercio ficticio usado en los datos
de demostración. Rasero es una herramienta genérica; NO está construida para un comercio
específico, y ninguna regla de negocio particular de un comercio de ejemplo puede quedar
codificada en el modelo, el esquema o la interfaz.

El comercio ficticio de los datos de demostración es **Despensa Los Ríos**, con dos
sucursales: **Quevedo Centro** y **Buena Fe**. Ese nombre pertenece exclusivamente a los
datos de prueba y a los scripts de carga inicial, y vive únicamente como valor de fila.
Usarlo en nombres de tabla, esquemas, endpoints, componentes de interfaz, espacios de
nombres, ramas, variables o cualquier otro identificador técnico está PROHIBIDO. Rasero es
el sistema; Despensa Los Ríos es un juego de datos. Mezclarlos en el código ata la
herramienta a su propio ejemplo y contradice el párrafo anterior.

## Principios Fundamentales

### I. Dominio Primero, Contratos Explícitos

El modelo de dominio del retail —producto, existencia, precio, venta, devolución, caja,
sucursal— DEBE definirse antes que cualquier decisión de framework, biblioteca o
infraestructura. Cada funcionalidad DEBE declarar en su especificación las entidades que
toca y el contrato observable que expone (endpoint, comando, evento o vista) antes de
escribir código de implementación.

La constitución fija un conjunto cerrado y enumerado de decisiones técnicas, y solo ese: el
motor de datos y su configuración de desarrollo (ver "Infraestructura de datos"), la
convención de nomenclatura de datos, y la tipografía y paleta del sistema de diseño. Todo
lo demás —lenguaje, framework de aplicación, capa de acceso a datos, empaquetado— se decide
por funcionalidad en `plan.md` y DEBE justificarse frente a los requisitos del dominio, no
frente a la familiaridad del equipo. Introducir una segunda tecnología que cumple la misma
función que una ya presente en el proyecto está PROHIBIDO salvo justificación registrada en
la sección de complejidad del plan.

**Razón**: en retail el dominio sobrevive a los frameworks. Un modelo de existencias mal
definido corrompe inventario, arqueos y previsiones durante años; un framework se sustituye.
Las pocas decisiones que sí se fijan aquí lo están porque su cambio invalidaría datos ya
capturados (precisión numérica) o rompería la coherencia visual del conjunto.

### II. Fiabilidad Operativa en el Punto de Venta

Una caja no puede detenerse. Todo flujo que participe en una venta DEBE cumplir:

- **Degradación, nunca bloqueo**: si un servicio de inteligencia, red o reporte no responde,
  la venta se completa igualmente con el comportamiento base determinista. Ninguna función
  de IA, analítica o telemetría puede ser camino crítico de un cobro.
- **Idempotencia obligatoria**: toda operación que altera inventario, dinero o documentos
  fiscales DEBE aceptar una clave de idempotencia y producir el mismo resultado ante
  reintentos. Los reintentos duplicados NO pueden generar ventas, cargos ni movimientos
  de existencias duplicados.
- **Reconciliación explícita**: las operaciones ejecutadas sin conectividad DEBEN encolarse
  con marca de tiempo de origen y resolverse mediante una regla de conflicto documentada en
  la especificación de la funcionalidad. Descartar silenciosamente una operación encolada
  está PROHIBIDO.

  La implementación mínima exigida de esta regla es la siguiente, y es propiedad de
  `001-core-ventas-inventario`:

  - Toda operación ejecutada sin conectividad se persiste localmente con estado
    `pendiente_de_sincronizar` y su marca de tiempo de origen.
  - Al recuperar conectividad, las operaciones pendientes se envían al servidor en orden de
    marca de tiempo de origen.
  - La regla de conflicto por defecto es **gana la marca de tiempo más antigua sobre el mismo
    recurso**: prevalece la operación que ocurrió primero en el mundo físico, no la que llegó
    primero al servidor.
  - La operación desplazada por un conflicto se marca como `conflicto_resuelto` con
    referencia a la operación que prevaleció, y permanece visible para revisión humana.
    Eliminarla u ocultarla está PROHIBIDO.

  No se exige resolución automática más allá de esta regla de desempate. Una estrategia de
  fusión más sofisticada es mejora futura, no requisito de entrega; implementarla sin
  necesidad demostrada es complejidad que DEBE justificarse en el plan.

**Razón**: el coste de un fallo en caja es una fila de clientes y dinero descuadrado, no un
error en un registro técnico. La fiabilidad es requisito funcional, no atributo de calidad.

### III. Pruebas Proporcionales al Riesgo

Las pruebas son OBLIGATORIAS donde el error cuesta dinero o corrompe datos; en el resto son
una decisión de ingeniería. No se exige TDD estricto ni un umbral global de cobertura.

DEBEN existir pruebas automatizadas, y estar en verde antes de fusionar, para:

- Cálculo monetario, impuestos, descuentos, redondeo y totales.
- Toda transición de estado de inventario y de documentos de venta o devolución.
- Todo contrato público (API, evento, esquema persistido) en su forma feliz y en sus modos
  de fallo declarados.
- Toda corrección de defecto: la prueba de regresión DEBE fallar antes del arreglo y pasar
  después. Un arreglo sin esa prueba no se fusiona.

Para interfaz de usuario, maquetación y código exploratorio, las pruebas son opcionales y su
ausencia NO bloquea la revisión. Añadir pruebas que solo replican la implementación está
desaconsejado.

**Razón**: exigir cobertura uniforme produce suites caras que nadie mantiene; concentrar el
esfuerzo en dinero, existencias y contratos protege lo que realmente no puede fallar.

### IV. Trazabilidad de Cada Transacción

Toda operación que mueva dinero o existencias DEBE dejar un rastro reconstruible: qué pasó,
cuándo, en qué sucursal y caja, iniciada por qué operador o proceso, y con qué resultado.

- Los registros DEBEN ser estructurados y consultables por identificador de venta, de
  producto y de sucursal. El filtro por sucursal es obligatorio con independencia de cuántas
  sucursales haya desplegadas; agregar sin discriminar la sucursal de origen está PROHIBIDO.
- El estado de inventario DEBE poder reconstruirse a partir de sus movimientos; sobrescribir
  una cantidad sin registrar el movimiento que la origina está PROHIBIDO.
- **Traspaso entre sucursales**: todo traspaso de inventario entre sucursales DEBE
  registrarse como dos asientos enlazados —salida en la sucursal de origen y entrada en la
  de destino— referidos ambos a una misma operación de traspaso identificable. Registrarlo
  como dos ajustes de inventario independientes, sin referencia común entre ellos, está
  PROHIBIDO. La existencia total del sistema DEBE ser reconstruible en cualquier instante,
  incluido el intervalo en que un traspaso está en curso: la mercancía en tránsito pertenece
  a la operación de traspaso y no desaparece del inventario total mientras viaja.
- Los mensajes de error expuestos al operador DEBEN indicar la acción correctiva; volcar
  trazas técnicas en la interfaz de caja está PROHIBIDO.
- Los rastros NO DEBEN contener datos de pago completos ni datos personales más allá del
  identificador mínimo necesario.

**Razón**: un arqueo que no cuadra se resuelve con historia, no con conjeturas. Sin rastro
reconstruible, cada discrepancia se convierte en una investigación manual. Dos ajustes
sueltos hacen que la mercancía en tránsito se evapore del recuento total, y ese hueco es
indistinguible de una merma o de un robo.

### V. Inteligencia Explicable y Reversible

Las funciones "inteligentes" —previsión de demanda, sugerencia de reposición, precios
dinámicos, detección de anomalías— están sujetas a restricciones adicionales:

- **Explicable**: cada salida DEBE ir acompañada de los factores que la determinan y del
  periodo de datos usado. Una recomendación que el encargado de tienda no puede justificar
  ante su gerente no se despliega.
- **Consultiva por defecto**: la inteligencia propone; la persona decide. Cualquier acción
  automática sobre inventario o precio requiere aprobación explícita registrada en la
  especificación de la funcionalidad, y DEBE ser reversible con una operación de deshacer.
- **Con línea base**: toda funcionalidad predictiva DEBE declarar su alternativa determinista
  de respaldo y medirse contra ella. Si no supera la línea base, no se despliega.
- **Acotada**: los límites del modelo (datos mínimos, estacionalidad no cubierta, productos
  nuevos sin histórico) DEBEN documentarse en la especificación antes de la implementación.
- **Visible**: la explicabilidad se ejerce en la interfaz, no solo en la documentación. El
  sistema de diseño es parte de este principio y sus reglas —distinción entre dato observado
  y valor estimado, portadores redundantes de incertidumbre— son de cumplimiento obligatorio.
  Ver la sección "Sistema de Diseño".

**Razón**: una previsión errónea que compra de más inmoviliza capital real. La inteligencia
solo aporta valor si es auditable y se puede revertir, y una explicación que el operador no
puede leer en pantalla no es una explicación.

### VI. Autorización y Roles

Quién puede hacer qué se decide en un solo lugar y se hace visible en la interfaz. Este
principio gobierna la **autorización** (qué acciones permite un rol) y la **identidad de
sesión** (cómo el backend sabe qué operador llama), pero no la **autenticación** (la credencial
que el operador presenta). La credencial NO cambia: sigue siendo el PIN + hash (FR-006,
SHA-256 + sal), presentado al abrir turno. Lo que la enmienda **v2.4.0** corrige es que, hasta
entonces, la identidad del operador en cada petición se resolvía leyendo un `id_operador` que
el propio cliente enviaba en el cuerpo, sin verificar — una brecha heredada de
`007-pagos-seguridad`, no introducida por la jerarquía de roles de v2.3.0. Desde v2.4.0 esa
identidad se deriva de un token de sesión de turno (ver "Identidad de sesión" más abajo).

- **Un operador, una sucursal.** `operador` DEBE declarar `id_sucursal` (FK a `sucursal`, NOT
  NULL): relación uno-a-uno, un operador pertenece a exactamente una sucursal. Una tabla de
  asociación operador↔sucursal está PROHIBIDA salvo que exista un caso de uso demostrado de
  rotación entre sucursales, justificado en el plan. Para `cajero` y `encargado` esa sucursal
  es además una restricción funcional: la apertura de turno se resuelve a ella sin selector
  visible, y el backend rechaza —con el formato `{codigo, mensaje}` de todo el sistema— abrir
  turno en otra. Para `admin` es sólo dato de registro: `admin` no está atado operativamente a
  una tienda y puede abrir turno en cualquier sucursal.

- **Tres roles, jerarquía cerrada y acumulativa.** El rol de `operador` DEBE ser uno de un
  ENUM cerrado: `cajero` < `encargado` < `admin`. Cada nivel puede todo lo del anterior más lo
  suyo. `cajero` es el nivel base (operar caja, vender, identificar cliente, registrar
  consultas no atendidas). `encargado` añade la operación táctica y gerencial del día a día
  —precios y márgenes, competencia, pronóstico, análisis de clientes, promociones, traspasos,
  capital inmovilizado, caja y fraude— más las terminales de pago y la cobertura de medios de
  pago. `admin` añade, **en exclusiva**, la gestión de operadores —alta, edición,
  desactivación— y la asignación de rol y de sucursal de otros operadores, **y la
  administración de datos maestros** (`sucursal`, `producto`, `categoria`, `zona_exhibicion`,
  `medio_pago`): alta, edición y desactivación. *(Corrección **v2.7.1**: la frase original
  atribuía "la administración de datos maestros" a `encargado`, en contradicción con la tabla
  de "Autorización de pantalla" de la enmienda v2.5.0 —que ya la listaba bajo `admin` en
  exclusiva— y con la implementación real de `api/operadores.py`. Se corrige el cuerpo para que
  coincida con la tabla; el alta y la edición de `cliente` siguen SIN restricción de rol.)*
  Ningún `encargado` puede ascender a otro operador a `encargado` ni a `admin`.
  Introducir un cuarto rol, o un permiso suelto fuera de esta jerarquía, DEBE justificarse en
  una enmienda.

- **Autorización centralizada, nunca duplicada.** La verificación de rol DEBE vivir en UN
  mecanismo de backend —una función y su dependency reutilizable— y exponerse al frontend por
  UN hook. Replicar el chequeo de rol por servicio, por router o por pantalla está PROHIBIDO.
  El código de error de un fallo de autorización reutiliza los tipos de error ya existentes del
  sistema; no se inventa un tipo nuevo si uno cubre el caso.

- **Ocultar, no deshabilitar.** La navegación y las acciones que el rol activo no puede usar
  NO se muestran: no un botón deshabilitado, no una pantalla que da error al guardar, sino
  ausencia. El patrón ya establecido para el atajo "+ Crear producto nuevo" desde Venta
  —"nunca lleva a un error de permisos, simplemente no se ofrece"— es la regla para todo el
  sistema. El backend valida igualmente (defensa en profundidad): que el frontend oculte una
  opción no exime al servidor de rechazarla.

- **Excepción explícita.** La edición de `cliente` NO tiene restricción de rol: cualquier
  `cajero` puede editarla. Esta excepción ya está documentada y se mantiene.

**Autorización de pantalla** (enmienda v2.5.0). No introduce una regla nueva: cierra un
incumplimiento de "Ocultar, no deshabilitar" y de "Autorización centralizada". Hasta v2.4.0
sólo "Administración" (y, parcialmente, algunos endpoints de pagos) filtraban por rol; las
demás pantallas del nav eran visibles y llamables por cualquier `cajero`, contra este mismo
principio. El rol MÍNIMO por pantalla es:

| Rol mínimo | Pantallas |
|---|---|
| `cajero` (nivel base) | Venta · Conteo físico · Entradas de inventario · Arqueo de caja (del propio turno) · Consultas no atendidas (dentro de Venta) |
| `encargado` | Traspasos · Capital inmovilizado · Precios · Competencia · Pronóstico · Promociones · Caja y fraude (mermas, anomalías, indicadores por operador) · Terminales de pago · Pagos / Cobertura de medios · **Clientes** (pantalla de análisis: valor, fuga, segmentos) · **Reportes e inteligencia** (spec `008`, capa táctica/estratégica) |
| `admin` (en exclusiva) | Administración: gestión de operadores, alta/edición de datos maestros |

- **Alta y edición de `cliente`.** La "Excepción explícita" de arriba NO cambia: el alta y la
  edición de un `cliente` siguen SIN restricción de rol (un `cajero` las hace desde
  `IdentificarCliente` en Venta). Lo que es de rol `encargado` es la PANTALLA de análisis de
  clientes (puntuación de valor, señal de fuga, gráfico de segmentos) y sus lecturas: el listado
  ordenado por valor (`GET /clientes`), el detalle (`GET /clientes/{id}`, con el desglose de
  valor y el estado de fuga), `GET /clientes/fuga/resumen` y `GET /clientes/cumpleanos`. En nivel
  base queda sólo la **búsqueda por nombre** (`GET /clientes/busqueda`), que `IdentificarCliente`
  de Venta necesita para identificar a un cliente durante el cobro.
- **`estado_fuga` no viaja en `/clientes/busqueda`.** Aunque la ruta queda en nivel base (la usa
  `IdentificarCliente` de Venta), su respuesta NO incluye `estado_fuga` — sólo `valor` (FR-011a,
  uso ya legítimo desde antes de esta enmienda). `estado_fuga` sigue siendo de `encargado`,
  igual que en `GET /clientes` y `GET /clientes/{id}`. Corrección 2026-09-07 (la memoria de
  proyecto lo tenía pendiente desde antes de esta enmienda).
- **Sólo-lectura que el cajero necesita.** Los endpoints de lectura que consume un flujo de
  `cajero` —cupones y ofertas de recompra que `AplicarPromocionVenta` evalúa en la venta,
  sucursales y productos para poblar selectores, existencias— NO se cierran: pertenecen al
  nivel base aunque su pantalla de gestión sea de `encargado`.
- **Arqueo junto a Venta.** `Arqueo` sale del grupo de nav "Caja y seguridad" (que queda de
  puras pantallas de `encargado`) y se ofrece junto a `Venta`, siempre visible para un
  `cajero`: es una tarea diaria de caja, no de análisis.
- **Doble capa.** El nav oculta la opción (frontend, un solo hook) Y el backend rechaza el
  endpoint (un solo mecanismo, `exige_rol`). Ninguna capa exime a la otra.

**Identidad de sesión** (enmienda v2.4.0). La identidad del operador que ejecuta una petición
DEBE derivarse de una sesión verificable, nunca de un dato que el cliente envía sin prueba.

- **Token de sesión de turno.** Al abrir turno, y sólo tras validar el PIN, el backend DEBE
  emitir un JSON Web Token firmado con clave simétrica (HS256). Un token por turno abierto. Sus
  claims son el mínimo necesario —`id_operador`, `id_turno`, `rol`, `exp`— y el backend NUNCA
  autoriza confiando en el `rol` del claim: `requiere_rol` sigue resolviendo el rol real desde
  la tabla `operador` en cada verificación. El claim `rol` existe sólo para la interfaz.
- **Transporte y almacenamiento.** El token viaja en el header `Authorization: Bearer <token>`
  en toda petición que exija verificación de rol. El frontend lo mantiene en memoria, junto al
  turno abierto; guardarlo en `localStorage`, `sessionStorage` o cualquier almacenamiento de
  navegador está PROHIBIDO (convención del proyecto). Perderlo al recargar la página es el
  comportamiento correcto: la sesión de turno no sobrevive a una recarga, igual que hoy no
  sobrevive el turno abierto.
- **Doble invalidación.** El token DEBE dejar de ser válido por CUALQUIERA de: (a) expiración
  por tiempo —`exp` fijo a 12 horas desde la emisión—; (b) cierre del turno asociado; (c)
  desactivación del operador (`operador.activo = false`). El cierre se comprueba contra el
  estado ya existente del turno (`instante_cierre`), sin tabla de revocación ni columna nueva.
  La desactivación se comprueba en cada petición, igual que ya hace `requiere_rol`.
- **Una sola fuente de verdad.** El `id_operador` (o `id_operador_solicitante`) que viajaba en
  el cuerpo de los endpoints de escritura sujetos a rol queda DEPRECADO para efectos de
  autorización y se retira de esos cuerpos. Mantener dos fuentes —cuerpo y token— y validar su
  cruce no cierra la brecha, sólo la enmascara. El token es la única fuente.
- **Alcance.** Esta regla obliga a los endpoints que ya verificaban rol (`requiere_rol` /
  `exige_rol`). Los que hoy no verifican identidad alguna quedan fuera de su alcance hasta que
  una especificación los incorpore; cerrarlos de oficio sería expandir el alcance sin spec.
- **Un solo mecanismo, igual que la autorización.** La emisión y la verificación del token
  DEBEN vivir junto a `requiere_rol`, en `backend/rasero/seguridad.py`, y exponerse como una
  dependency reutilizable de FastAPI. Replicar la verificación de sesión por router o por
  servicio está PROHIBIDO. El fallo de sesión reutiliza el formato de error `{codigo, mensaje}`
  del resto del sistema, con `401` y un `codigo` que no colisione con los ya existentes.

**Razón**: un chequeo de permiso duplicado en tres servicios diverge en tres comportamientos
distintos en un mes, y el cuarto servicio que se añade se olvida de chequear. Un mecanismo
único es la única forma de que "quién puede hacer esto" tenga una sola respuesta. Y una opción
que aparece pero falla al usarse enseña al operador a desconfiar de la interfaz; una opción que
no aparece no miente.

## Lecturas Críticas del Enunciado

El caso de negocio provisto por el docente se implementa con criterio, no al pie de la letra.
Las siguientes seis lecturas son decisiones de análisis ya tomadas: DEBEN mantenerse
documentadas y cualquier especificación que las contradiga DEBE justificar por qué. Se
registran como sección propia y no como principio porque son análisis del caso, no reglas
de ingeniería de aplicación general.

1. **El arqueo horario no detecta el fraude que parece detectar.** "Cobrar 5, registrar 3"
   NO produce descuadre de caja: si el cajero se queda la diferencia, el efectivo físico
   coincide con lo registrado y no hay nada que un arqueo pueda encontrar. Ese fraude se
   detecta por otras señales —discrepancia entre salida de inventario y venta registrada,
   tasa de anulaciones por cajero, concentración de ventas bajo precio de lista en un turno—
   y esas señales DEBEN implementarse. El arqueo horario sí detecta un fraude distinto
   (retiro de efectivo sin registrar venta) y se implementa para ese caso, no para aquel.

2. **El precio depende del rol del producto, no de una regla única.** Bajar el precio de los
   productos más vendidos (gancho de tráfico) y subirlo en los de nicho (generador de margen)
   no contradice "decidir por margen y no por volumen": son dos roles distintos. El rol del
   producto DEBE modelarse de forma explícita; sin él, las recomendaciones del propio sistema
   se contradicen entre sí.

3. **La colocación física es parte de la decisión de precio.** El producto de mayor margen va
   a zona de exhibición privilegiada y el de menor margen a zona relegada. La salida del
   módulo de precios y márgenes DEBE incluir sugerencia de zona, no solo de precio.

4. **Hay venta perdida antes de que exista transacción.** Un cliente que no entra porque el
   comercio no acepta su medio de pago preferido no aparece en ningún registro de ventas,
   porque no hay transacción que registrar. Se trata como métrica de cobertura de medios de
   pago por sucursal, no como venta perdida en el sentido de faltante de inventario.

5. **El umbral de inactividad no puede ser global.** Treinta días sin comprar pueden ser
   abandono para un cliente y comportamiento normal para otro. El modelo DEBE derivar un
   intervalo de compra esperado por cliente individual; aplicar un umbral uniforme de fuga a
   toda la base de clientes está PROHIBIDO.

6. **Las promociones son tres mecanismos, no uno.** Implementarlas como un mecanismo único
   está PROHIBIDO. Son:
   - **Cupón por fecha fija** (cumpleaños): regla simple, sin inferencia.
   - **Empuje por patrón de recompra detectado**, con reserva del producto: regla de patrón.
   - **Descuento de reactivación a cliente inactivo**: el único que exige medir el efecto
     incremental real contra un grupo de control —si el cliente habría vuelto igualmente, el
     descuento destruye el margen que pretendía proteger. El grupo de control es obligatorio
     para este tipo, y su ausencia invalida cualquier afirmación sobre la eficacia de la
     campaña.

## Propiedad de Datos y Nomenclatura

Cada entidad del modelo pertenece a exactamente una funcionalidad. Las demás la consultan;
NO la redefinen, NO la duplican y NO alteran su esquema. Un cambio de esquema sobre una
entidad ajena DEBE hacerse en la funcionalidad propietaria. Esta tabla es de referencia
obligatoria y se mantiene actualizada conforme evolucionan los `data-model.md` de cada
funcionalidad; si un `data-model.md` y esta tabla discrepan, prevalece esta tabla hasta que
una enmienda la corrija.

- **001-core-ventas-inventario**: `sucursal`, `producto`, `producto_precio_sucursal`, `categoria`,
  `zona_exhibicion`, `lote`, `existencia`, `movimiento_inventario`, `traspaso`, `venta`,
  `renglon_venta`, `anulacion_venta`, `consulta_no_atendida`, `observacion_precio`,
  `canal_competencia`, `conteo_fisico`, `conteo_renglon`, `operador`, `turno`,
  `operacion_pendiente`. (20 entidades, sin cambio de conteo desde v2.1.2. La enmienda
  **v2.3.0** cambia el **esquema** de `operador`, no la lista: `operador` gana `id_sucursal`
  (FK → `sucursal`, NOT NULL, uno-a-uno) y su columna booleana `es_encargado` se retira y se
  reemplaza por `rol`, ENUM cerrado `cajero` | `encargado` | `admin`. Es un cambio de esquema
  sobre una entidad ya certificada de 001: la migración de Alembic convierte los datos
  existentes con la regla `es_encargado = FALSE → rol = 'cajero'` y `es_encargado = TRUE → rol
  = 'encargado'`, sin volver `admin` a ningún operador automáticamente, y lleva su procedimiento
  de reversión documentado. Ver Principio VI y la frontera de "autorización" más abajo.
  La enmienda **v2.7.2** hace un segundo cambio de esquema, ADITIVO PURO, sobre `venta`: gana
  `id_medio_pago` (FK → `medio_pago` de 007, NULL-able, sin default) para guardar la CATEGORÍA
  del pago que el cliente elige en el POS —efectivo, tarjeta, transferencia…—, nunca un dato de
  instrumento (el PAN/CVV siguen fuera de todo módulo). `NULL` en toda venta anterior; la
  factura de 009 usa el nombre del medio cuando la venta lo declara y cae a su heurística
  previa cuando es `NULL`. Migración `0014`, con reversión documentada.)
- **002-clientes-fidelizacion**: `cliente`, `visita`, `intervalo_compra`, `senal_fuga`.
- **003-precios-margenes**: `margen_calculado`, `rol_producto`, `sugerencia_precio`,
  `sugerencia_colocacion`. (`costo_producto` retirado y `sugerencia_precio` añadida por la
  enmienda **v2.2.3**, a raíz de la especificación real de 003 — ver frontera de "costo" más
  abajo.)
- **004-pronostico-demanda**: `demanda_observada`, `demanda_corregida`, `pronostico`,
  `sustitucion_producto`. (`sustitucion_producto` añadida por la enmienda **v2.2.4**, a raíz de la
  especificación real de 004 — FR-032, User Story 6 y FR-009 b; ver frontera demanda/pronóstico más
  abajo.)
- **005-promociones-inteligentes**: `campania`, `cupon`, `oferta_recompra`,
  `experimento_reactivacion`, `asignacion_experimento`, `redencion_promocion`. (`envio_promocional` y
  `grupo_control` retirados, y `cupon`, `oferta_recompra`, `experimento_reactivacion`,
  `asignacion_experimento` y `redencion_promocion` añadidos, por la enmienda **v2.2.5**, a raíz de la
  especificación real de 005 — tres mecanismos de promoción distintos, cada uno con su entidad, más
  el registro de redención compartido; ver frontera de "promoción" más abajo.)
- **006-caja-mermas-fraude**: `arqueo`, `merma`, `anomalia_caja`.
- **007-pagos-seguridad**: `terminal_pago`, `medio_pago`, `cobertura_pago`,
  `bitacora_auditoria`, `token_pago`. (`token_pago` añadida por la enmienda **v2.2.6**, a raíz de la
  especificación real de 007 — FR-016 a FR-022 y User Story 3: la persistencia del token de un cobro
  con tarjeta {token opaco, últimos cuatro dígitos, marca, tipo, terminal de captura, referencia de
  venta, clave de idempotencia}, nunca el PAN. No cabía en las otras cuatro entidades; ver frontera
  de "pago" más abajo.)
- **009-facturacion-electronica**: `factura_simulada`. (Añadida por la enmienda **v2.7.0**, a raíz
  de la especificación real de 009.) Es el documento con la **forma** de una factura electrónica
  ecuatoriana —RUC del comercio y razón social (de configuración, nunca literal de código, mismo
  patrón que `VITE_LOGO_COMERCIO`), secuencial `establecimiento-punto-correlativo`, subtotal, IVA,
  total, datos del comprador o "Consumidor Final"— generado **DESPUÉS** de una `venta` ya
  confirmada de 001. **SIMULADA**: sin conexión al SRI, sin firma electrónica, sin XML válido para
  el ente regulador — limitación de alcance honesta, no una integración fallida (mismo criterio
  que 007 para "sin pasarela real"). Ver frontera de "factura" más abajo.
  (Añadidas por la enmienda **v2.6.0**, a raíz de la especificación real de 008.) Las tres son
  **derivadas y regenerables**: `agregado_reporte` cachea el resultado de una vista (comparativo,
  tendencia o tablero) por tipo, ámbito de sucursal y período; `segmento_cliente` guarda la
  definición de cada grupo del último clustering (centroide por eje, descripción derivada, semilla,
  instante); `asignacion_segmento` es la relación cliente ↔ grupo de ese mismo recálculo. Borrar
  las tres y ejecutar de nuevo los cálculos de 008 sobre 001–006 reproduce exactamente el mismo
  estado. **008 no posee ningún dato de negocio** y **nada de 008 alimenta de vuelta a 001–007**;
  ver frontera de "reportes" más abajo.

Fronteras entre funcionalidades adyacentes, donde la propiedad es fácil de confundir:

- El **costo** del producto es dato de compra y pertenece a 001; el **margen** es cálculo
  derivado con reglas de negocio y pertenece a 003.
- La **fecha de caducidad** del lote vive en inventario (001); la **política de alerta** y la
  **contabilización de la pérdida** viven en mermas (006).
- El **conteo físico** y la **diferencia bruta** contra el saldo calculado pertenecen a inventario
  (001), que ejecuta el conteo y expone el descuadre sin interpretarlo; la **clasificación de la
  causa** de esa diferencia —merma, robo, error de registro— pertenece a 006, que no ejecuta
  conteos.
- La **detección** de riesgo de fuga pertenece a clientes (002); la **decisión** de ofrecer
  descuento de reactivación pertenece a promociones (005). Las **tres promociones son tres
  mecanismos distintos** (Lectura Crítica n.º 6), cada uno con su propia entidad en 005: `cupon`
  (fecha fija / cumpleaños), `oferta_recompra` (empuje por recompra, con reserva **de precio**, no
  de inventario — 005 no escribe contra `existencia` ni `movimiento_inventario` de 001) y
  `experimento_reactivacion` + `asignacion_experimento` (reactivación con grupo de control
  obligatorio). Que una promoción se redimió en una venta es `redencion_promocion`, propiedad de
  005, que **consulta** `venta` de 001 sin poseerla. La **marca de "promoción activa"** por
  producto, sucursal y período que 004 consume para corregir su serie de demanda es un cálculo
  derivado de esas redenciones y pertenece a 005; 004 la lee, no la reimplementa.
- La **demanda observada** —las ventas ya registradas, agregadas a una serie— descansa sobre datos
  de 001 (`venta`, `renglon_venta`, `movimiento_inventario`); la **serie de demanda corregida** por
  censura de quiebre, precio y promoción, y el **pronóstico** que se deriva de ella, son cálculo
  derivado con reglas de negocio y pertenecen a 004. La **relación de sustitución** entre dos
  productos es una declaración de negocio propia de 004 (`sustitucion_producto`), no un atributo de
  `producto` (001) — mismo patrón que `rol_producto` de 003.
- `anomalia_caja` es propiedad de 006, pero se **calcula consultando** `movimiento_inventario`,
  `venta` y `anulacion_venta`, propiedad de 001. Eso es consulta entre funcionalidades, no
  redefinición, y no infringe la regla de propiedad. Es además la forma en que la Lectura Crítica
  n.º 1 exige detectar el fraude de "cobrar 5, registrar 3": cruzando salida de inventario contra
  venta registrada y tasa de anulaciones por operador, no buscando un descuadre de efectivo que ese
  fraude nunca produce.
- La **referencia a la terminal de pago** que 001 guarda en cada `venta` (`referencia_terminal_pago`)
  es un valor **opaco** para 001, que no lo interpreta; la **tokenización** de los datos de pago
  —sustituir el número de tarjeta por un identificador sustituto y conservar solo {token, últimos
  cuatro dígitos, marca, tipo}— pertenece a 007 (`token_pago`). `token_pago` **consulta** `venta` de
  001 sin poseerla y **rellena** esa referencia opaca sin alterar el tipo ni la semántica del campo
  en el esquema de 001. El PAN completo, el CVV y los datos de banda/chip **no se almacenan,
  registran ni transmiten en ningún módulo** (Restricciones Técnicas, "Datos de pago"; Principio IV).
  La **cobertura de medios de pago aceptados por sucursal** —incluida la métrica de intención de
  compra no atendida cuando el cliente no puede pagar como quería (Lectura Crítica n.º 4)— es
  `cobertura_pago`, propiedad de 007, distinta de `consulta_no_atendida` de 001 ("no hay producto").

- La **autorización** —qué puede hacer cada rol de `operador`— es un mecanismo central
  (Principio VI): la función `requiere_rol` de `backend/rasero/seguridad.py` y su dependency de
  FastAPI en el backend, y un hook único en el frontend. NO pertenece a ninguna funcionalidad
  concreta: la consumen todos los routers que hoy chequeaban `es_encargado` por su cuenta
  (`administracion`, `cobertura_pago`, `terminales_pago`) y cualquiera futuro. La **identidad
  de sesión** —de qué operador es una petición— es la otra mitad del mismo mecanismo desde la
  enmienda **v2.4.0**: la emisión del token de sesión de turno al abrir turno y su verificación
  (firma, expiración, turno abierto, operador activo) viven también en `seguridad.py` y se
  exponen como dependency. El token de turno NO es una entidad persistida: es un valor firmado y
  sin estado, sin fila en ninguna tabla; la invalidación por cierre de turno se lee de
  `turno.instante_cierre`, propiedad de 001. La **autenticación** —la credencial PIN + hash
  (FR-006)— es cosa distinta, vive en `seguridad.py` desde 001 y no cambia con v2.3.0 ni con
  v2.4.0. La `id_sucursal` de `operador`
  es propiedad de 001 (columna de una entidad de 001); su uso como restricción de apertura de
  turno para `cajero`/`encargado` lo implementa el servicio de turnos de 001, y `admin` queda
  exento (abre turno en cualquier sucursal).

- La **factura** de 009 (`factura_simulada`) es un documento **derivado de una `venta` ya
  confirmada** de 001: 009 **consulta** `venta` y `renglon_venta` de 001 y los datos de `cliente`
  de 002 (nombre e identificador, si la venta se identificó), **sin poseer ninguno de los dos**.
  009 NO escribe contra ninguna tabla de 001–002. La factura se genera en el mismo punto del
  flujo donde 002 registra la `visita` y 005 la `redencion_promocion` —después del cobro, nunca
  como camino crítico de él (Principio II)—: si la generación falla, la venta queda intacta y
  sólo se pierde la factura de ese cobro, que puede regenerarse. El **IVA** y la **razón social /
  RUC** son configuración del despliegue, no literales de código (mismo patrón que
  `VITE_LOGO_COMERCIO`). Una `factura_simulada` NO contiene datos de pago (PAN, CVV, banda): a lo
  sumo el medio como etiqueta. Desde la enmienda **v2.7.2** ese medio es el que el cliente eligió
  en el POS (`venta.id_medio_pago` → nombre del `medio_pago` de 007); si la venta no lo declara
  (`NULL`), la factura cae a la heurística previa ("con referencia de terminal → tarjeta, sin ella
  → efectivo"). **Simulada** = sin SRI, sin firma, sin XML
  regulatorio; el sistema no afirma en ninguna parte que la factura tenga validez tributaria.
- Los **reportes e inteligencia** de 008 son **capa de solo lectura** sobre 001–007: cruzan y
  agregan (`agregado_reporte`) y agrupan clientes por similitud (`segmento_cliente`,
  `asignacion_segmento`), a la escala de la semana y el mes. 008 NO escribe contra ninguna tabla
  de 001–007 y **nada de 008 alimenta de vuelta** a esos módulos: la etiqueta de segmento que
  aparece en el detalle de un `cliente` (002) es lectura de `asignacion_segmento` de 008, no una
  columna de `cliente`. El clustering encaja en el **Principio V** sin redefinirlo: es explicable
  (algoritmo de pocos pasos, sin librería pesada ni datos externos), reversible (borrar y
  recalcular) y determinista (semilla fija, misma exigencia que el experimento de reactivación de
  005). Las tres entidades de 008 son regenerables; borrarlas no pierde ningún dato de negocio.

**Convención de nomenclatura**: identificadores de datos en español, `snake_case`, sustantivo
en singular, sin prefijo de número de módulo. La letra "ñ" está PROHIBIDA en identificadores
—se translitera como "ni": `campania`, nunca `campaña`— por compatibilidad de codificación
entre clientes de base de datos. Las claves foráneas se nombran `id_` seguido del nombre de
la tabla referida (`id_sucursal`, `id_producto`).

## Sistema de Diseño

El diseño visual es el vehículo de la explicabilidad exigida por el Principio V, no un tema
estético aparte. Sus reglas son normativas.

**Dos registros visuales según contexto de uso**, nunca uno uniforme:

- **Operación** (punto de venta, inventario, arqueo): alta densidad de información, la tabla
  como elemento principal, sin tarjetas. Radio de borde 2px. La animación se permite
  únicamente como confirmación de una acción del usuario —registrar venta, confirmar cobro,
  marcar consulta no atendida—. La animación decorativa, o disparada por scroll o por hover
  pasivo, está PROHIBIDA en este registro.
- **Análisis** (márgenes, pronóstico, clientes, promociones): una decisión por bloque, aire
  visual, líneas de texto por debajo de 80 caracteres. Radio de borde 6px. Se admite un
  momento de animación deliberado por pantalla —por ejemplo, al revelar el detalle de un
  cliente en riesgo de fuga— para señalar que eso es una decisión y no un dato más.

Un momento orquestado y deliberado por pantalla es PREFERIBLE a efectos repetidos en cada
elemento. El hover en cada fila y el fade-in en cada tarjeta son la señal más reconocible de
interfaz genérica y están desaconsejados en todo el sistema.

**Paleta**, anclada en objetos del comercio físico. Los fondos oscuros y los degradados están
PROHIBIDOS:

| Rol | Valor |
|---|---|
| Superficie base | `#F1F4F1` |
| Superficie alta | `#FFFFFF` |
| Tinta | `#1B2621` |
| Tinta suave | `#5A6862` |
| Marca | `#0F5132` |
| Borde | `#D5DCD6` |

Los colores semánticos se reservan exclusivamente para su significado y su uso decorativo
está PROHIBIDO: atención `#9A5B08` (dato envejecido, stock bajo), crítico `#8E2A2A`
(caducado, anomalía), estimado `#1F5673` (valor calculado, no observado).

**Tipografía por registro**: IBM Plex Sans en operación, con cifras tabulares reales para que
las columnas de dinero y de peso alineen por dígito; Source Serif 4 en análisis. Inter como
tipografía por defecto está PROHIBIDA.

**Redundancia de portadores**: todo dato con antigüedad o incertidumbre DEBE mostrar tres
portadores simultáneos y nunca solo color: el color semántico, un indicador de forma (punto
lleno, medio o hueco) y la antigüedad en texto explícito ("hace 3 d"). Un portador único
falla ante daltonismo, impresión en blanco y negro o reflejo de pantalla.

**Herramienta de ejecución**: la implementación de estos tokens en código durante la fase de
frontend se hace con la skill/toolkit Impeccable (`github.com/pbakaus/impeccable`). La
herramienta EJECUTA las decisiones de esta sección; NO las toma por su cuenta. Opera en pasos
distintos, y confundirlos es lo que esta constitución ya erró tres veces:

- **`init`** captura verdad de producto en `PRODUCT.md` —usuarios, propósito, restricciones—.
  Tiene PROHIBIDO escribir `DESIGN.md` y PROHIBIDO recibir contenido visual: paleta,
  tipografía y radios no se le entregan aquí.
- **`new-work`** construye una superficie. Cuando el mundo visual ya está fijado —como lo está
  en esta sección— NO abre torneo de identidad: mantiene el sistema fijo y decide únicamente
  la composición de esa pantalla. Es el paso que recibe esta sección como mundo fijado.
- **El agente documenter** escribe `DESIGN.md` AL FINAL, derivándolo de la interfaz ya
  construida, no de las intenciones previas. `DESIGN.md` no existe antes de la primera
  pantalla.

Es OBLIGATORIO que el contenido de esta sección llegue a `new-work` como mundo fijado antes de
generar cualquier interfaz: omitirlo hace que la herramienta derive hacia sus valores por
defecto genéricos, que es exactamente el resultado que esta sección existe para evitar. Ningún
paso de Impeccable puede proponer paleta o tipografía alternativas: están decididas aquí.

## Restricciones Técnicas y de Datos

- **Modelo multi-sucursal**: `sucursal` es una entidad de primera clase del dominio, con
  cardinalidad no acotada. El esquema, las consultas y los contratos DEBEN admitir N
  sucursales sin cambios estructurales: toda existencia, venta, caja, arqueo y previsión
  se identifica por su sucursal. Codificar un número fijo de sucursales en esquemas,
  consultas, claves, índices o interfaces está PROHIBIDO. El alcance de implementación y
  demostración de este examen cubre exactamente dos sucursales; esa cifra es una
  restricción de entrega, nunca un supuesto del modelo.
- **Infraestructura de datos**: el motor es PostgreSQL. En desarrollo se ejecuta de forma
  nativa, no en contenedor, para no consumir recursos de máquina durante el trabajo activo, y
  escucha en el puerto **5442** en lugar del 5432 por defecto, para no colisionar con otros
  proyectos del curso instalados en la misma máquina. El empaquetado en Docker Compose con
  volumen nombrado se hace en la fase final del proyecto, no durante el desarrollo. El uso de
  SQLite está PROHIBIDO en toda fase: carece de tipo `NUMERIC` real y opera en coma flotante,
  lo que introduce error de redondeo en cálculos de dinero y de peso en gramos, y no
  reproduce el comportamiento de PostgreSQL contra el que se valida el sistema.
- **Tiempo**: los instantes DEBEN almacenarse en UTC y presentarse en la zona horaria de la
  sucursal a la que pertenece la operación. Las agregaciones de negocio (cierre de caja,
  ventas del día) DEBEN calcularse sobre el día local de esa sucursal, no sobre el día UTC.
  Un informe que abarque varias sucursales DEBE declarar qué criterio de día aplica.
- **Precisión monetaria**: los importes DEBEN representarse con tipos decimales de precisión
  fija o enteros en la unidad mínima de la moneda. El uso de coma flotante binaria para
  dinero está PROHIBIDO. Cada importe persistido DEBE llevar su moneda asociada. La misma
  regla aplica al peso en gramos de los productos a granel.
- **Datos de pago**: los datos completos de tarjeta NO se almacenan, registran ni transmiten
  por sistemas propios. La integración con pasarelas de pago DEBE delegar la captura del
  medio de pago y conservar únicamente identificadores y últimos dígitos.
- **Datos personales**: los datos de clientes se recogen solo cuando una funcionalidad
  declarada los requiere, con finalidad y periodo de retención documentados en su
  especificación.
- **Migraciones**: todo cambio de esquema persistido DEBE ser versionado, aplicarse mediante
  script reproducible y llevar un procedimiento de reversión documentado.
- **Configuración y secretos**: los secretos DEBEN inyectarse por entorno. Un secreto en el
  repositorio es un defecto bloqueante, y su rotación es obligatoria si llegó a fusionarse.

## Flujo de Desarrollo y Puertas de Calidad

- **Ciclo Spec Kit**: toda funcionalidad no trivial recorre `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. La especificación describe el
  comportamiento observable; las decisiones de implementación pertenecen al plan.
- **Puerta constitucional**: el `plan.md` DEBE completar su sección `Constitution Check`.
  Cualquier desviación se registra en la tabla de complejidad con su justificación y la
  alternativa más simple descartada. Una desviación no registrada bloquea la fusión.
- **Puerta de propiedad de datos**: toda especificación que introduzca o modifique una
  entidad DEBE contrastarla contra la tabla de "Propiedad de Datos y Nomenclatura". Definir
  una entidad ya propiedad de otra funcionalidad, o nombrarla fuera de la convención,
  bloquea la fusión.
- **Puerta de sincronización de enmiendas**: toda enmienda a esta constitución DEBE, en el
  mismo cambio, actualizar todas las referencias a ella que existan en los artefactos de las
  funcionalidades afectadas (`spec.md`, `plan.md`, `data-model.md`, `contracts/`,
  `checklists/`, `tasks.md`) — número de versión citado como vigente, listas y conteos de
  entidades, y cualquier nota que describa como pendiente o bloqueado algo que la enmienda
  resuelve. Dejar un artefacto citando como vigente una versión superada está PROHIBIDO. Una
  enmienda que no sincroniza sus artefactos no está completa, aunque `constitution.md` sea
  correcto en sí mismo. Excepción: una cita histórica —que describe qué enmienda introdujo
  qué regla, no que reclama ser el estado actual— NO se barre; permanece correcta de forma
  permanente. La puerta aplica únicamente a las referencias que afirman describir el estado
  vigente.
- **Revisión**: todo cambio se revisa antes de fusionar. La revisión DEBE verificar
  explícitamente el cumplimiento de los Principios II, III y IV cuando el cambio toca
  dinero, existencias o contratos públicos.
- **Puertas automáticas**: compilación, análisis estático y las pruebas exigidas por el
  Principio III DEBEN estar en verde. Fusionar con puertas en rojo está PROHIBIDO;
  deshabilitar una prueba requiere registrar el motivo y la fecha límite de reactivación.
- **Ámbito acotado**: un cambio que altera un contrato público y además refactoriza su
  implementación DEBE separarse en cambios distintos.
- **Despliegue**: cada versión desplegable DEBE ser identificable y poder revertirse sin
  intervención manual sobre los datos.

## Gobernanza

Esta constitución prevalece sobre cualquier otra práctica, convención o preferencia del
equipo. Ante conflicto entre este documento y una guía, plantilla o costumbre, prevalece
este documento.

**Enmiendas**: cualquier persona del equipo puede proponer una enmienda mediante un cambio
sobre este archivo que incluya la motivación, el impacto sobre funcionalidades en curso y,
si procede, el plan de migración. La enmienda requiere aprobación en revisión antes de
fusionarse. Los cambios en artefactos ya especificados o planificados se reconcilian en su
propia funcionalidad; ninguna enmienda reescribe retroactivamente trabajo ya entregado.

**Versionado**: esta constitución sigue versionado semántico.

- **MAYOR**: eliminación o redefinición incompatible de un principio o de la gobernanza.
- **MENOR**: nuevo principio o sección, o ampliación material de una guía existente.
- **PARCHE**: aclaraciones, redacción y correcciones sin cambio de significado.

**Cumplimiento**: la verificación ocurre en dos puntos. En `/speckit-plan`, mediante la
puerta `Constitution Check` antes de generar artefactos de diseño. En revisión de código,
antes de fusionar. Una violación detectada tras la fusión se registra como defecto y se
corrige o se convierte en enmienda; permanecer indefinidamente en incumplimiento tácito
está PROHIBIDO.

**Versión**: 2.7.2 | **Ratificada**: 2026-09-04 | **Última enmienda**: 2026-09-08
