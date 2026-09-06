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
import marcaSistema from "./activos/marca/rasero-wordmark-512w.png";
import estilos from "./App.module.css";

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
  const [turno, setTurno] = useState<Turno | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla>("venta");
  const [nombreOperador, setNombreOperador] = useState<string>("");
  const [esEncargado, setEsEncargado] = useState(false);

  useEffect(() => {
    if (!turno) return;
    listarOperadores()
      .then((lista) => {
        const op = lista.find((o) => o.id_operador === turno.id_operador);
        setNombreOperador(op?.nombre ?? `Operador ${turno.id_operador}`);
        setEsEncargado(Boolean(op?.es_encargado));
      })
      .catch(() => setNombreOperador(`Operador ${turno.id_operador}`));
  }, [turno]);

  if (!turno) {
    return <AperturaTurno onTurnoAbierto={setTurno} />;
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
        <img
          className={estilos.marcaSistema}
          src={marcaSistema}
          alt="Rasero"
          width={106}
          height={26}
        />
        <button
          className={pantalla === "venta" ? estilos.pestanaActiva : estilos.pestanaInactiva}
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

        <span className={estilos.separador} aria-hidden="true" />

        <button
          className={
            pantalla === "administracion" ? estilos.pestanaActiva : estilos.pestanaInactiva
          }
          onClick={() => setPantalla("administracion")}
        >
          Administración
        </button>

        {nombreOperador && (
          <span className={estilos.operador}>
            {nombreOperador}
            {esEncargado ? " · encargado" : ""}
          </span>
        )}
      </nav>
      <div className={estilos.contenido}>
        {pantalla === "venta" && (
          <Venta turno={turno} onCerrarTurno={manejarCierre} esEncargado={esEncargado} />
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
        {pantalla === "terminales" && (
          <TerminalesPago idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
        {pantalla === "pagos" && (
          <Pagos idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
        {pantalla === "administracion" && (
          <Administracion idOperador={turno.id_operador} esEncargado={esEncargado} />
        )}
      </div>
    </div>
  );
}
