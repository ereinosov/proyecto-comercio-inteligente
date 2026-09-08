# Research — 008-reportes-inteligencia

## 1. Naturaleza de solo lectura y las tres entidades derivadas

**Decisión**: 008 no posee ningún dato de negocio. Sus únicas tablas —`agregado_reporte`,
`segmento_cliente`, `asignacion_segmento`— son caché y resultado de cálculo, todas regenerables
desde 001–006.

**Razón**: la pregunta que motiva 008 ("¿cómo va el negocio?") se responde cruzando lo que ya
existe, no capturando algo nuevo. Si 008 escribiera contra `venta`, `cliente` o `merma` estaría
redefiniendo datos ajenos (prohibido por Propiedad de Datos). La caché existe sólo por
rendimiento; la asignación de segmento existe sólo para no recalcular el clustering en cada
carga y para que 002 pueda mostrar la etiqueta. Ambas se pueden truncar sin pérdida.

**Alternativas descartadas**: (a) calcular todo en vivo sin caché — repetir el mismo `GROUP BY`
de decenas de miles de filas en cada carga de pantalla gerencial es gasto sin frescura real; (b)
materializar los agregados como vistas de PostgreSQL — acopla el esquema a la estrategia de
caché y complica el `downgrade`; una tabla simple con `(tipo, ambito, periodo) UNIQUE` e
`instante_calculo` es suficiente y explícita.

## 2. k-means en Python puro, no una librería

**Decisión**: el clustering es el **algoritmo de Lloyd** implementado en `dominio/kmeans.py`
como función pura sobre `list[tuple[float, float, float]]`: inicialización de centroides
(k-means++ con RNG de semilla fija, o los k primeros puntos ordenados de forma determinista),
asignación de cada punto al centroide más cercano por distancia euclídea, recálculo de cada
centroide como la media aritmética de sus puntos, parada por convergencia (ninguna reasignación)
o iteración máxima (p. ej. 50). Sin `numpy`, `scipy`, `scikit-learn`, `pandas`.

**Razón**: mismo criterio que 006 aplicó al rechazar `scipy`/`statsmodels` para la prueba z —
Principio I: un segundo ecosistema de librería para una función que cabe en 40 líneas de Python
es complejidad injustificada. Con cientos de clientes y tres dimensiones, el coste es
trivialmente bajo. Y una implementación propia es **auditable**: un evaluador puede leer los
cuatro pasos, cosa que no puede hacer con `sklearn.cluster.KMeans`.

**Determinismo (FR-019)**: el RNG se construye con una semilla de `config/reportes.py` (fija,
como la del experimento de 005). k-means++ y el orden de recorrido de los puntos se hacen
deterministas ordenando los clientes por `id_cliente` antes de empezar. Dos ejecuciones sobre
los mismos datos dan la misma partición.

**Elección de k (resuelto — hallazgo BAJO #1 del analysis)**: `K_SEGMENTOS = 4`, fijado en
`backend/rasero/config/reportes.py`. Se evaluaron 3 y 4 sobre la forma esperada de la base —un
minimarket de dos tiendas—: con **4** la clientela se separa en los grupos que un encargado
reconoce y sobre los que puede actuar (frecuentes de buen margen, frecuentes de bajo margen,
esporádicos, y dormidos / en fuga); con **3** "esporádicos" y "dormidos" se colapsan en un solo
grupo poco accionable, y con **5+** se fragmenta sin ganar interpretabilidad. `k` NO es un
parámetro de interfaz en esta versión (FR-018, Assumption). Si hay menos de `k` clientes
clasificables, `dominio/kmeans.agrupar` reduce `k` a esa cantidad automáticamente (FR-024); el
servicio devuelve `409` sólo si no hay clientes clasificables en absoluto.

**Alternativas descartadas**: (a) reglas de umbrales fijos por eje ("alto valor = gasta > X") —
obliga a elegir y re-justificar X, que enveja; el clustering deja que los datos digan dónde
están los grupos (Clarification). (b) DBSCAN / jerárquico — más parámetros que explicar (ε,
min_pts / criterio de enlace) y resultado menos estable; k-means con k pequeño es lo más simple
que resuelve el caso. (c) Modelo supervisado — no hay etiquetas de "buen/mal cliente" que
aprender, y entrenar contra un proxy introduce el sesgo que el Principio V quiere evitar.

## 3. Features del clustering y su normalización

**Decisión**: tres ejes por cliente clasificable (≥ 3 visitas):

- **Frecuencia** = `1 / intervalo_compra_estimado` de 002 (visitas por día), o
  `n_visitas / (dias entre primera y última visita)` si 002 no tiene el intervalo calculado.
- **Margen** = media de `visita.margen_relativo` de sus visitas (ya es un ratio, 002).
- **Recencia** = días desde la última `visita` a hoy (negado o invertido para que "más reciente"
  sea "mejor" en la misma dirección que los otros dos ejes — se documenta en data-model).

Cada eje se **estandariza** (z-score sobre la población de clientes clasificables: restar la
media, dividir por la desviación) para que k-means no quede dominado por el eje de mayor escala.
La estandarización usa media y desviación de la corrida actual, se guarda en `segmento_cliente`
para poder describir los centroides en unidades originales.

**Razón**: son exactamente los tres datos que 002 ya calcula para su puntuación de valor y su
señal de fuga; 008 no captura nada nuevo (FR-018). El z-score es la normalización estándar para
k-means y es de una línea por eje.

## 4. Descripción de un grupo derivada del centroide (FR-022)

**Decisión**: cada eje del centroide, en unidades estandarizadas, se traduce a **alto / medio /
bajo** por su signo y magnitud (p. ej. `z > 0.5` → alto, `z < -0.5` → bajo, en medio → medio).
La descripción se compone de esas tres etiquetas: "vienen {seguido|a veces|poco}, dejan
{buen|medio|poco} margen, compraron {hace poco|hace un tiempo|hace mucho}". No hay ningún texto
de grupo fijo ni nombre humano preasignado ("VIP", "en riesgo"): el nombre es la frase derivada.

**Razón**: FR-022 lo exige explícitamente. Un nombre fijo mentiría si el clustering de esta
corrida no produjo ese perfil; la frase derivada siempre corresponde a lo que el grupo es.

## 5. Reutilizar los servicios de lectura de 001–006

**Decisión**: donde un módulo ya expone el agregado que 008 necesita, 008 llama a ese servicio
en vez de re-consultar las tablas base:

| Necesidad de 008 | Servicio existente |
|---|---|
| margen promedio ponderado por sucursal | `servicios/margenes.resolver_margen_visita` / `listar_margenes_sucursal` (003) |
| merma valorada por semana y causa | `servicios/mermas.resumen_mermas_por_causa` (006) |
| distribución de fuga | `servicios/clientes.resumen_fuga_por_segmento` (002) |
| serie de demanda corregida | servicio de demanda de 004 |
| cobertura / intención no atendida | `servicios/cobertura_pago.resumen_cobertura` (007) |
| veredicto del último experimento | `servicios/experimentos` (005) |

Sólo se consultan tablas base directamente para lo que ningún servicio agrega hoy: ventas y
tickets por período y sucursal (`venta`, `renglon_venta` de 001) y las tres features del
clustering (`visita`, `intervalo_compra` de 002).

**Razón**: evita reimplementar reglas de negocio ajenas (Propiedad de Datos) y mantiene un solo
lugar donde vive cada cálculo. Si el margen ponderado de 003 cambia, 008 lo hereda.

## 6. Granularidad temporal: semana y mes locales

**Decisión**: los períodos se calculan en la **zona horaria de la sucursal** (`sucursal.zona_horaria`,
mismo criterio que 006 usa para `dia_local`). "Semana" = semana ISO local (lunes–domingo);
"mes" = mes calendario local. Para el ámbito "todas las sucursales", se agrega por período local
de cada sucursal y se suman los agregados por período nominal (research-note: dos sucursales en
la misma zona horaria hoy, así que no hay desalineación real; se documenta el criterio para
cuando no sea así).

`dominio/periodo_local.py` es una función pura que, dada una zona horaria y un rango, devuelve la
lista de `(inicio_utc, fin_utc, etiqueta, completo: bool)`.

**Razón**: una venta a las 23:30 del domingo local pertenece a esa semana, no a la siguiente en
UTC. El mismo bug que 006 ya resolvió para el día.

## 7. Caché: clave, invalidación, sin trabajo programado

**Decisión**: `agregado_reporte` tiene `UNIQUE (tipo, ambito, periodo_inicio, periodo_fin,
granularidad)`. Se escribe la primera vez que se pide esa combinación; se lee mientras exista;
el encargado la invalida con un botón "Actualizar" que hace `DELETE` de esa fila y recalcula. No
hay TTL ni job que la refresque: FR-028 dice explícitamente que el sistema no intenta detectar
cambios aguas arriba, y añadir un cron contradiría "sin trabajo programado en esta
funcionalidad" (Assumption).

**Razón**: la frescura la controla la persona, informada por `instante_calculo` visible. Un TTL
arbitrario recalcularía sin que nada haya cambiado o serviría datos viejos sin avisar; el botón
explícito es honesto.

**Detalle de la tendencia**: el `UNIQUE` de `agregado_reporte` es `(tipo, ambito_sucursal,
periodo_inicio, periodo_fin, granularidad)` — no distingue el *indicador* ni el *producto* de una
tendencia. En vez de ampliar el esquema con dos columnas más (o de plegar el indicador en
`tipo`, que rompería el `CHECK`), el indicador+producto viajan dentro de
`contenido["_clave"]`; al leer, si `_clave` no coincide con lo pedido se trata como fallo de
caché y se sobrescribe (last-writer-wins por clave de período). Aceptable: cada gráfico de la
pantalla pide un indicador a la vez, así que el trasiego real es mínimo. El comparativo y el
tablero no tienen este matiz (una sola forma por clave de período).

## 8. Recálculo de segmentos: por lote, disparado por persona, idempotente

**Decisión**: `POST /reportes/segmentos/recalculo` ejecuta el clustering completo, reemplaza
**todas** las filas de `asignacion_segmento` y `segmento_cliente` de la corrida anterior, y
graba la nueva marca de tiempo y semilla. Dos llamadas seguidas producen el mismo resultado
(mismos datos, misma semilla) y sólo mueven el `instante_calculo`. No hay recálculo en
`GET /reportes/segmentos` (sólo lee la última corrida).

**Razón**: FR-020. Correr k-means en cada `GET` gastaría CPU repitiendo un resultado que no
cambia entre las 15:00 y las 15:05, y haría la pantalla lenta. El clustering es una foto que se
actualiza cuando alguien decide.

## 9. Rol y frontera con 002

**Decisión**: todo `/reportes/*` exige `encargado` (`exige_rol`, router-level). La etiqueta de
segmento en el detalle de un cliente de 002 se sirve desde 008 (`GET /clientes/{id}` de 002 NO
gana un campo; el frontend de Clientes llama a `GET /reportes/segmentos/cliente/{id}` de 008, o
002 lo incluye leyendo `asignacion_segmento` sin poseerla — se decide en el plan de detalle, sin
que 002 escriba nada).

**Razón**: constitución v2.5.0 (rol) y v2.6.0 (frontera: nada de 008 alimenta de vuelta a 002).

## 10. Sin migración de datos

**Decisión**: la migración `0012` crea tres tablas vacías. No hay backfill: los agregados y los
segmentos se generan la primera vez que alguien abre cada vista / pulsa "Recalcular". El
`downgrade` elimina las tres tablas — no se pierde ningún dato de negocio (Propiedad de Datos,
v2.6.0).
