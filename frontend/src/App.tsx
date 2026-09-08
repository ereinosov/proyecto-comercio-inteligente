import { useEffect, useRef, useState } from "react";
import { AperturaTurno } from "./componentes/AperturaTurno";
import { Venta } from "./pantallas/Venta";
import { ConteoFisico } from "./pantallas/ConteoFisico";
import { EntradaInventario } from "./pantallas/EntradaInventario";
import { DespachoTraspaso } from "./pantallas/DespachoTraspaso";
import { CapitalInmovilizado } from "./pantallas/CapitalInmovilizado";
import { Competencia } from "./pantallas/Competencia";
import { Clientes } from "./pantallas/Clientes";
import { Precios } from "./pantallas/Precios";
import { Pronostico } from "./pantallas/Pronostico";
import { Promociones } from "./pantallas/Promociones";
import { Arqueo } from "./pantallas/Arqueo";
import { CajaFraude } from "./pantallas/CajaFraude";
import { TerminalesPago } from "./pantallas/TerminalesPago";
import { Pagos } from "./pantallas/Pagos";
import { Administracion } from "./pantallas/Administracion";
import { Reportes } from "./pantallas/Reportes";
import { Documentacion } from "./pantallas/Documentacion";
import { cerrarTurno, listarOperadores, type Turno } from "./servicios/turnos";
import { listarSucursales } from "./servicios/sucursales";
import {
  fijarTokenSesion,
  limpiarTokenSesion,
  alPerderSesionDeTurno,
} from "./servicios/clienteHttp";
import { useRol, type Rol } from "./hooks/useRol";
import marcaSistema from "./activos/marca/rasero-wordmark-512w.png";
import iconoComercioPorDefecto from "./activos/marca/despensa-icon-verde-512.png";
import estilos from "./App.module.css";

// La Regla de la Marca Persistente (DESIGN.md v1.4.0): las dos marcas no comparten lugar. El nav
// global lleva SOLO el wordmark de Rasero (la herramienta); el ícono del comercio baja al footer,
// delante de "{sucursal} · {caja}" (dónde estoy). Configurable por entorno igual que el logo a
// color de la apertura de turno.
const ICONO_COMERCIO: string = import.meta.env.VITE_ICONO_COMERCIO ?? iconoComercioPorDefecto;

type Pantalla =
  | "venta"
  | "conteo"
  | "entradas"
  | "traspasos"
  | "capital"
  | "competencia"
  | "clientes"
  | "precios"
  | "pronostico"
  | "promociones"
  | "arqueo"
  | "cajafraude"
  | "terminales"
  | "pagos"
  | "reportes"
  | "administracion";

// La Regla del Grupo de Navegación (DESIGN.md v1.2.0): "Venta" suelta y siempre visible; el
// resto en grupos desplegables; "Administración" al final, pantalla propia (no grupo).
//
// Rol mínimo por opción (enmienda constitucional v2.5.0, Principio VI): el cajero opera caja
// (Venta, Arqueo), inventario del día a día (Conteo, Entradas) y sus consultas no atendidas;
// todo lo táctico/gerencial —traspasos, capital, precios, competencia, pronóstico, clientes,
// promociones, fraude, terminales, cobertura— es `encargado` o más. "Ocultar, no deshabilitar":
// una opción que el rol no alcanza no se renderiza (el backend la valida además,
// independientemente). Arqueo sale del grupo "Caja y seguridad" y va junto a Venta: es tarea
// diaria de cajero, y el grupo quedaría de una sola opción para un cajero.
type OpcionNav = { valor: Pantalla; texto: string; rol: Rol };

const GRUPOS: { etiqueta: string; opciones: OpcionNav[] }[] = [
  {
    etiqueta: "Inventario",
    opciones: [
      { valor: "conteo", texto: "Conteo", rol: "cajero" },
      { valor: "entradas", texto: "Entradas", rol: "cajero" },
      { valor: "traspasos", texto: "Traspasos", rol: "encargado" },
      { valor: "capital", texto: "Capital", rol: "encargado" },
    ],
  },
  {
    etiqueta: "Precios y demanda",
    opciones: [
      { valor: "precios", texto: "Precios", rol: "encargado" },
      { valor: "competencia", texto: "Competencia", rol: "encargado" },
      { valor: "pronostico", texto: "Pronóstico", rol: "encargado" },
      { valor: "reportes", texto: "Reportes", rol: "encargado" },
    ],
  },
  {
    etiqueta: "Clientes y promos",
    opciones: [
      { valor: "clientes", texto: "Clientes", rol: "encargado" },
      { valor: "promociones", texto: "Promociones", rol: "encargado" },
    ],
  },
  {
    etiqueta: "Caja y seguridad",
    opciones: [
      { valor: "cajafraude", texto: "Caja y fraude", rol: "encargado" },
      { valor: "terminales", texto: "Terminales", rol: "encargado" },
      { valor: "pagos", texto: "Pagos", rol: "encargado" },
    ],
  },
];

function Chevron() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <path
        d="M2 3.5 L5 6.5 L8 3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GrupoNav({
  etiqueta,
  opciones,
  pantalla,
  onElegir,
}: {
  etiqueta: string;
  opciones: OpcionNav[];
  pantalla: Pantalla;
  onElegir: (p: Pantalla) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const activo = opciones.some((o) => o.valor === pantalla);

  useEffect(() => {
    if (!abierto) return;
    function fuera(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false);
    }
    window.addEventListener("mousedown", fuera);
    return () => window.removeEventListener("mousedown", fuera);
  }, [abierto]);

  return (
    <div className={estilos.grupo} ref={ref}>
      <button
        className={activo ? estilos.grupoBotonActivo : estilos.grupoBoton}
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
      >
        {etiqueta}
        <span className={`${estilos.chevron} ${abierto ? estilos.chevronAbierto : ""}`}>
          <Chevron />
        </span>
      </button>
      {abierto && (
        <div className={estilos.desplegable}>
          {opciones.map((o) => (
            <button
              key={o.valor}
              className={o.valor === pantalla ? estilos.opcionActiva : estilos.opcion}
              onClick={() => {
                onElegir(o.valor);
                setAbierto(false);
              }}
            >
              {o.texto}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function App() {
  const [turno, setTurnoEstado] = useState<Turno | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla>("venta");
  const [nombreOperador, setNombreOperador] = useState<string>("");
  const [rol, setRol] = useState<Rol | null>(null);
  const [nombreSucursal, setNombreSucursal] = useState<string>("");
  // Superficie de DEMOSTRACIÓN (no operativa): documentación del sistema, accesible sólo desde
  // la pantalla de apertura de turno. No entra en el nav ni en la autorización por rol.
  const [verDocumentacion, setVerDocumentacion] = useState(false);
  // Hallazgo #2 de la auditoría: el arqueo es paso OBLIGATORIO de "Cerrar turno". Al cerrar, el
  // turno recién cerrado queda aquí y se muestra su arqueo antes de dejar abrir uno nuevo.
  const [turnoPorArquear, setTurnoPorArquear] = useState<Turno | null>(null);
  // User Story 11 (Principio VI, "Identidad de sesión"): el token JWT de la sesión de turno
  // vive junto al turno, en memoria. `setTurno` lo sincroniza con el cliente HTTP.
  const [avisoSesion, setAvisoSesion] = useState<string | null>(null);

  function setTurno(nuevo: Turno | null) {
    if (nuevo?.token) {
      fijarTokenSesion(nuevo.token);
      setAvisoSesion(null);
    } else {
      limpiarTokenSesion();
    }
    setTurnoEstado(nuevo);
  }

  // Sesión perdida (401 sesion_invalida / sesion_expirada): volver a la apertura de turno con
  // un mensaje claro, nunca el error genérico (FR-071).
  useEffect(() => {
    alPerderSesionDeTurno((error) => {
      setTurnoEstado(null);
      setAvisoSesion(error.message);
      setPantalla("venta");
    });
    return () => alPerderSesionDeTurno(null);
  }, []);
  // Hook único de rol (User Story 10, Principio VI). Los componentes deciden qué OFRECER con
  // `puedeVer` / `esAdmin` / `esEncargadoOMas`; nunca leen `rol` a mano.
  const autoriz = useRol(rol);

  // Defensa en profundidad (enmienda v2.5.0): si el rol activo no alcanza la pantalla actual
  // (p. ej. cambió el rol del operador, o un estado quedó de una sesión previa), se vuelve a
  // Venta. El backend valida además cada endpoint por su cuenta.
  useEffect(() => {
    if (rol === null) return;
    const permitidas = new Set<Pantalla>(["venta", "arqueo"]);
    for (const g of GRUPOS) {
      for (const o of g.opciones) if (autoriz.puedeVer(o.rol)) permitidas.add(o.valor);
    }
    if (autoriz.esAdmin()) permitidas.add("administracion");
    if (!permitidas.has(pantalla)) setPantalla("venta");
  }, [rol, pantalla, autoriz]);

  useEffect(() => {
    if (!turno) return;
    listarOperadores()
      .then((lista) => {
        const op = lista.find((o) => o.id_operador === turno.id_operador);
        setNombreOperador(op?.nombre ?? `Operador ${turno.id_operador}`);
        setRol(op?.rol ?? null);
      })
      .catch(() => setNombreOperador(`Operador ${turno.id_operador}`));
    // Nombre de sucursal para el footer (Regla de la Marca Persistente). `incluir_inactivas`
    // por si la sucursal del turno se desactivó después de abrirlo — no perder el dato.
    listarSucursales(true)
      .then((lista) => {
        const s = lista.find((x) => x.id_sucursal === turno.id_sucursal);
        setNombreSucursal(s?.nombre ?? "");
      })
      .catch(() => setNombreSucursal(""));
  }, [turno]);

  if (!turno) {
    if (turnoPorArquear) {
      return (
        <Arqueo
          turno={turnoPorArquear}
          modoCierre
          onListo={() => setTurnoPorArquear(null)}
        />
      );
    }
    if (verDocumentacion) {
      return <Documentacion onVolver={() => setVerDocumentacion(false)} />;
    }
    return (
      <AperturaTurno
        onTurnoAbierto={setTurno}
        avisoSesion={avisoSesion}
        onVerDocumentacion={() => setVerDocumentacion(true)}
      />
    );
  }

  async function manejarCierre() {
    if (!turno) return;
    const cerrado = turno;
    await cerrarTurno(turno.id_turno).catch(() => {
      // El turno se cierra en el servidor de todos modos si la petición llegó;
      // un fallo de red no debe dejar la caja bloqueada en esta pantalla (Principio II).
    });
    // Hallazgo #2: no se vuelve directo a la apertura de turno — primero el arqueo de ESE turno.
    setTurnoPorArquear(cerrado);
    setTurno(null);
  }

  return (
    <div className={estilos.aplicacion}>
      <nav className={estilos.navegacion} data-noprint>
        {/* La Regla de la Marca Persistente (v1.7.0): la herramienta (wordmark Rasero) al
            extremo izquierdo; el "dónde estoy / quién soy" (ícono del comercio + sucursal +
            caja + operador + rol) agrupado al extremo derecho. Extremos opuestos, no compiten. */}
        <span className={estilos.marca}>
          <img
            className={estilos.marcaSistema}
            src={marcaSistema}
            alt="Rasero"
            width={106}
            height={26}
          />
        </span>
        <button
          className={`${estilos.venta} ${
            pantalla === "venta" ? estilos.pestanaActiva : estilos.pestanaInactiva
          }`}
          onClick={() => setPantalla("venta")}
        >
          Venta
        </button>
        {/* Arqueo: tarea diaria de cajero, junto a Venta (antes vivía en "Caja y seguridad"). */}
        <button
          className={pantalla === "arqueo" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("arqueo")}
        >
          Arqueo
        </button>

        <span className={estilos.separador} aria-hidden="true" />

        {/* "Ocultar, no deshabilitar" (Principio VI, enmienda v2.5.0): cada opción se filtra por
            el rol mínimo; un grupo sin opciones visibles no se renderiza. */}
        {GRUPOS.map((g) => {
          const visibles = g.opciones.filter((o) => autoriz.puedeVer(o.rol));
          if (visibles.length === 0) return null;
          return (
            <GrupoNav
              key={g.etiqueta}
              etiqueta={g.etiqueta}
              opciones={visibles}
              pantalla={pantalla}
              onElegir={setPantalla}
            />
          );
        })}

        {/* "Ocultar, no deshabilitar" (Principio VI): Administración es admin EN EXCLUSIVA
            (constitución v2.5.0 tabla de autorización de pantalla + v2.7.1); un cajero o un
            encargado no ven el ítem en absoluto. */}
        {autoriz.esAdmin() && (
          <>
            <span className={estilos.separador} aria-hidden="true" />
            <button
              className={
                pantalla === "administracion" ? estilos.pestanaActiva : estilos.pestanaInactiva
              }
              onClick={() => setPantalla("administracion")}
            >
              Administración
            </button>
          </>
        )}

        {/* Bloque de contexto de sesión, al extremo derecho del nav. */}
        <div className={estilos.contexto}>
          <img
            className={estilos.contextoIcono}
            src={ICONO_COMERCIO}
            alt=""
            width={24}
            height={24}
          />
          <span className={estilos.contextoGrupo}>
            <span className={estilos.contextoPrincipal}>
              {nombreSucursal || `Sucursal ${turno.id_sucursal}`}
            </span>
            <span className={estilos.contextoSecundario}>{turno.caja}</span>
          </span>
          {nombreOperador && (
            <>
              <span className={estilos.contextoDivisor} aria-hidden="true" />
              <span className={estilos.contextoGrupo}>
                <span className={estilos.contextoPrincipal}>{nombreOperador}</span>
                {rol && <span className={estilos.contextoRol}>{rol}</span>}
              </span>
            </>
          )}
        </div>
      </nav>
      <div className={estilos.contenido}>
        {pantalla === "venta" && (
          <Venta turno={turno} onCerrarTurno={manejarCierre} rol={rol} />
        )}
        {pantalla === "conteo" && <ConteoFisico idSucursal={turno.id_sucursal} />}
        {pantalla === "entradas" && <EntradaInventario idSucursal={turno.id_sucursal} />}
        {pantalla === "traspasos" && <DespachoTraspaso idSucursal={turno.id_sucursal} />}
        {pantalla === "capital" && <CapitalInmovilizado idSucursal={turno.id_sucursal} />}
        {pantalla === "competencia" && (
          <Competencia idSucursal={turno.id_sucursal} idTurno={turno.id_turno} />
        )}
        {pantalla === "clientes" && <Clientes />}
        {pantalla === "precios" && <Precios idSucursal={turno.id_sucursal} />}
        {pantalla === "pronostico" && <Pronostico idSucursal={turno.id_sucursal} />}
        {pantalla === "promociones" && <Promociones idSucursal={turno.id_sucursal} />}
        {pantalla === "arqueo" && <Arqueo turno={turno} />}
        {pantalla === "cajafraude" && (
          <CajaFraude idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
        {pantalla === "terminales" && <TerminalesPago idSucursal={turno.id_sucursal} />}
        {pantalla === "pagos" && (
          <Pagos idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
        {pantalla === "reportes" && autoriz.esEncargadoOMas() && <Reportes />}
        {pantalla === "administracion" && autoriz.esAdmin() && (
          <Administracion rol={rol} />
        )}
      </div>
    </div>
  );
}
