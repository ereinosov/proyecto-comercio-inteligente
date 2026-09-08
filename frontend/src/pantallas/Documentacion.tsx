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

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
  { id: "casos-uso", titulo: "7 · Casos de uso" },
  { id: "arquitectura", titulo: "8 · Arquitectura" },
  { id: "speckit", titulo: "9 · Aplicación de Spec Kit" },
  { id: "glosario", titulo: "10 · Glosario" },
];

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

export function Documentacion({ onVolver }: Props) {
  const [activa, setActiva] = useState<string>(SECCIONES[0].id);
  const contenidoRef = useRef<HTMLDivElement>(null);
  const ids = useMemo(() => SECCIONES.map((s) => s.id), []);

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
        <Boton variante="neutra" registro="analisis" onClick={onVolver}>
          Volver a la apertura de turno
        </Boton>
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
          <section id="casos-uso" className={estilos.seccion}>
            <h2 className={estilos.h2}>7 · Casos de uso</h2>

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
            <h2 className={estilos.h2}>8 · Arquitectura</h2>

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
                <C>0013_factura_simulada</C>, cada una con procedimiento de reversión.
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

          {/* ─── 9 · Spec Kit ─────────────────────────────────────────────────────────────── */}
          <section id="speckit" className={estilos.seccion}>
            <h2 className={estilos.h2}>9 · Aplicación de Spec Kit</h2>
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
          </section>

          {/* ─── 10 · Glosario ────────────────────────────────────────────────────────────── */}
          <section id="glosario" className={estilos.seccion}>
            <h2 className={estilos.h2}>10 · Glosario</h2>
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
        </div>
      </div>
    </div>
  );
}
