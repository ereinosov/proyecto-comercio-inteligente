import { useState } from "react";
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
import { cerrarTurno, type Turno } from "./servicios/turnos";
import marcaSistema from "./activos/marca/rasero-wordmark-512w.png";
import marcaNegocio from "./activos/marca/despensa-icon-verde-512.png";
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
  | "pagos";

export function App() {
  const [turno, setTurno] = useState<Turno | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla>("venta");

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
        <button
          className={pantalla === "conteo" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("conteo")}
        >
          Conteo
        </button>
        <button
          className={pantalla === "entradas" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("entradas")}
        >
          Entradas
        </button>
        <button
          className={pantalla === "traspasos" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("traspasos")}
        >
          Traspasos
        </button>
        <button
          className={pantalla === "capital" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("capital")}
        >
          Capital
        </button>
        <button
          className={pantalla === "competencia" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("competencia")}
        >
          Competencia
        </button>
        <button
          className={pantalla === "clientes" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("clientes")}
        >
          Clientes
        </button>
        <button
          className={pantalla === "precios" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("precios")}
        >
          Precios
        </button>
        <button
          className={pantalla === "pronostico" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("pronostico")}
        >
          Pronóstico
        </button>
        <button
          className={pantalla === "promociones" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("promociones")}
        >
          Promociones
        </button>
        <button
          className={pantalla === "arqueo" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("arqueo")}
        >
          Arqueo
        </button>
        <button
          className={pantalla === "cajafraude" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("cajafraude")}
        >
          Caja y fraude
        </button>
        <button
          className={pantalla === "terminales" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("terminales")}
        >
          Terminales
        </button>
        <button
          className={pantalla === "pagos" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("pagos")}
        >
          Pagos
        </button>
        <img
          className={estilos.marcaNegocio}
          src={marcaNegocio}
          alt="Despensa Los Ríos"
          title="Datos de: Despensa Los Ríos"
          width={30}
          height={30}
        />
      </nav>
      <div className={estilos.contenido}>
        {pantalla === "venta" && <Venta turno={turno} onCerrarTurno={manejarCierre} />}
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
        {pantalla === "arqueo" && <Arqueo idSucursal={turno.id_sucursal} />}
        {pantalla === "cajafraude" && <CajaFraude idSucursal={turno.id_sucursal} />}
        {pantalla === "terminales" && (
          <TerminalesPago idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
        {pantalla === "pagos" && (
          <Pagos idSucursal={turno.id_sucursal} idOperador={turno.id_operador} />
        )}
      </div>
    </div>
  );
}
