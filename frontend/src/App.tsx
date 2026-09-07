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
  | "administracion";

// La Regla del Grupo de Navegación (DESIGN.md v1.2.0): "Venta" suelta y siempre visible; el
// resto en cuatro grupos desplegables; "Administración" al final, pantalla propia (no grupo).
const GRUPOS: { etiqueta: string; opciones: { valor: Pantalla; texto: string }[] }[] = [
  {
    etiqueta: "Inventario",
    opciones: [
      { valor: "conteo", texto: "Conteo" },
      { valor: "entradas", texto: "Entradas" },
      { valor: "traspasos", texto: "Traspasos" },
      { valor: "capital", texto: "Capital" },
    ],
  },
  {
    etiqueta: "Precios y demanda",
    opciones: [
      { valor: "precios", texto: "Precios" },
      { valor: "competencia", texto: "Competencia" },
      { valor: "pronostico", texto: "Pronóstico" },
    ],
  },
  {
    etiqueta: "Clientes y promos",
    opciones: [
      { valor: "clientes", texto: "Clientes" },
      { valor: "promociones", texto: "Promociones" },
    ],
  },
  {
    etiqueta: "Caja y seguridad",
    opciones: [
      { valor: "arqueo", texto: "Arqueo" },
      { valor: "cajafraude", texto: "Caja y fraude" },
      { valor: "terminales", texto: "Terminales" },
      { valor: "pagos", texto: "Pagos" },
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
  opciones: { valor: Pantalla; texto: string }[];
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
    return <AperturaTurno onTurnoAbierto={setTurno} avisoSesion={avisoSesion} />;
  }

  async function manejarCierre() {
    if (!turno) return;
    await cerrarTurno(turno.id_turno).catch(() => {
      // El turno se cierra en el servidor de todos modos si la petición llegó;
      // un fallo de red no debe dejar la caja bloqueada en esta pantalla (Principio II).
    });
    setTurno(null);
  }

  return (
    <div className={estilos.aplicacion}>
      <nav className={estilos.navegacion}>
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

        <span className={estilos.separador} aria-hidden="true" />

        {GRUPOS.map((g) => (
          <GrupoNav
            key={g.etiqueta}
            etiqueta={g.etiqueta}
            opciones={g.opciones}
            pantalla={pantalla}
            onElegir={setPantalla}
          />
        ))}

        {/* "Ocultar, no deshabilitar" (Principio VI): Administración sólo se ofrece a
            encargado o admin; un cajero no ve el ítem en absoluto. */}
        {autoriz.esEncargadoOMas() && (
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
        {pantalla === "administracion" && autoriz.esEncargadoOMas() && (
          <Administracion rol={rol} />
        )}
      </div>
    </div>
  );
}
