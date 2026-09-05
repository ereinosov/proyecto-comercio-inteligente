import { useState } from "react";
import { AperturaTurno } from "./componentes/AperturaTurno";
import { Venta } from "./pantallas/Venta";
import { Clientes } from "./pantallas/Clientes";
import { Precios } from "./pantallas/Precios";
import { Pronostico } from "./pantallas/Pronostico";
import { cerrarTurno, type Turno } from "./servicios/turnos";
import estilos from "./App.module.css";

type Pantalla = "venta" | "clientes" | "precios" | "pronostico";

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
        <button
          className={pantalla === "venta" ? estilos.pestanaActiva : estilos.pestanaInactiva}
          onClick={() => setPantalla("venta")}
        >
          Venta
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
      </nav>
      <div className={estilos.contenido}>
        {pantalla === "venta" && <Venta turno={turno} onCerrarTurno={manejarCierre} />}
        {pantalla === "clientes" && <Clientes />}
        {pantalla === "precios" && <Precios idSucursal={turno.id_sucursal} />}
        {pantalla === "pronostico" && <Pronostico idSucursal={turno.id_sucursal} />}
      </div>
    </div>
  );
}
