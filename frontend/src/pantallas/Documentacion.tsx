/**
 * Documentación del sistema — superficie de DEMOSTRACIÓN, no parte del flujo de un operador.
 *
 * Se abre desde un enlace en la pantalla de apertura de turno (`AperturaTurno`) y no aparece en
 * la navegación de la aplicación: ningún rol la "usa" para operar. Reúne, en una sola pantalla
 * de lectura, el objetivo del proyecto, su origen en el enunciado del curso, la segmentación de
 * la empresa (operativa / táctica / estratégica), los actores, los nueve módulos, los casos de
 * uso, la arquitectura y la aplicación de Spec Kit.
 *
 * Registro de Análisis (Source Serif 4 en prosa, IBM Plex Sans en tablas y etiquetas), radio
 * 6px, contorno estructural, cero sombras, sin Verde Rasero (La Regla del Registro Sin Dinero).
 */

import { useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { Boton } from "../componentes/Boton";
import marcaSistema from "../activos/marca/rasero-wordmark-512w.png";
import marcaMono from "../activos/marca/despensa-logo-mono-800w.png";
import estilos from "./Documentacion.module.css";

interface Props {
  onVolver: () => void;
}

const SECCIONES: { id: string; titulo: string }[] = [
  { id: "objetivo", titulo: "1 · Objetivo del sistema" },
  { id: "empresa", titulo: "2 · La empresa de demostración" },
  { id: "origen", titulo: "3 · Del enunciado al sistema" },
  { id: "segmentacion", titulo: "4 · Segmentación de la empresa" },
  { id: "actores", titulo: "5 · Actores del sistema" },
  { id: "modulos", titulo: "6 · Módulos (001–009)" },
  { id: "alcance", titulo: "7 · Decisiones de alcance" },
  { id: "casos-uso", titulo: "8 · Casos de uso" },
  { id: "arquitectura", titulo: "9 · Arquitectura" },
  { id: "modelo-datos", titulo: "10 · Modelo de datos (tablas)" },
  { id: "speckit", titulo: "11 · Aplicación de Spec Kit" },
  { id: "glosario", titulo: "12 · Glosario" },
  { id: "creditos", titulo: "13 · Créditos académicos" },
  { id: "despliegue", titulo: "14 · Puesta en marcha" },
];

function Comando({ children }: { children: ReactNode }) {
  return <pre className={estilos.bloqueComandos}>{children}</pre>;
}

function P({ children }: { children: ReactNode }) {
  return <p className={estilos.p}>{children}</p>;
}
function H3({ children }: { children: ReactNode }) {
  return <h3 className={estilos.h3}>{children}</h3>;
}
function F({ children }: { children: ReactNode }) {
  return <span className={estilos.fuerte}>{children}</span>;
}
function C({ children }: { children: ReactNode }) {
  return <code className={estilos.codigo}>{children}</code>;
}

function Tabla({ cabeceras, filas }: { cabeceras: string[]; filas: ReactNode[][] }) {
  return (
    <div className={estilos.tablaEnvoltura}>
      <table className={estilos.tabla}>
        <thead>
          <tr>
            {cabeceras.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i}>
              {fila.map((celda, j) => (
                <td key={j}>{celda}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Modelo de datos ────────────────────────────────────────────────────────────
// Las 50 tablas del esquema (migraciones Alembic 0001–0013), tal como las declara
// `backend/rasero/persistencia/modelos.py`. Cada tabla pertenece a exactamente un
// módulo (tabla de Propiedad de Datos de la constitución). Notación: PK = clave
// primaria, FK→x = clave foránea a `x`, U = restricción UNIQUE, · = anulable.
// Tipos: num(p,e) = NUMERIC de precisión fija (nunca coma flotante), ts = timestamptz.

type ColBD = [string, string, string];
interface TablaBDDef {
  nombre: string;
  proposito: string;
  cols: ColBD[];
}

const MODELO_DATOS: { modulo: string; intro: ReactNode; tablas: TablaBDDef[] }[] = [
  {
    modulo: "001 · Core de ventas e inventario — 20 tablas",
    intro: (
      <>
        Dueño de la estructura del negocio (sucursales, catálogo, personas) y de los hechos de
        caja e inventario. El inventario es reconstruible en su totalidad desde{" "}
        <C>movimiento_inventario</C>: <C>existencia</C> es sólo una agregación derivada.
      </>
    ),
    tablas: [
      {
        nombre: "sucursal",
        proposito: "Cada local. El modelo admite N; dos es el alcance de la entrega.",
        cols: [
          ["id_sucursal", "int", "PK"],
          ["nombre", "text", "U"],
          ["zona_horaria", "text", "para el día local de cierres y arqueos"],
          ["activo", "bool", "baja lógica (nunca se borra)"],
        ],
      },
      {
        nombre: "categoria",
        proposito: "Familia de producto; define el ícono y el umbral de capital inmovilizado.",
        cols: [
          ["id_categoria", "int", "PK"],
          ["nombre", "text", "U"],
          ["dias_umbral_inmovilizado", "int", "· días sin rotación para alertar"],
          ["activo", "bool", ""],
        ],
      },
      {
        nombre: "producto",
        proposito: "Ítem del catálogo. Precio base; el override por sucursal va aparte.",
        cols: [
          ["id_producto", "int", "PK"],
          ["id_categoria", "int", "· FK→categoria"],
          ["nombre", "text", ""],
          ["es_granel", "bool", "true = se vende pesado en gramos"],
          ["precio_vigente", "num(12,4)", "precio base de lista"],
          ["lleva_caducidad", "bool", "exige fecha de caducidad al recibir lote"],
          ["moneda", "text(3)", "USD"],
          ["url_imagen", "text", "· imagen opcional para el catálogo de Venta"],
          ["activo", "bool", ""],
        ],
      },
      {
        nombre: "producto_precio_sucursal",
        proposito: "Override opcional del precio base para una sucursal concreta.",
        cols: [
          ["id_producto", "int", "PK · FK→producto"],
          ["id_sucursal", "int", "PK · FK→sucursal"],
          ["precio_vigente", "num(12,4)", "precio efectivo en esa sucursal"],
          ["moneda", "text(3)", "USD"],
        ],
      },
      {
        nombre: "zona_exhibicion",
        proposito: "Ubicación física en góndola; destino de las sugerencias de colocación de 003.",
        cols: [
          ["id_zona_exhibicion", "int", "PK"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["nombre", "text", ""],
          ["grado_privilegio", "smallint", "mayor = más visible"],
          ["activo", "bool", ""],
        ],
      },
      {
        nombre: "operador",
        proposito: "Cajero / encargado / admin. Atado a una sola sucursal; se autentica con PIN.",
        cols: [
          ["id_operador", "int", "PK"],
          ["nombre", "text", ""],
          ["pin_hash", "text", "hash del PIN de 4 dígitos, nunca el PIN"],
          ["id_sucursal", "int", "FK→sucursal (fija, uno-a-uno)"],
          ["rol", "text", "CHECK ∈ {cajero, encargado, admin}"],
          ["activo", "bool", "desactivar invalida su sesión de turno"],
        ],
      },
      {
        nombre: "turno",
        proposito: "Sesión de trabajo en una caja. Ancla ventas, arqueo y consultas no atendidas.",
        cols: [
          ["id_turno", "int", "PK"],
          ["id_operador", "int", "FK→operador"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["caja", "text", "identificador de la caja física"],
          ["instante_apertura", "ts", ""],
          ["instante_cierre", "ts", "· null mientras el turno está abierto"],
        ],
      },
      {
        nombre: "lote",
        proposito: "Una recepción concreta de mercadería, con su costo y su caducidad (FEFO).",
        cols: [
          ["id_lote", "int", "PK"],
          ["id_producto", "int", "FK→producto"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["costo_unitario", "num(12,4)", "costo real de ESTA entrada"],
          ["fecha_caducidad", "date", "· null si el producto no caduca"],
          ["instante_entrada", "ts", "desempate FEFO si no hay caducidad"],
          ["moneda", "text(3)", "USD"],
        ],
      },
      {
        nombre: "movimiento_inventario",
        proposito: "Libro mayor del inventario: la única fuente de verdad. Sólo se anexa.",
        cols: [
          ["id_movimiento_inventario", "bigint", "PK"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_producto", "int", "FK→producto"],
          ["id_lote", "int", "· FK→lote"],
          [
            "tipo",
            "text",
            "CHECK ∈ {entrada_compra, salida_venta, entrada_anulacion, salida_traspaso, entrada_traspaso, ajuste_conteo}",
          ],
          ["cantidad", "num(14,0)", "unidades, o gramos para granel"],
          ["instante", "ts", ""],
          ["id_venta · id_traspaso · id_conteo_fisico · id_anulacion_venta", "int", "· FK; exactamente uno según `tipo` (CHECK)"],
        ],
      },
      {
        nombre: "existencia",
        proposito: "Saldo por (sucursal, producto, lote). Derivado; ante duda gana el recálculo.",
        cols: [
          ["id_existencia", "bigint", "PK sustituta"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_producto", "int", "FK→producto"],
          ["id_lote", "int", "· FK→lote"],
          ["cantidad", "num(14,0)", "puede ser negativa: nunca bloquea un cobro"],
          ["—", "—", "U (sucursal, producto, lote) NULLS NOT DISTINCT"],
        ],
      },
      {
        nombre: "traspaso",
        proposito: "Movimiento entre sucursales como dos asientos enlazados (nada se pierde en tránsito).",
        cols: [
          ["id_traspaso", "int", "PK"],
          ["id_sucursal_origen", "int", "FK→sucursal"],
          ["id_sucursal_destino", "int", "FK→sucursal (CHECK: distinta del origen)"],
          ["estado", "text", "CHECK ∈ {en_transito, recibido}"],
          ["instante_despacho", "ts", ""],
          ["instante_recepcion", "ts", "· null hasta que la sucursal destino confirma"],
        ],
      },
      {
        nombre: "venta",
        proposito: "Cabecera del cobro. Idempotente por clave: un reintento de red no la duplica.",
        cols: [
          ["id_venta", "bigint", "PK"],
          ["clave_idempotencia", "text", "U"],
          ["id_turno", "int", "FK→turno"],
          ["referencia_terminal_pago", "text", "· referencia opaca del datáfono"],
          ["id_medio_pago", "int", "· FK→medio_pago (007); medio que eligió el cliente en el POS (v2.7.2)"],
          ["instante", "ts", ""],
          ["total", "num(12,2)", ""],
          ["moneda", "text(3)", "USD"],
        ],
      },
      {
        nombre: "renglon_venta",
        proposito: "Línea de una venta. Unidad O peso, nunca ambos (CHECK).",
        cols: [
          ["id_renglon_venta", "bigint", "PK"],
          ["id_venta", "int", "FK→venta"],
          ["id_producto", "int", "FK→producto"],
          ["cantidad_unidades", "int", "· exactamente una de las dos, > 0"],
          ["cantidad_gramos", "int", "· "],
          ["precio_aplicado", "num(12,4)", "precio unitario del momento"],
          ["importe", "num(12,2)", ""],
          ["moneda", "text(3)", "USD"],
        ],
      },
      {
        nombre: "anulacion_venta",
        proposito: "Anulación atada al turno o a un encargado. Genera reingreso de stock.",
        cols: [
          ["id_anulacion_venta", "bigint", "PK"],
          ["id_venta", "int", "U · FK→venta (a lo sumo una por venta)"],
          ["id_operador", "int", "FK→operador"],
          ["instante", "ts", ""],
          ["motivo", "text", "·"],
        ],
      },
      {
        nombre: "consulta_no_atendida",
        proposito: "El cliente pidió algo que no había. Venta perdida que normalmente nadie registra.",
        cols: [
          ["id_consulta_no_atendida", "bigint", "PK"],
          ["id_producto", "int", "FK→producto"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_turno", "int", "FK→turno"],
          ["instante", "ts", ""],
          ["saldo_en_el_instante", "num(14,0)", "stock en ese momento (normalmente 0)"],
        ],
      },
      {
        nombre: "canal_competencia",
        proposito: "Tienda / súper / bazar / app contra la que se compara el precio propio.",
        cols: [
          ["id_canal_competencia", "int", "PK"],
          ["nombre", "text", ""],
          ["nombre_normalizado", "text", "U"],
        ],
      },
      {
        nombre: "observacion_precio",
        proposito: "Precio de la competencia, fechado, con canal, presentación y frescura.",
        cols: [
          ["id_observacion_precio", "bigint", "PK"],
          ["id_producto", "int", "FK→producto"],
          ["id_canal_competencia", "int", "FK→canal_competencia"],
          ["presentacion_cantidad", "num(12,3)", ""],
          ["presentacion_unidad", "text", "CHECK ∈ {unidad, gramo, mililitro}"],
          ["precio_observado", "num(12,2)", ""],
          ["fuente", "text", "quién / dónde se observó"],
          ["origen_captura", "text", "CHECK ∈ {manual, archivo}"],
          ["instante_captura", "ts", "define la antigüedad del dato"],
          ["id_turno", "int", "· FK→turno"],
          ["comparable", "bool", "false = presentación no equiparable"],
        ],
      },
      {
        nombre: "conteo_fisico",
        proposito: "Recuento de stock real. Expone el descuadre bruto; no lo interpreta.",
        cols: [
          ["id_conteo_fisico", "int", "PK"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["estado", "text", "CHECK ∈ {abierto, resuelto}"],
          ["alcance", "jsonb", "· qué productos/zonas abarca"],
          ["instante_inicio", "ts", ""],
          ["instante_resolucion", "ts", "·"],
        ],
      },
      {
        nombre: "conteo_renglon",
        proposito: "Línea de un conteo: contado vs. esperado y su diferencia.",
        cols: [
          ["id_conteo_renglon", "bigint", "PK"],
          ["id_conteo_fisico", "int", "FK→conteo_fisico"],
          ["id_producto", "int", "FK→producto"],
          ["id_lote", "int", "· FK→lote"],
          ["cantidad_contada · cantidad_esperada · diferencia", "num(14,0)", "la causa la clasifica 006"],
        ],
      },
      {
        nombre: "operacion_pendiente",
        proposito: "Cola de lo trabajado sin conexión. Ante conflicto gana la operación más antigua.",
        cols: [
          ["id_operacion_pendiente", "uuid", "PK"],
          ["tipo_operacion", "text", "CHECK ∈ {venta, consulta_no_atendida, anulacion_venta, recepcion_traspaso, resolucion_conteo}"],
          ["carga", "jsonb", "la petición original, íntegra"],
          ["recurso_afectado", "text", "clave para detectar el conflicto"],
          ["marca_tiempo_origen", "ts", "instante real en el mundo físico"],
          ["instante_recepcion", "ts", "· cuándo llegó al servidor"],
          ["estado", "text", "CHECK ∈ {pendiente_de_sincronizar, sincronizada, conflicto_resuelto}"],
          ["id_operacion_prevaleciente", "uuid", "· FK→operacion_pendiente (la que ganó)"],
        ],
      },
    ],
  },
  {
    modulo: "002 · Clientes y fidelización — 4 tablas",
    intro: (
      <>
        El valor de un cliente combina <F>frecuencia, monto y margen</F>; la fuga se detecta
        contra <F>su propio</F> intervalo de compra, nunca con un umbral global.
      </>
    ),
    tablas: [
      {
        nombre: "cliente",
        proposito: "Ficha del cliente: nombre, contacto, cumpleaños e identificador. Anonimizable.",
        cols: [
          ["id_cliente", "int", "PK"],
          ["nombre", "text", "·"],
          ["fecha_nacimiento", "date", "· alimenta el cupón de cumpleaños de 005"],
          ["contacto", "text", "· se vacía al anonimizar"],
          ["identificador", "text", "· cédula/RUC; U parcial; sólo para no duplicar"],
          ["fecha_alta", "ts", ""],
          ["anonimizado", "bool", ""],
          ["instante_anonimizacion", "ts", "·"],
        ],
      },
      {
        nombre: "visita",
        proposito: "Una compra identificada. Monto y margen se congelan al crearla (no se recalculan).",
        cols: [
          ["id_visita", "bigint", "PK"],
          ["id_cliente", "int", "FK→cliente"],
          ["id_venta", "int", "U · FK→venta (001, sólo lectura)"],
          ["instante", "ts", ""],
          ["monto_total", "num(12,2)", "snapshot"],
          ["margen_relativo", "num(6,4)", "ratio sobre precio, no un monto"],
        ],
      },
      {
        nombre: "intervalo_compra",
        proposito: "Una fila por cliente: cada cuánto compra (mediana de intervalos, ≥ 3 visitas).",
        cols: [
          ["id_cliente", "int", "PK · FK→cliente"],
          ["intervalo_esperado_dias", "num(8,2)", "· null si aún no hay datos"],
          ["visitas_consideradas", "int", ""],
          ["estado", "text", "CHECK ∈ {datos_insuficientes, calculado}"],
          ["instante_calculo", "ts", ""],
        ],
      },
      {
        nombre: "senal_fuga",
        proposito: "Máquina de estados de la fuga silenciosa. A lo sumo una fila abierta por cliente.",
        cols: [
          ["id_senal_fuga", "bigint", "PK"],
          ["id_cliente", "int", "FK→cliente"],
          ["estado", "text", "CHECK ∈ {activa, confirmada, resuelta}"],
          ["instante_deteccion", "ts", "supera 1× el intervalo esperado"],
          ["instante_confirmacion", "ts", "· supera 5× o 12 meses"],
          ["instante_resolucion", "ts", "· nueva visita"],
          ["instante_purga_programada", "ts", "·"],
        ],
      },
    ],
  },
  {
    modulo: "003 · Precios y márgenes — 4 tablas",
    intro: (
      <>
        Todo lo que 003 escribe es propio: alterar el esquema de <C>producto</C> (de 001) desde
        aquí está prohibido. Las sugerencias son <F>append-only</F> y guardan los insumos que
        usaron, para seguir siendo explicables después.
      </>
    ),
    tablas: [
      {
        nombre: "rol_producto",
        proposito: "Rol comercial: gancho de tráfico vs. generador de margen. Sin fila = sin clasificar.",
        cols: [
          ["id_producto", "int", "PK · FK→producto"],
          ["rol", "text", "CHECK ∈ {gancho_trafico, generador_margen}"],
          ["instante_asignacion", "ts", ""],
        ],
      },
      {
        nombre: "margen_calculado",
        proposito: "Margen real por producto y sucursal. Se recalcula en cada lectura (upsert).",
        cols: [
          ["id_producto", "int", "PK · FK→producto"],
          ["id_sucursal", "int", "PK · FK→sucursal"],
          ["costo_vigente", "num(12,4)", "· null si no hay existencia con lote"],
          ["precio_vigente", "num(12,4)", ""],
          ["margen", "num(6,4)", "· null, nunca cero, cuando no es calculable"],
          ["confiable", "bool", "false si el costo es cero o negativo"],
          ["instante_calculo", "ts", ""],
        ],
      },
      {
        nombre: "sugerencia_precio",
        proposito: "Propuesta de precio (margen + rol + competencia). Append-only; la persona decide.",
        cols: [
          ["id_sugerencia_precio", "bigint", "PK"],
          ["id_producto", "int", "FK→producto"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["precio_sugerido", "num(12,4)", ""],
          ["margen_usado", "num(6,4)", "· snapshot del instante de generación"],
          ["rol_usado", "text", "· snapshot; CHECK ∈ {gancho_trafico, generador_margen}"],
          ["id_observacion_precio_usada", "int", "· FK→observacion_precio"],
          ["instante_generacion", "ts", ""],
          ["aplicada", "bool", ""],
          ["instante_aplicacion", "ts", "·"],
        ],
      },
      {
        nombre: "sugerencia_colocacion",
        proposito: "Propuesta de zona de exhibición. Usa una zona ya catalogada por 001; no crea zonas.",
        cols: [
          ["id_sugerencia_colocacion", "bigint", "PK"],
          ["id_producto", "int", "FK→producto"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_zona_exhibicion", "int", "FK→zona_exhibicion"],
          ["margen_usado · rol_usado", "num(6,4) / text", "· snapshots"],
          ["instante_generacion", "ts", ""],
          ["aplicada", "bool", ""],
          ["instante_aplicacion", "ts", "·"],
        ],
      },
    ],
  },
  {
    modulo: "004 · Pronóstico de demanda — 4 tablas",
    intro: (
      <>
        La serie observada se <F>corrige</F> por quiebre de stock, precio, promoción y
        sustitutos, en orden fijo; el pronóstico se deriva siempre de la serie corregida, nunca
        de las ventas en bruto, y se compara contra una línea base determinista.
      </>
    ),
    tablas: [
      {
        nombre: "demanda_observada",
        proposito: "Serie de demanda tal como se registró, por producto/sucursal/día local. Hechos.",
        cols: [
          ["id_producto", "int", "PK · FK→producto"],
          ["id_sucursal", "int", "PK · FK→sucursal"],
          ["periodo", "date", "PK (día local)"],
          ["cantidad", "num(14,0)", ""],
          ["dias_en_quiebre", "num(4,3)", "fracción del período sin stock"],
          ["precio_vigente_periodo", "num(12,4)", "·"],
          ["con_promocion", "bool", ""],
          ["es_sintetico", "bool", "fila de escenario, no dato real"],
          ["demanda_latente_verdadera", "num(14,4)", "· sólo en filas sintéticas de quiebre"],
          ["consultas_no_atendidas_sinteticas", "int", "·"],
          ["instante_materializacion", "ts", ""],
        ],
      },
      {
        nombre: "demanda_corregida",
        proposito: "Serie corregida (descensura). `valor_observado` es snapshot de partida, no FK.",
        cols: [
          ["id_producto · id_sucursal · periodo", "int / date", "PK compuesta"],
          ["valor_observado", "num(14,0)", "snapshot"],
          ["valor", "num(14,4)", "demanda estimada tras corregir"],
          ["correccion_quiebre", "num(14,4)", ""],
          ["respaldo_quiebre", "text", "CHECK ∈ {no_aplica, metodo_base, consulta_no_atendida}"],
          ["ajuste_cruzado_sustituto · correccion_precio", "num(14,4)", ""],
          ["elasticidad_usada", "num(4,3)", "·"],
          ["excluido_por_promocion · censura_total · es_sintetico", "bool", ""],
          ["instante_materializacion", "ts", ""],
        ],
      },
      {
        nombre: "pronostico",
        proposito: "Cada generación es una fila nueva con sus factores y su línea base. Append-only.",
        cols: [
          ["id_pronostico", "bigint", "PK"],
          ["id_producto · id_sucursal", "int", "FK"],
          ["horizonte", "text", "CHECK ∈ {corto, medio}"],
          ["dias_horizonte", "smallint", ""],
          ["serie_pronosticada", "jsonb", "valores por período"],
          ["nivel_suavizado · alfa_usado", "num", "parámetros del suavizado exponencial"],
          ["multiplicadores_tramo", "jsonb", "·"],
          ["periodo_datos_desde · periodo_datos_hasta", "date", "ventana de datos usada"],
          ["valor_linea_base", "num(14,4)", "referencia determinista"],
          ["error_retrospectivo · error_linea_base", "num(14,4)", "·"],
          ["vigente", "bool", "false = sin histórico suficiente"],
          ["motivo_no_vigente", "text", "·"],
          ["es_sintetico", "bool", ""],
          ["instante_generacion", "ts", ""],
        ],
      },
      {
        nombre: "sustitucion_producto",
        proposito: "Relación de sustitución declarada A MANO. Dirigida. No se infiere de correlación.",
        cols: [
          ["id_sustitucion_producto", "bigint", "PK"],
          ["id_producto", "int", "FK→producto (el que queda en quiebre)"],
          ["id_producto_sustituto", "int", "FK→producto (CHECK: distinto)"],
          ["instante_declaracion", "ts", "U (producto, sustituto)"],
        ],
      },
    ],
  },
  {
    modulo: "005 · Promociones inteligentes — 6 tablas",
    intro: (
      <>
        Tres mecanismos <F>separados</F> (Lectura Crítica n.º 6): cupón por fecha fija, oferta de
        recompra con reserva de precio, y experimento de reactivación con grupo de control
        obligatorio. Una sola tabla y un solo endpoint de redención para los tres.
      </>
    ),
    tablas: [
      {
        nombre: "campania",
        proposito: "Paraguas de una corrida de UN solo mecanismo. id_sucursal null = toda la cadena.",
        cols: [
          ["id_campania", "int", "PK"],
          ["tipo", "text", "CHECK ∈ {fecha_fija, recompra, reactivacion}"],
          ["id_sucursal", "int", "· FK→sucursal"],
          ["nombre", "text", ""],
          ["ventana_desde · ventana_hasta", "date", "CHECK: hasta ≥ desde"],
          ["instante_creacion", "ts", ""],
        ],
      },
      {
        nombre: "cupon",
        proposito: "Mecanismo 1: cumpleaños. Regla directa, sin inferencia ni medición.",
        cols: [
          ["id_cupon", "bigint", "PK"],
          ["id_campania", "int", "FK→campania"],
          ["id_cliente", "int", "FK→cliente"],
          ["motivo", "text", "CHECK = fecha_fija_cumpleanos"],
          ["fecha_objetivo", "date", "U (id_cliente, fecha_objetivo)"],
          ["valido_desde · valido_hasta", "date", ""],
          ["porcentaje_descuento", "num(5,2)", ""],
          ["estado", "text", "CHECK ∈ {generado, redimido, vencido}"],
          ["instante_generacion", "ts", ""],
        ],
      },
      {
        nombre: "oferta_recompra",
        proposito: "Mecanismo 2: empuje por patrón de recompra con reserva de precio (no aparta stock).",
        cols: [
          ["id_oferta_recompra", "bigint", "PK"],
          ["id_campania · id_cliente · id_producto · id_sucursal", "int", "FK"],
          ["intervalo_esperado_dias_disparo", "num(8,2)", ""],
          ["justificacion", "jsonb", "qué compras del cliente la sustentan"],
          ["precio_garantizado", "num(12,4)", "lo único que la reserva garantiza"],
          ["reserva_desde · reserva_hasta", "date", ""],
          ["estado_reserva", "text", "CHECK ∈ {vigente, vencida}"],
          ["desenlace", "text", "CHECK ∈ {pendiente, comprado, no_comprado, reserva_vencida}"],
          ["instante_generacion", "ts", ""],
        ],
      },
      {
        nombre: "experimento_reactivacion",
        proposito: "Mecanismo 3: la corrida experimental. Guarda parametrización y resultado (z, p).",
        cols: [
          ["id_experimento_reactivacion", "bigint", "PK"],
          ["id_campania", "int", "FK→campania"],
          ["id_sucursal", "int", "· FK→sucursal"],
          ["semilla · algoritmo", "bigint / text", "reproducibilidad"],
          ["proporcion_tratamiento", "num(4,3)", ""],
          ["ventana_medicion_dias", "smallint", ""],
          ["porcentaje_descuento", "num(5,2)", ""],
          ["tasa_retorno_base_esperada · mde_puntos_porcentuales · alfa · poder", "num", "diseño estadístico"],
          ["tamano_minimo_muestra · n_elegibles · n_tratamiento · n_control", "int", "· tamaños"],
          ["retorno_tratamiento · retorno_control · incrementalidad", "num(6,4)", "· resultado"],
          ["estadistico_z · valor_p", "num", "· prueba z de dos proporciones"],
          ["veredicto", "text", "CHECK ∈ {en_curso, efectivo, no_efectivo, muestra_insuficiente}"],
          ["instante_asignacion · instante_cierre", "ts", "·"],
        ],
      },
      {
        nombre: "asignacion_experimento",
        proposito: "Una fila por cliente inactivo elegible, con su grupo. El grupo de control es obligatorio.",
        cols: [
          ["id_asignacion_experimento", "bigint", "PK"],
          ["id_experimento_reactivacion", "int", "FK"],
          ["id_cliente", "int", "FK→cliente"],
          ["id_senal_fuga", "bigint", "la senal_fuga de 002 que lo hizo elegible (auditoría)"],
          ["grupo", "text", "CHECK ∈ {tratamiento, control} — sin tercer valor"],
          ["retorno", "bool", "se fija al cerrar mirando `visita` de 002"],
          ["id_venta_retorno", "bigint", "·"],
          ["instante_retorno", "ts", "·"],
          ["—", "—", "U (experimento, cliente)"],
        ],
      },
      {
        nombre: "redencion_promocion",
        proposito: "El hecho de que un cupón / oferta / asignación se usó en una venta. Inmutable.",
        cols: [
          ["id_redencion_promocion", "bigint", "PK"],
          ["tipo_origen", "text", "CHECK ∈ {cupon, oferta_recompra, reactivacion}"],
          ["id_cupon · id_oferta_recompra · id_asignacion_experimento", "int", "· FK; exactamente uno (CHECK)"],
          ["id_venta", "int", "FK→venta (001, sólo lectura)"],
          ["id_producto", "int", "·"],
          ["id_sucursal · periodo", "int / date", "denormalizados de venta→turno→sucursal"],
          ["descuento_aplicado", "num(12,4)", "·"],
          ["instante_redencion", "ts", ""],
        ],
      },
    ],
  },
  {
    modulo: "006 · Caja, mermas y fraude — 3 tablas",
    intro: (
      <>
        Tres fenómenos con lógica distinta, no un cajón genérico de «descuadre». El{" "}
        <F>arqueo</F> por sí solo nunca es señal del fraude de sub-registro (Lectura Crítica
        n.º 1); ese fraude se persigue cruzando inventario contra ventas por operador —cálculo
        derivado sobre 001, no tabla—.
      </>
    ),
    tablas: [
      {
        nombre: "arqueo",
        proposito: "Cuadre de efectivo al cierre de un turno. `monto_esperado` se congela al cerrar.",
        cols: [
          ["id_arqueo", "bigint", "PK"],
          ["id_turno", "int", "U · FK→turno"],
          ["id_operador · id_sucursal", "int", "denormalizados del turno (inmutables)"],
          ["dia_local", "date", ""],
          ["monto_esperado", "num(12,2)", "Σ ventas del turno, congelado"],
          ["monto_contado · diferencia", "num(12,2)", ""],
          ["motivo_conocido", "text", "· si se explica, no genera anomalía"],
          ["ajustes", "jsonb", "retiros/ingresos declarados"],
          ["instante_cierre_arqueo · marca_tiempo_origen", "ts", ""],
          ["moneda", "text(3)", "USD"],
        ],
      },
      {
        nombre: "merma",
        proposito: "Pérdida de producto SIN venta, clasificada por causa. Nunca se atribuye a un operador.",
        cols: [
          ["id_merma", "bigint", "PK"],
          ["id_conteo_renglon", "int", "· FK→conteo_renglon (001); null = fuera de conteo"],
          ["id_producto", "int", "FK→producto"],
          ["id_lote", "int", "· FK→lote"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["cantidad_faltante", "num(14,0)", "CHECK > 0"],
          ["causa", "text", "CHECK ∈ {vencimiento, dano, robo_externo, error_conteo, merma_granel, pendiente_clasificar}"],
          ["valoracion", "num(12,2)", "· cantidad × costo FEFO; null = no calculable, nunca 0"],
          ["periodo_desde · periodo_hasta", "date", "entre conteos"],
          ["estado", "text", "CHECK ∈ {pendiente_clasificar, clasificada}"],
          ["conciliar_con_conteo", "bool", ""],
          ["id_operador_registro", "int", "FK→operador (quién registró, no a quién se imputa)"],
          ["instante_registro", "ts", ""],
          ["nota", "text", "·"],
        ],
      },
      {
        nombre: "anomalia_caja",
        proposito: "Una diferencia (de efectivo o de inventario) que ninguna causa conocida explica.",
        cols: [
          ["id_anomalia_caja", "bigint", "PK"],
          ["origen", "text", "CHECK ∈ {efectivo, inventario}"],
          ["estado", "text", "CHECK ∈ {sin_explicacion, resuelta} — sólo una persona resuelve"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_arqueo · id_turno · id_operador · id_producto · id_conteo_fisico", "int", "· FK según origen"],
          ["monto · magnitud · valor_estimado", "num", "·"],
          ["periodo_desde · periodo_hasta · dia_local", "date", ""],
          ["indicador_snapshot", "jsonb", "· congela los indicadores por operador"],
          ["historial", "jsonb", "cada cambio de estado"],
          ["resolucion", "text", "· texto libre"],
          ["id_operador_resolucion · instante_resolucion", "int / ts", "· coherentes con estado (CHECK)"],
          ["instante_deteccion", "ts", ""],
          ["moneda", "text(3)", "USD"],
        ],
      },
    ],
  },
  {
    modulo: "007 · Pagos y seguridad — 5 tablas",
    intro: (
      <>
        007 <F>sólo lee</F> de 001. Nunca se almacena el PAN, el CVV ni la banda: sólo token,
        últimos cuatro dígitos y marca. La bitácora es de <F>sólo anexado</F>, con un trigger
        que rechaza UPDATE y DELETE a nivel de motor.
      </>
    ),
    tablas: [
      {
        nombre: "medio_pago",
        proposito: "Catálogo global de formas de pago. Extensible sin migración.",
        cols: [
          ["id_medio_pago", "int", "PK"],
          ["nombre", "text", "U"],
          ["requiere_terminal", "bool", ""],
          ["admite_tokenizacion", "bool", ""],
          ["activo", "bool", ""],
        ],
      },
      {
        nombre: "terminal_pago",
        proposito: "Datáfono físico. «Desactualizada» / «expuesta» son cálculo derivado, no columnas.",
        cols: [
          ["id_terminal_pago", "int", "PK"],
          ["identificador", "text", "U"],
          ["modelo", "text", ""],
          ["id_sucursal", "int", "FK→sucursal"],
          ["version_firmware", "text", "CHECK: formato x.y.z"],
          ["fecha_ultima_actualizacion_firmware", "date", "·"],
          ["historial_ubicacion · historial_firmware", "jsonb", ""],
          ["id_operador_registro", "int", "FK→operador"],
          ["instante_registro", "ts", ""],
          ["activa", "bool", "el sistema NUNCA la desactiva por una señal de firmware"],
        ],
      },
      {
        nombre: "cobertura_pago",
        proposito: "Qué medio acepta qué sucursal, con vigencia por tramos sin solape.",
        cols: [
          ["id_cobertura_pago", "int", "PK"],
          ["id_medio_pago", "int", "FK→medio_pago"],
          ["id_sucursal", "int", "FK→sucursal"],
          ["fecha_desde", "date", ""],
          ["fecha_hasta", "date", "· null = vigente; CHECK: hasta ≥ desde"],
          ["id_operador", "int", "FK→operador"],
          ["instante_registro", "ts", ""],
        ],
      },
      {
        nombre: "bitacora_auditoria",
        proposito: "Rastro de sólo anexado de los hechos de pago. Trigger rechaza UPDATE/DELETE.",
        cols: [
          ["id_bitacora_auditoria", "bigint", "PK"],
          ["tipo_evento", "text", "CHECK: 14 valores (token_emitido, firmware_actualizado, intencion_no_atendida…)"],
          ["instante · dia_local", "ts / date", ""],
          ["id_sucursal", "int", "FK→sucursal"],
          ["id_terminal_pago · id_medio_pago", "int", "·"],
          ["iniciador_tipo", "text", "CHECK ∈ {operador, proceso}"],
          ["id_operador", "int", "·"],
          ["proceso", "text", "·"],
          ["resultado", "text", "redactado desde plantilla, nunca texto libre del cliente"],
          ["referencia_recurso_tipo · referencia_recurso_id", "text", "· CHECK sobre el tipo"],
          ["clave_idempotencia", "text", "·"],
        ],
      },
      {
        nombre: "token_pago",
        proposito: "Registro autoritativo de un cobro con tarjeta tokenizado. SIN PAN/CVV/banda.",
        cols: [
          ["id_token_pago", "bigint", "PK"],
          ["token", "text", "U — identificador sustituto opaco"],
          ["id_venta", "int", "U · FK→venta (001, sólo lectura)"],
          ["clave_idempotencia", "text", "U"],
          ["ultimos_digitos", "char(4)", "CHECK: exactamente 4 dígitos"],
          ["marca", "text", "CHECK ∈ {visa, mastercard, amex, diners, otra}"],
          ["tipo", "text", "CHECK ∈ {debito, credito, desconocido}"],
          ["id_terminal_pago · id_sucursal", "int", "FK"],
          ["instante · dia_local · marca_tiempo_origen", "ts / date", ""],
        ],
      },
    ],
  },
  {
    modulo: "008 · Reportes e inteligencia — 3 tablas (derivadas y regenerables)",
    intro: (
      <>
        Ninguna es fuente de verdad: borrarlas y reejecutar los cálculos de 008 sobre 001–006
        reproduce el mismo estado. <F>Nada de 008 alimenta de vuelta</F> a los otros módulos.
      </>
    ),
    tablas: [
      {
        nombre: "agregado_reporte",
        proposito: "Caché del resultado ya calculado de una vista (comparativo / tendencia / tablero).",
        cols: [
          ["id_agregado_reporte", "bigint", "PK"],
          ["tipo", "text", "CHECK ∈ {comparativo, tendencia, tablero}"],
          ["ambito_sucursal", "int", "· FK→sucursal"],
          ["periodo_inicio · periodo_fin", "date", ""],
          ["granularidad", "text", "CHECK ∈ {total, semana, mes}"],
          ["contenido", "jsonb", "el resultado, listo para pintar"],
          ["instante_calculo", "ts", "U (tipo, ámbito, período, granularidad)"],
        ],
      },
      {
        nombre: "segmento_cliente",
        proposito: "Un grupo del ÚLTIMO recálculo de k-means. Se reemplaza entero en cada corrida.",
        cols: [
          ["id_segmento_cliente", "bigint", "PK"],
          ["corrida", "ts", "marca de tiempo del cálculo"],
          ["etiqueta_grupo", "text", ""],
          ["centroide_frecuencia · centroide_margen · centroide_recencia_dias", "num", "posición del grupo"],
          ["n_clientes", "int", ""],
          ["descripcion", "text", "nombre legible derivado del centroide"],
          ["semilla", "bigint", "resultado determinista"],
          ["—", "—", "U (corrida, etiqueta_grupo)"],
        ],
      },
      {
        nombre: "asignacion_segmento",
        proposito: "Cliente ↔ grupo del último recálculo. Una fila por cliente.",
        cols: [
          ["id_cliente", "int", "PK · FK→cliente (ON DELETE CASCADE)"],
          ["corrida · etiqueta_grupo", "ts / text", "FK→segmento_cliente"],
          ["distancia_al_centroide", "num(10,4)", "·"],
        ],
      },
    ],
  },
  {
    modulo: "009 · Facturación electrónica (simulada) — 1 tabla",
    intro: (
      <>
        Derivada de una <C>venta</C> ya confirmada de 001. Todo el contenido es un{" "}
        <F>snapshot</F>: una factura emitida no cambia aunque cambie la venta o el cliente. Sin
        SRI, sin firma, sin XML regulatorio.
      </>
    ),
    tablas: [
      {
        nombre: "factura_simulada",
        proposito: "Documento con la forma de una factura ecuatoriana. Idempotente por venta.",
        cols: [
          ["id_factura_simulada", "bigint", "PK"],
          ["id_venta", "int", "FK→venta (001, sólo lectura)"],
          ["tipo", "text", "CHECK ∈ {factura, nota_credito}"],
          ["id_factura_referida", "int", "· FK→factura_simulada (para la nota de crédito)"],
          ["establecimiento · punto_emision · numero · secuencial", "text / int", "U (estab., punto, tipo, número)"],
          ["fecha_emision", "date", ""],
          ["emisor · comprador · renglones", "jsonb", "snapshots congelados"],
          ["subtotal · tarifa_iva · monto_iva · total", "num", ""],
          ["medio_pago", "text", "·"],
          ["estado", "text", "CHECK ∈ {emitida, anulada}"],
          ["instante_generacion", "ts", ""],
        ],
      },
    ],
  },
];

function TablaBD({ nombre, proposito, cols }: TablaBDDef) {
  return (
    <div className={estilos.bloqueTabla}>
      <p className={estilos.nombreTabla}>
        <C>{nombre}</C> — {proposito}
      </p>
      <Tabla
        cabeceras={["Columna", "Tipo", "Clave / restricción / nota"]}
        filas={cols.map((c) => [<C>{c[0]}</C>, c[1], c[2]])}
      />
    </div>
  );
}

export function Documentacion({ onVolver }: Props) {
  const [activa, setActiva] = useState<string>(SECCIONES[0].id);
  const contenidoRef = useRef<HTMLDivElement>(null);
  const ids = useMemo(() => SECCIONES.map((s) => s.id), []);

  // El salto nativo de un `<a href="#id">` hace `scrollIntoView` sobre TODA la cadena de
  // ancestros con scroll — incluida `html`/`body`, no sólo `.contenido` — y como `.barra` es un
  // hijo de flujo normal de `.pantalla` (no `position: sticky`/`fixed`), si el documento llega a
  // desplazarse aunque sea unos píxeles la barra superior se corre fuera de vista y `.pantalla`
  // (con `overflow: hidden`) la recorta: el "bug" del encabezado que desaparece al usar el
  // índice lateral. Se intercepta el clic y se hace el scroll a mano, sólo dentro de
  // `.contenido`, sin dejar que el navegador toque el scroll del documento.
  function irASeccion(evento: MouseEvent<HTMLAnchorElement>, id: string) {
    evento.preventDefault();
    const raiz = contenidoRef.current;
    const destino = raiz?.querySelector<HTMLElement>(`#${id}`);
    if (!raiz || !destino) return;
    raiz.scrollTo({ top: destino.offsetTop, behavior: "smooth" });
    setActiva(id);
    history.replaceState(null, "", `#${id}`);
  }

  useEffect(() => {
    const raiz = contenidoRef.current;
    if (!raiz) return;
    const observador = new IntersectionObserver(
      (entradas) => {
        const visible = entradas
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActiva(visible.target.id);
      },
      { root: raiz, rootMargin: "0px 0px -70% 0px", threshold: 0 },
    );
    ids.forEach((id) => {
      const el = raiz.querySelector(`#${id}`);
      if (el) observador.observe(el);
    });
    return () => observador.disconnect();
  }, [ids]);

  return (
    <div className={estilos.pantalla}>
      <img className={estilos.marca} src={marcaMono} alt="" aria-hidden="true" />

      <div className={estilos.barra}>
        <img className={estilos.marcaSistema} src={marcaSistema} alt="Rasero" width={88} height={22} />
        <h1 className={estilos.tituloBarra}>Documentación del sistema</h1>
        <span className={estilos.accionBarra}>
          <Boton variante="neutra" registro="analisis" onClick={onVolver}>
            Volver a la apertura de turno
          </Boton>
        </span>
      </div>

      <div className={estilos.marco}>
        <nav className={estilos.indice} aria-label="Índice de la documentación">
          <p className={estilos.indiceTitulo}>Contenido</p>
          <ul className={estilos.indiceLista}>
            {SECCIONES.map((s) => (
              <li key={s.id}>
                <a
                  className={`${estilos.indiceEnlace} ${activa === s.id ? estilos.indiceActivo : ""}`}
                  href={`#${s.id}`}
                  onClick={(e) => irASeccion(e, s.id)}
                >
                  {s.titulo}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={estilos.contenido} ref={contenidoRef}>
          {/* ─── 1 · Objetivo ─────────────────────────────────────────────────────────────── */}
          <section id="objetivo" className={estilos.seccion}>
            <h2 className={estilos.h2}>1 · Objetivo del sistema</h2>
            <P>
              <F>Rasero</F> es una plataforma de <F>comercio minorista inteligente</F> para una
              tienda de barrio (minimarket) con varias sucursales: punto de venta, inventario,
              márgenes, previsión de demanda, fidelización de clientes, control de caja y detección
              de fraude, pagos y seguridad, reportes y facturación simulada.
            </P>
            <P>
              Un <F>rasero</F> es la tablilla que se pasa sobre una medida de grano para nivelarla
              al ras; de ahí la expresión «medir a todos con el mismo rasero». Esa es la tesis del
              producto: hoy el dueño juzga sus productos y sus clientes <F>por impresión</F>
              («esto se vende mucho», «este cliente gasta bastante», «creo que hay merma»). Rasero
              aplica <F>un mismo criterio objetivo y explícito</F> a todo:
            </P>
            <ul className={estilos.lista}>
              <li>
                el valor de un producto es su <F>margen real</F>, no su volumen de ventas;
              </li>
              <li>
                el valor de un cliente combina <F>frecuencia, monto y margen</F> de lo que compra,
                no su gasto total;
              </li>
              <li>
                la demanda real son las ventas <F>corregidas</F> por quiebres de stock, precio y
                promociones, no las ventas en bruto.
              </li>
            </ul>
            <P>
              Regla transversal (Principio V de la constitución del proyecto):{" "}
              <F>toda salida «inteligente» debe poder explicarse</F> en esos términos, en la propia
              pantalla, y ser reversible. La inteligencia <F>propone</F>; la persona <F>decide</F>.
            </P>
            <H3>Qué NO es</H3>
            <ul className={estilos.lista}>
              <li>
                <F>No es un procesador de pagos.</F> No hay pasarela real; no mueve dinero de
                bancos ni hace autorización con un adquirente.
              </li>
              <li>
                <F>No factura ante el SRI.</F> El documento del módulo 009 es una{" "}
                <F>factura simulada</F>: tiene la forma legal ecuatoriana pero sin firma
                electrónica ni XML válido.
              </li>
              <li>
                <F>No decide solo.</F> Ninguna acción sobre precio o inventario se ejecuta sin
                aprobación humana registrada.
              </li>
            </ul>
            <P>
              <F>Criterio de éxito del núcleo:</F> la caja nunca se detiene por una validación, y el
              inventario total siempre se puede reconstruir a partir de su historial de movimientos.
            </P>
          </section>

          {/* ─── 2 · Empresa ──────────────────────────────────────────────────────────────── */}
          <section id="empresa" className={estilos.seccion}>
            <h2 className={estilos.h2}>2 · La empresa de demostración</h2>
            <P>
              El proyecto separa con rigor dos cosas que no deben mezclarse nunca en el código:
            </P>
            <Tabla
              cabeceras={["", "Nombre", "Qué es"]}
              filas={[
                [
                  <F>La herramienta</F>,
                  <F>Rasero</F>,
                  "Software genérico, vendible a cualquier comercio. Su nombre y su marca visual son lo único que aparece en la interfaz del sistema.",
                ],
                [
                  <F>El negocio de ejemplo</F>,
                  <F>Despensa Los Ríos</F>,
                  <>
                    Minimarket ficticio con <F>dos sucursales</F>: <F>Quevedo Centro</F> y{" "}
                    <F>Buena Fe</F>. Existe solo como datos de demostración (semillas). Su nombre
                    tiene prohibido aparecer en tablas, endpoints, componentes o cualquier
                    identificador técnico.
                  </>,
                ],
              ]}
            />
            <P>
              <F>Perfil del negocio:</F> tienda de barrio con sección de <F>frescos vendidos a peso</F>{" "}
              (queso, embutidos), lácteos y perecederos; conectividad de internet inestable en caja;
              márgenes ajustados donde cada merma y cada venta perdida duelen. El modelo admite{" "}
              <F>N sucursales</F> sin cambios estructurales; dos es solo el alcance de esta entrega.
            </P>
            <div className={estilos.nota}>
              <F>Restricciones no negociables:</F> moneda única (USD); ninguna validación de
              existencias bloquea un cobro; el mismo producto puede tener precio distinto por
              sucursal; los mensajes de error indican la acción correctiva, nunca una traza técnica.
            </div>
          </section>

          {/* ─── 3 · Origen ───────────────────────────────────────────────────────────────── */}
          <section id="origen" className={estilos.seccion}>
            <h2 className={estilos.h2}>3 · Del enunciado ambiguo al sistema</h2>
            <P>
              Todo parte de un <F>texto deliberadamente ofuscado</F> entregado por el docente: los
              nombres reales están sustituidos por palabras sin sentido (quesos, personajes, marcas
              inventadas — «requesón», «ki-requesón», «Guernica», «Halloumi», «plutarco»…). No
              codifican nada: son ruido intencional para obligar a <F>interpretar el problema</F> en
              lugar de copiar un requisito. Cada párrafo, bajo el disfraz, describe un dolor clásico
              del comercio de barrio.
            </P>
            <div className={estilos.cita}>
              «…compara precios en las tiendas, en el supermercado, en el chino y en tiendas
              digitales en 15 segundos. Si tienes un precio ligeramente mayor, pierdes la venta. Ese
              cliente no vuelve. […] Si no acepta medio de pago electrónico directamente no entra,
              ha perdido a toda una generación de consumidores. […] Sabe que cuajada se hace siempre
              de cerveza sin alcohol y le manda un descuento al móvil para que vaya a recogerla.
              […] Sin cuadre de caja cada hora, es imposible detectarlo.»
            </div>
            <P>El análisis del equipo tradujo ese texto a fenómenos concretos:</P>
            <Tabla
              cabeceras={["Fragmento del enunciado (disfrazado)", "Dolor real", "Módulo"]}
              filas={[
                ["«compara precios en 15 segundos… pierdes la venta»", "El cliente compara precios con el móvil; hay que conocer el precio propio frente a la competencia.", "003 + 001"],
                ["«cobrar lento es perder dinero»", "La caja no se puede detener: ninguna validación es camino crítico de un cobro.", "001 (Principio II)"],
                ["«si no acepta pago electrónico… ha perdido a una generación»", "Venta perdida antes de que exista la transacción: el cliente que no entra.", "007 (cobertura de medios)"],
                ["«producto X 40% de margen, producto Y 10%»", "El precio depende del rol comercial del producto (gancho de tráfico vs. generador de margen) y del margen real.", "003"],
                ["«el de mayor margen a zona privilegiada»", "La colocación física en góndola es parte de la decisión de precio.", "003"],
                ["«le manda un descuento al móvil para que recoja la cuajada»", "Promoción por patrón de recompra detectado.", "005"],
                ["«las bolsas de patatas y los lácteos se vencen en tu estantería»", "Mermas por caducidad no controlada (hasta el 20% de la ganancia anual).", "006 + 001"],
                ["«Guernica no tiene café molido y no se entera hasta que 5 clientes se van»", "Demanda perdida por quiebre de stock, invisible en las ventas; registrar consultas no atendidas.", "001 + 004"],
                ["«no sabe quién compra qué, ni cuándo, ni con qué frecuencia»", "No hay base de datos de clientes con historial.", "002"],
                ["«el día de su cumpleaños le envía un cupón»", "Cupón de cumpleaños (promoción por fecha fija).", "005"],
                ["«cuando un cliente fiel se va, no te das ni cuenta»", "Fuga silenciosa; detectarla por cliente, no con un umbral global.", "002"],
                ["«la demanda no depende solo de cuánto se vendió antes…»", "La demanda histórica está contaminada por promociones, precio, sustitutos y quiebres; hay que corregirla.", "004"],
                ["«el valor del cliente no es solo cuánto gastó»", "Valor de cliente multidimensional (frecuencia + monto + margen).", "002"],
                ["«compró 50 pechugas ‘baratas’ y nadie las compra»", "Capital inmovilizado en inventario que no rota.", "001"],
                ["«sin un inventario digital que cuadre cada día, ¿cómo sabes?»", "Conteo físico periódico que cuadre el inventario.", "001"],
                ["«cobra 5 €, registra 3 € en la caja»", "Fraude por sub-registro. El arqueo NO lo detecta: el efectivo cuadra. Se cruza salida de inventario contra venta registrada, por operador.", "006"],
                ["«un datáfono viejo sin actualizar → clonan las tarjetas»", "Firmware del datáfono desactualizado y exposición a clonación (skimming).", "007"],
                ["«un cliente que deja de comprar 30 días puede estar en su intervalo normal»", "El umbral de inactividad no puede ser global: se deriva por cliente.", "002"],
                ["«darle un descuento… podría reducir el valor que se intenta proteger si iba a volver igual»", "La reactivación necesita grupo de control: medir el efecto incremental real.", "005"],
              ]}
            />
            <P>
              Seis de estas lecturas se fijaron como <F>«Lecturas Críticas del Enunciado»</F> en la
              constitución: decisiones de interpretación que cualquier especificación posterior debe
              respetar (p. ej. «el arqueo no detecta ese fraude», «las promociones son tres
              mecanismos distintos, no uno»).
            </P>
          </section>

          {/* ─── 4 · Segmentación ─────────────────────────────────────────────────────────── */}
          <section id="segmentacion" className={estilos.seccion}>
            <h2 className={estilos.h2}>4 · Segmentación de la empresa</h2>
            <P>
              El sistema está organizado según los <F>tres niveles de decisión</F> de una empresa.
              Cada nivel trabaja a una escala de tiempo distinta y lo usa un rol distinto.
            </P>

            <H3>Nivel operativo — «el turno y el día»</H3>
            <P>
              Registrar los hechos económicos tal como ocurren en el mostrador. Lo ejecuta el{" "}
              <span className={estilos.pildora}>cajero</span>. Escala: minutos y horas.
            </P>
            <ul className={estilos.lista}>
              <li>
                <F>Venta en caja</F> — cobro de productos por unidad y a peso mezclados;
                idempotente ante reintentos de red.
              </li>
              <li>
                <F>Identificación opcional del cliente</F> y aplicación de cupones que el cliente
                presenta — nunca frena el cobro.
              </li>
              <li>
                <F>Consulta no atendida</F> — marcar en dos toques que un cliente pidió algo que no
                había.
              </li>
              <li>
                <F>Entradas de inventario</F> — recepción de mercadería del proveedor en lotes, con
                costo y caducidad.
              </li>
              <li>
                <F>Conteo físico</F> — contar el stock real y exponer el descuadre bruto, sin
                interpretarlo.
              </li>
              <li>
                <F>Arqueo de caja</F> — contar el efectivo al cierre del turno.
              </li>
              <li>
                <F>Factura simulada</F> — se emite después del cobro; nunca lo bloquea.
              </li>
            </ul>

            <H3>Nivel táctico — «la semana»</H3>
            <P>
              Ajustar la operación con datos ya calculados. Lo ejecuta el{" "}
              <span className={estilos.pildora}>encargado</span>. Escala: días y semanas.
            </P>
            <ul className={estilos.lista}>
              <li>
                <F>Precios y márgenes</F> — margen real por producto, rol comercial, sugerencia de
                precio y de zona de exhibición.
              </li>
              <li>
                <F>Competencia</F> — registrar observaciones de precio de la competencia, fechadas,
                con canal y frescura.
              </li>
              <li>
                <F>Pronóstico de demanda</F> — serie observada vs. corregida (por quiebre, precio,
                promoción, sustitutos) y pronóstico consultivo.
              </li>
              <li>
                <F>Clientes</F> — listado por valor real, desglose de sus tres dimensiones, señal
                de fuga por cliente, cumpleaños.
              </li>
              <li>
                <F>Promociones</F> — cupón de cumpleaños, oferta de recompra con reserva de precio,
                experimento de reactivación con grupo de control.
              </li>
              <li>
                <F>Traspasos</F> entre sucursales y <F>capital inmovilizado</F>.
              </li>
              <li>
                <F>Caja y fraude</F> — mermas por causa, anomalías de caja, indicadores por
                operador (anulaciones, ventas bajo precio de lista, discrepancia inventario-ventas).
              </li>
              <li>
                <F>Terminales de pago</F> (firmware, exposición a clonación) y{" "}
                <F>cobertura de medios de pago</F> por sucursal.
              </li>
            </ul>

            <H3>Nivel estratégico — «el mes»</H3>
            <P>
              La pregunta del dueño el domingo por la noche: <F>¿cómo va el negocio y en qué se
              distinguen mis dos tiendas?</F> Lo ejecuta el{" "}
              <span className={estilos.pildora}>encargado</span>. Escala: semanas y meses.
            </P>
            <ul className={estilos.lista}>
              <li>
                <F>Reportes e inteligencia (módulo 008)</F> — capa de solo lectura sobre 001–007:
              </li>
              <li>
                — <F>Comparativo entre sucursales</F> (Quevedo Centro vs. Buena Fe, mismo período,
                en ventas, margen y merma);
              </li>
              <li>
                — <F>Tendencias</F> de los indicadores agregados por semana o por mes;
              </li>
              <li>
                — <F>Tablero de KPIs</F> consolidados de cada módulo;
              </li>
              <li>
                — <F>Segmentos de clientes</F> por agrupamiento (clustering) según frecuencia,
                margen y recencia.
              </li>
            </ul>
            <div className={estilos.nota}>
              El nivel estratégico <F>no captura ningún dato nuevo</F> y <F>no alimenta de vuelta</F>{" "}
              a los otros módulos: solo cruza, agrega y presenta. Sus tres tablas son regenerables:
              borrarlas y recalcular reproduce el mismo estado.
            </div>
          </section>

          {/* ─── 5 · Actores ──────────────────────────────────────────────────────────────── */}
          <section id="actores" className={estilos.seccion}>
            <h2 className={estilos.h2}>5 · Actores del sistema</h2>
            <P>
              Tres roles en jerarquía <F>acumulativa</F>: cada nivel puede todo lo del anterior más
              lo suyo. La regla de interfaz es <F>«ocultar, no deshabilitar»</F>: lo que un rol no
              puede usar no aparece en el menú. El backend valida además por su cuenta.
            </P>
            <Tabla
              cabeceras={["Rol", "Quién es", "Qué añade"]}
              filas={[
                [
                  <span className={estilos.pildora}>cajero</span>,
                  "Cobra en caja durante la jornada. Atado a una sola sucursal (no la elige al abrir turno). Se identifica eligiéndose de una lista + PIN de 4 dígitos.",
                  "Nivel base: vender, identificar cliente, marcar consultas no atendidas, entradas de inventario, conteo físico, arqueo del propio turno. Crear/editar clientes (sin restricción de rol).",
                ],
                [
                  <span className={estilos.pildora}>encargado</span>,
                  "Responsable táctico y gerencial de una o varias sucursales.",
                  "Todo lo táctico y estratégico: precios, competencia, pronóstico, clientes (análisis), promociones, traspasos, capital, caja y fraude, terminales, cobertura de medios, reportes.",
                ],
                [
                  <span className={estilos.pildora}>admin</span>,
                  "Administración del sistema. No está atado a una sucursal; abre turno en cualquiera.",
                  "En exclusiva: gestión de operadores (alta, edición de rol y sucursal, desactivación) y alta/edición de datos maestros.",
                ],
              ]}
            />
            <H3>Cómo se sostiene la sesión</H3>
            <P>
              Al abrir turno y validar el PIN, el backend emite un <F>token JWT de sesión de
              turno</F> (firma HS256, expira a las 12 h, se invalida al cerrar turno o si se
              desactiva al operador). Viaja en cada petición y se guarda <F>solo en memoria</F>: al
              recargar la página se vuelve a la apertura de turno. Antes de esta decisión el sistema
              confiaba en un <C>id_operador</C> que el navegador enviaba sin verificar — una brecha
              que se corrigió.
            </P>
          </section>

          {/* ─── 6 · Módulos ──────────────────────────────────────────────────────────────── */}
          <section id="modulos" className={estilos.seccion}>
            <h2 className={estilos.h2}>6 · Módulos (001–009)</h2>
            <P>
              Nueve módulos, cada uno <F>dueño de sus propias entidades</F> de datos: los demás las
              consultan, nunca las redefinen ni alteran su esquema.
            </P>
            <Tabla
              cabeceras={["#", "Módulo", "Funcionalidades / casos de uso principales", "Entidades propias"]}
              filas={[
                [
                  "001",
                  <F>Core de ventas e inventario</F>,
                  "Venta mixta (unidad + peso), consumo de lote por caducidad (FEFO), precio efectivo por sucursal, venta idempotente, anulación atada al turno, entradas por compra, traspasos entre sucursales (dos asientos enlazados), consultas no atendidas, observaciones de precio de competencia, conteo físico, capital inmovilizado, cola de operaciones offline, roles y turnos.",
                  "sucursal, producto, lote, existencia, movimiento_inventario, traspaso, venta, renglon_venta, anulacion_venta, conteo_fisico, operador, turno… (20)",
                ],
                [
                  "002",
                  <F>Clientes y fidelización</F>,
                  "Catálogo de clientes con fecha de nacimiento e identificador (cédula/RUC), historial de visitas, valor de cliente (frecuencia + monto + margen), intervalo de compra esperado por cliente, señal de fuga silenciosa, curva de fuga por segmento.",
                  "cliente, visita, intervalo_compra, senal_fuga",
                ],
                [
                  "003",
                  <F>Precios y márgenes</F>,
                  "Margen real por producto, clasificación del rol comercial (gancho de tráfico / generador de margen), sugerencia de precio combinando margen + rol + competencia, sugerencia de colocación en zona de exhibición.",
                  "margen_calculado, rol_producto, sugerencia_precio, sugerencia_colocacion",
                ],
                [
                  "004",
                  <F>Pronóstico de demanda</F>,
                  "Serie de demanda observada; corrección (descensura) por quiebre de stock, por precio vigente de cada período y por promoción activa; declaración manual de sustitutos; pronóstico contra línea base determinista con veredicto explícito.",
                  "demanda_observada, demanda_corregida, pronostico, sustitucion_producto",
                ],
                [
                  "005",
                  <F>Promociones inteligentes</F>,
                  "Tres mecanismos separados: cupón por fecha fija (cumpleaños); oferta de recompra con reserva de precio; experimento de reactivación de inactivos con grupo de control e incrementalidad (prueba z). Registro de redenciones. Marca de «promoción activa» para el pronóstico.",
                  "campania, cupon, oferta_recompra, experimento_reactivacion, asignacion_experimento, redencion_promocion",
                ],
                [
                  "006",
                  <F>Caja, mermas y fraude</F>,
                  "Arqueo de caja por turno (detecta retiro de efectivo sin registrar venta); clasificación de la causa de una diferencia de conteo como merma; detección de sub-registro cruzando inventario contra ventas por operador; gestión de anomalías de caja sin explicación; mermas por causa en el tiempo.",
                  "arqueo, merma, anomalia_caja",
                ],
                [
                  "007",
                  <F>Pagos y seguridad</F>,
                  "Cobertura de medios de pago por sucursal e intención de compra no atendida; registro de terminales y vigilancia de firmware / exposición a clonación; tokenización de los datos de tarjeta (nunca el PAN ni el CVV); bitácora de auditoría de la actividad de pagos (solo anexado).",
                  "terminal_pago, medio_pago, cobertura_pago, bitacora_auditoria, token_pago",
                ],
                [
                  "008",
                  <F>Reportes e inteligencia</F>,
                  "Capa de solo lectura sobre 001–007: comparativo entre sucursales, tendencias por semana/mes, tablero de KPIs, segmentación de clientes por k-means (semilla fija, reversible).",
                  "agregado_reporte, segmento_cliente, asignacion_segmento (derivadas)",
                ],
                [
                  "009",
                  <F>Facturación electrónica (simulada)</F>,
                  "Genera, tras una venta ya confirmada, un documento con la forma de una factura electrónica ecuatoriana (RUC, razón social, secuencial establecimiento-punto-correlativo, subtotal, IVA, total, «Consumidor Final»). Ver, regenerar y anular. Nota de crédito.",
                  "factura_simulada",
                ],
              ]}
            />
            <div className={estilos.nota}>
              <F>Simulada</F> significa: sin conexión al SRI, sin firma electrónica y sin XML
              regulatorio. Es una limitación de alcance declarada con honestidad, no una integración
              fallida — el mismo criterio que 007 usa para «sin pasarela de pago real».
            </div>
          </section>

          {/* ─── 7 · Casos de uso ─────────────────────────────────────────────────────────── */}
          {/* ─── 7 · Decisiones de alcance ────────────────────────────────────────────────── */}
          <section id="alcance" className={estilos.seccion}>
            <h2 className={estilos.h2}>7 · Decisiones de alcance</h2>
            <P>
              El enunciado del docente no es una lista de requisitos: es un texto ofuscado que
              describe <F>dolores</F>. Traducir cada dolor a una funcionalidad obliga a decidir
              qué entra, qué se interpreta y qué queda fuera. Esta sección deja esas decisiones
              por escrito para que el trabajo sea <F>defendible</F>: nada del sistema está por
              capricho, y lo que excede el texto se declara con honestidad.
            </P>

            <H3>Qué ancla directo en el enunciado</H3>
            <P>
              Los módulos <F>001 a 007</F> mapean uno a uno con un dolor <F>nombrado</F> en el
              texto (ver la tabla de la sección 3). No hay decisión de alcance que justificar en
              ellos: si el enunciado habla de «cobrar lento es perder dinero», de «cobrar 5 y
              registrar 3», de «el datáfono viejo que clona tarjetas» o de «el cliente que se fue
              y no te diste cuenta», existe un módulo que lo resuelve.
            </P>
            <Tabla
              cabeceras={["Módulo", "Anclaje en el enunciado", "Alcance"]}
              filas={[
                ["001 Core ventas e inventario", "«cobrar lento es perder dinero», «50 pechugas que nadie compra», «inventario que cuadre cada día», «5 clientes se van sin café»", "Directo"],
                ["002 Clientes y fidelización", "«no sabes quién compra qué, ni cuándo, ni con qué frecuencia», «cuando un fiel se va no te enteras», «30 días puede ser su intervalo normal», «el valor no es solo cuánto gastó»", "Directo"],
                ["003 Precios y márgenes", "«producto X 40%, producto Y 10%», «el de más margen a zona privilegiada», «comparas precios en 15 segundos»", "Directo"],
                ["004 Pronóstico de demanda", "«la demanda no depende solo de cuánto se vendió antes» (promoción, precio, sustitutos, quiebre)", "Directo"],
                ["005 Promociones inteligentes", "«descuento al móvil para que recoja la cuajada», «cupón el día de su cumpleaños», «el descuento podría destruir el margen si iba a volver igual»", "Directo"],
                ["006 Caja, mermas y fraude", "«las mermas se comen el 20% de la ganancia», «cobra 5 registra 3, sin cuadre es imposible detectarlo»", "Directo"],
                ["007 Pagos y seguridad", "«si no acepta pago electrónico ha perdido a una generación», «datáfono viejo → clonan las tarjetas → la culpa recae en ti»", "Directo"],
              ]}
            />

            <H3>Qué es extensión razonada (y por qué se mantiene)</H3>
            <P>
              Dos módulos <F>no</F> tienen una frase del enunciado que los pida palabra por
              palabra. Se decidió <F>mantenerlos visibles</F>, documentando aquí la razón, en
              lugar de ocultarlos:
            </P>
            <Tabla
              cabeceras={["Módulo", "Qué parte ancla y qué parte es inferencia", "Decisión"]}
              filas={[
                [
                  <F>008 Reportes e inteligencia</F>,
                  <>
                    <F>Ancla:</F> la <F>segmentación de clientes</F> es lectura directa de «no
                    sabes quién compra qué» + «el valor del cliente no es solo cuánto gastó» —
                    responde a ambas con agrupamiento por parecido en vez de un umbral arbitrario.{" "}
                    <F>Inferencia:</F> el comparativo entre sucursales, las tendencias y el
                    tablero de KPIs no están pedidos literalmente; se derivan de que el enunciado
                    habla de varios «requesones» compitiendo y de un dueño que necesita ver cómo
                    va el negocio.
                  </>,
                  "Se mantiene. Es capa de SOLO LECTURA sobre 001–006: no captura ni decide nada, y sus tres tablas son regenerables. Riesgo nulo; retirarla no haría el sistema más fiel, solo más pobre.",
                ],
                [
                  <F>009 Facturación electrónica (simulada)</F>,
                  <>
                    <F>Ancla:</F> ninguna. El enunciado no menciona comprobantes, SRI, IVA ni
                    facturas en ningún párrafo. <F>Inferencia:</F> un comercio ecuatoriano que
                    cobra necesita entregar un comprobante; es el complemento natural del cobro de
                    001 y del flujo de pago de 007.
                  </>,
                  "Se mantiene como SIMULADA y declarada: sin conexión al SRI, sin firma, sin XML válido, con aviso visible de «comprobante de demostración». Es una limitación de alcance honesta —el mismo criterio que 007 usa para «sin pasarela de pago real»—, no una integración a medias.",
                ],
              ]}
            />
            <div className={estilos.nota}>
              <F>Cómo defender esto:</F> si en la sustentación se pregunta «¿dónde pide el
              enunciado una factura?», la respuesta es: <F>no la pide</F>. 009 es una extensión
              consciente, marcada como simulada en la propia interfaz y en la constitución
              (enmienda v2.7.0). El núcleo evaluable del sistema —001 a 007— sí responde, línea
              por línea, al texto entregado.
            </div>

            <H3>Medio de pago en el punto de venta</H3>
            <P>
              El enunciado trata el pago electrónico como <F>cobertura</F> («si no acepta pago
              electrónico… ha perdido a una generación» → Lectura Crítica n.º 4, módulo 007), no
              como dato por transacción. Aun así, la factura simulada mostraba un «medio de pago»
              que se <F>adivinaba</F> con una heurística de dos valores. La enmienda{" "}
              <F>v2.7.2</F> cierra ese hueco: la pantalla de Venta ofrece un selector de medio de
              pago (efectivo, tarjeta, transferencia…, alimentado por el catálogo de 007), y la
              venta guarda la <F>categoría</F> elegida en <C>venta.id_medio_pago</C> — nunca un
              dato del instrumento (el PAN y el CVV siguen fuera de todo el sistema). La factura
              usa ese medio real; si una venta no lo declara, cae a la heurística anterior.
            </P>

            <H3>Exportación a PDF de facturas y reportes</H3>
            <P>
              Tanto la <F>factura simulada</F> (009) como el <F>reporte activo</F> de la pantalla
              de Reportes (008) se exportan a PDF con <F>vista previa</F>: el botón «Ver como
              documento» / «Exportar PDF» abre el documento a pantalla completa y el diálogo de
              impresión del navegador —que ya trae su propia previsualización y la opción
              «Guardar como PDF»—. No hay generación de PDF en el servidor: el PDF contiene{" "}
              <F>sólo la información</F> (cabecera, tablas, cifras), sin el armazón de la
              aplicación. Es la vía de coste cero que la investigación de 009 ya había fijado.
            </P>

            <H3>Interpretaciones fijadas como «Lecturas Críticas»</H3>
            <P>
              Seis decisiones de interpretación se congelaron en la constitución del proyecto
              porque contradicen una lectura ingenua del enunciado y cualquier especificación
              posterior debe respetarlas:
            </P>
            <ul className={estilos.lista}>
              <li>
                <F>El arqueo NO detecta el fraude de «cobrar 5, registrar 3».</F> El efectivo
                cuadra; ese fraude se persigue por otras señales (inventario vs. ventas por
                operador, tasa de anulaciones).
              </li>
              <li>
                <F>El precio depende del rol del producto</F>, no de una regla única: bajar el
                precio de los ganchos y subir el de los nichos no contradice «decidir por margen».
              </li>
              <li>
                <F>La colocación física es parte de la decisión de precio</F>: 003 sugiere zona,
                no solo precio.
              </li>
              <li>
                <F>Hay venta perdida antes de que exista transacción</F>: el cliente que no entra
                porque no acepta su medio de pago es métrica de cobertura (007), no faltante de
                inventario.
              </li>
              <li>
                <F>El umbral de inactividad no puede ser global</F>: 30 días son abandono para uno
                y rutina para otro; el intervalo se deriva por cliente.
              </li>
              <li>
                <F>Las promociones son tres mecanismos distintos</F>, no uno: cupón de fecha fija,
                empuje por recompra y experimento de reactivación con grupo de control obligatorio.
              </li>
            </ul>
          </section>

          {/* ─── 8 · Casos de uso ─────────────────────────────────────────────────────────── */}
          <section id="casos-uso" className={estilos.seccion}>
            <h2 className={estilos.h2}>8 · Casos de uso</h2>

            <H3>CU-1 · Registrar una venta en caja</H3>
            <P>
              El cajero abre turno con su PIN. Arma el carrito mezclando unidades (una lata de atún)
              y peso (0,700 kg de queso leídos de báscula). Opcionalmente identifica al cliente y
              aplica un cupón que el cliente trae. Cobra. El sistema descuenta las existencias por
              lote según <F>FEFO</F>, deja constancia del operador y de la terminal, y{" "}
              <F>no duplica nada</F> si el cobro se reintenta. Si un servicio no crítico (pronóstico,
              analítica) está caído, la venta se completa igual. Después del cobro se genera la
              factura simulada, se registra la visita del cliente (002) y la redención de la
              promoción (005) — ninguno de esos pasos puede bloquear el cobro.
            </P>

            <H3>CU-2 · Recibir mercadería y cuadrar el inventario</H3>
            <P>
              El encargado registra una compra: producto, cantidad, costo y —si es perecedero—
              fecha de caducidad. Cada recepción crea o alimenta un lote. Periódicamente, el cajero
              hace un <F>conteo físico</F>: el sistema muestra el descuadre bruto contra el saldo
              calculado, sin interpretarlo. El módulo 006 clasifica después la causa de ese
              descuadre (merma por caducidad, daño, robo o error de registro).
            </P>

            <H3>CU-3 · Decidir un precio</H3>
            <P>
              El encargado abre <F>Precios</F>. Ve el margen real de un producto, lo clasifica como
              gancho de tráfico o generador de margen, y recibe una sugerencia de precio y de zona
              de exhibición que muestra <F>qué insumos usó</F> (margen, rol, última observación de
              competencia con su antigüedad). El encargado decide si la aplica; nada se ejecuta
              solo.
            </P>

            <H3>CU-4 · Recuperar un cliente inactivo sin regalar margen</H3>
            <P>
              El módulo 002 marca a un cliente como <F>en riesgo de fuga</F> porque su tiempo sin
              comprar superó varias veces <F>su</F> intervalo esperado. El módulo 005 crea un{" "}
              <F>experimento</F>: a un grupo se le envía el descuento y a un <F>grupo de control</F>{" "}
              no. Al cierre, el sistema compara el % de retorno de ambos grupos y reporta la{" "}
              <F>incrementalidad</F> con su prueba estadística — si no es significativa, el descuento
              no sirvió.
            </P>

            <H3>CU-5 · Detectar el fraude que el arqueo no ve</H3>
            <P>
              «Cobrar 5, registrar 3» no descuadra la caja. El módulo 006 lo persigue cruzando,{" "}
              <F>por operador y por turno</F>, la salida real de inventario contra las ventas
              registradas y la tasa de anulaciones. Lo que el sistema no puede explicar queda como
              una <F>anomalía</F> para revisión humana.
            </P>

            <H3>CU-6 · Cerrar el flanco de pagos</H3>
            <P>
              El encargado registra los datáfonos de cada sucursal y su versión de firmware; el
              sistema señala (con tres portadores: color, forma y texto) los que están
              desactualizados o expuestos a clonación. Define qué medios de pago acepta cada
              sucursal y ve qué cuota de intención de compra se pierde cuando un cliente no puede
              pagar como quería.
            </P>

            <H3>CU-7 · Revisar el negocio a fin de mes</H3>
            <P>
              El encargado abre <F>Reportes</F>: compara las dos sucursales lado a lado, mira la
              tendencia de un indicador por semana o por mes, lee el tablero de KPIs y revisa los
              segmentos de clientes que produjo el clustering.
            </P>
          </section>

          {/* ─── 8 · Arquitectura ─────────────────────────────────────────────────────────── */}
          <section id="arquitectura" className={estilos.seccion}>
            <h2 className={estilos.h2}>9 · Arquitectura</h2>

            <H3>Visión de capas</H3>
            <div className={estilos.diagrama}>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>Frontend — SPA React 18 + Vite + TypeScript</p>
                <p className={estilos.capaDetalle}>
                  Sistema de diseño propio (sin Bootstrap / MUI). Componentes base: Boton, Campo,
                  EncabezadoPantalla, Segmentado. Una pantalla por módulo bajo un armazón con
                  navegación por rol. Estado de sesión (turno + token) en memoria. Gráficos con
                  Recharts. Cola offline que reenvía lo trabajado sin conexión en orden de origen.
                </p>
              </div>
              <span className={estilos.flecha}>↕ HTTP/JSON · header Authorization: Bearer</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>Backend — FastAPI (Python), en capas</p>
                <p className={estilos.capaDetalle}>
                  api/ (routers por módulo, un error handler que nunca filtra trazas) → servicios/
                  (orquestación y transacciones) → dominio/ (reglas puras: márgenes, censura,
                  k-means, experimento, arqueo, selección de lote, tokenización…) → persistencia/
                  (SQLAlchemy, modelos, registro de movimientos). Autorización y sesión
                  centralizadas en seguridad.py (requiere_rol / exige_rol + emisión y verificación
                  del token de turno).
                </p>
              </div>
              <span className={estilos.flecha}>↕ SQLAlchemy</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>Base de datos — PostgreSQL</p>
                <p className={estilos.capaDetalle}>
                  En desarrollo, nativo en el puerto 5442 (no 5432, para no colisionar con otros
                  proyectos del curso). SQLite está PROHIBIDO en toda fase: no tiene tipo NUMERIC
                  real y opera en coma flotante. Docker Compose se deja para la fase final.
                </p>
              </div>
            </div>

            <H3>Base de datos</H3>
            <ul className={estilos.lista}>
              <li>
                <F>Propiedad de datos por módulo:</F> cada entidad pertenece a exactamente una
                funcionalidad; un cambio de esquema sobre una entidad ajena se hace en su módulo
                dueño.
              </li>
              <li>
                <F>Migraciones versionadas</F> con Alembic: <C>0001_esquema_inicial</C> …{" "}
                <C>0014_venta_medio_pago</C>, cada una con procedimiento de reversión.
              </li>
              <li>
                <F>Precisión exacta:</F> dinero y peso en gramos se guardan con tipos decimales de
                precisión fija; nunca coma flotante binaria. Cada importe lleva su moneda.
              </li>
              <li>
                <F>Trazabilidad:</F> el inventario se reconstruye a partir de{" "}
                <C>movimiento_inventario</C>; sobrescribir una cantidad sin registrar el movimiento
                que la origina está prohibido. Todo filtrable por sucursal.
              </li>
              <li>
                <F>Tiempo:</F> los instantes se guardan en UTC y se presentan en la zona de la
                sucursal; los cierres de caja se calculan sobre el día local de esa sucursal.
              </li>
              <li>
                <F>Datos de pago:</F> el número completo de tarjeta, el CVV y la banda no se
                almacenan en ningún módulo; solo token, últimos cuatro dígitos y marca.
              </li>
            </ul>

            <H3>Decisiones de fiabilidad (Principio II)</H3>
            <ul className={estilos.lista}>
              <li>
                <F>Degradación, nunca bloqueo:</F> ninguna función de IA, analítica o telemetría es
                camino crítico de un cobro.
              </li>
              <li>
                <F>Idempotencia obligatoria:</F> toda operación que mueve inventario, dinero o
                documentos acepta una clave de idempotencia y produce el mismo resultado ante
                reintentos.
              </li>
              <li>
                <F>Reconciliación explícita:</F> lo ejecutado sin conexión se encola con marca de
                tiempo de origen; ante conflicto gana <F>la operación más antigua sobre el mismo
                recurso</F>, y la desplazada queda visible para revisión, nunca se borra.
              </li>
            </ul>
          </section>

          {/* ─── 10 · Modelo de datos ─────────────────────────────────────────────────────── */}
          <section id="modelo-datos" className={estilos.seccion}>
            <h2 className={estilos.h2}>10 · Modelo de datos (tablas)</h2>
            <P>
              El esquema tiene <F>50 tablas</F> en PostgreSQL, creadas por 14 migraciones de
              Alembic versionadas (<C>0001_esquema_inicial</C> … <C>0014_venta_medio_pago</C>),
              cada una con su procedimiento de reversión. Cada tabla <F>pertenece a exactamente
              un módulo</F> (tabla de Propiedad de Datos de la constitución): los demás módulos la
              consultan, nunca la redefinen ni alteran su esquema.
            </P>
            <ul className={estilos.lista}>
              <li>
                <F>Nomenclatura:</F> español, <C>snake_case</C>, singular, sin «ñ»; claves
                foráneas <C>id_</C> + tabla referida.
              </li>
              <li>
                <F>Precisión exacta:</F> <C>num(p,e)</C> es <C>NUMERIC</C> de precisión fija para
                dinero y para gramos; nunca hay coma flotante. <C>ts</C> es{" "}
                <C>timestamptz</C> (se guarda en UTC).
              </li>
              <li>
                <F>Notación de la columna:</F> <C>PK</C> clave primaria · <C>FK→x</C> clave
                foránea a <C>x</C> · <C>U</C> restricción <C>UNIQUE</C> · <C>·</C> anulable ·{" "}
                <C>CHECK</C> valores admitidos.
              </li>
              <li>
                <F>Trazabilidad:</F> el inventario entero se reconstruye desde{" "}
                <C>movimiento_inventario</C>; sobrescribir una cantidad sin registrar el
                movimiento que la origina está prohibido.
              </li>
            </ul>

            {MODELO_DATOS.map((grupo) => (
              <div key={grupo.modulo}>
                <H3>{grupo.modulo}</H3>
                <P>{grupo.intro}</P>
                {grupo.tablas.map((t) => (
                  <TablaBD key={t.nombre} nombre={t.nombre} proposito={t.proposito} cols={t.cols} />
                ))}
              </div>
            ))}

            <div className={estilos.nota}>
              <F>Entidades que NO son tabla:</F> varios cálculos «inteligentes» se resuelven al
              leer y no se persisten — los indicadores por operador de 006 (anulaciones, ventas
              bajo precio de lista, discrepancia inventario-ventas), los indicadores de firmware y
              la cuota de intención de compra no atendida de 007. Es una decisión deliberada:
              recalcular es barato y evita una tabla que podría quedar desincronizada.
            </div>
          </section>

          {/* ─── 11 · Spec Kit ────────────────────────────────────────────────────────────── */}
          <section id="speckit" className={estilos.seccion}>
            <h2 className={estilos.h2}>11 · Aplicación de Spec Kit</h2>
            <P>
              <F>Spec Kit</F> es un método de desarrollo dirigido por especificación: primero se
              describe el <F>comportamiento observable</F>, y solo después las decisiones de
              implementación. En este proyecto se aplicó módulo por módulo con este ciclo:
            </P>
            <div className={estilos.diagrama}>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-constitution</p>
                <p className={estilos.capaDetalle}>
                  La constitución del proyecto: 6 principios no negociables + 6 «Lecturas Críticas
                  del Enunciado» + tabla de propiedad de datos + sistema de diseño. Va por la
                  versión 2.7.0 tras más de 20 enmiendas, cada una con su informe de impacto.
                </p>
              </div>
              <span className={estilos.flecha}>↓ gobierna</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-specify → spec.md</p>
                <p className={estilos.capaDetalle}>
                  User stories priorizadas con escenarios de aceptación (Given/When/Then), requisitos
                  funcionales numerados (FR-xxx), entidades tocadas y casos límite. Sin decisiones de
                  framework.
                </p>
              </div>
              <span className={estilos.flecha}>↓</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-clarify</p>
                <p className={estilos.capaDetalle}>
                  Hasta 5 preguntas dirigidas a lo que quedó ambiguo; las respuestas se graban en el
                  propio spec.md (sección «Clarifications»).
                </p>
              </div>
              <span className={estilos.flecha}>↓</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-plan → plan.md, data-model.md, research.md</p>
                <p className={estilos.capaDetalle}>
                  Decisiones de implementación con «Constitution Check»: cualquier desviación se
                  registra con su justificación y la alternativa más simple descartada. Aquí nacen el
                  modelo de datos y la investigación de cada duda técnica.
                </p>
              </div>
              <span className={estilos.flecha}>↓</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-tasks → tasks.md</p>
                <p className={estilos.capaDetalle}>
                  Lista de tareas ordenada por dependencias, agrupada por user story, con las
                  paralelizables marcadas.
                </p>
              </div>
              <span className={estilos.flecha}>↓</span>
              <div className={estilos.capa}>
                <p className={estilos.capaTitulo}>/speckit-implement · /speckit-analyze · /speckit-converge</p>
                <p className={estilos.capaDetalle}>
                  Ejecución de las tareas; análisis de consistencia entre spec, plan y tasks; y cierre
                  del trabajo pendiente contra el código real.
                </p>
              </div>
            </div>
            <P>
              <F>Puertas de calidad</F> antes de fusionar: «Constitution Check» completo; puerta de
              propiedad de datos (ninguna especificación redefine una entidad de otro módulo);
              puerta de sincronización de enmiendas (toda cita de la constitución se actualiza en el
              mismo cambio); compilación, análisis estático y las pruebas obligatorias del Principio
              III (dinero, transiciones de estado de inventario, contratos públicos) en verde.
            </P>
            <P>
              <F>DESIGN.md</F> no se escribe al principio: lo deriva la herramienta Impeccable{" "}
              <F>de la interfaz ya construida</F>, al final. Contiene el sistema de diseño real
              (dos registros «Operación» / «Análisis», paleta de comercio físico, cero sombras,
              tres portadores de incertidumbre) como reglas con nombre.
            </P>

            <H3>Cómo se creó cada spec, módulo por módulo</H3>
            <P>
              El ciclo de arriba no se corrió una vez para todo el sistema: se corrió{" "}
              <F>una vez completa por módulo</F>, en orden (001 primero, 009 al final), porque
              cada módulo declara sus propias entidades y los siguientes solo las <F>consultan</F>{" "}
              (tabla de propiedad de datos de la constitución). Para un módulo dado, el paso a
              paso real fue:
            </P>
            <ol className={estilos.lista}>
              <li>
                <F>/speckit-specify «descripción del módulo en lenguaje natural»</F> — a partir de
                un fragmento del enunciado ofuscado del docente (ver sección 3), la IA redacta{" "}
                <C>specs/00X-módulo/spec.md</C>: las user stories priorizadas (P1 = mínimo
                entregable) con sus escenarios Given/When/Then y los requisitos funcionales
                numerados (<C>FR-001</C>, <C>FR-002</C>…).
              </li>
              <li>
                <F>/speckit-clarify</F> — la IA relee ese spec buscando ambigüedad real (nunca más
                de 5 preguntas) y las respuestas del propietario del producto quedan grabadas,
                textuales, en la sección «Clarifications» del propio <C>spec.md</C> — nunca en un
                chat que se pierde.
              </li>
              <li>
                <F>/speckit-plan</F> — con el spec ya cerrado, la IA propone <C>plan.md</C> (
                arquitectura y decisiones técnicas), <C>data-model.md</C> (las tablas nuevas de ese
                módulo) y <C>research.md</C> (una entrada por cada duda técnica, con la alternativa
                descartada y por qué). Cada decisión pasa un «Constitution Check» explícito.
              </li>
              <li>
                <F>/speckit-tasks</F> — la IA descompone el plan en <C>tasks.md</C>: una lista
                ordenada por dependencias, agrupada por user story, con las tareas paralelizables
                marcadas — para poder implementar P1 completo y ya tener algo entregable antes de
                tocar P2.
              </li>
              <li>
                <F>/speckit-implement</F> — la IA escribe el código seguido de <C>tasks.md</C>,
                tarea por tarea (dominio → persistencia → servicios → API → frontend), y las
                pruebas que exige el Principio III antes de dar una tarea por cerrada.
              </li>
              <li>
                <F>/speckit-analyze</F> y <F>/speckit-converge</F> — al terminar, la IA audita que{" "}
                <C>spec.md</C>, <C>plan.md</C>, <C>tasks.md</C> y el código sigan siendo el mismo
                sistema (nada se implementó sin spec, nada del spec quedó sin implementar) y cierra
                cualquier brecha real contra el código.
              </li>
            </ol>
            <P>
              La evidencia de cada paso queda en el repositorio, no solo en esta pantalla:{" "}
              <C>specs/00X-módulo/</C> tiene siempre <C>spec.md</C>, <C>plan.md</C>,{" "}
              <C>research.md</C>, <C>data-model.md</C>, <C>tasks.md</C> y un <C>quickstart.md</C>{" "}
              (cómo probar manualmente esa historia de usuario ya implementada).
            </P>

            <H3>Qué se especificó en cada módulo</H3>
            <P>
              Lo que sigue son las user stories reales de cada <C>spec.md</C>, en su orden de
              prioridad (P1 = la que por sí sola ya seria un entregable útil) — no un resumen
              inventado después, sino lo que la IA redactó y el propietario aprobó antes de que se
              escribiera una sola línea de código de ese módulo.
            </P>
            <Tabla
              cabeceras={["Módulo", "User stories especificadas (orden de prioridad)", "FR"]}
              filas={[
                [
                  "001 · Core",
                  <ul className={estilos.lista}>
                    <li>Registrar una venta en caja</li>
                    <li>Recibir mercancía del proveedor en lotes</li>
                    <li>Registrar una consulta no atendida</li>
                    <li>Comparar el precio propio contra la competencia</li>
                    <li>Cuadrar el inventario con un conteo físico</li>
                    <li>Traspasar mercancía entre las dos sucursales</li>
                    <li>Ver el capital inmovilizado</li>
                    <li>Sincronizar lo trabajado sin conexión</li>
                    <li>Corregir el carrito antes de cobrar</li>
                    <li>Roles de operador, sucursal fija y autorización centralizada</li>
                  </ul>,
                  "83",
                ],
                [
                  "002 · Clientes",
                  <ul className={estilos.lista}>
                    <li>Mantener el catálogo de clientes y su historial de visitas</li>
                    <li>Medir el valor real de cada cliente</li>
                    <li>Detectar señales de fuga silenciosa por cliente</li>
                    <li>Identificar cliente por cédula o RUC para evitar duplicados</li>
                    <li>Visualizar la curva de fuga por segmento</li>
                  </ul>,
                  "20",
                ],
                [
                  "003 · Precios",
                  <ul className={estilos.lista}>
                    <li>Calcular el margen real de un producto</li>
                    <li>Clasificar el rol comercial de un producto</li>
                    <li>Sugerir precio de venta usando margen, rol y competencia</li>
                    <li>Sugerir colocación en zona de exhibición</li>
                    <li>Visualizar el margen real por producto</li>
                  </ul>,
                  "25",
                ],
                [
                  "004 · Pronóstico",
                  <ul className={estilos.lista}>
                    <li>Descensurar la demanda por quiebre de stock</li>
                    <li>Validar la descensura contra datos sintéticos con demanda latente conocida</li>
                    <li>Generar el pronóstico de demanda a partir de la serie corregida</li>
                    <li>Corregir la serie por el precio vigente en cada período histórico</li>
                    <li>Neutralizar los períodos con promoción activa</li>
                    <li>Declarar sustitutos y señalar demanda inflada por quiebre de un sustituto</li>
                    <li>Visualizar la demanda pronosticada vs. la histórica censurada</li>
                  </ul>,
                  "43",
                ],
                [
                  "005 · Promociones",
                  <ul className={estilos.lista}>
                    <li>Generar el cupón por fecha fija (cumpleaños)</li>
                    <li>Empujar la recompra con reserva de precio a un cliente en su intervalo esperado</li>
                    <li>Medir la reactivación de clientes inactivos contra un grupo de control</li>
                    <li>Exponer la marca de «promoción activa» para el pronóstico de demanda</li>
                    <li>Visualizar el resultado del experimento de reactivación</li>
                  </ul>,
                  "42",
                ],
                [
                  "006 · Caja y fraude",
                  <ul className={estilos.lista}>
                    <li>Arquear la caja al cierre de cada turno</li>
                    <li>Clasificar la causa de una diferencia de conteo físico como merma</li>
                    <li>Detectar el sub-registro cruzando inventario contra ventas por operador</li>
                    <li>Gestionar las anomalías de caja sin explicación</li>
                    <li>Visualizar las mermas por causa en el tiempo</li>
                  </ul>,
                  "45",
                ],
                [
                  "007 · Pagos",
                  <ul className={estilos.lista}>
                    <li>Conocer y mantener la cobertura de medios de pago por sucursal</li>
                    <li>Registrar las terminales de pago y vigilar su firmware y su exposición a clonación</li>
                    <li>Tokenizar los datos de pago de cada cobro con tarjeta</li>
                    <li>Auditar la actividad de pagos en una bitácora consultable</li>
                  </ul>,
                  "37",
                ],
                [
                  "008 · Reportes",
                  <ul className={estilos.lista}>
                    <li>Comparar las dos sucursales en un vistazo</li>
                    <li>Ver la tendencia de un indicador por semana o por mes</li>
                    <li>Leer el tablero de KPIs consolidados</li>
                    <li>Segmentar los clientes por similitud</li>
                  </ul>,
                  "31",
                ],
                [
                  "009 · Facturación",
                  <ul className={estilos.lista}>
                    <li>Recibir la factura simulada al terminar una venta</li>
                    <li>Volver a ver o regenerar la factura de una venta</li>
                    <li>Anular la factura cuando se anula la venta</li>
                  </ul>,
                  "21",
                ],
              ]}
            />
          </section>

          {/* ─── 12 · Glosario ────────────────────────────────────────────────────────────── */}
          <section id="glosario" className={estilos.seccion}>
            <h2 className={estilos.h2}>12 · Glosario</h2>
            <Tabla
              cabeceras={["Término", "Significado"]}
              filas={[
                [<span className={estilos.termino}>Rasero</span>, "La tablilla que nivela una medida de grano al ras. Nombre y tesis del sistema: el mismo criterio objetivo para todo."],
                [<span className={estilos.termino}>Punto de venta (POS)</span>, "La pantalla donde el cajero cobra."],
                [<span className={estilos.termino}>A granel / a peso</span>, "Producto que se vende pesando en báscula (queso), con cantidad decimal en gramos y precisión exacta."],
                [<span className={estilos.termino}>Lote</span>, "Una entrada concreta de mercadería, con su costo y su caducidad. El stock de un producto es la suma de sus lotes."],
                [<span className={estilos.termino}>FEFO</span>, "First-Expired, First-Out: al descontar stock sale primero el lote que caduca antes (y si no hay caducidad, el que entró antes)."],
                [<span className={estilos.termino}>Idempotencia</span>, "Si una operación se reintenta con la misma clave, no se duplica (ni la venta, ni el movimiento de inventario, ni el cargo)."],
                [<span className={estilos.termino}>Reconciliación offline</span>, "Las operaciones hechas sin internet se sincronizan después; ante conflicto gana la que ocurrió primero en el mundo físico."],
                [<span className={estilos.termino}>Consulta no atendida</span>, "El cliente preguntó por algo que no había y se fue. Venta perdida que normalmente nadie registra."],
                [<span className={estilos.termino}>Margen real</span>, "Cuánto deja de verdad un producto (precio − costo, con reglas de negocio), no cuántas unidades vende."],
                [<span className={estilos.termino}>Rol comercial del producto</span>, "Gancho de tráfico (precio mínimo, atrae clientes) vs. generador de margen (nicho, sube precio)."],
                [<span className={estilos.termino}>Zona de exhibición</span>, "Ubicación física en la góndola. El producto de más margen va a la zona privilegiada."],
                [<span className={estilos.termino}>Valor de cliente</span>, "Combinación de frecuencia de compra, monto y margen de lo que compra. No es el gasto total."],
                [<span className={estilos.termino}>Intervalo de compra esperado</span>, "El ritmo propio de cada cliente (uno compra cada 3 días, otro cada 3 semanas), derivado de su historial."],
                [<span className={estilos.termino}>Fuga silenciosa</span>, "El cliente fiel que deja de venir sin avisar. Se detecta cuando su tiempo sin comprar supera varias veces su intervalo."],
                [<span className={estilos.termino}>Censura / descensura</span>, "Durante los días sin stock, las ventas registradas subestiman la demanda real (demanda «censurada»). Descensurar es estimar cuánto se habría vendido."],
                [<span className={estilos.termino}>Sustituto / canibalización</span>, "Si se agota el café molido, sube la venta de café en grano — sin que haya más demanda real. Se declara manualmente la relación."],
                [<span className={estilos.termino}>Grupo de control</span>, "En una campaña de reactivación, el subgrupo al que NO se da el descuento, para medir el efecto incremental real."],
                [<span className={estilos.termino}>Incrementalidad</span>, "La diferencia de retorno entre el grupo con descuento y el grupo de control, con su prueba estadística (z, p)."],
                [<span className={estilos.termino}>Clustering (k-means)</span>, "Algoritmo que agrupa clientes parecidos sin que nadie defina los grupos. Semilla fija: siempre da el mismo resultado."],
                [<span className={estilos.termino}>Arqueo de caja</span>, "Contar el efectivo físico al cierre de turno y compararlo con lo registrado."],
                [<span className={estilos.termino}>Merma</span>, "Pérdida de inventario (caducado, roto, robado, mal registrado). En lácteos puede comerse hasta el 20% de la ganancia anual."],
                [<span className={estilos.termino}>Sub-registro</span>, "«Cobrar 5, registrar 3»: el cajero cobra el monto real pero registra menos. No descuadra la caja; se detecta cruzando inventario contra ventas por operador."],
                [<span className={estilos.termino}>Tokenización</span>, "Reemplazar el número de tarjeta (PAN) por un identificador sustituto. Rasero solo guarda el token, los últimos 4 dígitos y la marca."],
                [<span className={estilos.termino}>Skimming (clonación)</span>, "Copiar los datos de una tarjeta con un datáfono manipulado o con firmware vulnerable."],
                [<span className={estilos.termino}>Cobertura de medios de pago</span>, "Qué formas de pago acepta cada sucursal; si no aceptas la del cliente, la venta se pierde antes de existir."],
                [<span className={estilos.termino}>Factura simulada</span>, "Documento con la forma de una factura electrónica ecuatoriana pero sin SRI, sin firma y sin XML válido."],
                [<span className={estilos.termino}>Traspaso</span>, "Movimiento de mercadería entre sucursales, registrado como dos asientos enlazados para que la mercancía en tránsito nunca desaparezca del total."],
                [<span className={estilos.termino}>Capital inmovilizado</span>, "Dinero «dormido» en stock que no rota (lotes antiguos sin salida)."],
                [<span className={estilos.termino}>Tres portadores</span>, "Regla de diseño: todo dato incierto se marca con color + forma + texto, nunca solo color (falla ante daltonismo, impresión b/n o reflejo de pantalla)."],
                [<span className={estilos.termino}>Registro «Operación» / «Análisis»</span>, "Los dos modos visuales del sistema: denso y con tablas para la caja; con aire y una decisión por bloque para las pantallas donde se decide."],
              ]}
            />
          </section>

          {/* ─── 13 · Créditos académicos ─────────────────────────────────────────────────── */}
          <section id="creditos" className={estilos.seccion}>
            <h2 className={estilos.h2}>13 · Créditos académicos</h2>
            <P>
              Rasero es un proyecto académico desarrollado para la materia{" "}
              <F>Construcción del Software</F>, carrera de <F>Software</F>, en la{" "}
              <F>Facultad de Ciencias de la Computación (FCC)</F> de la{" "}
              <F>Universidad Técnica Estatal de Quevedo (UTEQ)</F>.
            </P>
            <Tabla
              cabeceras={["Dato", "Valor"]}
              filas={[
                ["Universidad", "Universidad Técnica Estatal de Quevedo (UTEQ)"],
                ["Facultad", "Facultad de Ciencias de la Computación (FCC)"],
                ["Carrera", "Software"],
                ["Materia", "Construcción del Software"],
                ["Estudiante", "Eduardo Reinoso Vélez"],
              ]}
            />
          </section>

          {/* ─── 14 · Puesta en marcha ────────────────────────────────────────────────────── */}
          <section id="despliegue" className={estilos.seccion}>
            <h2 className={estilos.h2}>14 · Puesta en marcha</h2>
            <P>
              Requisitos: Python <F>3.12+</F>, Node <F>20+</F>, PostgreSQL <F>16+</F> escuchando
              en el puerto <C>5442</C> (no 5432, para no chocar con otros proyectos), con una base
              y un rol llamados <C>rasero</C>. Cuatro momentos distintos, que no se repiten en
              cada arranque: <F>instalar</F> (una vez), <F>sembrar datos</F> (una vez, o cuando se
              quiera reiniciar la demo), <F>levantar</F> (cada vez que se trabaja) y{" "}
              <F>probar</F> (cuando se quiere validar un cambio).
            </P>

            <H3>1 · Instalación (sólo la primera vez)</H3>
            <P>Clona el repositorio, crea el entorno virtual del backend e instala ambas partes.</P>
            <Comando>{`cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows · source .venv/bin/activate en Linux/macOS
pip install -e .

export DATABASE_URL="postgresql+psycopg://rasero@localhost:5442/rasero"
python -m alembic -c migraciones/alembic.ini upgrade head    # crea las 50 tablas`}</Comando>
            <Comando>{`cd frontend
npm install`}</Comando>

            <H3>2 · Semillas de datos de demostración (sólo la primera vez, o para reiniciar la demo)</H3>
            <P>
              Cada semilla es independiente y se puede volver a correr sola; en orden, así se
              arma el escenario completo de demostración:
            </P>
            <Comando>{`python -m rasero.semilla                # operadores + sucursales + catálogo base
python -m rasero.semilla_catalogo        # catálogo de demostración
python -m rasero.semilla_movimientos     # ventas e inventario de ejemplo
python -m rasero.semilla_clientes        # clientes con historial
python -m rasero.semilla_reactivacion    # escenario de fuga y reactivación
python -m rasero.semilla_pagos           # medios de pago, cobertura y terminales`}</Comando>
            <P>
              El acceso de demostración lo imprime <C>python -m rasero.semilla</C>: por defecto,
              Ana Cajera (rol <C>cajero</C>, PIN <C>1234</C>), Luis Encargado (
              <C>encargado</C>, PIN <C>9999</C>) y Marta Administradora (<C>admin</C>, PIN{" "}
              <C>0000</C>).
            </P>

            <H3>3 · Levantar el sistema (cada vez que se trabaja)</H3>
            <P>Con todo ya instalado y sembrado, sólo hacen falta estos dos comandos, cada uno en su propia terminal:</P>
            <Comando>{`cd backend
.venv/Scripts/activate            # Windows · source .venv/bin/activate en Linux/macOS
python -m uvicorn rasero.api.aplicacion:app --port 8000`}</Comando>
            <Comando>{`cd frontend
npm run dev          # http://localhost:5173  (espera el backend en http://localhost:8000)`}</Comando>

            <H3>4 · Pruebas</H3>
            <P>
              La suite corre con <F>pytest</F>, contra un PostgreSQL real (nunca SQLite), desde la
              raíz del repositorio y con el intérprete del entorno virtual del backend:
            </P>
            <Comando>{`backend/.venv/Scripts/python.exe -m pytest -q      # Windows
backend/.venv/bin/python -m pytest -q              # Linux/macOS`}</Comando>
          </section>
        </div>
      </div>
    </div>
  );
}
